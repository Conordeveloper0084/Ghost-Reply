from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

# ============================
# ADMIN MAIN MENU
# ============================

admin_main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👤 Userlar")],
        [KeyboardButton(text="🛡 Adminlar")],
        [KeyboardButton(text="📢 Broadcasting")],
        [KeyboardButton(text="❌ Chiqish")],
    ],
    resize_keyboard=True
)

# ============================
# USERS SECTION MENU§
# ============================

admin_users_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Userlar soni")],
        [KeyboardButton(text="📄 Userlar ma'lumoti")],
        [KeyboardButton(text="🎁 User + Gift")],
        [KeyboardButton(text="⬅️ Ortga")],
    ],
    resize_keyboard=True
)

# ============================
# ADMINS SECTION MENU
# ============================

admin_admins_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Admin qo'shish")],
        [KeyboardButton(text="➖ Admin o'chirish")],
        [KeyboardButton(text="⬅️ Ortga")],
    ],
    resize_keyboard=True
)

# ============================
# USER GIFT PLAN KEYBOARD
# ============================

def admin_gift_kb(user_telegram_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎁 PRO (1 oy)",
                    callback_data=f"admin_gift:pro:{user_telegram_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎁 PREMIUM (1 oy)",
                    callback_data=f"admin_gift:premium:{user_telegram_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Ortga",
                    callback_data="admin_users"
                )
            ],
        ]
    )

# ============================
# PAGINATION KEYBOARD (USERS LIST)
# ============================

def admin_users_pagination_kb(offset: int, limit: int, total: int):
    buttons = []

    if offset > 0:
        buttons.append(
            InlineKeyboardButton(
                text="⬅️ Oldingi",
                callback_data=f"admin_users_page:{offset - limit}"
            )
        )

    if offset + limit < total:
        buttons.append(
            InlineKeyboardButton(
                text="➡️ Keyingi",
                callback_data=f"admin_users_page:{offset + limit}"
            )
        )

    keyboard = []
    if buttons:
        keyboard.append(buttons)

    keyboard.append(
        [InlineKeyboardButton(text="⬅️ Ortga", callback_data="admin_users")]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ============================
# USERS STATS BACK KEYBOARD
# ============================

admin_users_stats_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="⬅️ Ortga",
                callback_data="admin_users"
            )
        ]
    ]
)

# ============================
# ALIASES (HANDLERS COMPATIBILITY)
# ============================

# alias for handlers compatibility
admin_user_gift_kb = admin_gift_kb

# ============================
# BACK TO ADMIN MAIN (ALIAS)
# ============================

admin_back_main_kb = admin_main_kb
