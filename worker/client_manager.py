from __future__ import annotations
from typing import Dict
import asyncio
import httpx

from telethon import TelegramClient, events
from telethon.errors import AuthKeyUnregisteredError, SessionRevokedError
from telethon.sessions import StringSession

from worker.config import API_ID, API_HASH, BACKEND_URL
from worker.trigger_engine import handle_incoming_message

_clients: Dict[int, TelegramClient] = {}


async def monitor_session_revoked(telegram_id: int, client: TelegramClient) -> None:
    """
    Background guard: detects REAL Telegram-side revocation.
    """
    while True:
        try:
            await client.get_me()
            await asyncio.sleep(10)

        except (AuthKeyUnregisteredError, SessionRevokedError):
            async with httpx.AsyncClient(timeout=5) as http:
                await http.post(
                    f"{BACKEND_URL}/api/users/session-revoked/{telegram_id}"
                )
            await drop_client(telegram_id)
            return

        except Exception:
            await asyncio.sleep(10)


async def drop_client(telegram_id: int) -> None:
    client = _clients.pop(telegram_id, None)
    if client:
        try:
            await client.disconnect()
        except Exception:
            pass


async def get_or_create_client(
    telegram_id: int,
    session_string: str,
    worker_active: bool = True,
) -> TelegramClient:
    """
    IMPORTANT RULE:
    - Session mismatch ≠ revocation
    - Session mismatch = user re-logged in → rotate client cleanly
    """

    # ⏸ Worker paused → hard disconnect & do not connect
    if not worker_active:
        await drop_client(telegram_id)
        return None
    # 1️⃣ Existing cached client
    if telegram_id in _clients:
        client = _clients[telegram_id]

        # 🔁 Session rotated (user re-login) → recreate client
        if client.session.save() != session_string:
            await drop_client(telegram_id)
        else:
            if not client.is_connected():
                await client.connect()

            if not await client.is_user_authorized():
                await drop_client(telegram_id)
                raise SessionRevokedError(request=None)

            return client

    # 2️⃣ Create fresh client
    client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        await drop_client(telegram_id)
        raise AuthKeyUnregisteredError(request=None)

    @client.on(events.NewMessage(incoming=True))
    async def _on_new_message(event: events.NewMessage.Event):
        await handle_incoming_message(client, event, telegram_id)

    _clients[telegram_id] = client
    asyncio.create_task(monitor_session_revoked(telegram_id, client))
    return client