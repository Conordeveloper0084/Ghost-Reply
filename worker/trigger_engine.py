# worker/trigger_engine.py
import httpx
from telethon import events
import re
import asyncio
import logging

from worker.config import BACKEND_URL
from worker.utils import normalize_text

logger = logging.getLogger(__name__)


async def load_triggers(telegram_id: int) -> list[dict]:
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            res = await client.get(
                f"{BACKEND_URL}/api/triggers/",
                params={"user_telegram_id": telegram_id},
            )
            res.raise_for_status()

            triggers = res.json()
            if not isinstance(triggers, list):
                logger.warning(
                    f"⚠️ Invalid trigger response type for user {telegram_id}: {type(triggers)}"
                )
                return []

            logger.info(
                f"🔁 Loaded {len(triggers)} triggers for user {telegram_id}"
            )
            return triggers

        except Exception as e:
            logger.error(
                f"❌ Failed to load triggers for user {telegram_id}: {repr(e)}"
            )
            return []


async def handle_incoming_message(
    client,
    event: events.NewMessage.Event,
    telegram_id: int,
):
    # 🔎 DEBUG: event umuman kelayaptimi?
    try:
        print("📩 EVENT KELDI:", event.message.text if event.message else None)
    except Exception as e:
        print("❌ EVENT PRINT ERROR:", e)

    # Ignore outgoing messages (prevent self-reply loops)
    if event.out:
        return

    if not event.message or not event.message.text:
        return

    text = normalize_text(event.message.text)
    logger.debug(f"📩 Incoming message for {telegram_id}: {text}")

    triggers = await load_triggers(telegram_id)
    if not triggers:
        logger.debug(f"ℹ️ No triggers found for user {telegram_id}")
        return

    for t in triggers:
        trigger_text = t.get("trigger_text")
        reply_text = t.get("reply_text")

        if not trigger_text or not reply_text:
            continue

        pattern = rf"\b{re.escape(trigger_text)}\b"
        if re.search(pattern, text):
            try:
                logger.info(
                    f"🎯 Trigger matched for {telegram_id}: '{trigger_text}'"
                )
                await asyncio.sleep(1.6)
                await event.reply(reply_text)
                logger.info(
                    f"✅ Reply sent for {telegram_id}"
                )
            except Exception as e:
                logger.error(
                    f"⚠️ Failed to send reply for {telegram_id}: {repr(e)}"
                )
            break