# worker/trigger_engine.py

import httpx
import re
import asyncio
import logging
from telethon import events
from telethon.errors import AuthKeyUnregisteredError, SessionRevokedError

from worker.config import BACKEND_URL
from worker.utils import normalize_text

logger = logging.getLogger(__name__)


async def handle_incoming_message(
    client,
    event: events.NewMessage.Event,
    telegram_id: int,
):
    # ❌ Ignore group, supergroup, and channel messages (private chats only for now)
    if event.is_group or event.is_channel:
        return

    # ❌ Ignore messages sent by the account itself (double safety)
    if event.out or (event.sender_id == telegram_id):
        return

    if not event.message or not event.message.text:
        return

    text = normalize_text(event.message.text)
    logger.debug(f"📩 Incoming message for {telegram_id}: {text}")

    # 🔁 triggerlarni backenddan olish
    async with httpx.AsyncClient(timeout=10) as http:
        try:
            res = await http.get(
                f"{BACKEND_URL}/api/triggers/",
                params={"user_telegram_id": telegram_id},
            )
            res.raise_for_status()
            triggers = res.json()
        except Exception as e:
            logger.error(f"❌ Failed to load triggers for {telegram_id}: {e}")
            return

    if not triggers:
        return

    for t in triggers:
        trigger_text = t.get("trigger_text")
        reply_text = t.get("reply_text")

        if not trigger_text or not reply_text:
            continue

        pattern = rf"\b{re.escape(trigger_text)}\b"
        if not re.search(pattern, text):
            continue

        try:
            logger.info(f"🎯 Trigger matched for {telegram_id}: {trigger_text}")
            await asyncio.sleep(1.5)
            await event.reply(reply_text)
            logger.info(f"✅ Reply sent for {telegram_id}")

        # 🔥 🔥 🔥 MANA SIZ SO‘RAGAN KOD JOYI
        except (AuthKeyUnregisteredError, SessionRevokedError):
            logger.warning(
                f"🔌 Session revoked while replying for {telegram_id}"
            )

            async with httpx.AsyncClient(timeout=5) as http:
                await http.post(
                    f"{BACKEND_URL}/api/users/session-revoked/{telegram_id}"
                )
                await http.post(
                    f"{BACKEND_URL}/api/users/worker-disconnected/{telegram_id}"
                )

            try:
                await client.disconnect()
            except Exception:
                pass

            return  # ⛔ shu user uchun trigger ishlashi to‘xtaydi

        except Exception as e:
            logger.error(
                f"⚠️ Failed to send reply for {telegram_id}: {repr(e)}"
            )

        break