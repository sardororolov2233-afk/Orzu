from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Asosiy menu (reply tugmalar)
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📄 Referat yaratish"), KeyboardButton(text="📊 Taqdimot yaratish")],
        [KeyboardButton(text="Kurs ishi"), KeyboardButton(text="💰 Tayyor ishlar")],
        [KeyboardButton(text="💳 Balans"), KeyboardButton(text="🆘 Yordam")],
        [KeyboardButton(text="💵 Narxlar"), KeyboardButton(text="📝 Buyurtma asosida yaratish")],
        [KeyboardButton(text="🎓 Bitiruv Malakaviy ishi")],
    ],
    resize_keyboard=True
)

# Obuna tekshirish klaviaturasi
subscribe_channel_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url="https://t.me/yordamch_AI")],
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="check_subscription")]
    ]
)

# Hisobni to'ldirish inline tugmalari
payment_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="5 000 so'm", callback_data="pay_5000"),
            InlineKeyboardButton(text="10 000 so'm", callback_data="pay_10000"),
        ],
        [
            InlineKeyboardButton(text="15 000 so'm", callback_data="pay_15000"),
            InlineKeyboardButton(text="20 000 so'm", callback_data="pay_20000"),
        ],
        [
            InlineKeyboardButton(text="25 000 so'm", callback_data="pay_25000"),
            InlineKeyboardButton(text="30 000 so'm", callback_data="pay_30000"),
        ],
        [
            InlineKeyboardButton(text="50 000 so'm", callback_data="pay_50000"),
            InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_main"),
        ],
    ]
)

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



def get_page_selection_kb():
    """Taqdimot sahifalarini tanlash (5 dan 30 gacha, 5 qadam bilan)"""
    buttons = []
    # 5, 10, 15, 20, 25, 30 sahifalar uchun tugmalar
    row = []
    for i in range(5, 31, 5):
        row.append(InlineKeyboardButton(text=f"{i} sahifa", callback_data=f"ppt_pages_{i}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Shablon tanlash uchun inline tugmalar (1-10)
template_selection_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="1. Modern Blue", callback_data="template_1"),
            InlineKeyboardButton(text="2. Historical", callback_data="template_2"),
        ],
        [
            InlineKeyboardButton(text="3. Terminal", callback_data="template_3"),
            InlineKeyboardButton(text="4. Playful", callback_data="template_4"),
        ],
        [
            InlineKeyboardButton(text="5. Cybernetic", callback_data="template_5"),
            InlineKeyboardButton(text="6. Eco Haven", callback_data="template_6"),
        ],
        [
            InlineKeyboardButton(text="7. Retro Wave", callback_data="template_7"),
            InlineKeyboardButton(text="8. Premium", callback_data="template_8"),
        ],
        [
            InlineKeyboardButton(text="9. Simple", callback_data="template_9"),
            InlineKeyboardButton(text="10. Elegance", callback_data="template_10"),
        ],
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

# Taqdimot rejimi uchun (Rasmli/Rasmsiz)
presentation_mode_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🖼 Rasm kiritish", callback_data="presentation_custom")],
        [InlineKeyboardButton(text="🤖 AI yordamida", callback_data="presentation_ai")],
        [InlineKeyboardButton(text="🚫 Rasmsiz", callback_data="presentation_none")],
    ]
)

# Rasmlarni tasdiqlash uchun
presentation_img_confirm_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="images_confirm")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="images_cancel")],
    ]
)

# Taqdimotni tasdiqlash uchun inline tugmalar
presentation_confirm_inline_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✅Tayyorlash", callback_data="presentation_confirm")],
        [
            InlineKeyboardButton(text="✏️O'zgartirish", callback_data="presentation_edit"),
            InlineKeyboardButton(text="🚫Rad etish", callback_data="presentation_cancel")
        ],
    ]
)

# Referatni tasdiqlash uchun inline tugmalar
referat_confirm_inline_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✅Tayyorlash", callback_data="referat_confirm")],
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

# Referat Tariflarini tanlash
def get_referat_tariff_kb(has_promo: bool = False):
    oddiy_price = 2400 if has_promo else 8000
    pro_price = 4470 if has_promo else 14900
    kb = [
        [InlineKeyboardButton(text=f"Oddiy ({oddiy_price:,} so'm)".replace(',', ' '), callback_data="ref_tariff_oddiy")],
        [InlineKeyboardButton(text=f"PRO ({pro_price:,} so'm) 🔥".replace(',', ' '), callback_data="ref_tariff_pro")],
    ]
    if not has_promo:
        kb.append([InlineKeyboardButton(text="🎁 Promo-kod kiritish", callback_data="ref_promo")])
    kb.append([InlineKeyboardButton(text="⬅️ Ortga", callback_data="tariff_referat_back")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

# Kurs ishi tasdiqlash uchun inline tugmalar
course_confirm_inline_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✅Tayyorlash", callback_data="course_confirm")],
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

# Kurs ishi Tariflarini tanlash
def get_course_tariff_kb(has_promo: bool = False):
    oddiy_price = 4500 if has_promo else 15000
    pro_price = 8970 if has_promo else 29900
    kb = [
        [InlineKeyboardButton(text=f"Oddiy ({oddiy_price:,} so'm)".replace(',', ' '), callback_data="course_tariff_oddiy")],
        [InlineKeyboardButton(text=f"PRO ({pro_price:,} so'm) 🔥".replace(',', ' '), callback_data="course_tariff_pro")],
    ]
    if not has_promo:
        kb.append([InlineKeyboardButton(text="🎁 Promo-kod kiritish", callback_data="course_promo")])
    kb.append([InlineKeyboardButton(text="⬅️ Ortga", callback_data="tariff_course_back")])
    return InlineKeyboardMarkup(inline_keyboard=kb)



# Referat Reja tasdiqlash uchun
referat_plan_approval_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlayman", callback_data="plan_approve")],
        [InlineKeyboardButton(text="🔄 Boshqa reja", callback_data="plan_regenerate")],
        [InlineKeyboardButton(text="🚫 Bekor qilish", callback_data="plan_cancel")]
    ]
)

# Kurs ishi Reja tasdiqlash uchun
course_plan_approval_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlayman", callback_data="course_plan_approve")],
        [InlineKeyboardButton(text="🔄 Boshqa reja", callback_data="course_plan_regenerate")],
        [InlineKeyboardButton(text="🚫 Bekor qilish", callback_data="course_plan_cancel")]
    ]
)

__all__ = [
    "main_menu", "payment_keyboard", "send_receipt_kb", "get_admin_approval_kb",
    "presentation_mode_kb", "presentation_confirm_inline_kb",
    "presentation_img_confirm_kb", "template_selection_kb", 
    "language_selection_kb", "referat_confirm_inline_kb", "referat_edit_selection_kb",
    "course_confirm_inline_kb", "course_edit_selection_kb",
    "referat_type_kb", "referat_plan_approval_kb", "course_plan_approval_kb",
    "subscribe_channel_kb", "get_referat_tariff_kb", "get_course_tariff_kb",
    "get_page_selection_kb"
]
