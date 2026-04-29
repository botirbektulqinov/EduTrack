import uuid

import pytest

from tests.integration.factories import create_attempt, seed_core_data

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_websocket_rejects_invalid_attempt_token(ws_client, db_session_factory):
    async with db_session_factory() as db:
        seed = await seed_core_data(db)
        attempt = await create_attempt(
            db,
            assessment_id=seed.assessment.id,
            student_id=seed.student.id,
            status="in_progress",
        )

    with ws_client.websocket_connect(f"/ws/attempt/{attempt.id}?token={uuid.uuid4()}") as websocket:
        message = websocket.receive_json()

    assert message["type"] == "ERROR"
    assert "Invalid attempt" in message["message"]


@pytest.mark.asyncio
async def test_websocket_rejects_malformed_attempt_token(ws_client):
    with ws_client.websocket_connect("/ws/attempt/not-a-uuid?token=also-bad") as websocket:
        message = websocket.receive_json()

    assert message["type"] == "ERROR"
    assert message["message"] == "Invalid attempt token."
