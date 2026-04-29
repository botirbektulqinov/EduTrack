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
from uuid import UUID

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.rate_limit import rate_limiter
from app.models.assessment import Assessment
from app.models.assessment_attempt import AssessmentAttempt
from app.models.student_answer import StudentAnswer
from app.services.attempt_service import (
    ANSWER_MUTABLE_FIELDS,
    sync_attempt_timer,
    utc_now,
    validate_questions_belong_to_attempt,
)
from app.services.proctoring_service import ProctoringService

router = APIRouter()


# Active connections store (in production, use Redis pub/sub)
active_connections: dict[str, WebSocket] = {}


def _coerce_uuid(value: str) -> UUID | None:
    try:
        return UUID(value)
    except (TypeError, ValueError):
        return None


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
    parsed_attempt_id = _coerce_uuid(attempt_id)
    parsed_token = _coerce_uuid(token)
    if not parsed_attempt_id or not parsed_token:
        await websocket.send_json({"type": "ERROR", "message": "Invalid attempt token."})
        await websocket.close(code=1008)
        return

    async with async_session_factory() as db:
        try:
            # Validate attempt + server token
            result = await db.execute(
                select(AssessmentAttempt).where(
                    AssessmentAttempt.id == parsed_attempt_id,
                    AssessmentAttempt.server_token == parsed_token,
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
                "time_remaining": await sync_attempt_timer(db, attempt),
            })
            await db.commit()

            # Message loop
            while True:
                raw = await websocket.receive_text()
                data = json.loads(raw)
                msg_type = data.get("type")

                if msg_type == "HEARTBEAT":
                    server_remaining = await sync_attempt_timer(db, attempt) or 0

                    if server_remaining <= 0:
                        # Time expired → force submit
                        attempt.status = "submitted"
                        attempt.submitted_at = utc_now()
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
                    question_uuid = _coerce_uuid(question_id)

                    if question_uuid and attempt.status == "in_progress":
                        remaining = await sync_attempt_timer(db, attempt)
                        if remaining == 0:
                            await db.commit()
                            await websocket.send_json({
                                "type": "ERROR",
                                "message": "The assessment time limit has expired.",
                            })
                            continue
                        await validate_questions_belong_to_attempt(db, attempt, {question_uuid})
                        existing = await db.execute(
                            select(StudentAnswer).where(
                                StudentAnswer.attempt_id == attempt.id,
                                StudentAnswer.question_id == question_uuid,
                            )
                        )
                        answer = existing.scalar_one_or_none()

                        safe_answer_data = {
                            key: value
                            for key, value in answer_data.items()
                            if key in ANSWER_MUTABLE_FIELDS
                        }
                        if answer:
                            for key, value in safe_answer_data.items():
                                setattr(answer, key, value)
                            answer.saved_at = utc_now()
                        else:
                            answer = StudentAnswer(
                                attempt_id=attempt.id,
                                question_id=question_uuid,
                                **safe_answer_data,
                            )
                            db.add(answer)

                        await db.commit()
                        await websocket.send_json({
                            "type": "ANSWER_SAVED",
                            "question_id": question_id,
                        })
                    else:
                        await websocket.send_json({
                            "type": "ERROR",
                            "message": "Invalid question or inactive attempt.",
                        })

                elif msg_type == "VIOLATION":
                    # Proctoring violation detected on client
                    violation_type = data.get("violation_type", "UNKNOWN")
                    time_remaining = data.get("time_remaining")
                    try:
                        await rate_limiter.check(
                            key=f"ws-violation:attempt:{attempt.id}",
                            limit=settings.RATE_LIMIT_WS_VIOLATION_PER_MINUTE,
                            window_seconds=60,
                        )
                    except HTTPException:
                        await websocket.send_json({
                            "type": "ERROR",
                            "message": "Too many violation events. Please reconnect if the problem continues.",
                        })
                        continue

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
