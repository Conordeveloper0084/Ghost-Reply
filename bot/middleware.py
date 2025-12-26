# bot/middleware.py
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
import httpx
from .config import BACKEND_URL

# Callbacks that are ALWAYS allowed (even without registration)
ALLOWED_CALLBACKS = {
    "start_instructions",
    "start_privacy",
    "start_link_account",
    "check_account",
    "back_to_start",
    "sms_help",
    "login_help",
}

# Text commands always allowed
ALLOWED_TEXT_PREFIXES = (
    "/start",
    "+",        # phone number input
)

# FSM states related to Telegram login
LOGIN_STATES = {
    "RegistrationState:waiting_for_phone",
    "RegistrationState:waiting_for_sms_code",
    "RegistrationState:waiting_for_2fa",
}

def reconnect_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔌 Akkountni qayta ulash",
                    callback_data="start_link_account"
                )
            ]
        ]
    )


class RegistrationMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        state: FSMContext | None = data.get("state")
        user_id = None

        # ===================== MESSAGE =====================
        if isinstance(event, Message):
            user_id = event.from_user.id

            # Always allow /start
            if event.text and event.text.startswith("/start"):
                return await handler(event, data)

            # Allow during login FSM states (VERY IMPORTANT)
            if state:
                current_state = await state.get_state()
                if current_state in LOGIN_STATES:
                    return await handler(event, data)

            # Allow phone numbers
            if event.text and event.text.strip().startswith("+"):
                return await handler(event, data)

            # Allow numeric SMS / 2FA codes
            if event.text and event.text.strip().isdigit():
                return await handler(event, data)

            # Allow contact sharing
            if event.contact:
                return await handler(event, data)

        # ===================== CALLBACK =====================
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id

            # 🔥 ALWAYS allow registration / start related callbacks
            if event.data in ALLOWED_CALLBACKS:
                return await handler(event, data)

            # 🔥 Any other callback will be checked later

        # ===================== BACKEND CHECK =====================
        # 🔥 Do NOT block callbacks here — callbacks already passed allow-list
        if isinstance(event, CallbackQuery):
            return await handler(event, data)
        if not user_id:
            return await handler(event, data)

        async with httpx.AsyncClient() as client:
            try:
                res = await client.get(f"{BACKEND_URL}/api/users/{user_id}")
                info = res.json()
            except Exception as e:
                print("⚠️ Backend unreachable:", e)
                return await handler(event, data)

        is_registered = info.get("is_registered", False)
        worker_active = info.get("worker_active", False)

        # ===================== NOT REGISTERED =====================
        if not is_registered:
            if isinstance(event, CallbackQuery):
                await event.answer()
                await event.message.answer(
                    "🔐 Avval Telegram akkauntingizni ulang.\n\n"
                    "👇 Boshlash uchun:\n"
                    "🔌 Akkount ulash tugmasini bosing.",
                    reply_markup=reconnect_keyboard()
                )
                return
            if isinstance(event, Message):
                await event.answer(
                    "🔐 Avval Telegram akkauntingizni ulang.\n\n"
                    "👇 Boshlash uchun:\n"
                    "🔌 Akkount ulash tugmasini bosing.",
                    reply_markup=reconnect_keyboard()
                )
                return

        # ===================== WORKER DISCONNECTED =====================
        if is_registered and not worker_active:
            if isinstance(event, CallbackQuery):
                await event.answer()
                await event.message.answer(
                    "⚠️ Telegram akkauntingiz bilan aloqa uzilgan.\n\n"
                    "Sababi:\n"
                    "• Siz Telegram → Privacy → Devices bo‘limidan GhostReply qurilmasini o‘chirgansiz\n\n"
                    "👉 Yechim:\n"
                    "Akkountni qayta ulang.",
                    reply_markup=reconnect_keyboard()
                )
                return
            if isinstance(event, Message):
                await event.answer(
                    "⚠️ Telegram akkauntingiz bilan aloqa uzilgan.\n\n"
                    "Sababi:\n"
                    "• Siz Telegram → Privacy → Devices bo‘limidan GhostReply qurilmasini o‘chirgansiz\n\n"
                    "👉 Yechim:\n"
                    "Akkountni qayta ulang.",
                    reply_markup=reconnect_keyboard()
                )
                return

        # ===================== ALLOW =====================
        return await handler(event, data)