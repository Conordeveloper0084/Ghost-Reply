from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.types import ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
import httpx
from html import escape
from bot.keyboards import main_menu

from bot.config import BACKEND_URL
from bot.admin.keyboards import (
    admin_main_kb,
    admin_users_kb,
    admin_admins_kb,
    admin_users_stats_kb,
    admin_user_gift_kb,
    admin_users_pagination_kb
)
from bot.admin.states import (
    AdminGiftState,
    AdminAddState,
    AdminRemoveState,
    AdminBroadcastState,
)

router = Router()


# ============================
#        HELPERS
# ============================

async def is_admin(telegram_id: int) -> bool:
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{BACKEND_URL}/api/admin/check/{telegram_id}")
    return res.status_code == 200


# ============================
#           /admin
# ============================

@router.message(Command("admin"))
async def admin_entry(message: Message, state: FSMContext):
    await state.clear()
    telegram_id = message.from_user.id

    if not await is_admin(telegram_id):
        await message.answer("❌ Siz admin emassiz")
        return

    await message.answer(
        "🛠 <b>Admin panel</b>\nQuyidagi menyudan tanlang:",
        parse_mode="HTML",
        reply_markup=admin_main_kb
    )


# ============================
#        MAIN MENU
# ============================

@router.message(F.text == "👤 Userlar")
async def admin_users_message(message: Message):
    await message.answer(
        "👥 <b>Userlar bo‘limi</b>",
        parse_mode="HTML",
        reply_markup=admin_users_kb
    )

@router.message(F.text == "🛡 Adminlar")
async def admin_admins_message(message: Message):
    await message.answer(
        "👮 <b>Adminlar bo‘limi</b>",
        parse_mode="HTML",
        reply_markup=admin_admins_kb
    )

@router.message(F.text == "📢 Broadcasting")
async def admin_broadcast_message(message: Message, state: FSMContext):
    await state.set_state(AdminBroadcastState.waiting_for_message)
    await message.answer(
        "📣 <b>Broadcast xabarni yuboring</b>\n\n",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )

@router.message(F.text == "❌ Chiqish")
async def admin_exit_message(message: Message, state: FSMContext):
    await state.clear()

    await message.answer(
        "❌ Admin paneldan chiqildi \n\n 🏠 <b>Asosiy menyuga qaytdingiz</b>",
        parse_mode="HTML",
        reply_markup=main_menu
    )


# ============================
#        USERS SECTION
# ============================

@router.message(F.text == "📊 Userlar soni")
async def users_stats(message: Message):
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{BACKEND_URL}/api/admin/users/stats",
            params={"requester_telegram_id": message.from_user.id},
        )

    if res.status_code == 403:
        await message.answer("❌ Siz admin emassiz")
        return
    if res.status_code != 200:
        await message.answer("❌ Xatolik yuz berdi")
        return

    data = res.json()

    text = (
        "📊 <b>Userlar statistikasi</b>\n\n"
        f"👥 Jami: {data['total']}\n"
        f"🆓 Free: {data['free']}\n"
        f"⭐ Pro: {data['pro']}\n"
        f"💎 Premium: {data['premium']}"
    )

    await message.answer(text, parse_mode="HTML", reply_markup=admin_users_kb)


@router.message(F.text.startswith("📄 Userlar"))
async def admin_users_list_message(message: Message):
    limit = 10
    offset = 0

    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{BACKEND_URL}/api/admin/users",
            params={
                "requester_telegram_id": message.from_user.id,
                "limit": limit,
                "offset": offset,
            },
        )

    if res.status_code != 200:
        await message.answer("❌ Userlarni olishda xatolik")
        return

    data = res.json()
    users = data.get("items", [])

    if not users:
        await message.answer("📭 Userlar topilmadi")
        return

    text = "📄 Userlar ro‘yxati:\n\n"

    for u in users:
        text += (
            f"👤 Ism: {escape(u['name'] or 'not provided')}\n"
            f"🔗 Username: {u['username']}\n"
            f"📞 Telefon: {u.get('phone', 'not provided')}\n"
            f"🆔 Telegram ID: {u['telegram_id']}\n"
            f"📦 Tarif: {u['plan']}\n"
            f"⏳ Tugash sanasi: {u['plan_expires_at'] or '∞'}\n"
            f"🕒 Qo‘shilgan: {u['created_at']}\n"
            "──────────────\n"
        )

    await message.answer(text, parse_mode=None)


@router.message(F.text == "🎁 User + Gift")
async def start_user_gift(message: Message, state: FSMContext):
    await state.set_state(AdminGiftState.waiting_for_user_id)
    await message.answer("🎁 User Telegram ID kiriting:")


@router.callback_query(F.data.startswith("admin_users_page:"))
async def admin_users_page(callback: CallbackQuery):
    limit = 10
    offset = int(callback.data.split(":")[1])

    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{BACKEND_URL}/api/admin/users",
            params={
                "requester_telegram_id": callback.from_user.id,
                "limit": limit,
                "offset": offset,
            },
        )

    if res.status_code != 200:
        await callback.answer("Xatolik", show_alert=True)
        return

    data = res.json()
    users = data.get("items", [])
    total = data.get("total", 0)

    if not users:
        await callback.answer("Userlar topilmadi", show_alert=True)
        return

    text = "📄 <b>Userlar ro‘yxati</b>\n\n"
    for u in users:
        text += (
            f"👤 {u['name']}\n"
            f"🔗 {u['username']}\n"
            f"🆔 {u['telegram_id']}\n"
            f"📦 {u['plan']}\n"
            f"🕒 {u['created_at']}\n"
            "──────────────\n"
        )

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=admin_users_pagination_kb(offset, limit, total),
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_gift:"))
async def apply_gift(callback: CallbackQuery):
    _, plan, user_id = callback.data.split(":")

    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{BACKEND_URL}/api/admin/users/gift",
            json={
                "requester_telegram_id": callback.from_user.id,
                "target_telegram_id": int(user_id),
                "plan": plan,
            },
        )

    if res.status_code != 200:
        await callback.answer("❌ Gift berilmadi", show_alert=True)
        return

    # ✅ Admin paneldagi xabar
    await callback.message.edit_text(
        f"✅ Userga 1 oylik {plan.upper()} gift berildi"
    )
    await callback.answer()

    # 🎁 USERGA NOTIFICATION YUBORISH (bot orqali)
    try:
        await callback.bot.send_message(
            chat_id=int(user_id),
            text=(
                "🎉 <b>Tabriklayman!</b>\n\n"
                f"Sizga <b>{plan.upper()}</b> tarifi 1 oyga sovg‘a qilindi 🎁\n\n"
                "🚀 Endi GhostReply imkoniyatlaridan to‘liq foydalanishingiz mumkin!"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        # ⚠️ agar user botni bloklagan bo‘lsa yoki /start bosmagan bo‘lsa
        print(f"⚠️ Userga gift notification yuborilmadi: {e}")


@router.message(AdminGiftState.waiting_for_user_id)
async def process_user_gift(message: Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Telegram ID noto‘g‘ri")
        return

    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{BACKEND_URL}/api/admin/users/{user_id}",
            params={"requester_telegram_id": message.from_user.id},
        )

    if res.status_code == 403:
        await message.answer("❌ Siz admin emassiz")
        return
    if res.status_code != 200:
        await message.answer("❌ Xatolik yuz berdi")
        return

    user = res.json()
    await state.update_data(target_user_id=user_id)

    text = (
        "👤 <b>User ma’lumotlari</b>\n\n"
        f"Ism: {user['name']}\n"
        f"Username: @{user['username'] if user['username'] else 'not provided'}\n"
        f"Phone: {user['phone'] or 'not provided'}\n"
        f"Plan: {user['plan']}\n"
        f"Qo‘shilgan: {user['created_at']}"
    )

    await message.answer(text, parse_mode=None, reply_markup=admin_user_gift_kb(user_id))
    await state.clear()


# ============================
#        ADMINS SECTION
# ============================

@router.message(F.text == "➕ Admin qo'shish")
async def start_admin_add(message: Message, state: FSMContext):
    await state.set_state(AdminAddState.waiting_for_admin_id)
    await message.answer("➕ Qo‘shiladigan admin Telegram ID kiriting:")


@router.message(F.text == "➖ Admin o'chirish")
async def start_admin_remove(message: Message, state: FSMContext):
    await state.set_state(AdminRemoveState.waiting_for_admin_id)
    await message.answer("🗑 O‘chiriladigan admin Telegram ID kiriting:")


@router.message(AdminAddState.waiting_for_admin_id)
async def add_admin(message: Message, state: FSMContext):
    try:
        admin_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ ID noto‘g‘ri")
        return

    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{BACKEND_URL}/api/admin/admins/add",
            json={
                "requester_telegram_id": message.from_user.id,
                "new_admin_telegram_id": admin_id,
            },
        )

    await state.clear()

    if res.status_code != 200:
        await message.answer("❌ Admin qo‘shilmadi")
        return

    await message.answer("✅ Admin qo‘shildi", reply_markup=admin_main_kb)


@router.message(AdminRemoveState.waiting_for_admin_id)
async def remove_admin(message: Message, state: FSMContext):
    try:
        admin_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ ID noto‘g‘ri")
        return

    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{BACKEND_URL}/api/admin/admins/remove",
            json={
                "requester_telegram_id": message.from_user.id,
                "admin_telegram_id": admin_id,
            },
        )

    await state.clear()

    if res.status_code != 200:
        await message.answer("❌ Admin o‘chirilmadi")
        return

    await message.answer("✅ Admin o‘chirildi", reply_markup=admin_main_kb)


# ============================
#        BACK TO ADMIN MAIN
# ============================

@router.message(F.text == "⬅️ Ortga")
async def admin_back_main(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🛠 <b>Admin panel</b>",
        parse_mode="HTML",
        reply_markup=admin_main_kb
    )

@router.message(AdminBroadcastState.waiting_for_message)
async def process_admin_broadcast(message: Message, state: FSMContext):
    broadcast_text = message.html_text

    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{BACKEND_URL}/api/admin/users",
            params={
                "requester_telegram_id": message.from_user.id,
                "limit": 100000,
                "offset": 0,
            },
        )

    if res.status_code != 200:
        await message.answer("❌ Userlarni olishda xatolik")
        return

    data = res.json()
    users = data.get("items", [])

    sent = 0
    for user in users:
        try:
            await message.bot.send_message(
                chat_id=user["telegram_id"],
                text=broadcast_text,
                parse_mode="HTML",
            )
            sent += 1
        except Exception:
            continue

    await state.clear()
    await message.answer(
        f"✅ Broadcast yuborildi\n📨 Yuborilgan: {sent} ta user",
        reply_markup=admin_main_kb
    )
