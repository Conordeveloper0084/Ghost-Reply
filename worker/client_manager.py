from __future__ import annotations
from typing import Dict

from telethon import TelegramClient, events
from telethon.errors import AuthKeyUnregisteredError, SessionRevokedError
from telethon.sessions import StringSession

from worker.config import API_ID, API_HASH
from worker.trigger_engine import handle_incoming_message

_clients: Dict[int, TelegramClient] = {}


async def drop_client(telegram_id: int) -> None:
    client = _clients.pop(telegram_id, None)
    if client:
        try:
            await client.disconnect()
        except Exception:
            pass


async def get_or_create_client(telegram_id: int, session_string: str) -> TelegramClient:
    if telegram_id in _clients:
        client = _clients[telegram_id]

        # 🔎 Session string mismatch → drop old client
        if client.session.save() != session_string:
            await drop_client(telegram_id)
            raise SessionRevokedError(request=None)

        if not client.is_connected():
            await client.connect()

        if not await client.is_user_authorized():
            await drop_client(telegram_id)
            raise SessionRevokedError(request=None)

        return client

    # 🆕 Create new client
    client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        await drop_client(telegram_id)
        raise AuthKeyUnregisteredError(request=None)

    @client.on(events.NewMessage(incoming=True))
    async def _on_new_message(event: events.NewMessage.Event):
        await handle_incoming_message(client, event, telegram_id)

    _clients[telegram_id] = client
    return client