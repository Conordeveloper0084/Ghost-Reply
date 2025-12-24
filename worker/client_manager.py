from telethon import TelegramClient, events
from telethon.sessions import StringSession
from worker.config import API_ID, API_HASH
from worker.trigger_engine import handle_incoming_message
from typing import Dict

_clients: Dict[int, TelegramClient] = {}


async def get_or_create_client(telegram_id: int, session_string: str) -> TelegramClient:
    if telegram_id in _clients:
        client = _clients[telegram_id]
        if not client.is_connected():
            await client.connect()
        return client

    client = TelegramClient(
        StringSession(session_string),
        API_ID,
        API_HASH,
    )

    await client.connect()

    # 🔥 TO‘G‘RI EVENT HANDLER
    @client.on(events.NewMessage())
    async def _(event):
        await handle_incoming_message(client, event, telegram_id)

    _clients[telegram_id] = client
    return client