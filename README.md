# Orzu Telegram bot

Botning referat/kurs ishi oqimlari, do‘st taklif qilish, oylik obuna va karta to‘lovlari. Taqdimot va maqola uchun [`telegram_ai_presentation`](https://github.com/sardororolov2233-afk/telegram_ai_presentation) backendidagi yangi mini ilova ochiladi.

| Xizmat | Qoida |
|---|---|
| Har 5 ta yangi tasdiqlangan do‘st | Bir oyga 5 ta taqdimot **va** 1 ta kurs ishi bepul |
| Yana 5 ta yangi do‘st | Mukofot yana beriladi |
| Bir oylik obuna | 25 000 so‘mga 10 ta taqdimot |
| Qo‘shimcha taqdimot | Yana takliflar yoki 10 000 so‘m / taqdimot |
| Qo‘shimcha kurs ishi | Yana takliflar yoki 30 000 so‘m / ish |
| Referat / mustaqil ish | 8 000 so‘m |
| Maqola | 10 000 so‘m |
| Karta | `9860020144204623` |

Obuna taqdimotlarni qamrab oladi. Kurs ishi, maqola va referat alohida. Kurs mukofoti muddatsiz, taqdimot mukofoti faollashgan sanadan bir kalendar oy amal qiladi. Obuna avtomatik yangilanmaydi. Taklif mukofoti obunadan alohida qo‘shiladi. Referat, maqola va kurs ishi yagona `deepseek/deepseek-r1-0528` bilan yaratiladi; boshqa modelga yashirin almashtirish yo‘q.

## Sozlash

1. Backend va bot uchun **bitta Supabase loyihasi** ishlating. [`supabase/migrations/20261017_commerce.sql`](supabase/migrations/20261017_commerce.sql) ni SQL Editor’da bajaring. Backenddagi fayl aynan shu migratsiya; ikki marta bajarish shart emas. Mavjud balanslar saqlanadi. Ikkala eski servisni to‘xtatib, migratsiyadan keyin yangi versiyalarni ishga tushiring: eski kod hali balansni oddiy o‘qish/yozish orqali o‘zgartiradi.
2. `.env.example` dan `.env` yarating: `BOT_TOKEN`, `SUPABASE_URL`, server `SUPABASE_SERVICE_ROLE_KEY`, `OPENROUTER_API_KEY`, `ADMIN_ID`, `BACKEND_URL` ni to‘ldiring. `ADMIN_ID` bir nechta bo‘lsa vergul bilan ajrating. Server kalitini mini ilovaga bermang.
3. Backendni uning README’si bo‘yicha doim ishlaydigan konteynerga joylashtiring. `BACKEND_URL` HTTPS host bo‘lsin; bot `/miniapp` ni qo‘shadi. `MINI_APP_URL` ixtiyoriy to‘liq override. Backenddagi `TELEGRAM_BOT_TOKEN` ayni shu `BOT_TOKEN`, `TELEGRAM_BOT_USERNAME` esa bot username’i bo‘lsin.
4. BotFather’da backend domenini sozlang. Botni `CHANNEL_USERNAME` kanaliga admin qiling; a’zolik tekshiruvi uchun kerak.
5. `pip install -r requirements.txt` va `python main.py`. Polling faqat shu servisda ishlaydi; backend webhook’ini yoqmang. Eski obyektivka interfeysi `FRONTEND_URL` orqali saqlangan.

Birinchi `/start` ikki yo‘lni ko‘rsatadi: do‘stlarni taklif qilish yoki 25 000 so‘mga obuna. Taklif `https://t.me/BOT_USERNAME?start=ref_TELEGRAM_ID` bilan keladi, kanalga o‘tishdan oldin saqlanadi. Mukofot yangi foydalanuvchining kanal a’zoligi tasdiqlangach hisoblanadi. O‘zini, eski yoki takroriy foydalanuvchini taklif qilish hisoblanmaydi.

`👤 Hisob va limitlar` bot hamda mini ilovadagi bir xil qolgan limitlarni ko‘rsatadi. `🎁 Do‘stlarni taklif qilish` shaxsiy havolani beradi. Taqdimot uchun bitta mini ilova tugmasi bor. Eskirgan tanlov tugmalari buyurtmani yashirin yaratmaydi.

## Karta to‘lovlari

Hisobni to‘ldirish va obuna uchun karta/chek tugmalari saqlangan. Chek AI tomonidan tahlil qilinadi, **admin kartaga tushumni tekshirib tasdiqlaydi**. `/payments` kutayotgan to‘lovlarni ochadi. Tasdiqlash/rad etish faqat `ADMIN_ID` ga ruxsat etilgan. Bir to‘lov qayta tasdiqlansa balans takror oshmaydi; eski cheklar himoyasi ham saqlanadi. Eski 50% bonus olib tashlangan.

## Ishonchlilik va tekshirish

Pullar va kreditlar Supabase tranzaksiyalari bilan band qilinadi. Tasdiqlashni takror bosish ikkinchi haq yechmaydi. Generatsiya xatosi pul yoki limitni qaytaradi. Bot jarayoni uzilsa, 3 daqiqalik band qilish muddati tugagach qaytarish ishlaydi; qoralamani qayta boshlash kerak. Backend navbati esa bazada saqlanadi.

```bash
pip install -r requirements-dev.txt
pytest -q
```

Qo‘shimcha SQL va ikkala repo integratsiya sinovlari backendning README’sida. Testlarda haqiqiy AI, Telegram yoki bankka pulli buyurtma yuborilmaydi. Ishlab turgan Supabase migratsiyasi, kalitlar, kanal huquqi, bir martalik haqiqiy AI generatsiyasi va haqiqiy chek/admin tasdig‘i server sozlamalari bilan tekshirilishi kerak.
