# Orzu Telegram bot

Telegram polling bot va [`telegram_ai_presentation`](https://github.com/sardororolov2233-afk/telegram_ai_presentation)
backend bir Supabase loyihasi, bir bot tokeni va bir taklif kvotasi balansidan foydalanadi.

| Xizmat / amal | Kvota |
|---|---|
| Har bir yangi, kanal a’zoligi tasdiqlangan do‘st | +1 |
| Taqdimot | −1 |
| Dizayn (3 ta variant) | −1 |
| Kurs ishi | −2 |
| Referat, mustaqil ish, maqola, obyektivka | Bepul |

Kvota umumiy va muddatsiz. Bitta kvotani bir nechta xizmatda qayta ishlatib bo‘lmaydi.
Obuna, to‘lov va balans to‘ldirish o‘chirilgan. Eski xabarlardagi to‘lov tugmalari ham hech narsa
sotib olmaydi, foydalanuvchini do‘st taklif qilishga yo‘naltiradi. Eski moliyaviy ma’lumotlar
tarix uchun saqlanadi; yangi xizmatlarda pul yechilmaydi.

Matn modeli: `anthropic/claude-haiku-5.5`. Backend rasmlari:
`bytedance-seed/seedream-5-0-flash`. Bir taqdimotda ko‘pi bilan 3 ta AI rasm yaratiladi,
ko‘proq rasmli shablonlarda ular qayta ishlatiladi. Foydalanuvchi pul to‘lamaydi;
OpenRouter API xarajatlarini loyiha egasi qoplaydi.

## Ishga tushirish

1. Bot va backendni birga yangilang. Umumiy Supabase’da eski `20261017_commerce.sql` bor bo‘lsa,
   faqat [`supabase/migrations/20261022_referral_only.sql`](supabase/migrations/20261022_referral_only.sql)
   ni bajaring. Yangi bazada ikkala migratsiya sana tartibida bajariladi. Backend reposidagi
   SQL nusxasi aynan bir xil; umumiy bazaga ikki marta alohida o‘rnatish shart emas.
2. Migratsiya eski sarflanmagan taklif mukofotlarini saqlaydi; 5 kishilik chegaraga yetmagan
   tasdiqlangan takliflarni ham hisoblaydi. Qayta bajarish kvotani takrorlamaydi. Eski pul
   balansi va obuna kvotaga aylantirilmaydi.
3. `.env.example` asosida `.env` yarating. `BOT_TOKEN`, `OPENROUTER_API_KEY`,
   `SUPABASE_URL`, server uchun `SUPABASE_SERVICE_ROLE_KEY`, `CHANNEL_USERNAME`,
   `BACKEND_URL=https://BACKEND_HOST` kerak. `MINI_APP_URL` berilmasa bot backenddagi `/miniapp`
   oynasini ochadi. Obyektivkaning eski tashqi oynasi uchun `FRONTEND_URL` saqlangan.
4. Kanal a’zoligini tekshirish uchun botni rasmiy kanalga admin qiling.
5. `pip install -r requirements.txt` va `python main.py`. `ADMIN_ID` faqat admin menyusi uchun
   ixtiyoriy; to‘lovni tasdiqlash endi yo‘q. Yangi `commerce_policy` RPC o‘rnatilmaguncha bot
   so‘rov qabul qilmaydi.

Taklif birinchi `/start ref_ID` da bog‘lanadi. Kanalga o‘tish vaqtida yo‘qolmaydi. Keyingi
havola uni o‘zgartirmaydi. Faqat yangi Telegram foydalanuvchisi, bir marta tasdiqlanganda
1 kvota beradi; o‘zini, botni, eski yoki qayta kelgan foydalanuvchini taklif qilish hisoblanmaydi.

Kurs ishi va referat tasdiqlash tugmalari bir buyurtmaga bitta doimiy UUID beradi. Takroriy
bosish ishni qayta yaratmaydi. Kurs kvotasi bazada atomar band qilinadi; xatoda bir marta qaytadi.
Referat bepul. Jarayon uzilib qolsa eskirgan band qilish qaytariladi. Telegram yangilanishlarini
faqat shu polling bot qabul qiladi — parallel webhook yoqmang.

## Tekshiruvlar

```bash
pip install -r requirements-dev.txt
pytest -q
```

Bot sinovlari yangi model, bepul xizmatlar, umumiy kvota, eski to‘lov tugmalarining yopilgani,
takroriy bosish va xatoda qaytarishni tekshiradi. Backend reposida SQL va bot → API → haqiqiy
PPTX/DOCX sinovlari ham bor. `commerce.py` hamda ikkala SQL migratsiyasi ikkala repoda mos bo‘lsin.
