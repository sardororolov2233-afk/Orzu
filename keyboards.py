import os
from config import CHANNEL_USERNAME
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types.web_app_info import WebAppInfo

WEBAPP_URL = (os.getenv("MINI_APP_URL") or (os.getenv("BACKEND_URL", "").rstrip("/") + "/miniapp" if os.getenv("BACKEND_URL") else os.getenv("FRONTEND_URL", "https://orzu-two.vercel.app"))).rstrip("/")

main_menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="📊 Taqdimot yaratish"), KeyboardButton(text="Kurs ishi")],
    [KeyboardButton(text="📄 Referat yaratish"), KeyboardButton(text="📝 Maqola yaratish")],
    [KeyboardButton(text="🎁 Do‘stlarni taklif qilish"), KeyboardButton(text="👤 Hisob va limitlar")],
    [KeyboardButton(text="💳 Hisobni to'ldirish"), KeyboardButton(text="💵 Narxlar")],
    [KeyboardButton(text="📋 Obyektivka tayyorlash"), KeyboardButton(text="🆘 Yordam")],
], resize_keyboard=True)

access_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🎁 5 ta do‘st taklif qilish", callback_data="invite")],
    [InlineKeyboardButton(text="🗓 Bir oylik obuna — 25 000 so‘m", callback_data="subscribe")],
    [InlineKeyboardButton(text="💳 Hisobni to‘ldirish", callback_data="payment"),
     InlineKeyboardButton(text="👤 Limitlarim", callback_data="account")],
])
subscription_confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✅ Balansdan 25 000 so‘mga sotib olish", callback_data="subscribe_confirm")],
    [InlineKeyboardButton(text="💳 Karta orqali 25 000 so‘m to‘lash", callback_data="pay_subscription")],
    [InlineKeyboardButton(text="🎁 Do‘st taklif qilish", callback_data="invite")],
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
        [InlineKeyboardButton(text="🎨 Dizayn yaratish", web_app=WebAppInfo(url=f"{WEBAPP_URL}/design"))]
    ]
)

# Obuna tekshirish klaviaturasi
subscribe_channel_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=f"https://t.me/{CHANNEL_USERNAME.lstrip(chr(64))}")],
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="check_subscription")]
    ]
)

# Hisobni to'ldirish inline tugmalari
payment_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🗓 Obuna — 25 000 so‘m", callback_data="pay_subscription")],
    [InlineKeyboardButton(text="8 000 so‘m", callback_data="pay_8000"),
     InlineKeyboardButton(text="10 000 so‘m", callback_data="pay_10000")],
    [InlineKeyboardButton(text="30 000 so‘m", callback_data="pay_30000"),
     InlineKeyboardButton(text="50 000 so‘m", callback_data="pay_50000")],
    [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_main")],
])

# Chek yuborish tugmasi
send_receipt_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📤 Chek yuborish", callback_data="send_receipt")],
        [InlineKeyboardButton(text="⬅️ Bekor qilish", callback_data="payment_cancel")],
    ]
)

# Admin uchun chekni tasdiqlash
def get_admin_approval_kb(payment_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{payment_id}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{payment_id}"),
            ]
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
        [InlineKeyboardButton(text="✅ 8 000 so‘mga yaratish", callback_data="plan_approve")],
        [InlineKeyboardButton(text="🔄 Boshqa reja", callback_data="plan_regenerate")],
        [InlineKeyboardButton(text="🚫 Bekor qilish", callback_data="plan_cancel")]
    ]
)

# Kurs ishi Reja tasdiqlash uchun
course_plan_approval_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✅ Limitdan yoki 30 000 so‘mga yaratish", callback_data="course_plan_approve")],
        [InlineKeyboardButton(text="🔄 Boshqa reja", callback_data="course_plan_regenerate")],
        [InlineKeyboardButton(text="🚫 Bekor qilish", callback_data="course_plan_cancel")]
    ]
)
