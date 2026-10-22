import os
from config import CHANNEL_USERNAME
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types.web_app_info import WebAppInfo

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://orzu-two.vercel.app").rstrip("/")

WEBAPP_URL = (os.getenv("MINI_APP_URL") or (os.getenv("BACKEND_URL", "").rstrip("/") + "/miniapp" if os.getenv("BACKEND_URL") else os.getenv("FRONTEND_URL", "https://orzu-two.vercel.app"))).rstrip("/")

main_menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="📊 Taqdimot yaratish"), KeyboardButton(text="Kurs ishi")],
    [KeyboardButton(text="📄 Referat yaratish"), KeyboardButton(text="📝 Maqola yaratish")],
    [KeyboardButton(text="🎁 Do‘stlarni taklif qilish"), KeyboardButton(text="👤 Hisob va limitlar")],
    [KeyboardButton(text="🎨 Dizayn yaratish"), KeyboardButton(text="📌 Foydalanish qoidalari")],
    [KeyboardButton(text="📋 Obyektivka tayyorlash"), KeyboardButton(text="🆘 Yordam")],
], resize_keyboard=True)

access_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🎁 Do‘st taklif qilish · +1 kvota", callback_data="invite")],
    [InlineKeyboardButton(text="👤 Kvotalarim", callback_data="account")],
])

# Obyektivka uchun havola tugmasi (Standart oyna)
obyektivka_link_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📋 Standart oynani ochish", web_app=WebAppInfo(url=f"{os.getenv("FRONTEND_URL", "https://orzu-two.vercel.app").rstrip(chr(47))}?tab=standard"))]
    ]
)

# Grafik dizayn uchun havola tugmasi
design_link_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🎨 Dizayn yaratish", web_app=WebAppInfo(url=f"{WEBAPP_URL}?tab=designs"))]
    ]
)

# Obuna tekshirish klaviaturasi
subscribe_channel_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=f"https://t.me/{CHANNEL_USERNAME.lstrip(chr(64))}")],
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="check_subscription")]
    ]
)

# Til tanlash uchun inline tugmalar
language_selection_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="lang_uz"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
        ],
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton(text="🇫🇷 Français", callback_data="lang_fr"),
        ],
    ]
)

# Referat turi (Referat / Mustaqil ish)
referat_type_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="📄 REFERAT", callback_data="type_referat"),
            InlineKeyboardButton(text="📝 MUSTAQIL ISH", callback_data="type_mustaqil"),
        ]
    ]
)

# Referatni tasdiqlash uchun inline tugmalar
referat_confirm_inline_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📝 Reja tuzish", callback_data="referat_confirm")],
        [
            InlineKeyboardButton(text="✏️O'zgartirish", callback_data="referat_edit"),
            InlineKeyboardButton(text="🚫Rad etish", callback_data="referat_cancel")
        ],
    ]
)

# Referat tahrirlash menyusi
referat_edit_selection_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Mavzu", callback_data="edit_referat_tema"),
            InlineKeyboardButton(text="📄 Ish turi", callback_data="edit_referat_ish_turi"),
        ],
        [
            InlineKeyboardButton(text="🏛 Institut", callback_data="edit_referat_uni"),
            InlineKeyboardButton(text="🏢 Fakultet", callback_data="edit_referat_fakultet"),
        ],
        [
            InlineKeyboardButton(text="👤 Muallif", callback_data="edit_referat_muallif"),
            InlineKeyboardButton(text="👨‍🎓 Kurs/Guruh", callback_data="edit_referat_kurs_guruh"),
        ],
        [
            InlineKeyboardButton(text="📄 Sahifa", callback_data="edit_referat_sahifa"),
            InlineKeyboardButton(text="🌐 Til", callback_data="edit_referat_lang"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Ortga", callback_data="edit_referat_back"),
        ]
    ]
)

# Kurs ishi tasdiqlash uchun inline tugmalar
course_confirm_inline_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📝 Reja tuzish", callback_data="course_confirm")],
        [
            InlineKeyboardButton(text="✏️O'zgartirish", callback_data="course_edit"),
            InlineKeyboardButton(text="🚫Rad etish", callback_data="course_cancel")
        ],
    ]
)

# Kurs ishi tahrirlash menyusi
course_edit_selection_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Mavzu", callback_data="edit_course_tema"),
            InlineKeyboardButton(text="🏛 Institut", callback_data="edit_course_uni"),
        ],
        [
            InlineKeyboardButton(text="👤 Muallif", callback_data="edit_course_muallif"),
            InlineKeyboardButton(text="📄 Sahifa", callback_data="edit_course_sahifa"),
        ],
        [
            InlineKeyboardButton(text="👨‍🎓 Kurs", callback_data="edit_course_kurs"),
            InlineKeyboardButton(text="👥 Guruh", callback_data="edit_course_guruh"),
        ],
        [
            InlineKeyboardButton(text="🖋 Uslub", callback_data="edit_course_uslub"),
            InlineKeyboardButton(text="🌐 Til", callback_data="edit_course_lang"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Ortga", callback_data="edit_course_back"),
        ]
    ]
)

# Referat Reja tasdiqlash uchun
referat_plan_approval_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✅ Bepul limitdan yoki 1 kvota bilan yaratish", callback_data="plan_approve")],
        [InlineKeyboardButton(text="🔄 Boshqa reja", callback_data="plan_regenerate")],
        [InlineKeyboardButton(text="🚫 Bekor qilish", callback_data="plan_cancel")]
    ]
)

# Kurs ishi Reja tasdiqlash uchun
course_plan_approval_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✅ 2 kvota bilan yaratish", callback_data="course_plan_approve")],
        [InlineKeyboardButton(text="🔄 Boshqa reja", callback_data="course_plan_regenerate")],
        [InlineKeyboardButton(text="🚫 Bekor qilish", callback_data="course_plan_cancel")]
    ]
)
