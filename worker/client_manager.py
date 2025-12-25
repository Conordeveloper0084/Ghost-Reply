from __future__ import annotations

from typing import Dict

from telethon import TelegramClient, events
from telethon.errors import AuthKeyUnregisteredError, SessionRevokedError
from telethon.sessions import StringSession

from worker.config import API_ID, API_HASH
from worker.trigger_engine import handle_incoming_message

# telegram_id -> TelegramClient
_clients: Dict[int, TelegramClient] = {}


def drop_client(telegram_id: int) -> None:
    """Remove a cached client (used when session is revoked/invalid)."""
    _clients.pop(telegram_id, None)


async def get_or_create_client(telegram_id: int, session_string: str) -> TelegramClient:
    """Return a connected Telethon client for the given user.

    - Reuses a cached client when possible.
    - Validates authorization (session still alive).
    - Attaches the trigger handler exactly once (on first creation).

    Raises:
        SessionRevokedError / AuthKeyUnregisteredError when session is not authorized.
    """

    # Reuse existing client
    if telegram_id in _clients:
        client = _clients[telegram_id]

        if not client.is_connected():
            await client.connect()

        # If the session got revoked after being cached, surface it
        if not await client.is_user_authorized():
            try:
                await client.disconnect()
            finally:
                drop_client(telegram_id)
            raise SessionRevokedError(request=None)

        return client

    # Create a new client
    client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
    await client.connect()

    # Session validity check (important)
    if not await client.is_user_authorized():
        try:
            await client.disconnect()
        finally:
            drop_client(telegram_id)
        raise AuthKeyUnregisteredError(request=None)

    # Attach trigger handler (incoming messages only)
    @client.on(events.NewMessage(incoming=True))
    async def _on_new_message(event: events.NewMessage.Event):
        await handle_incoming_message(client, event, telegram_id)

    _clients[telegram_id] = client
    return client