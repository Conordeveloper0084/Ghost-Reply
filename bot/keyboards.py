from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

# 📌 Asosiy menyu (ONLY reply keyboard we keep)
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Trigger qo'shish")],
        [KeyboardButton(text="📄 Triggerlarim")],
        [KeyboardButton(text="📦 Tariflar")],
        [KeyboardButton(text="💡 Yo'riqnoma")],
        [KeyboardButton(text="🔐 Xavfsizlik")],
        [KeyboardButton(text="🚪 Akkountdan chiqish")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

# 🚫 Trigger limiti tugagan holat (INLINE) - placeholder version
def trigger_limit_reached_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔒 Tariflar hozircha mavjud emas",
                    callback_data="noop"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Ortga",
                    callback_data="triggers_back"
                )
            ]
        ]
    )

# 🔹 START menyusi (INLINE)
start_menu_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🔌 Akkount ulash",
                callback_data="start_link_account"
            )
        ],
        [
            InlineKeyboardButton(
                text="📘 Qanday ishlaydi?",
                callback_data="start_instructions"
            )
        ],
    ]
)

# 🔐 Xavfsizlik va rozilik (INLINE)
consent_confirm_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Roziman",
                callback_data="consent_accept"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Bekor qilish",
                callback_data="back_to_start"
            )
        ]
    ]
)

# 🔙 Startga qaytish (INLINE)
back_to_start_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="⬅️ Ortga",
                callback_data="back_to_start"
            )
        ]
    ]
)

# 🔄 Akkount holatini tekshirish (INLINE)
check_account_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🔄 Akkountni tekshirish",
                callback_data="check_account"
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅️ Ortga",
                callback_data="back_to_start"
            )
        ]
    ]
)



def link_account_kb(login_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🌐 Ghost Reply akkaunt ulash",
                    url=login_url
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Akkountni tekshirish",
                    callback_data="check_account"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Ortga",
                    callback_data="back_to_start"
                )
            ]
        ]
    )

# ⚡ Tarif o‘zgartirish - removed

# 📦 Tariflar menyusi - placeholder version
def plans_menu_kb(current_plan: str):
    buttons = [
        [InlineKeyboardButton(text="🔒 Tariflar hozircha mavjud emas", callback_data="noop")],
        [InlineKeyboardButton(text="⬅️ Ortga", callback_data="plans_back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# pay_kb - placeholder version
def pay_kb(payment_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🔒 To‘lovlar hozircha mavjud emas",
                callback_data="noop"
            )],
            [InlineKeyboardButton(text="⬅️ Ortga", callback_data="plans_back")]
        ]
    )

# 📄 Triggerlar ro‘yxati (INLINE keyboard)
def triggers_inline_kb(triggers):
    buttons = []

    for t in triggers:
        trigger_text = t.get("trigger_text")
        trigger_id = t.get("id")

        # ❌ Skip fake / system trigger
        if not trigger_text or trigger_text.lower() == "triggerlarim":
            continue

        buttons.append([
            InlineKeyboardButton(
                text=f"🔹 {trigger_text}",
                callback_data=f"trigger_open:{trigger_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="⬅️ Ortga",
            callback_data="triggers_back"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

# 📭 Triggerlar yo‘q holati (INLINE)
def empty_triggers_inline_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Ortga",
                    callback_data="triggers_back"
                )
            ]
        ]
    )

# ✏️ / 🗑 trigger actions (INLINE)
def trigger_actions_inline_kb(trigger_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Tahrirlash",
                    callback_data=f"trigger_edit:{trigger_id}"
                ),
                InlineKeyboardButton(
                    text="🗑 O‘chirish",
                    callback_data=f"trigger_delete:{trigger_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Ortga",
                    callback_data="triggers_back"
                )
            ]
        ]
    )

# ❗ O‘chirishni tasdiqlash (INLINE)
def confirm_delete_inline_kb(trigger_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Ha, o‘chirish!",
                    callback_data=f"trigger_delete_confirm:{trigger_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Yo‘q, qaytish",
                    callback_data=f"trigger_open:{trigger_id}"
                )
            ]
        ]
    )
