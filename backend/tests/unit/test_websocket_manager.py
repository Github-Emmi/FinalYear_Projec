import pytest
from app.websockets.manager import ConnectionManager
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_connect_registers_websocket():
    manager = ConnectionManager()
    ws = AsyncMock()
    await manager.connect("user1", ws)
    assert "user1" in manager.active
    assert ws in manager.active["user1"]

@pytest.mark.asyncio
async def test_disconnect_removes_websocket():
    manager = ConnectionManager()
    ws = AsyncMock()
    await manager.connect("user1", ws)
    await manager.disconnect("user1", ws)
    assert "user1" not in manager.active

@pytest.mark.asyncio
async def test_send_to_user_when_connected():
    manager = ConnectionManager()
    ws = AsyncMock()
    await manager.connect("user1", ws)
    await manager.send_to_user("user1", {"msg": "hi"})
    ws.send_json.assert_awaited_with({"msg": "hi"})

@pytest.mark.asyncio
async def test_send_to_user_when_not_connected():
    manager = ConnectionManager()
    # Should not raise
    await manager.send_to_user("userX", {"msg": "hi"})

@pytest.mark.asyncio
async def test_broadcast_sends_to_all():
    manager = ConnectionManager()
    ws1 = AsyncMock()
    ws2 = AsyncMock()
    await manager.connect("user1", ws1)
    await manager.connect("user2", ws2)
    await manager.broadcast({"msg": "all"})
    ws1.send_json.assert_awaited_with({"msg": "all"})
    ws2.send_json.assert_awaited_with({"msg": "all"})
