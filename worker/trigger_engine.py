# worker/trigger_engine.py

import httpx
import re
import asyncio
import logging
import random
from telethon import events
from telethon.errors import AuthKeyUnregisteredError, SessionRevokedError

from worker.config import BACKEND_URL



logger = logging.getLogger(__name__)

# NOTE: We must NOT remove spaces for trigger matching.
# Using normalize_text() here can break word-boundary regex (e.g. "hi bro" -> "hibro").
def _prep_text(s: str) -> str:
    # lower + trim + collapse multiple spaces, but keep word boundaries
    s = s.lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s

def _tokenize(s: str) -> list[str]:
    # split text into words, ignoring punctuation
    return re.findall(r"[a-zA-Z0-9_]+", s.lower())


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

    raw_text = event.message.text
    text = _prep_text(raw_text)
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

        trigger_norm = _prep_text(trigger_text)
        trigger_tokens = _tokenize(trigger_norm)
        message_tokens = _tokenize(text)

        # 🔒 Trigger must be at the START of the message
        if len(message_tokens) < len(trigger_tokens):
            continue

        if message_tokens[:len(trigger_tokens)] != trigger_tokens:
            continue

        try:
            logger.info(f"🎯 Trigger matched for {telegram_id}: {trigger_text}")

            # 🧠 Human-like delay to avoid spam / freeze (2–4 seconds)
            delay = random.uniform(5, 10)
            await client.send_read_acknowledge(event.chat_id)
            await client.send_typing(event.chat_id)
            await asyncio.sleep(delay)

            await event.reply(reply_text)
            logger.info(f"✅ Reply sent for {telegram_id} after {delay:.2f}s delay")

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