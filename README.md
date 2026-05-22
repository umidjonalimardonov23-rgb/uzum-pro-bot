# 🛍 UZUM MARKET — Telegram Mini App

Uzum Market uslubidagi to'liq Telegram Mini App do'kon.

## 📦 Tuzilish

```
uzum_bot/
├── app.py              ← Flask backend (API + sahifalar)
├── bot.py              ← Telegram bot (aiogram 3.x)
├── requirements.txt
├── .env.example        ← Bu faylni .env ga nusxalang
└── templates/
    ├── index.html      ← Mini App (Uzum Market uslubi)
    ├── login.html      ← Admin kirish sahifasi
    └── admin.html      ← Admin panel
```

## ⚡ O'rnatish

```bash
# 1. Paketlarni o'rnating
pip install -r requirements.txt

# 2. .env faylini yarating
cp .env.example .env
# .env faylini oching va qiymatlarni to'ldiring

# 3. Web serverni ishga tushiring
python app.py

# 4. Botni ishga tushiring (yangi terminlda)
python bot.py
```

## 🔑 .env to'ldirish

| O'zgaruvchi | Qiymat |
|---|---|
| `BOT_TOKEN` | @BotFather dan olingan token |
| `ADMIN_ID` | Sizning Telegram ID (@userinfobot orqali bilib oling) |
| `WEB_APP_URL` | Mini App URL (masalan: https://myshop.com) |
| `ADMIN_PASSWORD` | Admin panel paroli (murakkab qiling!) |
| `SECRET_KEY` | Tasodifiy uzun satr (python -c "import secrets; print(secrets.token_hex(32))") |

## 🤖 Bot imkoniyatlari

| Buyruq | Tavsif |
|---|---|
| `/start` | Xush kelibsiz + Mini App tugmasi |
| `/orders` | Foydalanuvchi buyurtmalari |
| `/help` | Yordam |
| `/admin` | Admin panel (faqat admin uchun) |

### Admin callback tugmalar:
- **✅ Tasdiqlash** → Buyurtmani tasdiqlaydi + foydalanuvchiga xabar
- **🚚 Yetkazishda** → Status o'zgartiradi + xabar
- **🎉 Yetkazildi** → Yakunlaydi + xabar
- **❌ Bekor** → Bekor qiladi + xabar

## 🌐 Admin Panel

URL: `https://your-domain.com/admin`

- 📊 Statistika (jami, bugungi, daromad)
- 📦 Buyurtmalar (filter, status o'zgartirish)
- 🛍 Mahsulotlar ro'yxati
- ➕ Mahsulot qo'shish / tahrirlash / o'chirish

## 🔒 Xavfsizlik

✅ Parol URL da emas (POST forma orqali)  
✅ Admin API session bilan himoyalangan  
✅ Karta raqami API da chiqmaydi  
✅ Real ma'lumotlar .env da, kodda emas  
✅ debug=False  
✅ Input validatsiya  

## 📱 Mini App imkoniyatlari

- 🎠 Banner slider (auto-scroll)
- 📂 Kategoriya filtri
- 🏷 Badge filtri (SALE, NEW, HOT...)
- 🔍 Real-time qidiruv
- ⇅ Saralash (yangi, mashhur, narx, reyting)
- ❤️ Sevimlilar
- 🛒 Savat (localStorage)
- 📦 Checkout (telefon, manzil, to'lov usuli)
- ✅ Buyurtma tasdiqlanishi animatsiya
- 📲 Telegram WebApp sendData integratsiya
