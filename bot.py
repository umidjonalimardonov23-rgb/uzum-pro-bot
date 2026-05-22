import os, asyncio, json, sqlite3, random, string
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import (Message, InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    BotCommand, BotCommandScopeChat, BotCommandScopeDefault)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ── CONFIG ────────────────────────────────────────────────────────────────────
BOT_TOKEN  = os.environ["BOT_TOKEN"]
ADMIN_ID   = int(os.environ["ADMIN_ID"])
WEB_URL    = os.getenv("WEB_APP_URL", "https://uzum-pro-bot.onrender.com")
SHOP_NAME  = os.getenv("SHOP_NAME", "UZUM MARKET")
SUPPORT    = os.getenv("SUPPORT", "@support")
DB_NAME    = os.getenv("DB_NAME", "uzum_market.db")
CHANNEL    = os.getenv("CHANNEL_ID", "@UZUM_AMAZON")

bot     = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp      = Dispatcher(storage=storage)

# ── STATES ────────────────────────────────────────────────────────────────────
class AddProd(StatesGroup):
    photo     = State()
    name      = State()
    price     = State()
    old_price = State()
    desc      = State()
    badge     = State()
    stock     = State()
    category  = State()

class Broadcast(StatesGroup):
    msg = State()

class PromoCreate(StatesGroup):
    code     = State()
    discount = State()
    max_uses = State()

class OrderReply(StatesGroup):
    msg = State()

# ── DB ────────────────────────────────────────────────────────────────────────
def db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def fmt(n):
    try: return f"{int(n):,}".replace(",", " ")
    except: return str(n)

def init_db():
    conn = db(); c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS categories(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE, icon TEXT DEFAULT '🛍', sort_order INTEGER DEFAULT 0)""")
    c.execute("""CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id INTEGER DEFAULT 1,
        name TEXT NOT NULL, description TEXT DEFAULT '',
        price INTEGER NOT NULL, old_price INTEGER DEFAULT 0,
        image TEXT DEFAULT '', badge TEXT DEFAULT 'NEW',
        stock INTEGER DEFAULT 99, active INTEGER DEFAULT 1,
        rating REAL DEFAULT 4.5, sold_count INTEGER DEFAULT 0,
        sizes TEXT DEFAULT '', colors TEXT DEFAULT '',
        created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_user_id TEXT, full_name TEXT, phone TEXT,
        items TEXT, total INTEGER, status TEXT DEFAULT 'new',
        note TEXT DEFAULT '', size TEXT DEFAULT '', color TEXT DEFAULT '',
        promo_code TEXT DEFAULT '', discount INTEGER DEFAULT 0,
        created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_user_id TEXT UNIQUE, full_name TEXT, username TEXT,
        phone TEXT DEFAULT '', referral_code TEXT UNIQUE,
        referred_by TEXT DEFAULT '', points INTEGER DEFAULT 0,
        total_spent INTEGER DEFAULT 0, orders_count INTEGER DEFAULT 0,
        vip INTEGER DEFAULT 0, blocked INTEGER DEFAULT 0, joined_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS promo_codes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE, discount_percent INTEGER DEFAULT 10,
        max_uses INTEGER DEFAULT 100, used_count INTEGER DEFAULT 0,
        active INTEGER DEFAULT 1, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS banners(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT, subtitle TEXT, color TEXT DEFAULT '#7c2cff',
        badge TEXT DEFAULT '', active INTEGER DEFAULT 1)""")

    c.execute("SELECT COUNT(*) FROM categories")
    if c.fetchone()[0] == 0:
        cats = [
            ("Erkaklar","👔",1),
            ("Ayollar","👗",2),
            ("Bolalar","🧒",3),
            ("Sport kiyim","🏃",4),
            ("Poyabzal","👟",5),
            ("Aksessuarlar","👜",6),
            ("Qishki kiyim","🧥",7),
            ("Ichki kiyim","🩲",8),
        ]
        c.executemany("INSERT INTO categories(name,icon,sort_order) VALUES(?,?,?)", cats)

    c.execute("SELECT COUNT(*) FROM promo_codes")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO promo_codes(code,discount_percent,max_uses,active,created_at) VALUES(?,?,?,?,?)",
                  ("FASHION10", 10, 1000, 1, now()))

    c.execute("SELECT COUNT(*) FROM banners")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO banners(title,subtitle,color,badge) VALUES(?,?,?,?)", [
            ("Yangi kolleksiya!","Kuz-qish mavsumi kiyimlari yetib keldi","#7c2cff","YANGI"),
            ("Mega chegirma -30%","Barcha sport kiyimlariga katta chegirma","#ff6b35","SALE"),
            ("Bestseller kiyimlar","Eng ko'p sotilgan modellar","#00c853","TOP"),
        ])
    conn.commit(); conn.close()

def get_user(tg_id):
    conn = db()
    r = conn.execute("SELECT * FROM users WHERE tg_user_id=?", (str(tg_id),)).fetchone()
    conn.close()
    return dict(r) if r else None

def reg_user(tg_id, name, username, ref=""):
    conn = db(); c = conn.cursor()
    ex = conn.execute("SELECT id FROM users WHERE tg_user_id=?", (str(tg_id),)).fetchone()
    if not ex:
        rc = ''.join(random.choices(string.ascii_uppercase+string.digits, k=8))
        c.execute("INSERT INTO users(tg_user_id,full_name,username,referral_code,referred_by,joined_at) VALUES(?,?,?,?,?,?)",
                  (str(tg_id), name, username or "", rc, ref, now()))
        if ref:
            c.execute("UPDATE users SET points=points+200 WHERE referral_code=?", (ref,))
        conn.commit()
    conn.close()

# ── KEYBOARDS ─────────────────────────────────────────────────────────────────
def main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🛍 Do'konni ochish", web_app=WebAppInfo(url=WEB_URL))],
        [KeyboardButton(text="🛒 Buyurtmalarim"), KeyboardButton(text="🏆 Ballarim")],
        [KeyboardButton(text="👥 Do'stni taklif qil"), KeyboardButton(text="📞 Yordam")],
    ], resize_keyboard=True)

def admin_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="➕ Mahsulot qo'shish")],
        [KeyboardButton(text="📦 Buyurtmalar"), KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="📢 Broadcast"), KeyboardButton(text="🏷️ Promo kod")],
        [KeyboardButton(text="👥 Foydalanuvchilar"), KeyboardButton(text="❌ Mahsulot o'chirish")],
        [KeyboardButton(text="🛍 Do'konni ochish", web_app=WebAppInfo(url=WEB_URL))],
    ], resize_keyboard=True)

def badge_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ YANGI",       callback_data="b_YANGI"),
         InlineKeyboardButton(text="🔥 HOT",         callback_data="b_HOT")],
        [InlineKeyboardButton(text="💸 SALE",        callback_data="b_SALE"),
         InlineKeyboardButton(text="⭐ TOP",         callback_data="b_TOP")],
        [InlineKeyboardButton(text="🏷️ CHEGIRMA",   callback_data="b_CHEGIRMA"),
         InlineKeyboardButton(text="🏆 BESTSELLER",  callback_data="b_BESTSELLER")],
        [InlineKeyboardButton(text="⏳ LIMITED",     callback_data="b_LIMITED"),
         InlineKeyboardButton(text="Badge yo'q",     callback_data="b_")],
    ])

def cat_kb():
    conn = db()
    cats = conn.execute("SELECT * FROM categories ORDER BY sort_order").fetchall()
    conn.close()
    kb = InlineKeyboardBuilder()
    for cat in cats:
        kb.button(text=f"{cat['icon']} {cat['name']}", callback_data=f"cat_{cat['id']}")
    kb.adjust(2)
    return kb.as_markup()

def order_kb(order_id, status):
    kb = InlineKeyboardBuilder()
    if status == "new":
        kb.button(text="✅ Tasdiqlash",  callback_data=f"o_confirm_{order_id}")
        kb.button(text="❌ Bekor qilish", callback_data=f"o_cancel_{order_id}")
    elif status == "confirmed":
        kb.button(text="🚚 Yo'lda",      callback_data=f"o_deliver_{order_id}")
        kb.button(text="❌ Bekor",        callback_data=f"o_cancel_{order_id}")
    elif status == "delivering":
        kb.button(text="🎉 Yetkazildi",  callback_data=f"o_done_{order_id}")
    kb.button(text="💬 Xabar yozish",    callback_data=f"o_reply_{order_id}")
    kb.adjust(2)
    return kb.as_markup()

STATUS = {
    "new":        ("🆕", "Yangi"),
    "confirmed":  ("✅", "Tasdiqlangan"),
    "delivering": ("🚚", "Yetkazilmoqda"),
    "delivered":  ("🎉", "Yetkazildi"),
    "cancelled":  ("❌", "Bekor"),
}

def order_text(o, admin=False):
    em, lb = STATUS.get(o.get("status","new"), ("❓","?"))
    try: items = json.loads(o.get("items","[]"))
    except: items = []
    lines = "".join(f"  • {i.get('name','?')} × {i.get('qty',1)} — {fmt(i.get('price',0)*i.get('qty',1))} so'm\n" for i in items[:10])
    disc = o.get("discount",0)
    total = o.get("total",0)
    pay = o.get("payment","naqd")
    pay_lbl = "💳 Plastik karta" if pay == "karta" else "💵 Naqd pul"
    txt = f"{em} <b>Buyurtma #{o['id']}</b> — <b>{lb}</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    if admin: txt += f"👤 ID: <code>{o.get('tg_user_id','-')}</code>\n"
    txt += f"🙋 <b>{o.get('full_name','-')}</b>\n📞 <code>{o.get('phone','-')}</code>\n"
    txt += f"{pay_lbl}\n"
    if o.get("size"):  txt += f"📏 O'lcham: {o['size']}\n"
    if o.get("color"): txt += f"🎨 Rang: {o['color']}\n"
    if o.get("promo_code"): txt += f"🏷️ Promo: {o['promo_code']} (-{disc}%)\n"
    if o.get("note"): txt += f"💬 {o['note']}\n"
    txt += f"\n🛍 Mahsulotlar:\n{lines}\n💰 <b>Jami: {fmt(total)} so'm</b>\n🕐 {o.get('created_at','')}"
    return txt

async def is_sub(uid):
    try:
        m = await bot.get_chat_member(CHANNEL, uid)
        return m.status not in ("left","kicked","banned")
    except: return True

# ── /START ────────────────────────────────────────────────────────────────────
@dp.message(CommandStart())
async def start(msg: Message, state: FSMContext):
    await state.clear()
    uid  = msg.from_user.id
    name = f"{msg.from_user.first_name or ''} {msg.from_user.last_name or ''}".strip() or "Foydalanuvchi"
    uname = msg.from_user.username or ""
    args  = msg.text.split()
    ref   = args[1] if len(args) > 1 else ""
    reg_user(uid, name, uname, ref)

    # ADMIN
    if uid == ADMIN_ID:
        conn = db()
        prods   = conn.execute("SELECT COUNT(*) FROM products WHERE active=1").fetchone()[0]
        orders  = conn.execute("SELECT COUNT(*) FROM orders WHERE status='new'").fetchone()[0]
        users_c = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        rev     = conn.execute("SELECT COALESCE(SUM(total),0) FROM orders WHERE status='delivered'").fetchone()[0]
        conn.close()
        await msg.answer(
            f"👑 <b>ADMIN PANEL — {SHOP_NAME}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📦 Mahsulotlar: <b>{prods} ta</b>\n"
            f"🆕 Yangi buyurtmalar: <b>{orders} ta</b>\n"
            f"👥 Foydalanuvchilar: <b>{users_c} ta</b>\n"
            f"💰 Jami daromad: <b>{fmt(rev)} so'm</b>\n\n"
            "👇 Quyidagi tugmalardan foydalaning:",
            reply_markup=admin_kb()
        )
        return

    # OBUNA TEKSHIRISH
    if not await is_sub(uid):
        await msg.answer(
            f"👋 Salom, <b>{name}</b>!\n\n"
            f"🔒 <b>{SHOP_NAME}</b> ga kirish uchun\n"
            "avval kanalimizga obuna bo'ling!\n\n"
            "📢 Kanalda: chegirmalar, yangiliklar, sovg'alar!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"📢 Kanalga obuna bo'lish", url=f"https://t.me/{CHANNEL.lstrip('@')}")],
                [InlineKeyboardButton(text="✅ Obuna bo'ldim, kirish", callback_data="check_sub")],
            ])
        )
        return

    u = get_user(uid)
    pts = u["points"] if u else 0
    vip = "👑 VIP" if (u and u["vip"]) else ""
    await msg.answer(
        f"👋 Salom, <b>{name}</b>! {vip}\n\n"
        f"🛍 <b>{SHOP_NAME}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⭐ Ballaringiz: <b>{fmt(pts)}</b>\n"
        "🔥 Eng yaxshi narxlar!\n"
        "🆓 Yangi obunachilarga promo kod: <code>UZUM10</code> (-10%)\n\n"
        "👇 Do'konni oching:",
        reply_markup=main_kb()
    )

@dp.callback_query(F.data == "check_sub")
async def check_sub(call: CallbackQuery, state: FSMContext):
    if not await is_sub(call.from_user.id):
        await call.answer("❌ Hali obuna bo'lmagansiz!", show_alert=True); return
    await call.message.delete()
    uid   = call.from_user.id
    name  = f"{call.from_user.first_name or ''} {call.from_user.last_name or ''}".strip()
    uname = call.from_user.username or ""
    reg_user(uid, name, uname)
    await call.message.answer(
        f"✅ Rahmat! Xush kelibsiz, <b>{name}</b>!\n\n"
        "🎁 Birinchi xaridingizga promo kod: <code>UZUM10</code> (-10%)\n\n"
        "👇 Do'konni oching:",
        reply_markup=main_kb()
    )

# ── FOYDALANUVCHI TUGMALARI ───────────────────────────────────────────────────
@dp.message(F.text == "🛒 Buyurtmalarim")
async def my_orders(msg: Message):
    conn = db()
    rows = conn.execute("SELECT * FROM orders WHERE tg_user_id=? ORDER BY id DESC LIMIT 5",
                        (str(msg.from_user.id),)).fetchall()
    conn.close()
    if not rows:
        await msg.answer("📭 Hali buyurtma bermadingiz!\n\n🛍 Do'konni oching va xarid qiling!", reply_markup=main_kb())
        return
    await msg.answer("📦 <b>Oxirgi 5 ta buyurtmangiz:</b>")
    for r in rows:
        o = dict(r)
        em, lb = STATUS.get(o["status"], ("❓","?"))
        await msg.answer(f"{em} <b>#{o['id']}</b> — {lb}\n💰 {fmt(o['total'])} so'm\n🕐 {o['created_at']}")

@dp.message(F.text == "🏆 Ballarim")
async def my_points(msg: Message):
    u = get_user(msg.from_user.id)
    if not u:
        await msg.answer("❌ Ma'lumot topilmadi"); return
    vip = "👑 VIP mijoz" if u["vip"] else "⬆️ VIP ga: 500 000 so'm xarid kerak"
    await msg.answer(
        f"🏆 <b>Sizning profilingiz</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 {u['full_name']}\n"
        f"⭐ Ballar: <b>{fmt(u['points'])}</b>\n"
        f"📦 Buyurtmalar: <b>{u['orders_count']}</b>\n"
        f"💰 Jami xarid: <b>{fmt(u['total_spent'])} so'm</b>\n"
        f"🎖 Status: <b>{vip}</b>\n\n"
        f"📌 Ball olish usullari:\n"
        f"  • Har 1 000 so'm xarid = 1 ball\n"
        f"  • Do'st taklif = 200 ball\n"
        f"  🎁 500 ball = 5 000 so'm chegirma",
        reply_markup=main_kb()
    )

@dp.message(F.text == "👥 Do'stni taklif qil")
async def referral(msg: Message):
    u = get_user(msg.from_user.id)
    if not u:
        await msg.answer("❌ Avval /start bosing"); return
    rc = u["referral_code"]
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={rc}"
    conn = db()
    inv = conn.execute("SELECT COUNT(*) FROM users WHERE referred_by=?", (rc,)).fetchone()[0]
    conn.close()
    await msg.answer(
        f"👥 <b>Referal tizimi</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Do'stingizni taklif qiling → <b>200 ball</b> oling!\n\n"
        f"🔗 Sizning havolangiz:\n<code>{link}</code>\n\n"
        f"👥 Taklif qilganlar: <b>{inv} ta</b>\n"
        f"⭐ Ballaringiz: <b>{fmt(u['points'])}</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Do'stlarga ulashish",
             url=f"https://t.me/share/url?url={link}&text=🛍 {SHOP_NAME} da ajoyib narxlar! Obuna bo'ling!")],
        ])
    )

@dp.message(F.text == "📞 Yordam")
async def support(msg: Message):
    await msg.answer(
        f"📞 <b>Yordam markazi</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Admin bilan bog'laning: {SUPPORT}\n\n"
        f"🕐 Ish vaqti: 09:00 — 22:00",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Adminga yozish", url=f"https://t.me/{SUPPORT.lstrip('@')}")],
        ])
    )

# ── ADMIN: MAHSULOT QO'SHISH ──────────────────────────────────────────────────
@dp.message(F.text == "➕ Mahsulot qo'shish")
async def add_product_start(msg: Message, state: FSMContext):
    if msg.from_user.id != ADMIN_ID: return
    await state.clear()
    await state.update_data(photos=[])
    await msg.answer(
        "📸 <b>Mahsulot qo'shish</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        "1️⃣ <b>Mahsulot rasmini yuboring</b>\n"
        "• 10 tagacha rasm yuborishingiz mumkin\n"
        "• Birinchi rasm — asosiy rasm bo'ladi\n\n"
        "Rasmlar yuborib bo'lgach, <b>Nomini yozish</b> tugmasini bosing:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Nomini yozishga o'tish →", callback_data="to_name")]
        ])
    )
    await state.set_state(AddProd.photo)

@dp.message(AddProd.photo, F.photo)
async def got_photos(msg: Message, state: FSMContext):
    if msg.from_user.id != ADMIN_ID: return
    data   = await state.get_data()
    photos = data.get("photos", [])
    fid    = msg.photo[-1].file_id
    f      = await bot.get_file(fid)
    url    = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{f.file_path}"
    photos.append(url)
    await state.update_data(photos=photos)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ {len(photos)} ta rasm | Nomini yozish →", callback_data="to_name")]
    ])
    await msg.answer(f"📸 {len(photos)}-rasm qabul qilindi! {'(max 10)' if len(photos)<10 else '✅ Maksimal'}\nYana rasm yuboring yoki nomini yozishga o'ting:", reply_markup=kb)
    if len(photos) >= 10:
        await state.set_state(AddProd.name)
        await msg.answer("✏️ Mahsulot <b>nomini</b> yozing:", reply_markup=ReplyKeyboardRemove())

@dp.callback_query(F.data == "to_name")
async def to_name(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    data = await state.get_data()
    if not data.get("photos"):
        await call.answer("❌ Kamida 1 ta rasm yuboring!", show_alert=True); return
    await call.message.answer("✏️ Mahsulot <b>nomini</b> yozing:\nMasalan: Oversize Futbolka", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AddProd.name)

@dp.message(AddProd.name)
async def got_name(msg: Message, state: FSMContext):
    if msg.from_user.id != ADMIN_ID: return
    await state.update_data(name=msg.text.strip())
    await msg.answer("💰 <b>Narxini</b> yozing (faqat raqam, so'mda):\nMasalan: 150000")
    await state.set_state(AddProd.price)

@dp.message(AddProd.price)
async def got_price(msg: Message, state: FSMContext):
    if msg.from_user.id != ADMIN_ID: return
    try:
        p = int(msg.text.strip().replace(" ","").replace(",",""))
        await state.update_data(price=p)
        await msg.answer("💸 <b>Eski narxini</b> yozing (chegirma ko'rsatish uchun):\nMasalan: 200000\n\n<i>Chegirma bo'lmasa 0 yozing</i>")
        await state.set_state(AddProd.old_price)
    except:
        await msg.answer("❌ Faqat raqam! Masalan: 150000")

@dp.message(AddProd.old_price)
async def got_old(msg: Message, state: FSMContext):
    if msg.from_user.id != ADMIN_ID: return
    try:
        o = int(msg.text.strip().replace(" ","").replace(",",""))
        await state.update_data(old_price=o)
        await msg.answer("📝 <b>Tavsifini</b> yozing:\nMasalan: 100% paxta, S-XXL o'lcham\n\n<i>Tavsif bo'lmasa 0 yozing</i>")
        await state.set_state(AddProd.desc)
    except:
        await msg.answer("❌ Faqat raqam!")

@dp.message(AddProd.desc)
async def got_desc(msg: Message, state: FSMContext):
    if msg.from_user.id != ADMIN_ID: return
    desc = "" if msg.text.strip() == "0" else msg.text.strip()
    await state.update_data(description=desc)
    await msg.answer("🏷️ <b>Badge tanlang:</b>", reply_markup=badge_kb())
    await state.set_state(AddProd.badge)

@dp.callback_query(F.data.startswith("b_"), AddProd.badge)
async def got_badge(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    badge = call.data[2:]
    await state.update_data(badge=badge)
    await call.message.answer("📂 <b>Kategoriya tanlang:</b>", reply_markup=cat_kb())
    await state.set_state(AddProd.category)

@dp.callback_query(F.data.startswith("cat_"), AddProd.category)
async def got_cat(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    cat_id = int(call.data[4:])
    await state.update_data(category_id=cat_id)
    await call.message.answer("📦 <b>Stok miqdori</b> yozing:\nMasalan: 50\n\n<i>Cheksiz bo'lsa 9999 yozing</i>")
    await state.set_state(AddProd.stock)

@dp.message(AddProd.stock)
async def got_stock(msg: Message, state: FSMContext):
    if msg.from_user.id != ADMIN_ID: return
    try:
        stock = int(msg.text.strip())
    except:
        await msg.answer("❌ Faqat raqam!"); return

    data   = await state.get_data()
    photos = data.get("photos", [])
    img    = photos[0] if photos else ""
    name   = data.get("name","")
    price  = data.get("price", 0)
    old    = data.get("old_price", 0)
    desc   = data.get("description","")
    badge  = data.get("badge","NEW")
    cat_id = data.get("category_id", 1)

    conn = db(); cur = conn.cursor()
    cur.execute("""INSERT INTO products(category_id,name,description,price,old_price,image,badge,stock,active,rating,sold_count,created_at)
        VALUES(?,?,?,?,?,?,?,?,1,4.5,0,?)""",
        (cat_id, name, desc, price, old, img, badge, stock, now()))
    pid = cur.lastrowid
    conn.commit(); conn.close()

    disc = round((1-price/old)*100) if old > price > 0 else 0
    caption = (
        f"✅ <b>Mahsulot qo'shildi! #{pid}</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 <b>{name}</b>\n"
        f"💰 {fmt(price)} so'm" +
        (f" | 💸 {fmt(old)} so'm (-{disc}%)" if disc else "") +
        (f"\n📝 {desc}" if desc else "") +
        f"\n🏷️ {badge} | 📦 {stock} ta | 🖼 {len(photos)} rasm"
    )
    try:
        await msg.answer_photo(img, caption=caption)
    except:
        await msg.answer(caption)

    await msg.answer(
        "🎉 Do'konga qo'shildi!",
        reply_markup=ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text="➕ Yana mahsulot qo'shish")],
            [KeyboardButton(text="📦 Buyurtmalar"), KeyboardButton(text="📊 Statistika")],
            [KeyboardButton(text="🛍 Do'konni ochish", web_app=WebAppInfo(url=WEB_URL))],
            [KeyboardButton(text="🔙 Admin panelga qaytish")],
        ], resize_keyboard=True)
    )
    await state.clear()

@dp.message(F.text == "➕ Yana mahsulot qo'shish")
async def add_again(msg: Message, state: FSMContext):
    if msg.from_user.id != ADMIN_ID: return
    await add_product_start(msg, state)

@dp.message(F.text == "🔙 Admin panelga qaytish")
async def back_admin(msg: Message, state: FSMContext):
    if msg.from_user.id != ADMIN_ID: return
    await state.clear()
    await start(msg, state)

# ── ADMIN: BUYURTMALAR ────────────────────────────────────────────────────────
@dp.message(F.text == "📦 Buyurtmalar")
async def admin_orders(msg: Message):
    if msg.from_user.id != ADMIN_ID: return
    conn = db()
    rows = conn.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 10").fetchall()
    conn.close()
    if not rows:
        await msg.answer("📭 Buyurtma yo'q hali"); return
    await msg.answer(f"📦 <b>Oxirgi 10 ta buyurtma:</b>")
    for r in rows:
        o = dict(r)
        await msg.answer(order_text(o, admin=True), reply_markup=order_kb(o["id"], o["status"]))

@dp.callback_query(F.data.startswith("o_"))
async def order_action(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌", show_alert=True); return
    parts  = call.data.split("_")
    action = parts[1]
    oid    = int(parts[2])
    conn   = db()

    if action == "reply":
        await state.update_data(reply_order_id=oid)
        order = dict(conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone())
        conn.close()
        await call.message.answer(
            f"💬 <b>#{oid} buyurtma egasiga xabar yozing:</b>\n"
            f"👤 {order.get('full_name','-')}\n📞 {order.get('phone','-')}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Bekor", callback_data="cancel_reply")]
            ])
        )
        await state.set_state(OrderReply.msg)
        return

    status_map = {"confirm":"confirmed","cancel":"cancelled","deliver":"delivering","done":"delivered"}
    ns = status_map.get(action)
    if not ns: conn.close(); return
    conn.execute("UPDATE orders SET status=? WHERE id=?", (ns, oid))
    conn.commit()
    order = dict(conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone())
    conn.close()

    em, lb = STATUS.get(ns, ("❓",""))
    await call.answer(f"{em} {lb}!", show_alert=True)
    await call.message.edit_reply_markup(reply_markup=order_kb(oid, ns))

    tg_uid = order.get("tg_user_id")
    if tg_uid:
        msgs = {
            "confirmed":  f"✅ <b>Buyurtma #{oid} tasdiqlandi!</b>\n\n📞 Admin tez orada bog'lanadi.",
            "delivering": f"🚚 <b>Buyurtma #{oid} yo'lda!</b>\n\nYaqinda yetib keladi.",
            "delivered":  f"🎉 <b>Buyurtma #{oid} yetkazildi!</b>\n\nRahmat! Yana keling! 🛍",
            "cancelled":  f"❌ <b>Buyurtma #{oid} bekor qilindi.</b>\n\nSavollar: {SUPPORT}",
        }
        if ns in msgs:
            try:
                await bot.send_message(int(tg_uid), msgs[ns], reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🛍 Do'konni ochish", web_app=WebAppInfo(url=WEB_URL))]
                ]))
            except: pass

@dp.callback_query(F.data == "cancel_reply")
async def cancel_reply(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.delete()
    await call.answer("Bekor qilindi")

@dp.message(OrderReply.msg)
async def send_order_reply(msg: Message, state: FSMContext):
    if msg.from_user.id != ADMIN_ID: return
    data = await state.get_data()
    oid  = data.get("reply_order_id")
    conn = db()
    order = conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    conn.close()
    if not order:
        await msg.answer("❌ Buyurtma topilmadi"); await state.clear(); return
    tg_uid = order["tg_user_id"]
    try:
        await bot.send_message(int(tg_uid),
            f"💬 <b>{SHOP_NAME} admini:</b>\n\n{msg.text}\n\n<i>Buyurtma #{oid}</i>")
        await msg.answer(f"✅ Xabar yuborildi → #{oid}", reply_markup=admin_kb())
    except:
        await msg.answer("❌ Foydalanuvchiga xabar yetmadi", reply_markup=admin_kb())
    await state.clear()

# ── ADMIN: STATISTIKA ─────────────────────────────────────────────────────────
@dp.message(F.text == "📊 Statistika")
async def stats(msg: Message):
    if msg.from_user.id != ADMIN_ID: return
    conn  = db()
    today = datetime.now().strftime("%Y-%m-%d")
    prods  = conn.execute("SELECT COUNT(*) FROM products WHERE active=1").fetchone()[0]
    users  = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    new_o  = conn.execute("SELECT COUNT(*) FROM orders WHERE status='new'").fetchone()[0]
    today_o= conn.execute("SELECT COUNT(*) FROM orders WHERE created_at LIKE ?", (today+"%",)).fetchone()[0]
    today_r= conn.execute("SELECT COALESCE(SUM(total),0) FROM orders WHERE created_at LIKE ? AND status!='cancelled'", (today+"%",)).fetchone()[0]
    total_r= conn.execute("SELECT COALESCE(SUM(total),0) FROM orders WHERE status='delivered'").fetchone()[0]
    vip_c  = conn.execute("SELECT COUNT(*) FROM users WHERE vip=1").fetchone()[0]
    conn.close()
    await msg.answer(
        f"📊 <b>Statistika — {SHOP_NAME}</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 Mahsulotlar: <b>{prods} ta</b>\n"
        f"👥 Foydalanuvchilar: <b>{users} ta</b>\n"
        f"👑 VIP mijozlar: <b>{vip_c} ta</b>\n\n"
        f"📋 Jami buyurtmalar: <b>{orders} ta</b>\n"
        f"🆕 Yangi: <b>{new_o} ta</b>\n"
        f"📅 Bugun: <b>{today_o} ta</b>\n\n"
        f"💰 Bugungi daromad: <b>{fmt(today_r)} so'm</b>\n"
        f"💎 Jami daromad: <b>{fmt(total_r)} so'm</b>",
        reply_markup=admin_kb()
    )

# ── ADMIN: BROADCAST ──────────────────────────────────────────────────────────
@dp.message(F.text == "📢 Broadcast")
async def broadcast_start(msg: Message, state: FSMContext):
    if msg.from_user.id != ADMIN_ID: return
    conn  = db()
    count = conn.execute("SELECT COUNT(*) FROM users WHERE blocked=0").fetchone()[0]
    conn.close()
    await msg.answer(
        f"📢 <b>Broadcast</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Yuboriladi: <b>{count} ta</b> foydalanuvchiga\n\n"
        "📝 Matn yozing yoki 📸 Rasm bilan caption yozing:\n\n"
        "<i>Bekor qilish uchun /cancel</i>",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Bekor")]], resize_keyboard=True)
    )
    await state.set_state(Broadcast.msg)

@dp.message(F.text == "❌ Bekor")
async def cancel_any(msg: Message, state: FSMContext):
    await state.clear()
    if msg.from_user.id == ADMIN_ID:
        await msg.answer("❌ Bekor qilindi", reply_markup=admin_kb())
    else:
        await msg.answer("❌ Bekor qilindi", reply_markup=main_kb())

@dp.message(Broadcast.msg)
async def do_broadcast(msg: Message, state: FSMContext):
    if msg.from_user.id != ADMIN_ID: return
    text     = msg.text or msg.caption or ""
    photo_id = msg.photo[-1].file_id if msg.photo else None
    conn     = db()
    users    = conn.execute("SELECT tg_user_id FROM users WHERE blocked=0").fetchall()
    conn.close()
    sent = 0; failed = 0
    prog = await msg.answer(f"📤 Yuborilmoqda... 0/{len(users)}")
    for i, u in enumerate(users):
        try:
            uid = int(u["tg_user_id"])
            shop_kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🛍 Do'konni ochish", web_app=WebAppInfo(url=WEB_URL))
            ]])
            if photo_id:
                await bot.send_photo(uid, photo_id, caption=text, reply_markup=shop_kb)
            else:
                await bot.send_message(uid, text, reply_markup=shop_kb)
            sent += 1
        except: failed += 1
        if (i+1) % 20 == 0:
            try: await prog.edit_text(f"📤 Yuborilmoqda... {i+1}/{len(users)}")
            except: pass
        await asyncio.sleep(0.05)
    await prog.edit_text(f"✅ Broadcast tugadi!\n✅ Yuborildi: {sent}\n❌ Xato: {failed}")
    await msg.answer("Tugadi!", reply_markup=admin_kb())
    await state.clear()

# ── ADMIN: PROMO KOD ──────────────────────────────────────────────────────────
@dp.message(F.text == "🏷️ Promo kod")
async def promo_menu(msg: Message):
    if msg.from_user.id != ADMIN_ID: return
    conn  = db()
    promos = conn.execute("SELECT * FROM promo_codes ORDER BY id DESC LIMIT 10").fetchall()
    conn.close()
    text = "🏷️ <b>Promo kodlar</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for p in promos:
        status = "✅" if p["active"] else "❌"
        text += f"{status} <code>{p['code']}</code> — {p['discount_percent']}% | {p['used_count']}/{p['max_uses']}\n"
    text += "\n<b>Yangi kod yaratish uchun yozing:</b>\n<code>/promo KOD FOIZ MAKS</code>\nMasalan: <code>/promo YANGI20 20 100</code>"
    await msg.answer(text, reply_markup=admin_kb())

@dp.message(Command("promo"))
async def make_promo(msg: Message):
    if msg.from_user.id != ADMIN_ID: return
    parts = msg.text.split()
    if len(parts) < 3:
        await msg.answer("❌ Format: /promo KOD FOIZ MAKS\nMasalan: /promo YANGI20 20 100"); return
    code = parts[1].upper()
    try:
        disc = int(parts[2])
        maks = int(parts[3]) if len(parts) > 3 else 100
    except:
        await msg.answer("❌ Foiz va maks raqam bo'lishi kerak"); return
    conn = db(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO promo_codes(code,discount_percent,max_uses,active,created_at) VALUES(?,?,?,1,?)",
                    (code, disc, maks, now()))
        conn.commit()
        await msg.answer(f"✅ Promo kod yaratildi!\n\n🏷️ Kod: <code>{code}</code>\n💸 Chegirma: {disc}%\n👥 Max: {maks} ta")
    except:
        await msg.answer("❌ Bu kod allaqachon mavjud!")
    conn.close()

# ── ADMIN: MAHSULOT O'CHIRISH ─────────────────────────────────────────────────
@dp.message(F.text == "❌ Mahsulot o'chirish")
async def delete_product_menu(msg: Message):
    if msg.from_user.id != ADMIN_ID: return
    conn  = db()
    prods = conn.execute("SELECT id, name, price FROM products WHERE active=1 ORDER BY id DESC LIMIT 20").fetchall()
    conn.close()
    if not prods:
        await msg.answer("📭 Mahsulot yo'q"); return
    kb = InlineKeyboardBuilder()
    for p in prods:
        kb.button(text=f"❌ #{p['id']} {p['name'][:25]}", callback_data=f"del_{p['id']}")
    kb.adjust(1)
    await msg.answer("🗑 <b>O'chirish uchun tanlang:</b>", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("del_"))
async def delete_product(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌", show_alert=True); return
    pid = int(call.data[4:])
    conn = db()
    prod = conn.execute("SELECT name FROM products WHERE id=?", (pid,)).fetchone()
    conn.execute("UPDATE products SET active=0 WHERE id=?", (pid,))
    conn.commit(); conn.close()
    await call.answer(f"✅ O'chirildi: {prod['name'] if prod else ''}", show_alert=True)
    await call.message.edit_reply_markup(reply_markup=None)

# ── ADMIN: FOYDALANUVCHILAR ───────────────────────────────────────────────────
@dp.message(F.text == "👥 Foydalanuvchilar")
async def admin_users(msg: Message):
    if msg.from_user.id != ADMIN_ID: return
    conn  = db()
    total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    vip   = conn.execute("SELECT COUNT(*) FROM users WHERE vip=1").fetchone()[0]
    users = conn.execute("SELECT * FROM users ORDER BY id DESC LIMIT 10").fetchall()
    conn.close()
    text = f"👥 <b>Foydalanuvchilar ({total} ta, {vip} VIP)</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for u in users:
        vip_ico = "👑" if u["vip"] else "👤"
        fname = u["full_name"] or "Noma'lum"
        text += f"{vip_ico} <b>{fname}</b>"
        if u["username"]: text += f" @{u['username']}"
        text += f" | ⭐{fmt(u['points'])} | 📦{u['orders_count']}\n"
    await msg.answer(text, reply_markup=admin_kb())

# ── WEB APP DATA ──────────────────────────────────────────────────────────────
@dp.message(F.web_app_data)
async def webapp_data(msg: Message):
    try: data = json.loads(msg.web_app_data.data)
    except: return
    oid   = data.get("order_id","?")
    total = data.get("total", 0)
    phone = data.get("phone","")
    fname = data.get("full_name","")
    await msg.answer(
        f"✅ <b>Buyurtma #{oid} qabul qilindi!</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 Jami: <b>{fmt(total)} so'm</b>\n📞 {phone}\n\n"
        f"⏳ Admin tez orada bog'lanadi!\n💬 Savol: {SUPPORT}",
        reply_markup=main_kb()
    )
    if oid != "?":
        conn = db()
        order = conn.execute("SELECT * FROM orders WHERE id=?", (int(oid),)).fetchone()
        conn.close()
        if order:
            o = dict(order)
            try:
                await bot.send_message(ADMIN_ID, "🆕 <b>YANGI BUYURTMA!</b>\n"+order_text(o, True),
                                        reply_markup=order_kb(int(oid), "new"))
            except: pass
            try:
                await bot.send_message(CHANNEL,
                    f"🛒 <b>YANGI BUYURTMA #{oid}</b>\n━━━━━━━━━━━━━━━━━━━━\n"
                    f"🙋 {o.get('full_name','-')}\n📞 <code>{o.get('phone','-')}</code>\n"
                    f"💰 <b>{fmt(o.get('total',0))} so'm</b>\n<i>{SHOP_NAME}</i>")
            except: pass
            # Update user stats
            tg_uid = o.get("tg_user_id","")
            if tg_uid:
                pts = max(1, total // 1000)
                conn2 = db()
                conn2.execute("UPDATE users SET total_spent=total_spent+?,orders_count=orders_count+1,points=points+?,vip=CASE WHEN total_spent+?>500000 THEN 1 ELSE vip END WHERE tg_user_id=?",
                              (total, pts, total, tg_uid))
                conn2.commit(); conn2.close()

# ── /ADMIN BUYRUG'I ───────────────────────────────────────────────────────────
@dp.message(Command("admin"))
async def cmd_admin(msg: Message, state: FSMContext):
    if msg.from_user.id != ADMIN_ID:
        await msg.answer("❌ Sizga ruxsat yo'q."); return
    await state.clear()
    conn = db()
    prods   = conn.execute("SELECT COUNT(*) FROM products WHERE active=1").fetchone()[0]
    orders  = conn.execute("SELECT COUNT(*) FROM orders WHERE status='new'").fetchone()[0]
    users_c = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    rev     = conn.execute("SELECT COALESCE(SUM(total),0) FROM orders WHERE status='delivered'").fetchone()[0]
    conn.close()
    await msg.answer(
        f"👑 <b>ADMIN PANEL — {SHOP_NAME}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 Mahsulotlar: <b>{prods} ta</b>\n"
        f"🆕 Yangi buyurtmalar: <b>{orders} ta</b>\n"
        f"👥 Foydalanuvchilar: <b>{users_c} ta</b>\n"
        f"💰 Jami daromad: <b>{fmt(rev)} so'm</b>",
        reply_markup=admin_kb()
    )

# ── /HELP BUYRUG'I ────────────────────────────────────────────────────────────
@dp.message(Command("help"))
async def cmd_help(msg: Message):
    if msg.from_user.id == ADMIN_ID:
        await msg.answer(
            "👑 <b>ADMIN buyruqlari</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            "/admin — Admin panelni ochish\n"
            "/neworders — Faqat yangi buyurtmalar\n"
            "/stats — Tezkor statistika\n"
            "/top — Eng ko'p sotilgan mahsulotlar\n"
            "/search <i>so'z</i> — Mahsulot qidirish\n"
            "/user <i>ID</i> — Foydalanuvchi ma'lumoti\n"
            "/ban <i>ID</i> — Foydalanuvchini bloklash\n"
            "/unban <i>ID</i> — Blokni ochish\n"
            "/setprice <i>ID narx</i> — Narx o'zgartirish\n"
            "/flash <i>ID chegirma soat</i> — Flash sale\n"
            "/promo <i>KOD FOIZ MAKS</i> — Promo kod\n"
            "/cancel — Amalni bekor qilish",
            reply_markup=admin_kb()
        )
    else:
        await msg.answer(
            f"📞 <b>{SHOP_NAME} — Yordam</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            "🛍 Do'konni ochish — Asosiy tugma orqali\n"
            "🛒 Buyurtmalarim — Buyurtmalar tarixi\n"
            "🏆 Ballarim — Ball va VIP status\n"
            "👥 Do'stni taklif qil — Referal havola\n\n"
            "❓ Savollar uchun:\n"
            f"💬 Admin: {SUPPORT}\n"
            "🕐 Ish vaqti: 09:00 — 22:00",
            reply_markup=main_kb()
        )

# ── /CANCEL BUYRUG'I ──────────────────────────────────────────────────────────
@dp.message(Command("cancel"))
async def cmd_cancel(msg: Message, state: FSMContext):
    await state.clear()
    if msg.from_user.id == ADMIN_ID:
        await msg.answer("❌ Bekor qilindi.", reply_markup=admin_kb())
    else:
        await msg.answer("❌ Bekor qilindi.", reply_markup=main_kb())

# ── /NEWORDERS — FAQAT YANGI BUYURTMALAR ─────────────────────────────────────
@dp.message(Command("neworders"))
async def cmd_neworders(msg: Message):
    if msg.from_user.id != ADMIN_ID: return
    conn = db()
    rows = conn.execute("SELECT * FROM orders WHERE status='new' ORDER BY id DESC LIMIT 10").fetchall()
    conn.close()
    if not rows:
        await msg.answer("✅ Yangi buyurtma yo'q!", reply_markup=admin_kb()); return
    await msg.answer(f"🆕 <b>Yangi buyurtmalar: {len(rows)} ta</b>")
    for r in rows:
        o = dict(r)
        await msg.answer(order_text(o, admin=True), reply_markup=order_kb(o["id"], o["status"]))

# ── /STATS — TEZKOR STATISTIKA ────────────────────────────────────────────────
@dp.message(Command("stats"))
async def cmd_stats(msg: Message):
    if msg.from_user.id != ADMIN_ID: return
    conn  = db()
    today = datetime.now().strftime("%Y-%m-%d")
    prods  = conn.execute("SELECT COUNT(*) FROM products WHERE active=1").fetchone()[0]
    users  = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    new_o  = conn.execute("SELECT COUNT(*) FROM orders WHERE status='new'").fetchone()[0]
    today_o= conn.execute("SELECT COUNT(*) FROM orders WHERE created_at LIKE ?", (today+"%",)).fetchone()[0]
    today_r= conn.execute("SELECT COALESCE(SUM(total),0) FROM orders WHERE created_at LIKE ? AND status!='cancelled'", (today+"%",)).fetchone()[0]
    total_r= conn.execute("SELECT COALESCE(SUM(total),0) FROM orders WHERE status='delivered'").fetchone()[0]
    vip_c  = conn.execute("SELECT COUNT(*) FROM users WHERE vip=1").fetchone()[0]
    conn.close()
    await msg.answer(
        f"📊 <b>{SHOP_NAME} — Statistika</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 Mahsulotlar: <b>{prods} ta</b>\n"
        f"👥 Foydalanuvchilar: <b>{users} ta</b>\n"
        f"👑 VIP: <b>{vip_c} ta</b>\n\n"
        f"📋 Jami buyurtmalar: <b>{orders} ta</b>\n"
        f"🆕 Yangi: <b>{new_o} ta</b>\n"
        f"📅 Bugun: <b>{today_o} ta</b>\n\n"
        f"💰 Bugungi daromad: <b>{fmt(today_r)} so'm</b>\n"
        f"💎 Jami daromad: <b>{fmt(total_r)} so'm</b>",
        reply_markup=admin_kb()
    )

# ── /TOP — ENG KO'P SOTILGAN MAHSULOTLAR ─────────────────────────────────────
@dp.message(Command("top"))
async def cmd_top(msg: Message):
    if msg.from_user.id != ADMIN_ID: return
    conn  = db()
    prods = conn.execute("""SELECT name, price, sold_count, badge FROM products
        WHERE active=1 ORDER BY sold_count DESC LIMIT 10""").fetchall()
    conn.close()
    if not prods:
        await msg.answer("📭 Mahsulot yo'q"); return
    text = "🏆 <b>Eng ko'p sotilgan 10 ta mahsulot</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, p in enumerate(prods, 1):
        medal = ["🥇","🥈","🥉"][i-1] if i <= 3 else f"{i}."
        text += f"{medal} <b>{p['name']}</b>\n   💰 {fmt(p['price'])} so'm | 📦 {p['sold_count']} ta sotilgan\n\n"
    await msg.answer(text, reply_markup=admin_kb())

# ── /SEARCH — MAHSULOT QIDIRISH ──────────────────────────────────────────────
@dp.message(Command("search"))
async def cmd_search(msg: Message):
    if msg.from_user.id != ADMIN_ID: return
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        await msg.answer("❌ Format: /search <i>mahsulot nomi</i>\nMasalan: /search futbolka"); return
    q = parts[1].lower().strip()
    conn = db()
    rows = conn.execute("""SELECT id, name, price, stock, active FROM products
        WHERE LOWER(name) LIKE ? ORDER BY id DESC LIMIT 10""", (f"%{q}%",)).fetchall()
    conn.close()
    if not rows:
        await msg.answer(f"🔍 '<b>{q}</b>' bo'yicha hech narsa topilmadi."); return
    text = f"🔍 <b>'{q}' qidirish natijalari:</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for p in rows:
        status = "✅" if p["active"] else "❌"
        text += f"{status} <b>#{p['id']}</b> {p['name']}\n   💰 {fmt(p['price'])} so'm | 📦 {p['stock']} ta\n\n"
    await msg.answer(text, reply_markup=admin_kb())

# ── /USER ID — FOYDALANUVCHI MA'LUMOTI ───────────────────────────────────────
@dp.message(Command("user"))
async def cmd_user_info(msg: Message):
    if msg.from_user.id != ADMIN_ID: return
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("❌ Format: /user <i>telegram_id</i>\nMasalan: /user 123456789"); return
    uid = parts[1].strip()
    conn = db()
    u = conn.execute("SELECT * FROM users WHERE tg_user_id=?", (uid,)).fetchone()
    if not u:
        conn.close()
        await msg.answer(f"❌ ID <code>{uid}</code> topilmadi."); return
    u = dict(u)
    orders = conn.execute("SELECT COUNT(*), COALESCE(SUM(total),0) FROM orders WHERE tg_user_id=? AND status!='cancelled'", (uid,)).fetchall()
    conn.close()
    total_orders, total_spent = orders[0][0], orders[0][1]
    vip  = "👑 VIP" if u["vip"] else "👤 Oddiy"
    blk      = "🚫 Bloklangan" if u["blocked"] else "✅ Faol"
    ism      = u["full_name"] or "Noma'lum"
    username = "@" + u["username"] if u["username"] else "Yo'q"
    phone    = u["phone"] or "Yo'q"
    joined   = u["joined_at"] or "-"
    await msg.answer(
        f"👤 <b>Foydalanuvchi ma'lumoti</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 ID: <code>{u['tg_user_id']}</code>\n"
        f"📛 Ism: <b>{ism}</b>\n"
        f"🔗 Username: {username}\n"
        f"📞 Telefon: {phone}\n\n"
        f"🎖 Status: {vip} | {blk}\n"
        f"⭐ Ballar: <b>{fmt(u['points'])}</b>\n"
        f"📦 Buyurtmalar: <b>{total_orders} ta</b>\n"
        f"💰 Jami xarid: <b>{fmt(total_spent)} so'm</b>\n"
        f"📅 Qo'shilgan: {joined}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚫 Bloklash", callback_data=f"ban_{uid}"),
             InlineKeyboardButton(text="✅ Blokni ochish", callback_data=f"unban_{uid}")],
            [InlineKeyboardButton(text="💬 Xabar yozish", callback_data=f"msg_{uid}")],
        ])
    )

@dp.callback_query(F.data.startswith("ban_"))
async def cb_ban_user(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌", show_alert=True); return
    uid = call.data[4:]
    conn = db()
    conn.execute("UPDATE users SET blocked=1 WHERE tg_user_id=?", (uid,))
    conn.commit(); conn.close()
    await call.answer(f"🚫 {uid} bloklandi", show_alert=True)
    try:
        await bot.send_message(int(uid), "🚫 Siz do'kondan bloklandingiz. Murojaat: " + SUPPORT)
    except: pass

@dp.callback_query(F.data.startswith("unban_"))
async def cb_unban_user(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌", show_alert=True); return
    uid = call.data[6:]
    conn = db()
    conn.execute("UPDATE users SET blocked=0 WHERE tg_user_id=?", (uid,))
    conn.commit(); conn.close()
    await call.answer(f"✅ {uid} bloki ochildi", show_alert=True)
    try:
        await bot.send_message(int(uid), f"✅ Blok ochildi! Endi {SHOP_NAME} dan xarid qilishingiz mumkin.")
    except: pass

@dp.callback_query(F.data.startswith("msg_"))
async def cb_msg_user(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌", show_alert=True); return
    uid = call.data[4:]
    await state.update_data(reply_order_id=None, direct_msg_uid=uid)
    await call.message.answer(
        f"💬 <b>ID {uid} ga xabar yozing:</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor", callback_data="cancel_reply")]
        ])
    )
    await state.set_state(OrderReply.msg)
    await call.answer()

# ── /BAN va /UNBAN BUYRUQLARI ─────────────────────────────────────────────────
@dp.message(Command("ban"))
async def cmd_ban(msg: Message):
    if msg.from_user.id != ADMIN_ID: return
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("❌ Format: /ban <i>telegram_id</i>"); return
    uid = parts[1].strip()
    conn = db()
    conn.execute("UPDATE users SET blocked=1 WHERE tg_user_id=?", (uid,))
    conn.commit(); conn.close()
    await msg.answer(f"🚫 <code>{uid}</code> bloklandi.")
    try:
        await bot.send_message(int(uid), f"🚫 Siz do'kondan bloklandingiz.\nMurojaat: {SUPPORT}")
    except: pass

@dp.message(Command("unban"))
async def cmd_unban(msg: Message):
    if msg.from_user.id != ADMIN_ID: return
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("❌ Format: /unban <i>telegram_id</i>"); return
    uid = parts[1].strip()
    conn = db()
    conn.execute("UPDATE users SET blocked=0 WHERE tg_user_id=?", (uid,))
    conn.commit(); conn.close()
    await msg.answer(f"✅ <code>{uid}</code> bloki ochildi.")
    try:
        await bot.send_message(int(uid), f"✅ Blok ochildi! Endi {SHOP_NAME} dan xarid qilishingiz mumkin.")
    except: pass

# ── /SETPRICE — NARX O'ZGARTIRISH ────────────────────────────────────────────
@dp.message(Command("setprice"))
async def cmd_setprice(msg: Message):
    if msg.from_user.id != ADMIN_ID: return
    parts = msg.text.split()
    if len(parts) < 3:
        await msg.answer("❌ Format: /setprice <i>mahsulot_id yangi_narx</i>\nMasalan: /setprice 5 150000"); return
    try:
        pid   = int(parts[1])
        price = int(parts[2].replace(" ","").replace(",",""))
    except:
        await msg.answer("❌ ID va narx raqam bo'lishi kerak."); return
    conn = db()
    prod = conn.execute("SELECT name FROM products WHERE id=? AND active=1", (pid,)).fetchone()
    if not prod:
        conn.close(); await msg.answer(f"❌ #{pid} mahsulot topilmadi."); return
    conn.execute("UPDATE products SET price=? WHERE id=?", (price, pid))
    conn.commit(); conn.close()
    await msg.answer(
        f"✅ <b>Narx yangilandi!</b>\n\n"
        f"📦 <b>#{pid}</b> {prod['name']}\n"
        f"💰 Yangi narx: <b>{fmt(price)} so'm</b>",
        reply_markup=admin_kb()
    )

# ── /FLASH — FLASH SALE YARATISH ─────────────────────────────────────────────
@dp.message(Command("flash"))
async def cmd_flash(msg: Message):
    if msg.from_user.id != ADMIN_ID: return
    parts = msg.text.split()
    if len(parts) < 4:
        await msg.answer(
            "❌ Format: /flash <i>mahsulot_id chegirma_foiz soat</i>\n"
            "Masalan: /flash 3 30 24\n"
            "<i>(#3 mahsulotga 30% chegirma, 24 soat davomida)</i>"
        ); return
    try:
        pid      = int(parts[1])
        discount = int(parts[2])
        hours    = int(parts[3])
    except:
        await msg.answer("❌ Barcha qiymatlar raqam bo'lishi kerak."); return
    if not (1 <= discount <= 90):
        await msg.answer("❌ Chegirma 1-90% oralig'ida bo'lishi kerak."); return
    conn = db()
    prod = conn.execute("SELECT name, price FROM products WHERE id=? AND active=1", (pid,)).fetchone()
    if not prod:
        conn.close(); await msg.answer(f"❌ #{pid} mahsulot topilmadi."); return
    starts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ends   = (datetime.now() + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("UPDATE flash_sales SET active=0 WHERE product_id=?", (pid,))
    conn.execute("""INSERT INTO flash_sales(product_id, discount_percent, starts_at, ends_at, active)
        VALUES(?,?,?,?,1)""", (pid, discount, starts, ends))
    conn.commit(); conn.close()
    new_price = int(prod["price"] * (1 - discount / 100))
    await msg.answer(
        f"⚡ <b>Flash Sale yaratildi!</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 <b>{prod['name']}</b>\n"
        f"💸 Chegirma: <b>-{discount}%</b>\n"
        f"💰 Asl narx: {fmt(prod['price'])} so'm\n"
        f"🔥 Flash narx: <b>{fmt(new_price)} so'm</b>\n"
        f"⏱ Davomiyligi: <b>{hours} soat</b>\n"
        f"🕐 Tugash vaqti: {ends}",
        reply_markup=admin_kb()
    )

# ── /STOPFLASH — FLASH SALENI TO'XTATISH ─────────────────────────────────────
@dp.message(Command("stopflash"))
async def cmd_stopflash(msg: Message):
    if msg.from_user.id != ADMIN_ID: return
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("❌ Format: /stopflash <i>mahsulot_id</i>"); return
    try:
        pid = int(parts[1])
    except:
        await msg.answer("❌ ID raqam bo'lishi kerak."); return
    conn = db()
    conn.execute("UPDATE flash_sales SET active=0 WHERE product_id=?", (pid,))
    conn.commit(); conn.close()
    await msg.answer(f"✅ #{pid} mahsulotning flash sale to'xtatildi.", reply_markup=admin_kb())

# ── /ADDVIP — VIP STATUS BERISH ───────────────────────────────────────────────
@dp.message(Command("addvip"))
async def cmd_addvip(msg: Message):
    if msg.from_user.id != ADMIN_ID: return
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("❌ Format: /addvip <i>telegram_id</i>"); return
    uid = parts[1].strip()
    conn = db()
    conn.execute("UPDATE users SET vip=1 WHERE tg_user_id=?", (uid,))
    conn.commit(); conn.close()
    await msg.answer(f"👑 <code>{uid}</code> ga VIP status berildi.")
    try:
        await bot.send_message(int(uid),
            f"👑 <b>Tabriklaymiz!</b>\n\nSizga <b>{SHOP_NAME}</b> VIP status berildi!\n"
            f"🎁 VIP mijozlarga maxsus chegirmalar va ustuvorlik xizmatlar beriladi!")
    except: pass

# ── /ADDPOINTS — BALL QO'SHISH ────────────────────────────────────────────────
@dp.message(Command("addpoints"))
async def cmd_addpoints(msg: Message):
    if msg.from_user.id != ADMIN_ID: return
    parts = msg.text.split()
    if len(parts) < 3:
        await msg.answer("❌ Format: /addpoints <i>telegram_id ball</i>\nMasalan: /addpoints 123456 500"); return
    uid = parts[1].strip()
    try:
        points = int(parts[2])
    except:
        await msg.answer("❌ Ball raqam bo'lishi kerak."); return
    conn = db()
    conn.execute("UPDATE users SET points=points+? WHERE tg_user_id=?", (points, uid))
    conn.commit()
    u = conn.execute("SELECT points FROM users WHERE tg_user_id=?", (uid,)).fetchone()
    conn.close()
    total_pts = u["points"] if u else points
    await msg.answer(f"⭐ <code>{uid}</code> ga <b>{fmt(points)}</b> ball qo'shildi.\nJami: <b>{fmt(total_pts)}</b> ball.")
    try:
        await bot.send_message(int(uid),
            f"🎁 <b>{fmt(points)} bonus ball qo'shildi!</b>\n\n"
            f"⭐ Jami ballaringiz: <b>{fmt(total_pts)}</b>\n"
            f"💡 500 ball = 5 000 so'm chegirma!")
    except: pass

# ── NOMA'LUM XABAR ────────────────────────────────────────────────────────────
@dp.message()
async def unknown_msg(msg: Message):
    if msg.from_user.id == ADMIN_ID:
        await msg.answer(
            "❓ Noma'lum buyruq. /help — buyruqlar ro'yxati",
            reply_markup=admin_kb()
        )
    else:
        await msg.answer(
            "❓ Tushunmadim. Quyidagi tugmalardan foydalaning:",
            reply_markup=main_kb()
        )

# ── BOT COMMANDS MENU ─────────────────────────────────────────────────────────
async def set_commands():
    # Oddiy foydalanuvchilar uchun
    user_commands = [
        BotCommand(command="start",  description="🏠 Bosh sahifa"),
        BotCommand(command="help",   description="📞 Yordam va ma'lumot"),
    ]
    await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

    # Admin uchun alohida buyruqlar ro'yxati
    admin_commands = [
        BotCommand(command="start",      description="🏠 Bosh sahifa"),
        BotCommand(command="admin",      description="👑 Admin panel"),
        BotCommand(command="neworders",  description="🆕 Yangi buyurtmalar"),
        BotCommand(command="stats",      description="📊 Statistika"),
        BotCommand(command="top",        description="🏆 Eng ko'p sotilganlar"),
        BotCommand(command="search",     description="🔍 Mahsulot qidirish"),
        BotCommand(command="user",       description="👤 Foydalanuvchi: /user ID"),
        BotCommand(command="ban",        description="🚫 Bloklash: /ban ID"),
        BotCommand(command="unban",      description="✅ Blokni ochish: /unban ID"),
        BotCommand(command="setprice",   description="💰 Narx: /setprice ID narx"),
        BotCommand(command="flash",      description="⚡ Flash sale: /flash ID % soat"),
        BotCommand(command="stopflash",  description="🛑 Flash stop: /stopflash ID"),
        BotCommand(command="addvip",     description="👑 VIP berish: /addvip ID"),
        BotCommand(command="addpoints",  description="⭐ Ball: /addpoints ID miqdor"),
        BotCommand(command="promo",      description="🏷️ Promo: /promo KOD % maks"),
        BotCommand(command="help",       description="📋 Barcha buyruqlar"),
        BotCommand(command="cancel",     description="❌ Amalni bekor qilish"),
    ]
    await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=ADMIN_ID))

# ── MAIN ──────────────────────────────────────────────────────────────────────
async def main():
    init_db()
    await set_commands()
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    asyncio.run(main())
