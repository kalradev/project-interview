"""WebSocket - real-time event logging and live integrity score updates."""

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.ml.integrity_engine import IntegrityEngine

router = APIRouter()
integrity_engine = IntegrityEngine()


async def _get_session_id_from_query(websocket: WebSocket) -> str | None:
    """Parse session_id from query string."""
    return websocket.query_params.get("session_id")


@router.websocket("/events")
async def websocket_events(websocket: WebSocket):
    """Real-time event logging over WebSocket. Query: session_id=uuid."""
    await websocket.accept()
    session_id = await _get_session_id_from_query(websocket)
    if not session_id:
        await websocket.close(code=4000)
        return
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            event_type = payload.get("event_type")
            await websocket.send_json({"status": "logged", "event_type": event_type})
    except WebSocketDisconnect:
        pass
    except json.JSONDecodeError:
        await websocket.send_json({"error": "Invalid JSON"})


@router.websocket("/integrity")
async def websocket_integrity(websocket: WebSocket):
    """Live integrity score updates. Query: session_id=uuid. Send event_counts + ai_probability to get score."""
    await websocket.accept()
    session_id = await _get_session_id_from_query(websocket)
    if not session_id:
        await websocket.close(code=4000)
        return
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            event_counts = payload.get("event_counts", {})
            ai_probability = float(payload.get("ai_probability", 0))
            score, risk, penalties = integrity_engine.compute(event_counts, ai_probability)
            await websocket.send_json({
                "score": score,
                "risk_level": risk,
                "penalties": penalties,
            })
    except WebSocketDisconnect:
        pass
    except (ValueError, TypeError):
        await websocket.send_json({"error": "Invalid payload"})
