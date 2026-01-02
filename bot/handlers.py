from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import httpx
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from .config import BACKEND_URL
from .keyboards import (
    main_menu,
    start_menu_kb,
    back_to_start_kb,
    check_account_kb,
    triggers_inline_kb,
    trigger_actions_inline_kb,
    confirm_delete_inline_kb,
    trigger_limit_reached_kb,
    plans_menu_kb,
)

router = Router()

# ============================
#     FSM STATE MODELS
# ============================

class AddTriggerState(StatesGroup):
    waiting_for_trigger = State()
    waiting_for_reply = State()

class EditTriggerState(StatesGroup):
    waiting_for_trigger = State()
    waiting_for_reply = State()



async def ensure_account_connected(telegram_id: int, message_or_callback):
    async with httpx.AsyncClient(timeout=5) as client:
        res = await client.get(f"{BACKEND_URL}/api/users/{telegram_id}")

    if res.status_code == 403:
        await message_or_callback.answer(
            "🔌 <b>Akkountingiz uzilgan</b>\n\n"
            "Telegram qurilmalar bo‘limidan GhostReply sessiyasi o‘chirilgan.\n"
            "Iltimos, akkountingizni qayta ulang.",
            parse_mode="HTML",
        )
        return False

    if res.status_code != 200:
        await message_or_callback.answer(
            "❌ Akkount holatini tekshirib bo‘lmadi."
        )
        return False

    user = res.json()

    if not user.get("is_registered") or not user.get("session_string"):
        await message_or_callback.answer(
            "🔐 Akkount ulanmagan yoki uzilgan.\n"
            "Iltimos, qayta ulang.",
            parse_mode="HTML",
        )
        return False

    return True


# ============================
#         /start
# ============================

@router.message(Command("start"))
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()

    telegram_id = message.from_user.id
    full_name = message.from_user.full_name

    async with httpx.AsyncClient(timeout=5) as client:
        register_res = await client.post(
            f"{BACKEND_URL}/api/users/register",
            json={"telegram_id": telegram_id, "name": full_name},
        )

        if register_res.status_code not in (200, 201):
            await message.answer(
                "❌ Server bilan bog‘lanishda xatolik (register)."
            )
            return

        res = await client.get(f"{BACKEND_URL}/api/users/{telegram_id}")

    if res.status_code != 200:
        await message.answer(
            "❌ Server bilan bog‘lanishda xatolik (get user)."
        )
        return

    user = res.json()

    # 📱 If phone number is missing OR backend returned "not provided", request contact FIRST
    phone = user.get("phone")

    if not phone or phone == "not provided":
        from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

        contact_kb = ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(
                        text="📱 Telefon raqamni yuborish",
                        request_contact=True
                    )
                ]
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        )

        await message.answer(
            "📱 <b>Davom etish uchun telefon raqamingizni yuboring</b>\n\n"
            "Bu To'lovlar va Xavfsizlik uchun zarur.",
            parse_mode="HTML",
            reply_markup=contact_kb,
        )
        return

    # ✅ Phone exists → normal flow continues
    if user.get("worker_active") and user.get("is_registered"):
        await message.answer(
            "🎉 <b>Akkountingiz ulangan!</b>\n"
            "Triggerlarni boshqarishingiz mumkin 👇",
            parse_mode="HTML",
            reply_markup=main_menu,
        )
        return

    text = (
        "👻 <b>Ghost Reply</b> ga xush kelibsiz!\n"
        "Men sizga Telegram’dagi xabarlarga avtomatik javob berishga yordam beraman☺️\n\n"
        "👇 Boshlash uchun pastdagi bo‘limlardan birini tanlang:"
    )

    await message.answer(text, parse_mode="HTML", reply_markup=start_menu_kb)


@router.message(F.contact)
async def save_contact(message: Message, state: FSMContext):
    contact = message.contact

    if contact.user_id != message.from_user.id:
        await message.answer("❌ Iltimos, o‘zingizning telefon raqamingizni yuboring")
        return

    telegram_id = message.from_user.id
    phone = contact.phone_number

    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{BACKEND_URL}/api/users/update_phone",
            params={"telegram_id": telegram_id},
            json={"phone": phone},
        )

    if res.status_code != 200:
        await message.answer("❌ Telefonni saqlashda xatolik yuz berdi")
        return

    await state.clear()
    await message.answer(
        "👻 <b>GhostReply</b> ga xush kelibsiz!\n"
        "Men sizga Telegram’dagi xabarlarga avtomatik javob berishga yordam beraman\n\n"
        "👇 Boshlash uchun pastdagi bo‘limlardan birini tanlang:",
        reply_markup=start_menu_kb,
    )

# ============================
#      START → INSTRUCTIONS
# ============================

@router.callback_query(F.data == "start_instructions")
async def show_instructions(callback: CallbackQuery):
    text = (
        "📘 <b>GhostReply qanday ishlaydi?</b>\n\n"
        "1️⃣ Triggerlar yaratiladi, bu sizga kim qanday xabar jo'natganda qanday javob berish uchun kerak.\n"
        "2️⃣ Ghost Reply chatlarda javob berishi uchun sizning akkauntingizga ulanadi.\n"
        "3️⃣ Kelayotgan xabar triggerga mos kelsa — avtomatik javob qaytariladi."
    )
    await callback.message.answer(text, parse_mode="HTML", reply_markup=back_to_start_kb)
    await callback.answer()



@router.callback_query(F.data == "back_to_start")
async def back_to_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("🏠 Asosiy bo'limga qaytdik: \n\n 👇 Boshlash uchun pastdagi bo‘limlardan birini tanlang:", reply_markup=start_menu_kb)
    await callback.answer()


# ============================
#     START → LINK ACCOUNT
# ============================


# ============================ #     START → LINK ACCOUNT # ============================

@router.callback_query(F.data == "start_link_account")
async def start_link_account(callback: CallbackQuery):
    text = (
        "🔐 <b>Xavfsizlik va Maxfiylik</b>\n\n"
        "<b>Ma'lumotlaringiz xavfsizligi bizning ustuvor vazifamiz.</b>\n\n"
        "📌 <b>Ro'yxatdan o'tish</b>\n"
        "Akkountingiz Ghost Reply xizmatiga ulanadi va botning barcha imkoniyatlaridan foydalanish imkonini beradi.\n\n"
        "📂 <b>Saqlanadigan ma'lumotlar</b>\n"
        "Xizmatdan foydalanish uchun quyidagi ma'lumotlar saqlanadi:\n"
        "• Telegram telefon raqamingiz\n"
        "• Ism va familiyangiz\n"
        "• Akkount ulangan vaqti\n"
        "• Username, agar mavjud bo‘lsa\n"
        "• Telegram public ID raqamingiz\n"
        "• Telegram session\n\n"
        "🛡 <b>Xavfsizlik kafolati</b>\n"
        "✓ Ma'lumotlaringiz xavfsiz holda saqlanadi\n"
        "✓ Qo‘shimcha maqsadlarda ishlatilmaydi\n"
        "✓ Uchinchi shaxslarga uzatilmaydi\n"
        "✓ Faqat bot ishlashi va gift/xabarlar uchun foydalaniladi\n\n"
        "🔌 <b>Akkountni uzish</b>\n"
        "Siz istalgan vaqtda Telegram → Qurilmalar bo‘limidan Ghost Reply sessiyasini o‘chirib, akkountni uzishingiz mumkin.\n\n"
        "📱 <b>Qurilma xavfsizligi (Muhim)</b>\n"
        "Bot quyidagi nom bilan ulanadi:\n"
        "<code>arm64, Ghost Reply 1.42.0, Android 24.9.0, khiva, Uzbekistan</code>\n"
        "Telegram sozlamalarida boshqa noma’lum qurilma yo‘qligini tekshiring, boshqa nomalum qurulmalar uchun bot javobgar emas!.\n\n"
        "🔑 <b>Parollar haqida</b>\n"
        "Telegram login kodlari va ikki bosqichli parollar hech qachon saqlanmaydi. "
        "Ular faqat bir martalik tasdiqlash uchun ishlatiladi.\n\n"
        "Davom etish orqali ushbu shartlarga rozilik bildirasiz."
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Roziman, davom etish",
                    callback_data="confirm_link_account"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Bekor qilish",
                    callback_data="cancel_link_account"
                )
            ]
        ]
    )

    await callback.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_link_account")
async def confirm_link_account(callback: CallbackQuery):
    login_url = "https://backend-production-2620.up.railway.app/web-login/start"

    text = (
        "🔐 <b>Akkount ulashga tayyormiz</b>\n\n"
        "Quyidagi havola orqali brauzerda Telegram akkauntingizni ulang 👇\n\n"
        f"🌐 <a href=\"{login_url}\">{login_url}</a>\n\n"
        "Ulash tugagach, pastdagi tugma orqali holatni tekshiring."
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 Akkount holatini tekshirish",
                    callback_data="check_account"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Bekor qilish",
                    callback_data="cancel_link_account"
                )
            ]
        ]
    )

    await callback.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )
    await callback.answer()

@router.callback_query(F.data == "cancel_link_account")
async def cancel_link_account(callback: CallbackQuery):
    await callback.message.answer(
        "❌ Akkount ulash bekor qilindi.\n\n"
        "Agar fikringizni o‘zgartirsangiz, istalgan vaqtda qayta urinishingiz mumkin.",
        reply_markup=start_menu_kb,
    )
    await callback.answer()


@router.callback_query(F.data == "check_account")
async def check_account(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id

    async with httpx.AsyncClient(timeout=5) as client:
        res = await client.get(f"{BACKEND_URL}/api/users/{telegram_id}")

    if res.status_code != 200:
        await callback.message.answer(
            "❌ Akkount holatini tekshirib bo‘lmadi. Keyinroq qayta urinib ko‘ring."
        )
        await callback.answer()
        return

    user = res.json()

    session_string = user.get("session_string")
    is_registered = user.get("is_registered") is True
    worker_active = user.get("worker_active") is True

    # 1️⃣ Session yo‘q → HAQIQIY uzilish
    if session_string is None:
        await callback.message.answer(
            "🔌 <b>Akkountingiz uzilgan</b>\n\n"
            "Telegram qurilmalar bo‘limidan Ghost Reply sessiyasi o‘chirilgan.\n"
            "Iltimos, akkountingizni qayta ulang.",
            parse_mode="HTML",
            reply_markup=start_menu_kb,
        )
        await callback.answer()
        return

    # 2️⃣ Session bor, lekin registration hali to‘liq emas (kamdan-kam holat)
    if not is_registered:
        await callback.message.answer(
            "⏳ <b>Akkount tayyorlanmoqda...</b>\n\n"
            "Maʼlumotlar saqlanmoqda, iltimos bir oz kuting va yana tekshiring.",
            parse_mode="HTML",
            reply_markup=check_account_kb,
        )
        await callback.answer()
        return

    # 3️⃣ Session bor, registration bor, lekin worker hali ulanmagan → NORMAL
    if not worker_active:
        await callback.message.answer(
            "⏳ <b>Akkount ulanmoqda...</b>\n\n"
            "Telegram bilan aloqa tiklandi.\n"
            "Worker ulanmoqda, iltimos 5–10 soniyadan keyin yana tekshirib ko‘ring.",
            parse_mode="HTML",
            reply_markup=check_account_kb,
        )
        await callback.answer()
        return

    # 4️⃣ Hammasi joyida
    await state.clear()
    await callback.message.answer(
        "🎉 <b>Akkountingiz muvaffaqiyatli ulandi!</b>\n\n"
        "Endi triggerlarni yaratishingiz va boshqarishingiz mumkin 👇",
        parse_mode="HTML",
        reply_markup=main_menu,
    )
    await callback.answer()

# ============================
#        YO'RIQNOMA
# ============================

@router.message(F.text == "💡 Yo'riqnoma")
async def show_guide(message: Message, state: FSMContext):
    await state.clear()

    text = (
        "📘 <b>Foydalanish yo‘riqnomasi</b>\n\n"
        "<b>Ghost Reply</b> botidan foydalanish uchun quyidagi qadamlarni bajaring:\n\n"
        "🔹 <b>1-qadam: Akkountni ulash (brauzer orqali)</b>\n"
        "• Ghost Reply bosh sahifasiga o‘ting\n"
        "• Telegram akkauntingizga bog‘langan telefon raqamingizni kiriting\n"
        "• Telegram orqali kelgan tasdiqlash kodini kiriting\n"
        "• Agar ikki bosqichli himoya (2FA) yoqilgan bo‘lsa, parolni kiriting\n\n"
        "🔹 <b>2-qadam: Triggerlarni sozlash (Telegram bot orqali)</b>\n"
        "• Telegram’dagi Ghost Reply botiga qayting\n"
        "• <b>➕ Trigger qo‘shish</b> tugmasini bosing\n"
        "• Trigger so‘zni kiriting (masalan: <code>salom</code>)\n"
        "• Javob matnini kiriting (masalan: <code>Va alaykum assalom!</code>)\n\n"
        "🔹 <b>3-qadam: Botni ishga tushirish</b>\n"
        "• Akkount ulanganidan so‘ng bot avtomatik tarzda faollashadi\n"
        "• Endi Ghost Reply kelayotgan xabarlarni kuzatib boradi\n"
        "• Kimdir trigger so‘zni yozsa — bot avtomatik javob qaytaradi\n\n"
        "⚠️ <b>Muhim eslatma</b>\n"
        "Trigger so‘zlar katta-kichik harflarni farqlamaydi.\n"
        "<code>Salom</code>, <code>salom</code> va <code>SALOM</code> — barchasi bir xil trigger hisoblanadi."
    )

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=main_menu,
    )

# ============================
#        XAVFSIZLIK
# ============================

@router.message(F.text == "🔐 Xavfsizlik")
async def show_security(message: Message, state: FSMContext):
    await state.clear()

    text = (
        "🔐 <b>Xavfsizlik va Maxfiylik</b>\n\n"
        "<b>Ma'lumotlaringiz xavfsizligi bizning ustuvor vazifamiz.</b>\n\n"
        "📌 <b>Ro'yxatdan o'tish</b>\n"
        "Akkountingiz Ghost Reply xizmatiga ulanadi va botning barcha imkoniyatlaridan foydalanish imkonini beradi.\n\n"
        "📂 <b>Saqlanadigan ma'lumotlar</b>\n"
        "Xizmatdan foydalanish uchun quyidagi ma'lumotlar saqlanadi:\n"
        "• Telegram telefon raqamingiz\n"
        "• Ism va familiyangiz\n"
        "• Akkount ulangan vaqti\n"
        "• Username, agar mavjud bo‘lsa\n"
        "• Telegram public ID raqamingiz\n"
        "• Telegram session (faqat ulanish uchun)\n\n"
        "🛡 <b>Xavfsizlik kafolati</b>\n"
        "✓ Ma'lumotlaringiz xavfsiz holda saqlanadi\n"
        "✓ Qo‘shimcha maqsadlarda ishlatilmaydi\n"
        "✓ Uchinchi shaxslarga uzatilmaydi\n"
        "✓ Faqat bot ishlashi va avtomatik javoblar uchun ishlatiladi\n\n"
        "🔌 <b>Akkountni uzish</b>\n"
        "Siz istalgan vaqtda Telegram → Qurilmalar bo‘limidan Ghost Reply sessiyasini o‘chirib, akkountni uzishingiz mumkin.\n\n"
        "📱 <b>Qurilma xavfsizligi (Muhim)</b>\n"
        "Bot faqat quyidagi nom bilan ulanadi:\n"
        "<code>arm64, Ghost Reply 1.42.0, Android 24.9.0, khiva, Uzbekistan</code>\n"
        "Agar Telegram sozlamalarida boshqa noma'lum qurilmalar bo‘lsa — darhol sessiyani o‘chiring.\n\n"
        "🔑 <b>Parollar haqida</b>\n"
        "Telegram login kodlari va 2-bosqichli parollar hech qachon saqlanmaydi.\n"
        "Ular faqat bir martalik tasdiqlash uchun ishlatiladi.\n\n"
        "Ma'lumotlaringiz ishonchli va himoyalangan."
    )

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=main_menu,
    )

# ============================
#        XAVFSIZLIK
# ============================

@router.message(F.text == "🚪 Akkountdan chiqish")
async def log_out(message: Message, state: FSMContext):
    await state.clear()

    text = (
        "❗️⛓️‍💥 <b>Akkountdan chiqish</b>\n\n"
        "<b>- Akkountdan chiqish uchun quyidagi amallarni bajaring:</b>\n\n"
        "1️⃣ <b>Telegram sozlamalari bo'limiga o'ting!</b>\n"
        "2️⃣ <b>Xavfsizlik sozlamalari bo'limidan Qurulmalar bo'limini toping!</b>\n"
        "3️⃣ <b>Botni qurulmalar ro'yxatidan chiqarib yuboring!</b>\n"
        "👻 <b>Bot/Qurulma nomi👇:</b>\n\n"
        "<code>🤖arm64, Ghost Reply 1.42.0, Android 24.9.0, khiva, Uzbekistan</code>\n\n"
        "‼️Ushbu qurulmani chiqarish orqali o'z akkountingizni Ghost Replydan uzgan bo'lasiz, va bot boshqa sizning o'rningizga javob bermaydi!\n\n"
        "🔗 <b>Botni qayta ulash uchun botga qayta start bering va akkountingizni qayta ulang!</b>\n"
    )

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=main_menu,
    )

# ============================
#     ADD TRIGGER HANDLERS
# ============================

@router.message(F.text == "➕ Trigger qo'shish")
async def add_trigger_start(message: Message, state: FSMContext):
    if not await ensure_account_connected(message.from_user.id, message):
        return
    await state.clear()

    telegram_id = message.from_user.id

    # 🔍 Avval trigger limitini tekshiramiz
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{BACKEND_URL}/api/triggers/",
            params={"user_telegram_id": telegram_id},
        )

    if res.status_code != 200:
        await message.answer(
            "❌ Triggerlarni tekshirishda xatolik yuz berdi. Keyinroq qayta urinib ko‘ring."
        )
        return

    triggers = res.json()
    trigger_count = len(triggers)

    # ⚠️ Free plan limit = 3 (backend bilan mos)
    if trigger_count >= 3:
        await message.answer(
            "🚫 <b>Trigger limitingiz tugadi</b>\n\n"
            "Ghost Reply hozircha test holatda, barcha foydalanuvchilar faqatgina 3 tagacha trigger qo'sha olishadi😕\n"
            "Tariflar qo'shimcha funksiyalar tez orada qo'shiladi, iltimos yangilanishni kuting!🙂",
            parse_mode="HTML",
            reply_markup=trigger_limit_reached_kb(),
        )
        return

    # ✅ Limit bor — FSM davom etadi
    await state.set_state(AddTriggerState.waiting_for_trigger)
    await message.answer(
        "✍️ Trigger matnini kiriting, bu bot qanday xabar kelganda ishga tushishi uchun: (masalan: <code>So'z 1</code>)",
        parse_mode="HTML",
    )


@router.message(AddTriggerState.waiting_for_trigger)
async def add_trigger_text(message: Message, state: FSMContext):
    if not await ensure_account_connected(message.from_user.id, message):
        await state.clear()
        return
    text = message.text.lower().strip()
    if len(text) < 2:
        await message.answer("❌ Trigger juda qisqa. Qayta kiriting kamida 2 ta belgi:")
        return

    await state.update_data(trigger_text=text)
    await state.set_state(AddTriggerState.waiting_for_reply)
    await message.answer("💬 Endi trigger uchun javob matnini yozing:")


@router.message(AddTriggerState.waiting_for_reply)
async def add_trigger_reply(message: Message, state: FSMContext):
    if not await ensure_account_connected(message.from_user.id, message):
        await state.clear()
        return
    data = await state.get_data()

    payload = {
        "user_telegram_id": message.from_user.id,
        "trigger_text": data["trigger_text"],
        "reply_text": message.text,
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(f"{BACKEND_URL}/api/triggers/", json=payload)

    await state.clear()

    if res.status_code == 403:
        await message.answer(
            "🚫 <b>Trigger limitingiz tugadi</b>\n\n"
            "Hozirgi test rejimida har bir foydalanuvchi maksimal <b>3 ta trigger</b> qo‘sha oladi.\n\n"
            "📦 Tariflar va ko‘proq triggerlar <b>yaqin orada</b> qo‘shiladi.\n"
            "Iltimos, yangilanishlarni kuting 👀",
            parse_mode="HTML",
            reply_markup=trigger_limit_reached_kb(),
        )
        return

    if res.status_code == 409:
        await message.answer("⚠️ Bu trigger allaqachon mavjud.")
        return

    if res.status_code != 200:
        await message.answer("❌ Trigger saqlashda xatolik yuz berdi.")
        return

    await message.answer("✅ Trigger qo‘shildi!", reply_markup=main_menu)


# ============================
#     TRIGGER LISTING (INLINE)
# ============================

@router.message(F.text == "📄 Triggerlarim")
async def list_triggers(message: Message, state: FSMContext):
    if not await ensure_account_connected(message.from_user.id, message):
        return
    await state.clear()
    user_id = message.from_user.id

    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{BACKEND_URL}/api/triggers/",
            params={"user_telegram_id": user_id},
        )

    if res.status_code != 200:
        await message.answer("❌ Triggerlar ro‘yxatini olishda xatolik yuz berdi.")
        return

    triggers = res.json()

    if not triggers:
        await message.answer(
            "📭 Sizda hali triggerlar mavjud emas.",
            reply_markup=main_menu
        )
        return

    await message.answer(
        "📄 Triggerlaringiz:",
        reply_markup=triggers_inline_kb(triggers)
    )


# ============================
#     CALLBACK HANDLERS FOR INLINE TRIGGERS
# ============================

@router.callback_query(F.data.startswith("trigger_open:"))
async def open_trigger(callback: CallbackQuery, state: FSMContext):
    if not await ensure_account_connected(callback.from_user.id, callback.message):
        await callback.answer()
        return
    trigger_id_str = callback.data.split(":", 1)[1]
    if not trigger_id_str.isdigit():
        await callback.answer("❌ Noto‘g‘ri trigger.", show_alert=True)
        return
    try:
        trigger_id = int(trigger_id_str)
    except ValueError:
        await callback.answer("❌ Noto‘g‘ri trigger ID.", show_alert=True)
        return

    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{BACKEND_URL}/api/triggers/",
            params={"user_telegram_id": callback.from_user.id},
        )

    if res.status_code != 200:
        await callback.answer("❌ Trigger topilmadi yoki server xatosi.", show_alert=True)
        return
    
    triggers = res.json()
    trigger = next((t for t in triggers if t["id"] == trigger_id), None)

    if not trigger:
        await callback.answer("❌ Trigger topilmadi yoki o‘chirilgan.", show_alert=True)
        return

    await state.update_data(trigger_id=trigger_id)
    await callback.message.edit_text(
        f"🧩 <b>Triggeringiz:</b> <code>{trigger['trigger_text']}</code>\n"
        f"💬 <b>Javobingiz:</b> {trigger['reply_text']}",
        parse_mode="HTML",
        reply_markup=trigger_actions_inline_kb(trigger_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("trigger_delete:"))
async def confirm_delete_trigger(callback: CallbackQuery, state: FSMContext):
    if not await ensure_account_connected(callback.from_user.id, callback.message):
        await callback.answer()
        return
    trigger_id_str = callback.data.split(":", 1)[1]
    try:
        trigger_id = int(trigger_id_str)
    except ValueError:
        await callback.answer("❌ Noto‘g‘ri trigger ID.", show_alert=True)
        return

    await callback.message.edit_reply_markup(reply_markup=confirm_delete_inline_kb(trigger_id))
    await callback.answer()


@router.callback_query(F.data.startswith("trigger_delete_confirm:"))
async def delete_trigger(callback: CallbackQuery, state: FSMContext):
    trigger_id_str = callback.data.split(":", 1)[1]
    try:
        trigger_id = int(trigger_id_str)
    except ValueError:
        await callback.answer("❌ Noto‘g‘ri trigger ID.", show_alert=True)
        return

    user_id = callback.from_user.id

    async with httpx.AsyncClient() as client:
        del_res = await client.delete(f"{BACKEND_URL}/api/triggers/{trigger_id}")

        if del_res.status_code != 200:
            await callback.answer("❌ Triggerni o‘chirishda xatolik yuz berdi.", show_alert=True)
            return

        res = await client.get(
            f"{BACKEND_URL}/api/triggers/",
            params={"user_telegram_id": user_id},
        )

    await state.clear()

    if res.status_code != 200:
        await callback.message.edit_text("❌ Triggerlar ro‘yxatini olishda xatolik yuz berdi.")
        await callback.answer()
        return

    triggers = res.json()

    if not triggers:
        await callback.message.edit_text(
            "📭 Sizda triggerlar qolmadi.",
            reply_markup=None
        )
    else:
        await callback.message.edit_text("📄 Triggerlaringiz:", reply_markup=triggers_inline_kb(triggers))

    await callback.answer("🗑 Trigger o‘chirildi!")


@router.callback_query(F.data == "triggers_back")
async def triggers_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(
        "🏠 Asosiy menyu:",
        reply_markup=main_menu
    )
    await callback.answer()


@router.callback_query(F.data.startswith("trigger_edit:"))
async def edit_trigger_start(callback: CallbackQuery, state: FSMContext):
    if not await ensure_account_connected(callback.from_user.id, callback.message):
        await callback.answer()
        return
    trigger_id_str = callback.data.split(":", 1)[1]
    try:
        trigger_id = int(trigger_id_str)
    except ValueError:
        await callback.answer("❌ Noto‘g‘ri trigger ID.", show_alert=True)
        return

    await state.update_data(trigger_id=trigger_id)
    await state.set_state(EditTriggerState.waiting_for_trigger)
    await callback.message.edit_text("✍️ Yangi trigger matnini kiriting:")
    await callback.answer()


@router.callback_query(F.data == "open_plans")
async def open_plans(callback: CallbackQuery):
    await callback.message.edit_text(
        "📦 <b>Tariflar</b>\n\n"
        "Hozircha GhostReply <b>test rejimida</b> ishlamoqda.\n\n"
        "🔒 Tariflar, to‘lovlar va qo‘shimcha imkoniyatlar "
        "yaqin orada qo‘shiladi.\n\n"
        "Hozirgi holatda:\n"
        "• Har bir foydalanuvchi maksimal <b>3 ta trigger</b> qo‘sha oladi\n\n"
        "Rahmat! 🚀",
        parse_mode="HTML",
        reply_markup=plans_menu_kb("free"),
    )
    await callback.answer()


# Handler for plans menu "Ortga" button
@router.callback_query(F.data == "plans_back")
async def plans_back(callback: CallbackQuery):
    # Tariflar oynasidan asosiy menyuga qaytish
    await callback.message.delete()
    await callback.message.answer(
        "🏠 Asosiy menyu:",
        reply_markup=main_menu
    )
    await callback.answer()


@router.message(F.text == "📦 Tariflar")
async def open_plans_message(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "📦 <b>Tariflar</b>\n\n"
        "Hozircha GhostReply <b>test rejimida</b> ishlamoqda.\n\n"
        "🔒 Tariflar, to‘lovlar va qo‘shimcha imkoniyatlar "
        "yaqin orada qo‘shiladi.\n\n"
        "Hozirgi holatda:\n"
        "• Har bir foydalanuvchi maksimal <b>3 ta trigger</b> qo‘sha oladi\n\n"
        "Rahmat! 🚀",
        parse_mode="HTML",
        reply_markup=plans_menu_kb("free"),
    )

# ============================
#     EDIT TRIGGER HANDLERS (FSM)
# ============================

@router.message(EditTriggerState.waiting_for_trigger)
async def edit_trigger_text(message: Message, state: FSMContext):
    if not await ensure_account_connected(message.from_user.id, message):
        await state.clear()
        return
    new_text = message.text.lower().strip()
    if len(new_text) < 2:
        await message.answer("❌ Trigger juda qisqa. Qayta kiriting, kamida 2 ta belgi:")
        return

    await state.update_data(new_trigger_text=new_text)
    await state.set_state(EditTriggerState.waiting_for_reply)
    await message.answer("💬 Endi yangi javob matnini kiriting:")


@router.message(EditTriggerState.waiting_for_reply)
async def edit_trigger_auto_save(message: Message, state: FSMContext):
    if not await ensure_account_connected(message.from_user.id, message):
        await state.clear()
        return
    data = await state.get_data()
    trigger_id = data.get("trigger_id")
    new_trigger_text = data.get("new_trigger_text")
    new_reply_text = message.text

    async with httpx.AsyncClient() as client:
        res = await client.patch(
            f"{BACKEND_URL}/api/triggers/{trigger_id}",
            json={
                "trigger_text": new_trigger_text,
                "reply_text": new_reply_text,
            },
        )

    await state.clear()

    if res.status_code != 200:
        await message.answer("❌ O‘zgarishlarni saqlashda xatolik.")
        return

    await message.answer("✅ O‘zgarishlar saqlandi!", reply_markup=main_menu)
