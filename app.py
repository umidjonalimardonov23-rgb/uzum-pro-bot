import os, sqlite3, json, hashlib, secrets, random, string, uuid, urllib.request, urllib.parse, threading, time
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
from werkzeug.utils import secure_filename

DB_NAME        = os.getenv("DB_NAME", "uzum_market.db")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
SECRET_KEY     = os.getenv("SECRET_KEY", secrets.token_hex(32))
SHOP_NAME      = os.getenv("SHOP_NAME", "UZUM MARKET")
SUPPORT        = os.getenv("SUPPORT", "@support")
BOT_TOKEN      = os.getenv("BOT_TOKEN", "")
ADMIN_ID       = os.getenv("ADMIN_ID", "")
CARD_NUMBER    = os.getenv("CARD_NUMBER", "9860606760806673")
CARD_HOLDER    = os.getenv("CARD_HOLDER", "Alimardonov Umidjon")

def tg_notify(chat_id, text, reply_markup=None):
    if not BOT_TOKEN or not chat_id: return
    try:
        payload = {"chat_id": str(chat_id), "text": text, "parse_mode": "HTML"}
        if reply_markup: payload["reply_markup"] = json.dumps(reply_markup)
        data = urllib.parse.urlencode(payload).encode()
        urllib.request.urlopen(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data, timeout=5)
    except Exception: pass

UPLOAD_FOLDER   = os.path.join(os.path.dirname(__file__), "static", "uploads")
ALLOWED_EXT     = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE

def db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def init_db():
    conn = db(); cur = conn.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS categories(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE, icon TEXT DEFAULT '🛍', sort_order INTEGER DEFAULT 0)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id INTEGER, name TEXT NOT NULL, description TEXT,
        price INTEGER NOT NULL, old_price INTEGER DEFAULT 0,
        image TEXT, badge TEXT DEFAULT '', stock INTEGER DEFAULT 99,
        active INTEGER DEFAULT 1, rating REAL DEFAULT 4.5,
        sold_count INTEGER DEFAULT 0, sizes TEXT DEFAULT '',
        colors TEXT DEFAULT '', created_at TEXT)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_user_id TEXT, full_name TEXT, phone TEXT, address TEXT,
        items TEXT, total INTEGER, payment TEXT DEFAULT 'naqd',
        status TEXT DEFAULT 'new', note TEXT DEFAULT '',
        size TEXT DEFAULT '', color TEXT DEFAULT '',
        promo_code TEXT DEFAULT '', discount INTEGER DEFAULT 0,
        created_at TEXT)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS banners(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT, subtitle TEXT, color TEXT DEFAULT '#7c2cff',
        badge TEXT DEFAULT '', image TEXT DEFAULT '', active INTEGER DEFAULT 1)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_user_id TEXT UNIQUE, full_name TEXT, username TEXT,
        phone TEXT, referral_code TEXT UNIQUE,
        referred_by TEXT DEFAULT '', points INTEGER DEFAULT 0,
        total_spent INTEGER DEFAULT 0, orders_count INTEGER DEFAULT 0,
        vip INTEGER DEFAULT 0, blocked INTEGER DEFAULT 0,
        joined_at TEXT)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS promo_codes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE, discount_percent INTEGER DEFAULT 10,
        max_uses INTEGER DEFAULT 100, used_count INTEGER DEFAULT 0,
        active INTEGER DEFAULT 1, expires_at TEXT, created_at TEXT)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS reviews(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER, tg_user_id TEXT, full_name TEXT,
        rating INTEGER DEFAULT 5, comment TEXT,
        created_at TEXT)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS broadcasts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT, image TEXT, sent_count INTEGER DEFAULT 0,
        created_at TEXT)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS flash_sales(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER, discount_percent INTEGER DEFAULT 20,
        starts_at TEXT, ends_at TEXT, active INTEGER DEFAULT 1)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS referrals(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        referrer_id TEXT, referred_id TEXT, bonus_points INTEGER DEFAULT 100,
        created_at TEXT)""")

    cur.execute("""CREATE TABLE IF NOT EXISTS chat_messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_user_id TEXT NOT NULL,
        user_name TEXT DEFAULT 'Foydalanuvchi',
        user_username TEXT DEFAULT '',
        message TEXT NOT NULL,
        reply_to INTEGER DEFAULT NULL,
        reply_text TEXT DEFAULT '',
        product_id INTEGER DEFAULT NULL,
        product_name TEXT DEFAULT '',
        product_price INTEGER DEFAULT 0,
        product_image TEXT DEFAULT '',
        reactions TEXT DEFAULT '{}',
        created_at TEXT)""")

    cur.execute("""SELECT COUNT(*) FROM categories""")
    if cur.fetchone()[0] == 0:
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
        cur.executemany("INSERT INTO categories(name,icon,sort_order) VALUES(?,?,?)", cats)

    cur.execute("SELECT COUNT(*) FROM products")
    if cur.fetchone()[0] == 0:
        products = [
            (1,"Oversize Futbolka","100% paxta, yuqori sifat, qulay kesim. Har kuni kiyish uchun ideal.",89000,120000,"https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400&q=80","YANGI",150,4.8,320,"S,M,L,XL,XXL","Oq,Qora,Ko'k,Kulrang,Yashil"),
            (1,"Premium Hoodie Erkaklar","Qalin fleece material, kengaytirilgan fit, kapyushonli.",199000,260000,"https://images.unsplash.com/photo-1556821840-3a63f95609a7?w=400&q=80","HOT",80,4.9,445,"S,M,L,XL,XXL","Qora,Kulrang,Navy,Jigarrang"),
            (1,"Slim Fit Ko'ylak","Yuqori sifatli mato, elegantli dizayn, ish va sayohat uchun.",149000,190000,"https://images.unsplash.com/photo-1598033129183-c4f50c736f10?w=400&q=80","SALE",60,4.7,210,"S,M,L,XL","Oq,Ko'k,Kulrang"),
            (2,"Ayollar Bluzka","Nozik chiffon material, romantik dizayn, bayram uchun.",119000,159000,"https://images.unsplash.com/photo-1485462537746-965f33f7f6a7?w=400&q=80","YANGI",90,4.8,180,"XS,S,M,L,XL","Qizil,Pushti,Oq,Sariq"),
            (2,"Maxi Ko'ylak","Uzun, oqimli dizayn, yoz mavsumi uchun, ipak kabi yumshoq.",189000,240000,"https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=400&q=80","TOP",45,4.9,120,"XS,S,M,L","Yashil,Ko'k,Qizil,Oq"),
            (3,"Bolalar Sport Kostyum","Yumshoq fleece, qulay kesim, 4-14 yosh uchun.",99000,130000,"https://images.unsplash.com/photo-1519238263530-99bdd11df2ea?w=400&q=80","YANGI",120,4.7,95,"4,6,8,10,12,14","Ko'k,Yashil,Qizil,Sariq"),
            (4,"Sport Leggings","4-yo'nalishda cho'ziladigan material, yuqori bel, sport uchun.",89000,115000,"https://images.unsplash.com/photo-1506629082955-511b1aa562c8?w=400&q=80","HOT",200,4.8,560,"XS,S,M,L,XL","Qora,Kulrang,Navy,Yashil"),
            (5,"Casual Krossovka","Engil va qulay, har kuni kiyish uchun, breathable material.",279000,350000,"https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&q=80","SALE",70,4.7,430,"36,37,38,39,40,41,42,43","Oq,Qora,Ko'k"),
            (6,"Charm Sumka","Yuqori sifatli sun'iy charm, keng sig'imli, zamonaviy dizayn.",159000,210000,"https://images.unsplash.com/photo-1548036328-c9fa89d128fa?w=400&q=80","TOP",50,4.6,280,"","Qora,Jigarrang,Pushti,Krem"),
            (7,"Qishki Palto","Qalin jun material, shamol va sovuqdan himoya, elegantli.",499000,650000,"https://images.unsplash.com/photo-1539533018447-63fcce2678e3?w=400&q=80","YANGI",30,4.9,85,"S,M,L,XL","Qora,Kulrang,Krem,Navy"),
        ]
        cur.executemany("""INSERT INTO products(category_id,name,description,price,old_price,image,badge,stock,rating,sold_count,sizes,colors,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""", [(c,n,d,p,o,img,b,st,r,s,sz,cl,now()) for c,n,d,p,o,img,b,st,r,s,sz,cl in products])

    cur.execute("SELECT COUNT(*) FROM banners")
    if cur.fetchone()[0] == 0:
        cur.executemany("INSERT INTO banners(title,subtitle,color,badge) VALUES(?,?,?,?)", [
            ("Yangi kolleksiya!","Kuz-qish mavsumi kiyimlari yetib keldi","#7c2cff","YANGI"),
            ("Mega chegirma -30%","Barcha sport kiyimlariga katta chegirma","#ff6b35","SALE"),
            ("Bestseller kiyimlar","Eng ko'p sotilgan modellar","#00c853","TOP"),
        ])

    cur.execute("SELECT COUNT(*) FROM promo_codes")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO promo_codes(code,discount_percent,max_uses,active,created_at) VALUES(?,?,?,?,?)",
                    ("UZUM10", 10, 1000, 1, now()))

    conn.commit(); conn.close()

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin"):
            if request.is_json: return jsonify({"error": "Unauthorized"}), 401
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated

# ── Pages ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html", shop_name=SHOP_NAME, support=SUPPORT)

@app.route("/admin/tg-auth", methods=["POST"])
def admin_tg_auth():
    data = request.json or {}
    tg_id = str(data.get("tg_user_id", ""))
    if tg_id and tg_id == str(ADMIN_ID):
        session["admin"] = True
        return jsonify({"ok": True})
    return jsonify({"ok": False}), 403

@app.route("/admin/login", methods=["GET","POST"])
def admin_login():
    if session.get("admin"):
        return redirect(url_for("admin_page"))
    error = None
    if request.method == "POST":
        if request.form.get("password","") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin_page"))
        error = "Parol noto'g'ri"
    return render_template("login.html", error=error)

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))

@app.route("/admin")
@admin_required
def admin_page():
    return render_template("admin.html", shop_name=SHOP_NAME)

# ── Public API ────────────────────────────────────────────────────────────────
@app.route("/api/config")
def api_config():
    support = SUPPORT.lstrip("@")
    return jsonify({"shop_name": SHOP_NAME, "support": SUPPORT, "support_username": support,
                    "currency": "so'm", "card_number": CARD_NUMBER, "card_holder": CARD_HOLDER})

@app.route("/api/banners")
def api_banners():
    conn = db()
    rows = conn.execute("SELECT * FROM banners WHERE active=1").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/categories")
def api_categories():
    conn = db()
    rows = conn.execute("SELECT * FROM categories ORDER BY sort_order").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/products")
def api_products():
    q = request.args.get("q","").strip().lower()
    category = request.args.get("category","")
    badge = request.args.get("badge","")
    sort = request.args.get("sort","newest")
    limit = min(int(request.args.get("limit",50)),100)
    offset = int(request.args.get("offset",0))

    conn = db()
    sql = """SELECT p.*, c.name as category_name, c.icon as category_icon
        FROM products p LEFT JOIN categories c ON p.category_id=c.id WHERE p.active=1"""
    params = []
    if category:
        sql += " AND c.name=?"; params.append(category)
    if badge:
        sql += " AND p.badge=?"; params.append(badge)
    if q:
        sql += " AND (LOWER(p.name) LIKE ? OR LOWER(p.description) LIKE ?)"; params.extend([f"%{q}%",f"%{q}%"])

    min_price = request.args.get("min_price","")
    max_price = request.args.get("max_price","")
    if min_price.isdigit(): sql += " AND p.price>=?"; params.append(int(min_price))
    if max_price.isdigit(): sql += " AND p.price<=?"; params.append(int(max_price))

    order_map = {"newest":"p.id DESC","price_asc":"p.price ASC","price_desc":"p.price DESC","rating":"p.rating DESC","popular":"p.sold_count DESC"}
    sql += f" ORDER BY {order_map.get(sort,'p.id DESC')} LIMIT ? OFFSET ?"; params.extend([limit,offset])

    # Check flash sales
    now_str = now()
    rows = conn.execute(sql, params).fetchall()
    result = []
    for r in rows:
        p = dict(r)
        flash = conn.execute("SELECT * FROM flash_sales WHERE product_id=? AND active=1 AND starts_at<=? AND ends_at>=?",
                             (p["id"], now_str, now_str)).fetchone()
        if flash:
            p["flash_discount"] = flash["discount_percent"]
            p["flash_ends"] = flash["ends_at"]
            p["flash_price"] = int(p["price"] * (1 - flash["discount_percent"]/100))
        result.append(p)
    conn.close()
    return jsonify(result)

@app.route("/api/products/<int:pid>")
def api_product_detail(pid):
    conn = db()
    row = conn.execute("""SELECT p.*, c.name as category_name FROM products p
        LEFT JOIN categories c ON p.category_id=c.id WHERE p.id=? AND p.active=1""", (pid,)).fetchone()
    if not row:
        conn.close(); return jsonify({"error": "Not found"}), 404
    p = dict(row)
    reviews = conn.execute("SELECT * FROM reviews WHERE product_id=? ORDER BY id DESC LIMIT 10", (pid,)).fetchall()
    p["reviews"] = [dict(r) for r in reviews]
    conn.close()
    return jsonify(p)

@app.route("/api/promo", methods=["POST"])
def api_promo():
    code = (request.json or {}).get("code","").strip().upper()
    conn = db()
    promo = conn.execute("SELECT * FROM promo_codes WHERE code=? AND active=1", (code,)).fetchone()
    conn.close()
    if not promo:
        return jsonify({"ok": False, "error": "Promo kod topilmadi"})
    if promo["max_uses"] > 0 and promo["used_count"] >= promo["max_uses"]:
        return jsonify({"ok": False, "error": "Promo kod tugagan"})
    if promo["expires_at"] and promo["expires_at"] < now():
        return jsonify({"ok": False, "error": "Promo kod muddati o'tgan"})
    return jsonify({"ok": True, "discount": promo["discount_percent"], "code": code})

@app.route("/api/review", methods=["POST"])
def api_review():
    data = request.json or {}
    conn = db(); cur = conn.cursor()
    cur.execute("INSERT INTO reviews(product_id,tg_user_id,full_name,rating,comment,created_at) VALUES(?,?,?,?,?,?)",
                (data.get("product_id"), str(data.get("user_id","")), data.get("full_name","Foydalanuvchi"),
                 int(data.get("rating",5)), data.get("comment",""), now()))
    # Update product rating
    avg = conn.execute("SELECT AVG(rating) FROM reviews WHERE product_id=?", (data.get("product_id"),)).fetchone()[0]
    if avg:
        conn.execute("UPDATE products SET rating=? WHERE id=?", (round(avg,1), data.get("product_id")))
    conn.commit(); conn.close()
    return jsonify({"ok": True})

@app.route("/api/register-user", methods=["POST"])
def api_register_user():
    data = request.json or {}
    tg_id = str(data.get("tg_id",""))
    if not tg_id: return jsonify({"ok": False})
    conn = db(); cur = conn.cursor()
    existing = conn.execute("SELECT * FROM users WHERE tg_user_id=?", (tg_id,)).fetchone()
    if not existing:
        ref_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        referred_by = data.get("ref","")
        cur.execute("""INSERT INTO users(tg_user_id,full_name,username,referral_code,referred_by,joined_at)
            VALUES(?,?,?,?,?,?)""", (tg_id, data.get("name",""), data.get("username",""), ref_code, referred_by, now()))
        # Give bonus to referrer
        if referred_by:
            cur.execute("UPDATE users SET points=points+200 WHERE referral_code=?", (referred_by,))
            cur.execute("INSERT INTO referrals(referrer_id,referred_id,bonus_points,created_at) VALUES(?,?,?,?)",
                        (referred_by, tg_id, 200, now()))
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE tg_user_id=?", (tg_id,)).fetchone()
    else:
        user = existing
    conn.close()
    return jsonify({"ok": True, "ref_code": user["referral_code"], "points": user["points"], "vip": user["vip"]})

@app.route("/api/order", methods=["POST"])
def api_order():
    data = request.json or {}
    items = data.get("items",[])
    if not items: return jsonify({"ok": False, "error": "Savat bo'sh"}), 400

    total = int(data.get("total",0))
    user = data.get("user") or {}
    phone = data.get("phone","").strip()
    full_name = data.get("full_name","").strip() or user.get("first_name","")
    if not phone: return jsonify({"ok": False, "error": "Telefon kerak"}), 400

    # Promo
    promo_code = data.get("promo_code","").strip().upper()
    discount = 0
    conn = db(); cur = conn.cursor()
    if promo_code:
        promo = conn.execute("SELECT * FROM promo_codes WHERE code=? AND active=1", (promo_code,)).fetchone()
        if promo:
            discount = promo["discount_percent"]
            cur.execute("UPDATE promo_codes SET used_count=used_count+1 WHERE code=?", (promo_code,))

    final_total = int(total * (1 - discount/100))

    for item in items:
        cur.execute("UPDATE products SET stock=MAX(0,stock-?), sold_count=sold_count+? WHERE id=?",
                    (item.get("qty",1), item.get("qty",1), item.get("id")))

    cur.execute("""INSERT INTO orders(tg_user_id,full_name,phone,address,items,total,payment,status,note,size,color,promo_code,discount,created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        str(user.get("id","")), full_name, phone, "Admin bog'lanadi",
        json.dumps(items, ensure_ascii=False), final_total,
        data.get("payment","naqd"), "new", data.get("note",""),
        data.get("size",""), data.get("color",""),
        promo_code, discount, now()))
    order_id = cur.lastrowid

    # Update user stats + points
    tg_id = str(user.get("id",""))
    if tg_id:
        points_earned = final_total // 1000  # 1 ball = 1000 so'm
        cur.execute("""UPDATE users SET total_spent=total_spent+?, orders_count=orders_count+1,
            points=points+?, vip=CASE WHEN total_spent+?>500000 THEN 1 ELSE vip END
            WHERE tg_user_id=?""", (final_total, points_earned, final_total, tg_id))

    conn.commit(); conn.close()

    # Notify admin via Telegram
    payment_label = "💳 Plastik karta" if data.get("payment") == "karta" else "💵 Naqd pul"
    items_txt = "\n".join(f"  • {i.get('name','?')} × {i.get('qty',1)}" for i in items[:6])
    bonus_d = int(data.get("bonus_discount", 0))
    promo_line = f"🏷️ Promo: {promo_code} (-{discount}%)\n" if promo_code else ""
    bonus_line = f"🎁 Bonus chegirma: -{bonus_d:,} so'm\n" if bonus_d else ""
    notify_txt = (
        f"🛍 <b>Yangi buyurtma #{order_id}!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>{full_name}</b>\n"
        f"📞 <code>{phone}</code>\n"
        f"{payment_label}\n"
        f"{promo_line}{bonus_line}"
        f"\n🛒 Mahsulotlar:\n{items_txt}\n\n"
        f"💰 <b>Jami: {final_total:,} so'm</b>"
    )
    confirm_kb = {"inline_keyboard": [[
        {"text": "✅ Tasdiqlash", "callback_data": f"o_confirm_{order_id}"},
        {"text": "❌ Bekor", "callback_data": f"o_cancel_{order_id}"}
    ]]}
    if ADMIN_ID:
        tg_notify(ADMIN_ID, notify_txt, confirm_kb)

    return jsonify({"ok": True, "order_id": order_id, "discount": discount, "final_total": final_total})

@app.route("/api/flash-sales")
def api_flash_sales():
    conn = db()
    now_str = now()
    rows = conn.execute("""SELECT f.*, p.name, p.image, p.price FROM flash_sales f
        JOIN products p ON f.product_id=p.id WHERE f.active=1 AND f.starts_at<=? AND f.ends_at>=?""",
        (now_str, now_str)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# ── Admin API ─────────────────────────────────────────────────────────────────
@app.route("/api/admin/stats")
@admin_required
def api_admin_stats():
    conn = db()
    users    = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    products = conn.execute("SELECT COUNT(*) FROM products WHERE active=1").fetchone()[0]
    orders   = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    revenue  = conn.execute("SELECT COALESCE(SUM(total),0) FROM orders WHERE status!='cancelled'").fetchone()[0]
    new_ord  = conn.execute("SELECT COUNT(*) FROM orders WHERE status='new'").fetchone()[0]
    today    = conn.execute("SELECT COUNT(*) FROM orders WHERE created_at LIKE ?", (datetime.now().strftime("%Y-%m-%d")+"%",)).fetchone()[0]
    today_rev = conn.execute("SELECT COALESCE(SUM(total),0) FROM orders WHERE created_at LIKE ? AND status!='cancelled'",
                             (datetime.now().strftime("%Y-%m-%d")+"%",)).fetchone()[0]
    conn.close()
    return jsonify({"users":users,"products":products,"orders":orders,"revenue":revenue,
                    "new_orders":new_ord,"today":today,"today_revenue":today_rev})

@app.route("/api/admin/chart-data")
@admin_required
def api_admin_chart_data():
    conn = db()
    days = []
    for i in range(6, -1, -1):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        label = (datetime.now() - timedelta(days=i)).strftime("%d.%m")
        cnt = conn.execute("SELECT COUNT(*) FROM orders WHERE created_at LIKE ?", (d+"%",)).fetchone()[0]
        rev = conn.execute("SELECT COALESCE(SUM(total),0) FROM orders WHERE created_at LIKE ? AND status!='cancelled'", (d+"%",)).fetchone()[0]
        days.append({"date": label, "orders": cnt, "revenue": int(rev)})
    # Top products
    top = conn.execute("""SELECT name, sold_count FROM products WHERE active=1
        ORDER BY sold_count DESC LIMIT 5""").fetchall()
    # Category sales
    cats = conn.execute("""SELECT c.name, COUNT(DISTINCT p.id) as cnt
        FROM categories c LEFT JOIN products p ON p.category_id=c.id AND p.active=1
        GROUP BY c.id ORDER BY cnt DESC""").fetchall()
    conn.close()
    return jsonify({
        "days": days,
        "top_products": [{"name": r["name"], "sold": r["sold_count"]} for r in top],
        "categories": [{"name": r["name"], "count": r["cnt"]} for r in cats]
    })

@app.route("/api/admin/orders")
@admin_required
def api_admin_orders():
    status = request.args.get("status","")
    conn = db()
    sql = "SELECT * FROM orders"
    params = []
    if status: sql += " WHERE status=?"; params.append(status)
    sql += " ORDER BY id DESC LIMIT 200"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/admin/order-status", methods=["POST"])
@admin_required
def api_admin_order_status():
    data = request.json or {}
    allowed = {"new","confirmed","delivering","delivered","cancelled"}
    status = data.get("status","new")
    if status not in allowed: return jsonify({"ok": False}), 400
    conn = db()
    conn.execute("UPDATE orders SET status=? WHERE id=?", (status, data.get("id")))
    conn.commit(); conn.close()
    return jsonify({"ok": True})

@app.route("/api/admin/products")
@admin_required
def api_admin_products():
    conn = db()
    rows = conn.execute("""SELECT p.*, c.name as category_name FROM products p
        LEFT JOIN categories c ON p.category_id=c.id ORDER BY p.id DESC""").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/admin/upload-image", methods=["POST"])
@admin_required
def api_admin_upload_image():
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "Fayl topilmadi"}), 400
    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"ok": False, "error": "Fayl tanlanmadi"}), 400
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXT:
        return jsonify({"ok": False, "error": "Ruxsat etilmagan format. PNG, JPG, WEBP yuboring"}), 400
    filename = uuid.uuid4().hex + "." + ext
    save_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(save_path)
    url = "/static/uploads/" + filename
    return jsonify({"ok": True, "url": url})

@app.route("/api/admin/add-product", methods=["POST"])
@admin_required
def api_admin_add_product():
    data = request.json or {}
    name = data.get("name","").strip()
    if not name: return jsonify({"ok": False, "error": "Nom kerak"}), 400
    conn = db(); cur = conn.cursor()
    cur.execute("""INSERT INTO products(category_id,name,description,price,old_price,image,badge,stock,active,rating,sold_count,sizes,colors,created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        int(data.get("category_id",1)), name, data.get("description",""),
        int(data.get("price",0)), int(data.get("old_price",0)),
        data.get("image",""), data.get("badge","NEW"),
        int(data.get("stock",99)), 1, 4.5, 0,
        data.get("sizes",""), data.get("colors",""), now()))
    new_id = cur.lastrowid; conn.commit(); conn.close()
    return jsonify({"ok": True, "id": new_id})

@app.route("/api/admin/edit-product", methods=["POST"])
@admin_required
def api_admin_edit_product():
    data = request.json or {}
    pid = data.get("id")
    if not pid: return jsonify({"ok": False}), 400
    conn = db()
    conn.execute("""UPDATE products SET category_id=?,name=?,description=?,price=?,old_price=?,
        image=?,badge=?,stock=?,active=?,sizes=?,colors=? WHERE id=?""", (
        int(data.get("category_id",1)), data.get("name",""), data.get("description",""),
        int(data.get("price",0)), int(data.get("old_price",0)),
        data.get("image",""), data.get("badge",""),
        int(data.get("stock",0)), int(data.get("active",1)),
        data.get("sizes",""), data.get("colors",""), pid))
    conn.commit(); conn.close()
    return jsonify({"ok": True})

@app.route("/api/admin/delete-product", methods=["POST"])
@admin_required
def api_admin_delete_product():
    data = request.json or {}
    conn = db()
    conn.execute("UPDATE products SET active=0 WHERE id=?", (data.get("id"),))
    conn.commit(); conn.close()
    return jsonify({"ok": True})

@app.route("/api/admin/categories")
@admin_required
def api_admin_categories():
    conn = db()
    rows = conn.execute("SELECT * FROM categories ORDER BY sort_order").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/admin/users")
@admin_required
def api_admin_users():
    conn = db()
    rows = conn.execute("SELECT * FROM users ORDER BY id DESC LIMIT 500").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/admin/promo-codes")
@admin_required
def api_admin_promos():
    conn = db()
    rows = conn.execute("SELECT * FROM promo_codes ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/admin/add-promo", methods=["POST"])
@admin_required
def api_admin_add_promo():
    data = request.json or {}
    code = data.get("code","").strip().upper()
    if not code: return jsonify({"ok": False, "error": "Kod kerak"}), 400
    conn = db(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO promo_codes(code,discount_percent,max_uses,active,created_at) VALUES(?,?,?,?,?)",
                    (code, int(data.get("discount",10)), int(data.get("max_uses",100)), 1, now()))
        conn.commit()
    except: conn.close(); return jsonify({"ok": False, "error": "Bu kod mavjud"})
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/admin/toggle-promo", methods=["POST"])
@admin_required
def api_admin_toggle_promo():
    data = request.json or {}
    conn = db()
    conn.execute("UPDATE promo_codes SET active=1-active WHERE id=?", (data.get("id"),))
    conn.commit(); conn.close()
    return jsonify({"ok": True})

@app.route("/api/admin/add-flash-sale", methods=["POST"])
@admin_required
def api_admin_flash_sale():
    data = request.json or {}
    hours = int(data.get("hours", 24))
    starts = now()
    ends = (datetime.now() + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    conn = db(); cur = conn.cursor()
    cur.execute("INSERT INTO flash_sales(product_id,discount_percent,starts_at,ends_at,active) VALUES(?,?,?,?,1)",
                (data.get("product_id"), int(data.get("discount",20)), starts, ends))
    conn.commit(); conn.close()
    return jsonify({"ok": True})

@app.route("/api/admin/broadcast", methods=["POST"])
@admin_required
def api_admin_broadcast():
    data = request.json or {}
    text = data.get("text","").strip()
    image = data.get("image","")
    if not text: return jsonify({"ok": False, "error": "Matn kerak"}), 400
    conn = db(); cur = conn.cursor()
    cur.execute("INSERT INTO broadcasts(text,image,created_at) VALUES(?,?,?)", (text, image, now()))
    broadcast_id = cur.lastrowid
    users = conn.execute("SELECT tg_user_id FROM users WHERE blocked=0").fetchall()
    conn.commit(); conn.close()
    return jsonify({"ok": True, "broadcast_id": broadcast_id, "users": [u["tg_user_id"] for u in users], "text": text, "image": image})

@app.route("/api/admin/reviews")
@admin_required
def api_admin_reviews():
    conn = db()
    rows = conn.execute("""SELECT r.*, p.name as product_name FROM reviews r
        JOIN products p ON r.product_id=p.id ORDER BY r.id DESC LIMIT 100""").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/chat")
def api_chat_get():
    since = int(request.args.get("since", 0))
    limit = min(int(request.args.get("limit", 60)), 100)
    conn = db()
    if since:
        rows = conn.execute("SELECT * FROM chat_messages WHERE id>? ORDER BY id ASC LIMIT ?", (since, limit)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM chat_messages ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        rows = list(reversed(rows))
    admin_id = str(os.getenv("ADMIN_ID", ""))
    my_id = str(request.args.get("uid", ""))
    msgs = []
    for r in rows:
        d = dict(r)
        import json as _json
        reactions_raw = {}
        try: reactions_raw = _json.loads(d.get("reactions") or "{}")
        except: pass
        reaction_counts = {e: len(uids) for e, uids in reactions_raw.items() if uids}
        my_reactions = [e for e, uids in reactions_raw.items() if my_id in uids]
        t = (d.get("created_at") or "")
        time_str = t[11:16] if len(t) >= 16 else ""
        d["reactions"] = reaction_counts
        d["my_reactions"] = my_reactions
        d["is_admin"] = (str(d.get("tg_user_id","")) == admin_id and bool(admin_id))
        d["time_str"] = time_str
        msgs.append(d)
    last_id = msgs[-1]["id"] if msgs else since
    conn.close()
    return jsonify({"messages": msgs, "last_id": last_id})

@app.route("/api/chat", methods=["POST"])
def api_chat_post():
    data = request.json or {}
    tg_user_id = str(data.get("tg_user_id", "")).strip()
    user_name = str(data.get("user_name", "Foydalanuvchi")).strip()[:50]
    user_username = str(data.get("user_username", "")).strip()[:50]
    message = str(data.get("message", "")).strip()[:300]
    if not tg_user_id or not message:
        return jsonify({"ok": False, "error": "Majburiy maydonlar"}), 400
    reply_to = data.get("reply_to")
    reply_text = str(data.get("reply_text", ""))[:80]
    product_id = data.get("product_id")
    product_name = str(data.get("product_name", ""))[:100]
    product_price = int(data.get("product_price", 0) or 0)
    product_image = str(data.get("product_image", ""))[:300]
    conn = db(); cur = conn.cursor()
    cur.execute("""INSERT INTO chat_messages
        (tg_user_id,user_name,user_username,message,reply_to,reply_text,product_id,product_name,product_price,product_image,reactions,created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,'{}',?)""",
        (tg_user_id, user_name, user_username, message, reply_to, reply_text,
         product_id, product_name, product_price, product_image, now()))
    msg_id = cur.lastrowid
    conn.commit(); conn.close()
    return jsonify({"ok": True, "id": msg_id})

@app.route("/api/chat/react", methods=["POST"])
def api_chat_react():
    import json as _json
    data = request.json or {}
    msg_id = int(data.get("message_id", 0))
    emoji = str(data.get("emoji", ""))[:8]
    tg_user_id = str(data.get("tg_user_id", "")).strip()
    if not msg_id or not emoji or not tg_user_id:
        return jsonify({"ok": False}), 400
    conn = db(); cur = conn.cursor()
    row = conn.execute("SELECT reactions FROM chat_messages WHERE id=?", (msg_id,)).fetchone()
    if not row: conn.close(); return jsonify({"ok": False}), 404
    try: reactions = _json.loads(row["reactions"] or "{}")
    except: reactions = {}
    users = reactions.get(emoji, [])
    if tg_user_id in users: users.remove(tg_user_id)
    else: users.append(tg_user_id)
    if users: reactions[emoji] = users
    elif emoji in reactions: del reactions[emoji]
    cur.execute("UPDATE chat_messages SET reactions=? WHERE id=?", (_json.dumps(reactions, ensure_ascii=False), msg_id))
    conn.commit(); conn.close()
    return jsonify({"ok": True})

@app.route("/api/chat/online")
def api_chat_online():
    conn = db()
    from datetime import datetime, timedelta
    threshold = (datetime.utcnow() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
    count = conn.execute("SELECT COUNT(DISTINCT tg_user_id) FROM chat_messages WHERE created_at>=?", (threshold,)).fetchone()[0]
    conn.close()
    return jsonify({"count": max(1, count)})

@app.route("/ping")
def ping():
    return "pong", 200

def keep_alive():
    url = os.getenv("WEB_APP_URL", "")
    if not url:
        return
    while True:
        time.sleep(14 * 60)
        try:
            urllib.request.urlopen(f"{url}/ping", timeout=10)
        except Exception:
            pass

if __name__ == "__main__":
    init_db()
    t = threading.Thread(target=keep_alive, daemon=True)
    t.start()
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
