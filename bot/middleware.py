# bot/middleware.py
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
import httpx
from .config import BACKEND_URL

ALLOWED_CALLBACKS = {
    "start_instructions",
    "start_privacy",
    "start_link_account",
    "confirm_link_account",
    "check_account",
    "back_to_start",
    "sms_help",
    "login_help",
}

PRE_LINK_CALLBACKS = {
    "start_link_account",
    "confirm_link_account",
    "cancel_link_account",
    "check_account",
}

LOGIN_STATES = {
    "RegistrationState:waiting_for_phone",
    "RegistrationState:waiting_for_sms_code",
    "RegistrationState:waiting_for_2fa",
}

MAIN_MENU_TEXTS = {
    "➕ Trigger qo'shish",
    "📄 Triggerlarim",
    "📦 Tariflar",
}

def reconnect_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔌 Akkountni qayta ulash", callback_data="start_link_account")]
        ]
    )

class RegistrationMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        state: FSMContext | None = data.get("state")
        user_id = None

        # ------------- Identify user + allow-lists -------------
        if isinstance(event, Message):
            user_id = event.from_user.id

            # /start always allowed
            if event.text and event.text.startswith("/start"):
                return await handler(event, data)

            # allow during login flow
            if state:
                current_state = await state.get_state()
                if current_state in LOGIN_STATES:
                    return await handler(event, data)

            # allow phone + numeric codes + contact
            if event.text and event.text.strip().startswith("+"):
                return await handler(event, data)
            if event.text and event.text.strip().isdigit():
                return await handler(event, data)
            if event.contact:
                return await handler(event, data)

            # allow main menu texts (still goes through backend check below!)
            # (BUNI bypass qilmaymiz — tekshiruvdan o‘tsin)

        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id

            # allow registration / linking callbacks BEFORE account is connected
            if event.data in PRE_LINK_CALLBACKS:
                return await handler(event, data)

            # allow static info callbacks
            if event.data in ALLOWED_CALLBACKS:
                return await handler(event, data)

        # If no user_id -> allow
        if not user_id:
            return await handler(event, data)

        # ------------- Backend check for BOTH Message and CallbackQuery -------------
        try:
            async with httpx.AsyncClient(timeout=6) as client:
                res = await client.get(f"{BACKEND_URL}/api/users/{user_id}")
                res.raise_for_status()
                info = res.json()
        except Exception as e:
            # Backend down -> allow (yoki xohlasangiz blok qilamiz)
            print("⚠️ Backend unreachable:", e)
            return await handler(event, data)

        is_registered = bool(info.get("is_registered", False))
        worker_active = bool(info.get("worker_active", False))
        session_string = info.get("session_string")  # <- MUHIM

        # --- Session truth: no session_string ALWAYS means disconnected
        if not session_string:
            worker_active = False
            is_registered = False

        if not is_registered:
            txt = (
                "🔐 Telegram akkauntingiz hali ulanmagan yoki uzilgan.\n\n"
                "👇 Davom etish uchun akkountni ulang:"
            )
            if isinstance(event, CallbackQuery):
                await event.answer()
                await event.message.answer(txt, reply_markup=reconnect_keyboard())
            else:
                await event.answer(txt, reply_markup=reconnect_keyboard())
            return

        if is_registered and not worker_active:
            txt = (
                "⚠️ Telegram akkauntingiz bilan aloqa uzilgan.\n\n"
                "Sababi:\n"
                "• Siz Telegram → Privacy → Devices bo‘limidan GhostReply qurilmasini o‘chirgansiz\n\n"
                "👉 Yechim:\n"
                "Akkountni qayta ulang."
            )
            if isinstance(event, CallbackQuery):
                await event.answer()
                await event.message.answer(txt, reply_markup=reconnect_keyboard())
            else:
                await event.answer(txt, reply_markup=reconnect_keyboard())
            return

        return await handler(event, data)