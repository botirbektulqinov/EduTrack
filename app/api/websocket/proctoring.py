"""
EduTrack — WebSocket Proctoring Endpoint
Real-time violation tracking, heartbeat, auto-save, timer sync.

WS /ws/attempt/{attempt_id}?token={server_token}

Client → Server events:
  { type: "HEARTBEAT", time_remaining: 1820 }
  { type: "ANSWER_SAVE", question_id: "...", data: {...} }
  { type: "VIOLATION", violation_type: "FULLSCREEN_EXIT", time_remaining: 1820 }

Server → Client events:
  { type: "TIME_UPDATE", time_remaining: 1818 }
  { type: "TIME_PENALTY", deducted: 120, new_remaining: 1700 }
  { type: "WARNING", count: 2, message: "2nd violation: 1 warning remaining" }
  { type: "TERMINATE", reason: "MAX_VIOLATIONS", score: 0 }
  { type: "FORCE_SUBMIT", reason: "TIME_EXPIRED" }
  { type: "ASSESSMENT_DEACTIVATED", message: "Teacher closed this assessment" }
"""

import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.assessment import Assessment
from app.models.assessment_attempt import AssessmentAttempt
from app.models.student_answer import StudentAnswer
from app.services.proctoring_service import ProctoringService

router = APIRouter()


# Active connections store (in production, use Redis pub/sub)
active_connections: dict[str, WebSocket] = {}


@router.websocket("/ws/attempt/{attempt_id}")
async def proctoring_websocket(
    websocket: WebSocket,
    attempt_id: str,
    token: str = Query(...),
):
    """
    WebSocket endpoint for real-time proctoring during an assessment attempt.
    Authenticates via the server_token issued on attempt start.
    """
    await websocket.accept()

    async with async_session_factory() as db:
        try:
            # Validate attempt + server token
            result = await db.execute(
                select(AssessmentAttempt).where(
                    AssessmentAttempt.id == UUID(attempt_id),
                    AssessmentAttempt.server_token == UUID(token),
                )
            )
            attempt = result.scalar_one_or_none()

            if not attempt or attempt.status != "in_progress":
                await websocket.send_json({
                    "type": "ERROR",
                    "message": "Invalid attempt or already completed.",
                })
                await websocket.close()
                return

            # Load assessment for proctoring settings
            assessment_result = await db.execute(
                select(Assessment).where(Assessment.id == attempt.assessment_id)
            )
            assessment = assessment_result.scalar_one()

            # Register connection
            connection_key = str(attempt.id)
            active_connections[connection_key] = websocket

            # Send initial time sync
            await websocket.send_json({
                "type": "TIME_UPDATE",
                "time_remaining": attempt.time_remaining_seconds,
            })

            # Message loop
            while True:
                raw = await websocket.receive_text()
                data = json.loads(raw)
                msg_type = data.get("type")

                if msg_type == "HEARTBEAT":
                    # Client-side heartbeat with time remaining
                    # Server is authoritative; update and reply
                    server_remaining = attempt.time_remaining_seconds or 0

                    if server_remaining <= 0:
                        # Time expired → force submit
                        attempt.status = "submitted"
                        attempt.submitted_at = datetime.now(timezone.utc)
                        await db.commit()

                        await websocket.send_json({
                            "type": "FORCE_SUBMIT",
                            "reason": "TIME_EXPIRED",
                        })
                        break

                    await websocket.send_json({
                        "type": "TIME_UPDATE",
                        "time_remaining": server_remaining,
                    })

                elif msg_type == "ANSWER_SAVE":
                    # Real-time answer save via WebSocket
                    question_id = data.get("question_id")
                    answer_data = data.get("data", {})

                    if question_id:
                        existing = await db.execute(
                            select(StudentAnswer).where(
                                StudentAnswer.attempt_id == attempt.id,
                                StudentAnswer.question_id == UUID(question_id),
                            )
                        )
                        answer = existing.scalar_one_or_none()

                        if answer:
                            for key, value in answer_data.items():
                                if hasattr(answer, key):
                                    setattr(answer, key, value)
                            answer.saved_at = datetime.now(timezone.utc)
                        else:
                            answer = StudentAnswer(
                                attempt_id=attempt.id,
                                question_id=UUID(question_id),
                                **{k: v for k, v in answer_data.items() if hasattr(StudentAnswer, k)},
                            )
                            db.add(answer)

                        await db.commit()
                        await websocket.send_json({
                            "type": "ANSWER_SAVED",
                            "question_id": question_id,
                        })

                elif msg_type == "VIOLATION":
                    # Proctoring violation detected on client
                    violation_type = data.get("violation_type", "UNKNOWN")
                    time_remaining = data.get("time_remaining")

                    result = await ProctoringService.record_violation(
                        db=db,
                        attempt=attempt,
                        assessment=assessment,
                        violation_type=violation_type,
                        time_remaining=time_remaining,
                        browser_info=data.get("browser_info"),
                        ip_address=None,  # Could extract from websocket if needed
                    )
                    await db.commit()

                    if result["action"] == "terminate":
                        await websocket.send_json({
                            "type": "TERMINATE",
                            "reason": "MAX_VIOLATIONS",
                            "score": 0,
                            "violation_count": result["violation_count"],
                        })
                        break
                    else:
                        remaining_warnings = assessment.max_violations - result["violation_count"]
                        await websocket.send_json({
                            "type": "WARNING",
                            "count": result["violation_count"],
                            "max": assessment.max_violations,
                            "message": f"Warning {result['violation_count']}/{assessment.max_violations}: "
                                       f"{remaining_warnings} warning(s) remaining before termination.",
                        })
                        await websocket.send_json({
                            "type": "TIME_PENALTY",
                            "deducted": result["time_deducted_seconds"],
                            "new_remaining": result.get("new_time_remaining", attempt.time_remaining_seconds),
                        })

        except WebSocketDisconnect:
            pass
        except json.JSONDecodeError:
            await websocket.send_json({"type": "ERROR", "message": "Invalid JSON."})
        except Exception as e:
            await websocket.send_json({"type": "ERROR", "message": str(e)})
        finally:
            active_connections.pop(str(attempt_id), None)
            try:
                await websocket.close()
            except Exception:
                pass
