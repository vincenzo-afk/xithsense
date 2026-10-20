"""
Live intelligence WebSocket: /api/v1/live/{match_id}?token=<jwt>  (Premium).
Backed by the CricketData live feed (integrations/live_feed.py).
"""
from __future__ import annotations

import asyncio
import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from backend.database import AsyncSessionLocal
from backend.dependencies import has_premium_access, user_from_token
from integrations.live_feed import live_manager

router = APIRouter(tags=["live"])

MAX_CONNECTIONS_PER_USER = 5
_connections: dict[str, int] = defaultdict(int)


@router.websocket("/api/v1/live/{match_id}")
async def live_feed(websocket: WebSocket, match_id: str):
    token = websocket.query_params.get("token", "")
    # Accept first so browsers receive our 44xx close codes (a pre-accept close surfaces as 1006)
    await websocket.accept()
    async with AsyncSessionLocal() as db:
        try:
            user = await user_from_token(token, db)
        except HTTPException as e:
            await websocket.close(code=4401, reason=e.detail.get("code", "UNAUTHORIZED"))
            return
        if not await has_premium_access(db, user):
            await websocket.send_json({"event": "error", "code": "PREMIUM_REQUIRED",
                                       "message": "Live intelligence requires Premium"})
            await websocket.close(code=4402, reason="PREMIUM_REQUIRED")
            return
    uid = str(user.id)
    if _connections[uid] >= MAX_CONNECTIONS_PER_USER:
        await websocket.close(code=4429, reason="TOO_MANY_CONNECTIONS")
        return

    lm = await live_manager.get(match_id)
    if lm is None:
        await websocket.send_json({"event": "error", "code": "MATCH_NOT_LIVE", "message": "This match is not live"})
        await websocket.close(code=4404)
        return

    _connections[uid] += 1
    queue = lm.subscribe()
    await websocket.send_json({"event": "connection_established", "match_id": match_id,
                               "connection_id": str(uuid.uuid4()), "match_status": lm.state.get("status"),
                               "current_over": lm.state.get("current_over", "0.0"),
                               "timestamp": datetime.now(timezone.utc).isoformat()})
    await websocket.send_json(lm.snapshot())

    async def pump():
        while True:
            msg = await queue.get()
            await websocket.send_text(json.dumps(msg, default=str))
            if msg.get("event") == "match_ended":
                await asyncio.sleep(30)
                await websocket.close(code=1000)
                return

    async def listen():
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            action = msg.get("action")
            if action == "ping":
                await websocket.send_json({"action": "pong", "timestamp": datetime.now(timezone.utc).isoformat()})
            elif action == "request_state":
                await websocket.send_json(lm.snapshot())

    tasks = [asyncio.create_task(pump()), asyncio.create_task(listen())]
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    except WebSocketDisconnect:
        pass
    finally:
        for t in tasks:
            t.cancel()
        lm.unsubscribe(queue)
        _connections[uid] = max(0, _connections[uid] - 1)
