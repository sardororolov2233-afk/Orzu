# Orzu’ni Telegram Serverless’da ishlatish

Bu alohida sinov boti emas: `tgcloud/` shu Orzu / `@Yordamchi_taalaba_bot`
uchun yozilgan. Python polling o‘rniga Telegram Serverless xabarlar va tugmalarni
qabul qiladi. Menyu, kanal tekshiruvi, referal, balans, obuna, karta/chek va admin
tasdig‘i saqlanadi. Referat va kurs ishi chat orqali to‘ldiriladi, reja tasdiqlanadi,
keyin mavjud backend navbatida DOCX tayyorlanadi. Taqdimot va maqola hozirgi
mini ilovada ochiladi. Obyektivka havolasi saqlangan.

## 1. Avval backend

Mos backend o‘zgarishlarini `telegram_ai_presentation` reposining
`codex/telegram-serverless` tarmog‘idan joylashtiring. Uning yangi worker’i
`course` va `referat` navbatlarini ham ishlaydi. Backend `/health` javobidagi
`features` ro‘yxatida `serverless-academic-queue-v1` ko‘rinishi kerak.
Bu imkoniyat bo‘lmasa bot kurs/referat buyurtmasini qabul qilmaydi va pul yechmaydi.

Supabase SQL Editor’da mavjud `20261017_commerce.sql` migratsiyasidan **keyin**
[`20261018_serverless.sql`](../supabase/migrations/20261018_serverless.sql) ni
bajaring. Ikkala repodagi yangi SQL aynan bir xil, bitta umumiy bazada bir marta
bajarish kifoya. Balanslar, mukofotlar, cheklar va eski buyurtmalar saqlanadi.

Migratsiya suhbat holati va takroriy Telegram update’lari uchun server-only
jadvallar qo‘shadi. Yangi moliyaviy hisob yoki Telegram bazasi yo‘q. Telegram’da
`tgcloud migrate` bajarish shart emas.

## 2. Orzu reposi va sozlamalar

Orzu ishlagan kompyuter yoki SSH terminalida Node.js 22.15+ (tavsiya: 24) kerak:

```bash
cd "$HOME/Orzu"
git fetch origin
git switch codex/telegram-serverless
npm ci --ignore-scripts
npm run check
npm test
npm run configure
```

`configure` mavjud `.env` ni qayta ishlatadi. Kerakli qiymatlar:
`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` (yoki `SUPABASE_KEY`),
`OPENROUTER_API_KEY`, raqamli `ADMIN_ID`, `CHANNEL_USERNAME`, `BACKEND_URL`.
`MINI_APP_URL` va `FRONTEND_URL` ixtiyoriy override’lar. Zarur bo‘lsa
`.env.serverless.example` dan mahalliy `.env.serverless` yarating. U `.env`
qiymatlarini almashtiradi; terminaldagi env ustun turadi.

Skript maxfiy qiymatlarni backend-only `tgcloud/lib/private.js` moduliga yozadi.
Bu modul Git’dan chiqarilgan va faqat Telegram backend’iga deploy bo‘ladi.
Uni commit qilmang. Token/kalitlarni chatga, screenshot’ga yoki GitHub’ga yubormang.
Bot API tokeni Serverless modullariga kerak emas; Telegram SDK o‘zi ulanadi.

## 3. Shu botni BotFather’da ulash

1. Orzu’ning eski `python main.py` polling jarayoni yoki Alwaysdata servisini to‘xtating.
2. `@BotFather` → **shu bot** → **Serverless** ni yoqing.
3. **CLI Access → Access token** ni oching. Bu `app...:...` shaklidagi alohida
   CLI token; oddiy Bot API tokeni emas.
4. Terminalda quyidagini bajaring va tokenni **faqat uning so‘roviga** kiriting:

```bash
npm run login
npm run deploy
npm run webhook
```

CLI tokenini ChatGPT’ga yuborish kerak emas. Token `.tgcloud/` ichida, Git’dan
tashqarida saqlanadi. `deploy` dan keyin webhook **In sync** bo‘lishi kerak.
Platforma webhook’ni boshqaradi; boshqa `setWebhook` yoki `deleteWebhook`
chaqirmang. Python polling va API webhook’ini yonma-yon ishga tushirmang.

Muvaffaqiyatli `deploy` dan keyin mahalliy `.env` ga
`BOT_TRANSPORT=serverless` yoziladi. Shu checkout’dagi eski `main.py` qayta
ishlasa boshqariladigan webhook’ni o‘chirib yubormaydi. Boshqa serverdagi eski
bot nusxalarini ham to‘xtatish kerak; bu belgi boshqa serverga avtomatik ko‘chmaydi.

## 4. Shu botda tekshirish

`/start` → kanalni tasdiqlash → asosiy menyu. Keyin:

- `👤 Hisob va limitlar`: avvalgi balans va mukofotlar.
- `🎁 Do‘stlarni taklif qilish`: ayni botdagi shaxsiy havola.
- `💳 Hisobni to‘ldirish`: karta `9860020144204623`, chek va admin tasdig‘i.
- `Kurs ishi` yoki `Referat`: ma’lumotlar → DeepSeek R1 reja → aniq narx yoki
  mukofot bilan tasdiqlash → navbat → fayl shu chatda.
- `/payments` va `/admin`: faqat sozlangan adminlar.
- Taqdimot/maqola: mavjud mini ilova. Tayyor faylni `Buyurtma holati` orqali ham
  mini ilovadan yuklab olish mumkin.

AI chek tahlili pul qo‘shmaydi; admin kartaga tushumni tasdiqlaydi. Hash va
tranzaksiya himoyasi Supabase’da qoladi. Telegram xabari qayta yetkazilsa
buyurtma uchun pul qayta yechilmaydi. Suhbat holati isolate xotirasida emas,
Supabase’da saqlanadi; tashlab ketilgan qoralama 2 kundan keyin bekor bo‘ladi.
Broadcast admin tasdig‘i bilan har safar 15 foydalanuvchiga yuboriladi; keyingi
guruh uchun admin Davom ettirish tugmasini bosadi.

## Qaytish

BotFather’da Serverless’ni o‘chiring. Eski polling’ga qaytish uchun `.env` dagi
`BOT_TRANSPORT=polling` ni belgilang va `python main.py` ni ishga tushiring.
Ikkala rejim ham bitta bazani ishlatadi. Backend navbatidagi buyurtmalar worker’da
davom etadi; yangi chat qoralamasini menyudan qayta boshlash mumkin.

## Tekshiruv chegarasi

Mahalliy testlarda haqiqiy Telegram, AI va bank so‘rovlari bajarilmaydi. Supabase
RPC’lari PostgreSQL/PGlite’da, bot esa SDK adapterida tekshiriladi. Haqiqiy botda
ishga tushirish, platformadagi bajarilish muddati, uzoq DeepSeek reja so‘rovi va
tarif/kvotalarni BotFather orqali tekshirish qoladi. Serverless CLI tokeni bo‘lmasa
kod GitHub’da tayyor bo‘ladi, lekin Telegram’ga deploy qilinmagan bo‘ladi.

Rasmiy qo‘llanma: https://core.telegram.org/bots/serverless
