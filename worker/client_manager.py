# worker/client_manager.py
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from typing import Dict

from worker.config import API_ID, API_HASH
from worker.trigger_engine import handle_incoming_message

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

    # 🔥 MUHIM QISM — MESSAGE HANDLER
    @client.on(events.NewMessage(incoming=True))
    async def _(event):
        await handle_incoming_message(client, event, telegram_id)

    await client.start()

    _clients[telegram_id] = client
    return client