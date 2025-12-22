# worker/trigger_engine.py
import httpx
from telethon import events
import re
import asyncio

from worker.config import BACKEND_URL
from worker.utils import normalize_text


async def load_triggers(telegram_id: int) -> list[dict]:
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            res = await client.get(
                f"{BACKEND_URL}/api/triggers/",
                params={"user_telegram_id": telegram_id}
            )
            res.raise_for_status()

            triggers = res.json()
            if not isinstance(triggers, list):
                print(f"⚠️ Invalid trigger response for user {telegram_id}")
                return []

            return triggers

        except Exception as e:
            print(f"❌ Failed to load triggers for user {telegram_id}:", e)
            return []


async def handle_incoming_message(
    client,
    event: events.NewMessage.Event,
    telegram_id: int,
):
    if not event.message or not event.message.text:
        return

    text = normalize_text(event.message.text)

    triggers = await load_triggers(telegram_id)
    if not triggers:
        return

    for t in triggers:
        trigger_text = t.get("trigger_text")
        reply_text = t.get("reply_text")

        if not trigger_text or not reply_text:
            continue

        pattern = rf"\b{re.escape(trigger_text)}\b"
        if re.search(pattern, text):
            try:
                await asyncio.sleep(1.6)
                await event.reply(reply_text)
            except Exception as e:
                print(f"⚠️ Failed to send delayed reply for {telegram_id}: {e}")
            break