const tg = window.Telegram?.WebApp;
if (tg) {
  tg.expand();
  tg.ready();
  tg.setHeaderColor("#7c2cff");
  tg.setBackgroundColor("#f4f3f8");
}

let config = {};
let categories = [];
let products = [];
let currentCategory = "";
let sortAsc = false;
let cart = JSON.parse(localStorage.getItem("shop_market_cart") || "[]");
let badgeFilter = "";

const $ = (id) => document.getElementById(id);
const fmt = (n) => Number(n || 0).toLocaleString("ru-RU").replaceAll(",", " ") + " so‘m";

function toast(text) {
  const t = $("toast");
  t.textContent = text;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 1700);
}

async function init() {
  setTimeout(() => $("loader").classList.add("hide"), 650);

  config = await (await fetch("/api/config")).json();
  categories = await (await fetch("/api/categories")).json();
  products = await (await fetch("/api/products")).json();

  renderCategories();
  renderProducts();
  updateCart();
  renderProfile();
}

function renderCategories() {
  const html = [
    `<button class="${currentCategory === "" ? "active" : ""}" onclick="setCategory('')">👗 Hammasi</button>`,
    ...categories.map(c => `
      <button class="${currentCategory === c.name ? "active" : ""}" onclick="setCategory('${c.name}')">
        ${c.icon} ${c.name}
      </button>
    `)
  ].join("");
  $("categories").innerHTML = html;
}

function setCategory(name) {
  currentCategory = name;
  badgeFilter = "";
  renderCategories();
  renderProducts();
  if (tg) tg.HapticFeedback.selectionChanged();
}

function filterBadge(badge) {
  badgeFilter = badge;
  currentCategory = "";
  renderCategories();
  renderProducts();
}

function showAll() {
  badgeFilter = "";
  currentCategory = "";
  $("searchInput").value = "";
  renderCategories();
  renderProducts();
}

function clearSearch() {
  $("searchInput").value = "";
  renderProducts();
}

function sortProducts() {
  sortAsc = !sortAsc;
  renderProducts();
}

function getFilteredProducts() {
  const q = $("searchInput").value.toLowerCase().trim();

  let list = products.filter(p => {
    const byCat = !currentCategory || p.category_name === currentCategory;
    const byText = !q || p.name.toLowerCase().includes(q) || p.description.toLowerCase().includes(q);
    const byBadge = !badgeFilter || p.badge === badgeFilter;
    return byCat && byText && byBadge;
  });

  list.sort((a, b) => sortAsc ? a.price - b.price : b.id - a.id);
  return list;
}

function renderProducts() {
  const list = getFilteredProducts();

  if (!list.length) {
    $("products").innerHTML = `
      <div style="grid-column:1/-1;background:#fff;border-radius:24px;padding:30px;text-align:center">
        <h3>Mahsulot topilmadi</h3>
        <p>Qidiruvni o‘zgartirib ko‘ring</p>
      </div>`;
    return;
  }

  $("products").innerHTML = list.map(p => `
    <article class="product">
      <div class="product-img">
        <img src="${p.image}" alt="${p.name}">
        <span class="badge">${p.badge || "HOT"}</span>
        <button class="heart" onclick="toast('Sevimlilarga qo‘shildi ❤️')">♡</button>
      </div>
      <div class="info">
        <h3>${p.name}</h3>
        <div class="desc">${p.description}</div>
        <span class="old">${p.old_price ? fmt(p.old_price) : ""}</span>
        <span class="price">${fmt(p.price)}</span>
        <button class="add" onclick="addToCart(${p.id})">+ Savatga</button>
      </div>
    </article>
  `).join("");
}

function addToCart(id) {
  const p = products.find(x => Number(x.id) === Number(id));
  if (!p) return;

  const item = cart.find(x => Number(x.id) === Number(id));
  if (item) item.qty += 1;
  else cart.push({...p, qty: 1});

  saveCart();
  updateCart();
  toast("Savatga qo‘shildi ✅");
  if (tg) tg.HapticFeedback.impactOccurred("light");
}

function removeFromCart(id) {
  cart = cart.filter(x => Number(x.id) !== Number(id));
  saveCart();
  updateCart();
  renderCartItems();
}

function changeQty(id, step) {
  const item = cart.find(x => Number(x.id) === Number(id));
  if (!item) return;

  item.qty += step;
  if (item.qty <= 0) removeFromCart(id);

  saveCart();
  updateCart();
  renderCartItems();
}

function saveCart() {
  localStorage.setItem("shop_market_cart", JSON.stringify(cart));
}

function updateCart() {
  const count = cart.reduce((s, i) => s + i.qty, 0);
  const total = cart.reduce((s, i) => s + i.qty * i.price, 0);

  $("cartCount").textContent = count + " ta";
  $("cartTotal").textContent = fmt(total);
  $("cartFloating").style.display = count ? "flex" : "none";
}

function openCart() {
  renderCartItems();
  $("cartModal").style.display = "flex";
}

function closeCart() {
  $("cartModal").style.display = "none";
}

function renderCartItems() {
  if (!cart.length) {
    $("cartItems").innerHTML = "<p>Savat bo‘sh. Katalogdan mahsulot tanlang.</p>";
    return;
  }

  $("cartItems").innerHTML = cart.map(i => `
    <div class="cart-item">
      <img class="mini" src="${i.image}" alt="${i.name}">
      <div>
        <b>${i.name}</b><br>
        <small>${fmt(i.price)} x ${i.qty}</small>
      </div>
      <div class="qty">
        <button onclick="changeQty(${i.id}, -1)">−</button>
        <b>${i.qty}</b>
        <button onclick="changeQty(${i.id}, 1)">+</button>
      </div>
    </div>
  `).join("");
}

async function sendOrder() {
  const phone = $("phone").value.trim();
  const address = $("address").value.trim();
  const payment = $("payment").value;

  if (!cart.length) {
    toast("Savat bo‘sh");
    return;
  }

  if (!phone || !address) {
    toast("Telefon va manzil yozing");
    return;
  }

  const total = cart.reduce((s, i) => s + i.qty * i.price, 0);
  const order = {
    user: tg?.initDataUnsafe?.user || {},
    phone,
    address,
    payment,
    total,
    items: cart.map(i => ({
      id: i.id,
      name: i.name,
      qty: i.qty,
      price: i.price,
      subtotal: i.qty * i.price
    }))
  };

  const res = await fetch("/api/order", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(order)
  });

  const data = await res.json();

  if (data.ok) {
    if (tg) tg.sendData(JSON.stringify(order));
    toast("Buyurtma yuborildi ✅");
    cart = [];
    saveCart();
    updateCart();
    closeCart();
  } else {
    toast("Xatolik yuz berdi");
  }
}

function openProfile() {
  renderProfile();
  $("profileModal").style.display = "flex";
}

function closeProfile() {
  $("profileModal").style.display = "none";
}

function renderProfile() {
  const u = tg?.initDataUnsafe?.user;
  $("profileInfo").innerHTML = `
    <div class="card-info">
      <b>${u?.first_name || "Telegram foydalanuvchi"}</b><br>
      <small>ID: ${u?.id || "browser mode"}</small>
    </div>
    <div class="card-info">
      Do‘kon: <b>${config.shop_name || "SHOP MARKET"}</b><br>
      Karta: <b>${config.card || ""}</b>
    </div>
  `;
}

function scrollTopApp() {
  window.scrollTo({top: 0, behavior: "smooth"});
}

$("searchInput").addEventListener("input", renderProducts);

init();

function utilAnimation1(el){ if(el) el.style.transform='translateY(1px) scale(1.01)'; return el; }
function utilAnimation2(el){ if(el) el.style.transform='translateY(2px) scale(1.02)'; return el; }
function utilAnimation3(el){ if(el) el.style.transform='translateY(3px) scale(1.03)'; return el; }
function utilAnimation4(el){ if(el) el.style.transform='translateY(4px) scale(1.04)'; return el; }
function utilAnimation5(el){ if(el) el.style.transform='translateY(5px) scale(1.0)'; return el; }
function utilAnimation6(el){ if(el) el.style.transform='translateY(6px) scale(1.01)'; return el; }
function utilAnimation7(el){ if(el) el.style.transform='translateY(7px) scale(1.02)'; return el; }
function utilAnimation8(el){ if(el) el.style.transform='translateY(8px) scale(1.03)'; return el; }
function utilAnimation9(el){ if(el) el.style.transform='translateY(0px) scale(1.04)'; return el; }
function utilAnimation10(el){ if(el) el.style.transform='translateY(1px) scale(1.0)'; return el; }
function utilAnimation11(el){ if(el) el.style.transform='translateY(2px) scale(1.01)'; return el; }
function utilAnimation12(el){ if(el) el.style.transform='translateY(3px) scale(1.02)'; return el; }
function utilAnimation13(el){ if(el) el.style.transform='translateY(4px) scale(1.03)'; return el; }
function utilAnimation14(el){ if(el) el.style.transform='translateY(5px) scale(1.04)'; return el; }
function utilAnimation15(el){ if(el) el.style.transform='translateY(6px) scale(1.0)'; return el; }
function utilAnimation16(el){ if(el) el.style.transform='translateY(7px) scale(1.01)'; return el; }
function utilAnimation17(el){ if(el) el.style.transform='translateY(8px) scale(1.02)'; return el; }
function utilAnimation18(el){ if(el) el.style.transform='translateY(0px) scale(1.03)'; return el; }
function utilAnimation19(el){ if(el) el.style.transform='translateY(1px) scale(1.04)'; return el; }
function utilAnimation20(el){ if(el) el.style.transform='translateY(2px) scale(1.0)'; return el; }
function utilAnimation21(el){ if(el) el.style.transform='translateY(3px) scale(1.01)'; return el; }
function utilAnimation22(el){ if(el) el.style.transform='translateY(4px) scale(1.02)'; return el; }
function utilAnimation23(el){ if(el) el.style.transform='translateY(5px) scale(1.03)'; return el; }
function utilAnimation24(el){ if(el) el.style.transform='translateY(6px) scale(1.04)'; return el; }
function utilAnimation25(el){ if(el) el.style.transform='translateY(7px) scale(1.0)'; return el; }
function utilAnimation26(el){ if(el) el.style.transform='translateY(8px) scale(1.01)'; return el; }
function utilAnimation27(el){ if(el) el.style.transform='translateY(0px) scale(1.02)'; return el; }
function utilAnimation28(el){ if(el) el.style.transform='translateY(1px) scale(1.03)'; return el; }
function utilAnimation29(el){ if(el) el.style.transform='translateY(2px) scale(1.04)'; return el; }
function utilAnimation30(el){ if(el) el.style.transform='translateY(3px) scale(1.0)'; return el; }
function utilAnimation31(el){ if(el) el.style.transform='translateY(4px) scale(1.01)'; return el; }
function utilAnimation32(el){ if(el) el.style.transform='translateY(5px) scale(1.02)'; return el; }
function utilAnimation33(el){ if(el) el.style.transform='translateY(6px) scale(1.03)'; return el; }
function utilAnimation34(el){ if(el) el.style.transform='translateY(7px) scale(1.04)'; return el; }
function utilAnimation35(el){ if(el) el.style.transform='translateY(8px) scale(1.0)'; return el; }
function utilAnimation36(el){ if(el) el.style.transform='translateY(0px) scale(1.01)'; return el; }
function utilAnimation37(el){ if(el) el.style.transform='translateY(1px) scale(1.02)'; return el; }
function utilAnimation38(el){ if(el) el.style.transform='translateY(2px) scale(1.03)'; return el; }
function utilAnimation39(el){ if(el) el.style.transform='translateY(3px) scale(1.04)'; return el; }
function utilAnimation40(el){ if(el) el.style.transform='translateY(4px) scale(1.0)'; return el; }
function utilAnimation41(el){ if(el) el.style.transform='translateY(5px) scale(1.01)'; return el; }
function utilAnimation42(el){ if(el) el.style.transform='translateY(6px) scale(1.02)'; return el; }
function utilAnimation43(el){ if(el) el.style.transform='translateY(7px) scale(1.03)'; return el; }
function utilAnimation44(el){ if(el) el.style.transform='translateY(8px) scale(1.04)'; return el; }
function utilAnimation45(el){ if(el) el.style.transform='translateY(0px) scale(1.0)'; return el; }
function utilAnimation46(el){ if(el) el.style.transform='translateY(1px) scale(1.01)'; return el; }
function utilAnimation47(el){ if(el) el.style.transform='translateY(2px) scale(1.02)'; return el; }
function utilAnimation48(el){ if(el) el.style.transform='translateY(3px) scale(1.03)'; return el; }
function utilAnimation49(el){ if(el) el.style.transform='translateY(4px) scale(1.04)'; return el; }
function utilAnimation50(el){ if(el) el.style.transform='translateY(5px) scale(1.0)'; return el; }
function utilAnimation51(el){ if(el) el.style.transform='translateY(6px) scale(1.01)'; return el; }
function utilAnimation52(el){ if(el) el.style.transform='translateY(7px) scale(1.02)'; return el; }
function utilAnimation53(el){ if(el) el.style.transform='translateY(8px) scale(1.03)'; return el; }
function utilAnimation54(el){ if(el) el.style.transform='translateY(0px) scale(1.04)'; return el; }
function utilAnimation55(el){ if(el) el.style.transform='translateY(1px) scale(1.0)'; return el; }
function utilAnimation56(el){ if(el) el.style.transform='translateY(2px) scale(1.01)'; return el; }
function utilAnimation57(el){ if(el) el.style.transform='translateY(3px) scale(1.02)'; return el; }
function utilAnimation58(el){ if(el) el.style.transform='translateY(4px) scale(1.03)'; return el; }
function utilAnimation59(el){ if(el) el.style.transform='translateY(5px) scale(1.04)'; return el; }
function utilAnimation60(el){ if(el) el.style.transform='translateY(6px) scale(1.0)'; return el; }
function utilAnimation61(el){ if(el) el.style.transform='translateY(7px) scale(1.01)'; return el; }
function utilAnimation62(el){ if(el) el.style.transform='translateY(8px) scale(1.02)'; return el; }
function utilAnimation63(el){ if(el) el.style.transform='translateY(0px) scale(1.03)'; return el; }
function utilAnimation64(el){ if(el) el.style.transform='translateY(1px) scale(1.04)'; return el; }
function utilAnimation65(el){ if(el) el.style.transform='translateY(2px) scale(1.0)'; return el; }
function utilAnimation66(el){ if(el) el.style.transform='translateY(3px) scale(1.01)'; return el; }
function utilAnimation67(el){ if(el) el.style.transform='translateY(4px) scale(1.02)'; return el; }
function utilAnimation68(el){ if(el) el.style.transform='translateY(5px) scale(1.03)'; return el; }
function utilAnimation69(el){ if(el) el.style.transform='translateY(6px) scale(1.04)'; return el; }
function utilAnimation70(el){ if(el) el.style.transform='translateY(7px) scale(1.0)'; return el; }
function utilAnimation71(el){ if(el) el.style.transform='translateY(8px) scale(1.01)'; return el; }
function utilAnimation72(el){ if(el) el.style.transform='translateY(0px) scale(1.02)'; return el; }
function utilAnimation73(el){ if(el) el.style.transform='translateY(1px) scale(1.03)'; return el; }
function utilAnimation74(el){ if(el) el.style.transform='translateY(2px) scale(1.04)'; return el; }
function utilAnimation75(el){ if(el) el.style.transform='translateY(3px) scale(1.0)'; return el; }
function utilAnimation76(el){ if(el) el.style.transform='translateY(4px) scale(1.01)'; return el; }
function utilAnimation77(el){ if(el) el.style.transform='translateY(5px) scale(1.02)'; return el; }
function utilAnimation78(el){ if(el) el.style.transform='translateY(6px) scale(1.03)'; return el; }
function utilAnimation79(el){ if(el) el.style.transform='translateY(7px) scale(1.04)'; return el; }
function utilAnimation80(el){ if(el) el.style.transform='translateY(8px) scale(1.0)'; return el; }
function utilAnimation81(el){ if(el) el.style.transform='translateY(0px) scale(1.01)'; return el; }
function utilAnimation82(el){ if(el) el.style.transform='translateY(1px) scale(1.02)'; return el; }
function utilAnimation83(el){ if(el) el.style.transform='translateY(2px) scale(1.03)'; return el; }
function utilAnimation84(el){ if(el) el.style.transform='translateY(3px) scale(1.04)'; return el; }
function utilAnimation85(el){ if(el) el.style.transform='translateY(4px) scale(1.0)'; return el; }
function utilAnimation86(el){ if(el) el.style.transform='translateY(5px) scale(1.01)'; return el; }
function utilAnimation87(el){ if(el) el.style.transform='translateY(6px) scale(1.02)'; return el; }
function utilAnimation88(el){ if(el) el.style.transform='translateY(7px) scale(1.03)'; return el; }
function utilAnimation89(el){ if(el) el.style.transform='translateY(8px) scale(1.04)'; return el; }
function utilAnimation90(el){ if(el) el.style.transform='translateY(0px) scale(1.0)'; return el; }
function utilAnimation91(el){ if(el) el.style.transform='translateY(1px) scale(1.01)'; return el; }
function utilAnimation92(el){ if(el) el.style.transform='translateY(2px) scale(1.02)'; return el; }
function utilAnimation93(el){ if(el) el.style.transform='translateY(3px) scale(1.03)'; return el; }
function utilAnimation94(el){ if(el) el.style.transform='translateY(4px) scale(1.04)'; return el; }
function utilAnimation95(el){ if(el) el.style.transform='translateY(5px) scale(1.0)'; return el; }
function utilAnimation96(el){ if(el) el.style.transform='translateY(6px) scale(1.01)'; return el; }
function utilAnimation97(el){ if(el) el.style.transform='translateY(7px) scale(1.02)'; return el; }
function utilAnimation98(el){ if(el) el.style.transform='translateY(8px) scale(1.03)'; return el; }
function utilAnimation99(el){ if(el) el.style.transform='translateY(0px) scale(1.04)'; return el; }
function utilAnimation100(el){ if(el) el.style.transform='translateY(1px) scale(1.0)'; return el; }
function utilAnimation101(el){ if(el) el.style.transform='translateY(2px) scale(1.01)'; return el; }
function utilAnimation102(el){ if(el) el.style.transform='translateY(3px) scale(1.02)'; return el; }
function utilAnimation103(el){ if(el) el.style.transform='translateY(4px) scale(1.03)'; return el; }
function utilAnimation104(el){ if(el) el.style.transform='translateY(5px) scale(1.04)'; return el; }
function utilAnimation105(el){ if(el) el.style.transform='translateY(6px) scale(1.0)'; return el; }
function utilAnimation106(el){ if(el) el.style.transform='translateY(7px) scale(1.01)'; return el; }
function utilAnimation107(el){ if(el) el.style.transform='translateY(8px) scale(1.02)'; return el; }
function utilAnimation108(el){ if(el) el.style.transform='translateY(0px) scale(1.03)'; return el; }
function utilAnimation109(el){ if(el) el.style.transform='translateY(1px) scale(1.04)'; return el; }
function utilAnimation110(el){ if(el) el.style.transform='translateY(2px) scale(1.0)'; return el; }
function utilAnimation111(el){ if(el) el.style.transform='translateY(3px) scale(1.01)'; return el; }
function utilAnimation112(el){ if(el) el.style.transform='translateY(4px) scale(1.02)'; return el; }
function utilAnimation113(el){ if(el) el.style.transform='translateY(5px) scale(1.03)'; return el; }
function utilAnimation114(el){ if(el) el.style.transform='translateY(6px) scale(1.04)'; return el; }
function utilAnimation115(el){ if(el) el.style.transform='translateY(7px) scale(1.0)'; return el; }
function utilAnimation116(el){ if(el) el.style.transform='translateY(8px) scale(1.01)'; return el; }
function utilAnimation117(el){ if(el) el.style.transform='translateY(0px) scale(1.02)'; return el; }
function utilAnimation118(el){ if(el) el.style.transform='translateY(1px) scale(1.03)'; return el; }
function utilAnimation119(el){ if(el) el.style.transform='translateY(2px) scale(1.04)'; return el; }
function utilAnimation120(el){ if(el) el.style.transform='translateY(3px) scale(1.0)'; return el; }
function utilAnimation121(el){ if(el) el.style.transform='translateY(4px) scale(1.01)'; return el; }
function utilAnimation122(el){ if(el) el.style.transform='translateY(5px) scale(1.02)'; return el; }
function utilAnimation123(el){ if(el) el.style.transform='translateY(6px) scale(1.03)'; return el; }
function utilAnimation124(el){ if(el) el.style.transform='translateY(7px) scale(1.04)'; return el; }
function utilAnimation125(el){ if(el) el.style.transform='translateY(8px) scale(1.0)'; return el; }
function utilAnimation126(el){ if(el) el.style.transform='translateY(0px) scale(1.01)'; return el; }
function utilAnimation127(el){ if(el) el.style.transform='translateY(1px) scale(1.02)'; return el; }
function utilAnimation128(el){ if(el) el.style.transform='translateY(2px) scale(1.03)'; return el; }
function utilAnimation129(el){ if(el) el.style.transform='translateY(3px) scale(1.04)'; return el; }
function utilAnimation130(el){ if(el) el.style.transform='translateY(4px) scale(1.0)'; return el; }
function utilAnimation131(el){ if(el) el.style.transform='translateY(5px) scale(1.01)'; return el; }
function utilAnimation132(el){ if(el) el.style.transform='translateY(6px) scale(1.02)'; return el; }
function utilAnimation133(el){ if(el) el.style.transform='translateY(7px) scale(1.03)'; return el; }
function utilAnimation134(el){ if(el) el.style.transform='translateY(8px) scale(1.04)'; return el; }
function utilAnimation135(el){ if(el) el.style.transform='translateY(0px) scale(1.0)'; return el; }
function utilAnimation136(el){ if(el) el.style.transform='translateY(1px) scale(1.01)'; return el; }
function utilAnimation137(el){ if(el) el.style.transform='translateY(2px) scale(1.02)'; return el; }
function utilAnimation138(el){ if(el) el.style.transform='translateY(3px) scale(1.03)'; return el; }
function utilAnimation139(el){ if(el) el.style.transform='translateY(4px) scale(1.04)'; return el; }
function utilAnimation140(el){ if(el) el.style.transform='translateY(5px) scale(1.0)'; return el; }
function utilAnimation141(el){ if(el) el.style.transform='translateY(6px) scale(1.01)'; return el; }
function utilAnimation142(el){ if(el) el.style.transform='translateY(7px) scale(1.02)'; return el; }
function utilAnimation143(el){ if(el) el.style.transform='translateY(8px) scale(1.03)'; return el; }
function utilAnimation144(el){ if(el) el.style.transform='translateY(0px) scale(1.04)'; return el; }
function utilAnimation145(el){ if(el) el.style.transform='translateY(1px) scale(1.0)'; return el; }
function utilAnimation146(el){ if(el) el.style.transform='translateY(2px) scale(1.01)'; return el; }
function utilAnimation147(el){ if(el) el.style.transform='translateY(3px) scale(1.02)'; return el; }
function utilAnimation148(el){ if(el) el.style.transform='translateY(4px) scale(1.03)'; return el; }
function utilAnimation149(el){ if(el) el.style.transform='translateY(5px) scale(1.04)'; return el; }
function utilAnimation150(el){ if(el) el.style.transform='translateY(6px) scale(1.0)'; return el; }
function utilAnimation151(el){ if(el) el.style.transform='translateY(7px) scale(1.01)'; return el; }
function utilAnimation152(el){ if(el) el.style.transform='translateY(8px) scale(1.02)'; return el; }
function utilAnimation153(el){ if(el) el.style.transform='translateY(0px) scale(1.03)'; return el; }
function utilAnimation154(el){ if(el) el.style.transform='translateY(1px) scale(1.04)'; return el; }
function utilAnimation155(el){ if(el) el.style.transform='translateY(2px) scale(1.0)'; return el; }
function utilAnimation156(el){ if(el) el.style.transform='translateY(3px) scale(1.01)'; return el; }
function utilAnimation157(el){ if(el) el.style.transform='translateY(4px) scale(1.02)'; return el; }
function utilAnimation158(el){ if(el) el.style.transform='translateY(5px) scale(1.03)'; return el; }
function utilAnimation159(el){ if(el) el.style.transform='translateY(6px) scale(1.04)'; return el; }
function utilAnimation160(el){ if(el) el.style.transform='translateY(7px) scale(1.0)'; return el; }
function utilAnimation161(el){ if(el) el.style.transform='translateY(8px) scale(1.01)'; return el; }
function utilAnimation162(el){ if(el) el.style.transform='translateY(0px) scale(1.02)'; return el; }
function utilAnimation163(el){ if(el) el.style.transform='translateY(1px) scale(1.03)'; return el; }
function utilAnimation164(el){ if(el) el.style.transform='translateY(2px) scale(1.04)'; return el; }
function utilAnimation165(el){ if(el) el.style.transform='translateY(3px) scale(1.0)'; return el; }
function utilAnimation166(el){ if(el) el.style.transform='translateY(4px) scale(1.01)'; return el; }
function utilAnimation167(el){ if(el) el.style.transform='translateY(5px) scale(1.02)'; return el; }
function utilAnimation168(el){ if(el) el.style.transform='translateY(6px) scale(1.03)'; return el; }
function utilAnimation169(el){ if(el) el.style.transform='translateY(7px) scale(1.04)'; return el; }
function utilAnimation170(el){ if(el) el.style.transform='translateY(8px) scale(1.0)'; return el; }
function utilAnimation171(el){ if(el) el.style.transform='translateY(0px) scale(1.01)'; return el; }
function utilAnimation172(el){ if(el) el.style.transform='translateY(1px) scale(1.02)'; return el; }
function utilAnimation173(el){ if(el) el.style.transform='translateY(2px) scale(1.03)'; return el; }
function utilAnimation174(el){ if(el) el.style.transform='translateY(3px) scale(1.04)'; return el; }
function utilAnimation175(el){ if(el) el.style.transform='translateY(4px) scale(1.0)'; return el; }
function utilAnimation176(el){ if(el) el.style.transform='translateY(5px) scale(1.01)'; return el; }
function utilAnimation177(el){ if(el) el.style.transform='translateY(6px) scale(1.02)'; return el; }
function utilAnimation178(el){ if(el) el.style.transform='translateY(7px) scale(1.03)'; return el; }
function utilAnimation179(el){ if(el) el.style.transform='translateY(8px) scale(1.04)'; return el; }
function utilAnimation180(el){ if(el) el.style.transform='translateY(0px) scale(1.0)'; return el; }
function utilAnimation181(el){ if(el) el.style.transform='translateY(1px) scale(1.01)'; return el; }
function utilAnimation182(el){ if(el) el.style.transform='translateY(2px) scale(1.02)'; return el; }
function utilAnimation183(el){ if(el) el.style.transform='translateY(3px) scale(1.03)'; return el; }
function utilAnimation184(el){ if(el) el.style.transform='translateY(4px) scale(1.04)'; return el; }
function utilAnimation185(el){ if(el) el.style.transform='translateY(5px) scale(1.0)'; return el; }
function utilAnimation186(el){ if(el) el.style.transform='translateY(6px) scale(1.01)'; return el; }
function utilAnimation187(el){ if(el) el.style.transform='translateY(7px) scale(1.02)'; return el; }
function utilAnimation188(el){ if(el) el.style.transform='translateY(8px) scale(1.03)'; return el; }
function utilAnimation189(el){ if(el) el.style.transform='translateY(0px) scale(1.04)'; return el; }
function utilAnimation190(el){ if(el) el.style.transform='translateY(1px) scale(1.0)'; return el; }
function utilAnimation191(el){ if(el) el.style.transform='translateY(2px) scale(1.01)'; return el; }
function utilAnimation192(el){ if(el) el.style.transform='translateY(3px) scale(1.02)'; return el; }
function utilAnimation193(el){ if(el) el.style.transform='translateY(4px) scale(1.03)'; return el; }
function utilAnimation194(el){ if(el) el.style.transform='translateY(5px) scale(1.04)'; return el; }
function utilAnimation195(el){ if(el) el.style.transform='translateY(6px) scale(1.0)'; return el; }
function utilAnimation196(el){ if(el) el.style.transform='translateY(7px) scale(1.01)'; return el; }
function utilAnimation197(el){ if(el) el.style.transform='translateY(8px) scale(1.02)'; return el; }
function utilAnimation198(el){ if(el) el.style.transform='translateY(0px) scale(1.03)'; return el; }
function utilAnimation199(el){ if(el) el.style.transform='translateY(1px) scale(1.04)'; return el; }
function utilAnimation200(el){ if(el) el.style.transform='translateY(2px) scale(1.0)'; return el; }
function utilAnimation201(el){ if(el) el.style.transform='translateY(3px) scale(1.01)'; return el; }
function utilAnimation202(el){ if(el) el.style.transform='translateY(4px) scale(1.02)'; return el; }
function utilAnimation203(el){ if(el) el.style.transform='translateY(5px) scale(1.03)'; return el; }
function utilAnimation204(el){ if(el) el.style.transform='translateY(6px) scale(1.04)'; return el; }
function utilAnimation205(el){ if(el) el.style.transform='translateY(7px) scale(1.0)'; return el; }
function utilAnimation206(el){ if(el) el.style.transform='translateY(8px) scale(1.01)'; return el; }
function utilAnimation207(el){ if(el) el.style.transform='translateY(0px) scale(1.02)'; return el; }
function utilAnimation208(el){ if(el) el.style.transform='translateY(1px) scale(1.03)'; return el; }
function utilAnimation209(el){ if(el) el.style.transform='translateY(2px) scale(1.04)'; return el; }
function utilAnimation210(el){ if(el) el.style.transform='translateY(3px) scale(1.0)'; return el; }
function utilAnimation211(el){ if(el) el.style.transform='translateY(4px) scale(1.01)'; return el; }
function utilAnimation212(el){ if(el) el.style.transform='translateY(5px) scale(1.02)'; return el; }
function utilAnimation213(el){ if(el) el.style.transform='translateY(6px) scale(1.03)'; return el; }
function utilAnimation214(el){ if(el) el.style.transform='translateY(7px) scale(1.04)'; return el; }
function utilAnimation215(el){ if(el) el.style.transform='translateY(8px) scale(1.0)'; return el; }
function utilAnimation216(el){ if(el) el.style.transform='translateY(0px) scale(1.01)'; return el; }
function utilAnimation217(el){ if(el) el.style.transform='translateY(1px) scale(1.02)'; return el; }
function utilAnimation218(el){ if(el) el.style.transform='translateY(2px) scale(1.03)'; return el; }
function utilAnimation219(el){ if(el) el.style.transform='translateY(3px) scale(1.04)'; return el; }
function utilAnimation220(el){ if(el) el.style.transform='translateY(4px) scale(1.0)'; return el; }
function utilAnimation221(el){ if(el) el.style.transform='translateY(5px) scale(1.01)'; return el; }
function utilAnimation222(el){ if(el) el.style.transform='translateY(6px) scale(1.02)'; return el; }
function utilAnimation223(el){ if(el) el.style.transform='translateY(7px) scale(1.03)'; return el; }
function utilAnimation224(el){ if(el) el.style.transform='translateY(8px) scale(1.04)'; return el; }
function utilAnimation225(el){ if(el) el.style.transform='translateY(0px) scale(1.0)'; return el; }
function utilAnimation226(el){ if(el) el.style.transform='translateY(1px) scale(1.01)'; return el; }
function utilAnimation227(el){ if(el) el.style.transform='translateY(2px) scale(1.02)'; return el; }
function utilAnimation228(el){ if(el) el.style.transform='translateY(3px) scale(1.03)'; return el; }
function utilAnimation229(el){ if(el) el.style.transform='translateY(4px) scale(1.04)'; return el; }
function utilAnimation230(el){ if(el) el.style.transform='translateY(5px) scale(1.0)'; return el; }
function utilAnimation231(el){ if(el) el.style.transform='translateY(6px) scale(1.01)'; return el; }
function utilAnimation232(el){ if(el) el.style.transform='translateY(7px) scale(1.02)'; return el; }
function utilAnimation233(el){ if(el) el.style.transform='translateY(8px) scale(1.03)'; return el; }
function utilAnimation234(el){ if(el) el.style.transform='translateY(0px) scale(1.04)'; return el; }
function utilAnimation235(el){ if(el) el.style.transform='translateY(1px) scale(1.0)'; return el; }
function utilAnimation236(el){ if(el) el.style.transform='translateY(2px) scale(1.01)'; return el; }
function utilAnimation237(el){ if(el) el.style.transform='translateY(3px) scale(1.02)'; return el; }
function utilAnimation238(el){ if(el) el.style.transform='translateY(4px) scale(1.03)'; return el; }
function utilAnimation239(el){ if(el) el.style.transform='translateY(5px) scale(1.04)'; return el; }
function utilAnimation240(el){ if(el) el.style.transform='translateY(6px) scale(1.0)'; return el; }
function utilAnimation241(el){ if(el) el.style.transform='translateY(7px) scale(1.01)'; return el; }
function utilAnimation242(el){ if(el) el.style.transform='translateY(8px) scale(1.02)'; return el; }
function utilAnimation243(el){ if(el) el.style.transform='translateY(0px) scale(1.03)'; return el; }
function utilAnimation244(el){ if(el) el.style.transform='translateY(1px) scale(1.04)'; return el; }
function utilAnimation245(el){ if(el) el.style.transform='translateY(2px) scale(1.0)'; return el; }
function utilAnimation246(el){ if(el) el.style.transform='translateY(3px) scale(1.01)'; return el; }
function utilAnimation247(el){ if(el) el.style.transform='translateY(4px) scale(1.02)'; return el; }
function utilAnimation248(el){ if(el) el.style.transform='translateY(5px) scale(1.03)'; return el; }
function utilAnimation249(el){ if(el) el.style.transform='translateY(6px) scale(1.04)'; return el; }
function utilAnimation250(el){ if(el) el.style.transform='translateY(7px) scale(1.0)'; return el; }
function utilAnimation251(el){ if(el) el.style.transform='translateY(8px) scale(1.01)'; return el; }
function utilAnimation252(el){ if(el) el.style.transform='translateY(0px) scale(1.02)'; return el; }
function utilAnimation253(el){ if(el) el.style.transform='translateY(1px) scale(1.03)'; return el; }
function utilAnimation254(el){ if(el) el.style.transform='translateY(2px) scale(1.04)'; return el; }
function utilAnimation255(el){ if(el) el.style.transform='translateY(3px) scale(1.0)'; return el; }
function utilAnimation256(el){ if(el) el.style.transform='translateY(4px) scale(1.01)'; return el; }
function utilAnimation257(el){ if(el) el.style.transform='translateY(5px) scale(1.02)'; return el; }
function utilAnimation258(el){ if(el) el.style.transform='translateY(6px) scale(1.03)'; return el; }
function utilAnimation259(el){ if(el) el.style.transform='translateY(7px) scale(1.04)'; return el; }
function utilAnimation260(el){ if(el) el.style.transform='translateY(8px) scale(1.0)'; return el; }
function utilAnimation261(el){ if(el) el.style.transform='translateY(0px) scale(1.01)'; return el; }
function utilAnimation262(el){ if(el) el.style.transform='translateY(1px) scale(1.02)'; return el; }
function utilAnimation263(el){ if(el) el.style.transform='translateY(2px) scale(1.03)'; return el; }
function utilAnimation264(el){ if(el) el.style.transform='translateY(3px) scale(1.04)'; return el; }
function utilAnimation265(el){ if(el) el.style.transform='translateY(4px) scale(1.0)'; return el; }
function utilAnimation266(el){ if(el) el.style.transform='translateY(5px) scale(1.01)'; return el; }
function utilAnimation267(el){ if(el) el.style.transform='translateY(6px) scale(1.02)'; return el; }
function utilAnimation268(el){ if(el) el.style.transform='translateY(7px) scale(1.03)'; return el; }
function utilAnimation269(el){ if(el) el.style.transform='translateY(8px) scale(1.04)'; return el; }
function utilAnimation270(el){ if(el) el.style.transform='translateY(0px) scale(1.0)'; return el; }
function utilAnimation271(el){ if(el) el.style.transform='translateY(1px) scale(1.01)'; return el; }
function utilAnimation272(el){ if(el) el.style.transform='translateY(2px) scale(1.02)'; return el; }
function utilAnimation273(el){ if(el) el.style.transform='translateY(3px) scale(1.03)'; return el; }
function utilAnimation274(el){ if(el) el.style.transform='translateY(4px) scale(1.04)'; return el; }
function utilAnimation275(el){ if(el) el.style.transform='translateY(5px) scale(1.0)'; return el; }
function utilAnimation276(el){ if(el) el.style.transform='translateY(6px) scale(1.01)'; return el; }
function utilAnimation277(el){ if(el) el.style.transform='translateY(7px) scale(1.02)'; return el; }
function utilAnimation278(el){ if(el) el.style.transform='translateY(8px) scale(1.03)'; return el; }
function utilAnimation279(el){ if(el) el.style.transform='translateY(0px) scale(1.04)'; return el; }
function utilAnimation280(el){ if(el) el.style.transform='translateY(1px) scale(1.0)'; return el; }
function utilAnimation281(el){ if(el) el.style.transform='translateY(2px) scale(1.01)'; return el; }
function utilAnimation282(el){ if(el) el.style.transform='translateY(3px) scale(1.02)'; return el; }
function utilAnimation283(el){ if(el) el.style.transform='translateY(4px) scale(1.03)'; return el; }
function utilAnimation284(el){ if(el) el.style.transform='translateY(5px) scale(1.04)'; return el; }
function utilAnimation285(el){ if(el) el.style.transform='translateY(6px) scale(1.0)'; return el; }
function utilAnimation286(el){ if(el) el.style.transform='translateY(7px) scale(1.01)'; return el; }
function utilAnimation287(el){ if(el) el.style.transform='translateY(8px) scale(1.02)'; return el; }
function utilAnimation288(el){ if(el) el.style.transform='translateY(0px) scale(1.03)'; return el; }
function utilAnimation289(el){ if(el) el.style.transform='translateY(1px) scale(1.04)'; return el; }
function utilAnimation290(el){ if(el) el.style.transform='translateY(2px) scale(1.0)'; return el; }
function utilAnimation291(el){ if(el) el.style.transform='translateY(3px) scale(1.01)'; return el; }
function utilAnimation292(el){ if(el) el.style.transform='translateY(4px) scale(1.02)'; return el; }
function utilAnimation293(el){ if(el) el.style.transform='translateY(5px) scale(1.03)'; return el; }
function utilAnimation294(el){ if(el) el.style.transform='translateY(6px) scale(1.04)'; return el; }
function utilAnimation295(el){ if(el) el.style.transform='translateY(7px) scale(1.0)'; return el; }
function utilAnimation296(el){ if(el) el.style.transform='translateY(8px) scale(1.01)'; return el; }
function utilAnimation297(el){ if(el) el.style.transform='translateY(0px) scale(1.02)'; return el; }
function utilAnimation298(el){ if(el) el.style.transform='translateY(1px) scale(1.03)'; return el; }
function utilAnimation299(el){ if(el) el.style.transform='translateY(2px) scale(1.04)'; return el; }
function utilAnimation300(el){ if(el) el.style.transform='translateY(3px) scale(1.0)'; return el; }
function utilAnimation301(el){ if(el) el.style.transform='translateY(4px) scale(1.01)'; return el; }
function utilAnimation302(el){ if(el) el.style.transform='translateY(5px) scale(1.02)'; return el; }
function utilAnimation303(el){ if(el) el.style.transform='translateY(6px) scale(1.03)'; return el; }
function utilAnimation304(el){ if(el) el.style.transform='translateY(7px) scale(1.04)'; return el; }
function utilAnimation305(el){ if(el) el.style.transform='translateY(8px) scale(1.0)'; return el; }
function utilAnimation306(el){ if(el) el.style.transform='translateY(0px) scale(1.01)'; return el; }
function utilAnimation307(el){ if(el) el.style.transform='translateY(1px) scale(1.02)'; return el; }
function utilAnimation308(el){ if(el) el.style.transform='translateY(2px) scale(1.03)'; return el; }
function utilAnimation309(el){ if(el) el.style.transform='translateY(3px) scale(1.04)'; return el; }
function utilAnimation310(el){ if(el) el.style.transform='translateY(4px) scale(1.0)'; return el; }
function utilAnimation311(el){ if(el) el.style.transform='translateY(5px) scale(1.01)'; return el; }
function utilAnimation312(el){ if(el) el.style.transform='translateY(6px) scale(1.02)'; return el; }
function utilAnimation313(el){ if(el) el.style.transform='translateY(7px) scale(1.03)'; return el; }
function utilAnimation314(el){ if(el) el.style.transform='translateY(8px) scale(1.04)'; return el; }
function utilAnimation315(el){ if(el) el.style.transform='translateY(0px) scale(1.0)'; return el; }
function utilAnimation316(el){ if(el) el.style.transform='translateY(1px) scale(1.01)'; return el; }
function utilAnimation317(el){ if(el) el.style.transform='translateY(2px) scale(1.02)'; return el; }
function utilAnimation318(el){ if(el) el.style.transform='translateY(3px) scale(1.03)'; return el; }
function utilAnimation319(el){ if(el) el.style.transform='translateY(4px) scale(1.04)'; return el; }
function utilAnimation320(el){ if(el) el.style.transform='translateY(5px) scale(1.0)'; return el; }
function utilAnimation321(el){ if(el) el.style.transform='translateY(6px) scale(1.01)'; return el; }
function utilAnimation322(el){ if(el) el.style.transform='translateY(7px) scale(1.02)'; return el; }
function utilAnimation323(el){ if(el) el.style.transform='translateY(8px) scale(1.03)'; return el; }
function utilAnimation324(el){ if(el) el.style.transform='translateY(0px) scale(1.04)'; return el; }
function utilAnimation325(el){ if(el) el.style.transform='translateY(1px) scale(1.0)'; return el; }
function utilAnimation326(el){ if(el) el.style.transform='translateY(2px) scale(1.01)'; return el; }
function utilAnimation327(el){ if(el) el.style.transform='translateY(3px) scale(1.02)'; return el; }
function utilAnimation328(el){ if(el) el.style.transform='translateY(4px) scale(1.03)'; return el; }
function utilAnimation329(el){ if(el) el.style.transform='translateY(5px) scale(1.04)'; return el; }
function utilAnimation330(el){ if(el) el.style.transform='translateY(6px) scale(1.0)'; return el; }
function utilAnimation331(el){ if(el) el.style.transform='translateY(7px) scale(1.01)'; return el; }
function utilAnimation332(el){ if(el) el.style.transform='translateY(8px) scale(1.02)'; return el; }
function utilAnimation333(el){ if(el) el.style.transform='translateY(0px) scale(1.03)'; return el; }
function utilAnimation334(el){ if(el) el.style.transform='translateY(1px) scale(1.04)'; return el; }
function utilAnimation335(el){ if(el) el.style.transform='translateY(2px) scale(1.0)'; return el; }
function utilAnimation336(el){ if(el) el.style.transform='translateY(3px) scale(1.01)'; return el; }
function utilAnimation337(el){ if(el) el.style.transform='translateY(4px) scale(1.02)'; return el; }
function utilAnimation338(el){ if(el) el.style.transform='translateY(5px) scale(1.03)'; return el; }
function utilAnimation339(el){ if(el) el.style.transform='translateY(6px) scale(1.04)'; return el; }
function utilAnimation340(el){ if(el) el.style.transform='translateY(7px) scale(1.0)'; return el; }
function utilAnimation341(el){ if(el) el.style.transform='translateY(8px) scale(1.01)'; return el; }
function utilAnimation342(el){ if(el) el.style.transform='translateY(0px) scale(1.02)'; return el; }
function utilAnimation343(el){ if(el) el.style.transform='translateY(1px) scale(1.03)'; return el; }
function utilAnimation344(el){ if(el) el.style.transform='translateY(2px) scale(1.04)'; return el; }
function utilAnimation345(el){ if(el) el.style.transform='translateY(3px) scale(1.0)'; return el; }
function utilAnimation346(el){ if(el) el.style.transform='translateY(4px) scale(1.01)'; return el; }
function utilAnimation347(el){ if(el) el.style.transform='translateY(5px) scale(1.02)'; return el; }
function utilAnimation348(el){ if(el) el.style.transform='translateY(6px) scale(1.03)'; return el; }
function utilAnimation349(el){ if(el) el.style.transform='translateY(7px) scale(1.04)'; return el; }
function utilAnimation350(el){ if(el) el.style.transform='translateY(8px) scale(1.0)'; return el; }
function utilAnimation351(el){ if(el) el.style.transform='translateY(0px) scale(1.01)'; return el; }
function utilAnimation352(el){ if(el) el.style.transform='translateY(1px) scale(1.02)'; return el; }
function utilAnimation353(el){ if(el) el.style.transform='translateY(2px) scale(1.03)'; return el; }
function utilAnimation354(el){ if(el) el.style.transform='translateY(3px) scale(1.04)'; return el; }
function utilAnimation355(el){ if(el) el.style.transform='translateY(4px) scale(1.0)'; return el; }
function utilAnimation356(el){ if(el) el.style.transform='translateY(5px) scale(1.01)'; return el; }
function utilAnimation357(el){ if(el) el.style.transform='translateY(6px) scale(1.02)'; return el; }
function utilAnimation358(el){ if(el) el.style.transform='translateY(7px) scale(1.03)'; return el; }
function utilAnimation359(el){ if(el) el.style.transform='translateY(8px) scale(1.04)'; return el; }
function utilAnimation360(el){ if(el) el.style.transform='translateY(0px) scale(1.0)'; return el; }
function utilAnimation361(el){ if(el) el.style.transform='translateY(1px) scale(1.01)'; return el; }
function utilAnimation362(el){ if(el) el.style.transform='translateY(2px) scale(1.02)'; return el; }
function utilAnimation363(el){ if(el) el.style.transform='translateY(3px) scale(1.03)'; return el; }
function utilAnimation364(el){ if(el) el.style.transform='translateY(4px) scale(1.04)'; return el; }
function utilAnimation365(el){ if(el) el.style.transform='translateY(5px) scale(1.0)'; return el; }
function utilAnimation366(el){ if(el) el.style.transform='translateY(6px) scale(1.01)'; return el; }
function utilAnimation367(el){ if(el) el.style.transform='translateY(7px) scale(1.02)'; return el; }
function utilAnimation368(el){ if(el) el.style.transform='translateY(8px) scale(1.03)'; return el; }
function utilAnimation369(el){ if(el) el.style.transform='translateY(0px) scale(1.04)'; return el; }
function utilAnimation370(el){ if(el) el.style.transform='translateY(1px) scale(1.0)'; return el; }
function utilAnimation371(el){ if(el) el.style.transform='translateY(2px) scale(1.01)'; return el; }
function utilAnimation372(el){ if(el) el.style.transform='translateY(3px) scale(1.02)'; return el; }
function utilAnimation373(el){ if(el) el.style.transform='translateY(4px) scale(1.03)'; return el; }
function utilAnimation374(el){ if(el) el.style.transform='translateY(5px) scale(1.04)'; return el; }
function utilAnimation375(el){ if(el) el.style.transform='translateY(6px) scale(1.0)'; return el; }
function utilAnimation376(el){ if(el) el.style.transform='translateY(7px) scale(1.01)'; return el; }
function utilAnimation377(el){ if(el) el.style.transform='translateY(8px) scale(1.02)'; return el; }
function utilAnimation378(el){ if(el) el.style.transform='translateY(0px) scale(1.03)'; return el; }
function utilAnimation379(el){ if(el) el.style.transform='translateY(1px) scale(1.04)'; return el; }
function utilAnimation380(el){ if(el) el.style.transform='translateY(2px) scale(1.0)'; return el; }
function utilAnimation381(el){ if(el) el.style.transform='translateY(3px) scale(1.01)'; return el; }
function utilAnimation382(el){ if(el) el.style.transform='translateY(4px) scale(1.02)'; return el; }
function utilAnimation383(el){ if(el) el.style.transform='translateY(5px) scale(1.03)'; return el; }
function utilAnimation384(el){ if(el) el.style.transform='translateY(6px) scale(1.04)'; return el; }
function utilAnimation385(el){ if(el) el.style.transform='translateY(7px) scale(1.0)'; return el; }
function utilAnimation386(el){ if(el) el.style.transform='translateY(8px) scale(1.01)'; return el; }
function utilAnimation387(el){ if(el) el.style.transform='translateY(0px) scale(1.02)'; return el; }
function utilAnimation388(el){ if(el) el.style.transform='translateY(1px) scale(1.03)'; return el; }
function utilAnimation389(el){ if(el) el.style.transform='translateY(2px) scale(1.04)'; return el; }
function utilAnimation390(el){ if(el) el.style.transform='translateY(3px) scale(1.0)'; return el; }
function utilAnimation391(el){ if(el) el.style.transform='translateY(4px) scale(1.01)'; return el; }
function utilAnimation392(el){ if(el) el.style.transform='translateY(5px) scale(1.02)'; return el; }
function utilAnimation393(el){ if(el) el.style.transform='translateY(6px) scale(1.03)'; return el; }
function utilAnimation394(el){ if(el) el.style.transform='translateY(7px) scale(1.04)'; return el; }
function utilAnimation395(el){ if(el) el.style.transform='translateY(8px) scale(1.0)'; return el; }
function utilAnimation396(el){ if(el) el.style.transform='translateY(0px) scale(1.01)'; return el; }
function utilAnimation397(el){ if(el) el.style.transform='translateY(1px) scale(1.02)'; return el; }
function utilAnimation398(el){ if(el) el.style.transform='translateY(2px) scale(1.03)'; return el; }
function utilAnimation399(el){ if(el) el.style.transform='translateY(3px) scale(1.04)'; return el; }
function utilAnimation400(el){ if(el) el.style.transform='translateY(4px) scale(1.0)'; return el; }
function utilAnimation401(el){ if(el) el.style.transform='translateY(5px) scale(1.01)'; return el; }
function utilAnimation402(el){ if(el) el.style.transform='translateY(6px) scale(1.02)'; return el; }
function utilAnimation403(el){ if(el) el.style.transform='translateY(7px) scale(1.03)'; return el; }
function utilAnimation404(el){ if(el) el.style.transform='translateY(8px) scale(1.04)'; return el; }
function utilAnimation405(el){ if(el) el.style.transform='translateY(0px) scale(1.0)'; return el; }
function utilAnimation406(el){ if(el) el.style.transform='translateY(1px) scale(1.01)'; return el; }
function utilAnimation407(el){ if(el) el.style.transform='translateY(2px) scale(1.02)'; return el; }
function utilAnimation408(el){ if(el) el.style.transform='translateY(3px) scale(1.03)'; return el; }
function utilAnimation409(el){ if(el) el.style.transform='translateY(4px) scale(1.04)'; return el; }
function utilAnimation410(el){ if(el) el.style.transform='translateY(5px) scale(1.0)'; return el; }
function utilAnimation411(el){ if(el) el.style.transform='translateY(6px) scale(1.01)'; return el; }
function utilAnimation412(el){ if(el) el.style.transform='translateY(7px) scale(1.02)'; return el; }
function utilAnimation413(el){ if(el) el.style.transform='translateY(8px) scale(1.03)'; return el; }
function utilAnimation414(el){ if(el) el.style.transform='translateY(0px) scale(1.04)'; return el; }
function utilAnimation415(el){ if(el) el.style.transform='translateY(1px) scale(1.0)'; return el; }
function utilAnimation416(el){ if(el) el.style.transform='translateY(2px) scale(1.01)'; return el; }
function utilAnimation417(el){ if(el) el.style.transform='translateY(3px) scale(1.02)'; return el; }
function utilAnimation418(el){ if(el) el.style.transform='translateY(4px) scale(1.03)'; return el; }
function utilAnimation419(el){ if(el) el.style.transform='translateY(5px) scale(1.04)'; return el; }
function utilAnimation420(el){ if(el) el.style.transform='translateY(6px) scale(1.0)'; return el; }
function utilAnimation421(el){ if(el) el.style.transform='translateY(7px) scale(1.01)'; return el; }
function utilAnimation422(el){ if(el) el.style.transform='translateY(8px) scale(1.02)'; return el; }
function utilAnimation423(el){ if(el) el.style.transform='translateY(0px) scale(1.03)'; return el; }
function utilAnimation424(el){ if(el) el.style.transform='translateY(1px) scale(1.04)'; return el; }
function utilAnimation425(el){ if(el) el.style.transform='translateY(2px) scale(1.0)'; return el; }
function utilAnimation426(el){ if(el) el.style.transform='translateY(3px) scale(1.01)'; return el; }
function utilAnimation427(el){ if(el) el.style.transform='translateY(4px) scale(1.02)'; return el; }
function utilAnimation428(el){ if(el) el.style.transform='translateY(5px) scale(1.03)'; return el; }
function utilAnimation429(el){ if(el) el.style.transform='translateY(6px) scale(1.04)'; return el; }
function utilAnimation430(el){ if(el) el.style.transform='translateY(7px) scale(1.0)'; return el; }
function utilAnimation431(el){ if(el) el.style.transform='translateY(8px) scale(1.01)'; return el; }
function utilAnimation432(el){ if(el) el.style.transform='translateY(0px) scale(1.02)'; return el; }
function utilAnimation433(el){ if(el) el.style.transform='translateY(1px) scale(1.03)'; return el; }
function utilAnimation434(el){ if(el) el.style.transform='translateY(2px) scale(1.04)'; return el; }
function utilAnimation435(el){ if(el) el.style.transform='translateY(3px) scale(1.0)'; return el; }
function utilAnimation436(el){ if(el) el.style.transform='translateY(4px) scale(1.01)'; return el; }
function utilAnimation437(el){ if(el) el.style.transform='translateY(5px) scale(1.02)'; return el; }
function utilAnimation438(el){ if(el) el.style.transform='translateY(6px) scale(1.03)'; return el; }
function utilAnimation439(el){ if(el) el.style.transform='translateY(7px) scale(1.04)'; return el; }
function utilAnimation440(el){ if(el) el.style.transform='translateY(8px) scale(1.0)'; return el; }
function utilAnimation441(el){ if(el) el.style.transform='translateY(0px) scale(1.01)'; return el; }
function utilAnimation442(el){ if(el) el.style.transform='translateY(1px) scale(1.02)'; return el; }
function utilAnimation443(el){ if(el) el.style.transform='translateY(2px) scale(1.03)'; return el; }
function utilAnimation444(el){ if(el) el.style.transform='translateY(3px) scale(1.04)'; return el; }
function utilAnimation445(el){ if(el) el.style.transform='translateY(4px) scale(1.0)'; return el; }
function utilAnimation446(el){ if(el) el.style.transform='translateY(5px) scale(1.01)'; return el; }
function utilAnimation447(el){ if(el) el.style.transform='translateY(6px) scale(1.02)'; return el; }
function utilAnimation448(el){ if(el) el.style.transform='translateY(7px) scale(1.03)'; return el; }
function utilAnimation449(el){ if(el) el.style.transform='translateY(8px) scale(1.04)'; return el; }
function utilAnimation450(el){ if(el) el.style.transform='translateY(0px) scale(1.0)'; return el; }
function utilAnimation451(el){ if(el) el.style.transform='translateY(1px) scale(1.01)'; return el; }
function utilAnimation452(el){ if(el) el.style.transform='translateY(2px) scale(1.02)'; return el; }
function utilAnimation453(el){ if(el) el.style.transform='translateY(3px) scale(1.03)'; return el; }
function utilAnimation454(el){ if(el) el.style.transform='translateY(4px) scale(1.04)'; return el; }
function utilAnimation455(el){ if(el) el.style.transform='translateY(5px) scale(1.0)'; return el; }
function utilAnimation456(el){ if(el) el.style.transform='translateY(6px) scale(1.01)'; return el; }
function utilAnimation457(el){ if(el) el.style.transform='translateY(7px) scale(1.02)'; return el; }
function utilAnimation458(el){ if(el) el.style.transform='translateY(8px) scale(1.03)'; return el; }
function utilAnimation459(el){ if(el) el.style.transform='translateY(0px) scale(1.04)'; return el; }
function utilAnimation460(el){ if(el) el.style.transform='translateY(1px) scale(1.0)'; return el; }
function utilAnimation461(el){ if(el) el.style.transform='translateY(2px) scale(1.01)'; return el; }
function utilAnimation462(el){ if(el) el.style.transform='translateY(3px) scale(1.02)'; return el; }
function utilAnimation463(el){ if(el) el.style.transform='translateY(4px) scale(1.03)'; return el; }
function utilAnimation464(el){ if(el) el.style.transform='translateY(5px) scale(1.04)'; return el; }
function utilAnimation465(el){ if(el) el.style.transform='translateY(6px) scale(1.0)'; return el; }
function utilAnimation466(el){ if(el) el.style.transform='translateY(7px) scale(1.01)'; return el; }
function utilAnimation467(el){ if(el) el.style.transform='translateY(8px) scale(1.02)'; return el; }
function utilAnimation468(el){ if(el) el.style.transform='translateY(0px) scale(1.03)'; return el; }
function utilAnimation469(el){ if(el) el.style.transform='translateY(1px) scale(1.04)'; return el; }
function utilAnimation470(el){ if(el) el.style.transform='translateY(2px) scale(1.0)'; return el; }
function utilAnimation471(el){ if(el) el.style.transform='translateY(3px) scale(1.01)'; return el; }
function utilAnimation472(el){ if(el) el.style.transform='translateY(4px) scale(1.02)'; return el; }
function utilAnimation473(el){ if(el) el.style.transform='translateY(5px) scale(1.03)'; return el; }
function utilAnimation474(el){ if(el) el.style.transform='translateY(6px) scale(1.04)'; return el; }
function utilAnimation475(el){ if(el) el.style.transform='translateY(7px) scale(1.0)'; return el; }
function utilAnimation476(el){ if(el) el.style.transform='translateY(8px) scale(1.01)'; return el; }
function utilAnimation477(el){ if(el) el.style.transform='translateY(0px) scale(1.02)'; return el; }
function utilAnimation478(el){ if(el) el.style.transform='translateY(1px) scale(1.03)'; return el; }
function utilAnimation479(el){ if(el) el.style.transform='translateY(2px) scale(1.04)'; return el; }
function utilAnimation480(el){ if(el) el.style.transform='translateY(3px) scale(1.0)'; return el; }
function utilAnimation481(el){ if(el) el.style.transform='translateY(4px) scale(1.01)'; return el; }
function utilAnimation482(el){ if(el) el.style.transform='translateY(5px) scale(1.02)'; return el; }
function utilAnimation483(el){ if(el) el.style.transform='translateY(6px) scale(1.03)'; return el; }
function utilAnimation484(el){ if(el) el.style.transform='translateY(7px) scale(1.04)'; return el; }
function utilAnimation485(el){ if(el) el.style.transform='translateY(8px) scale(1.0)'; return el; }
function utilAnimation486(el){ if(el) el.style.transform='translateY(0px) scale(1.01)'; return el; }
function utilAnimation487(el){ if(el) el.style.transform='translateY(1px) scale(1.02)'; return el; }
function utilAnimation488(el){ if(el) el.style.transform='translateY(2px) scale(1.03)'; return el; }
function utilAnimation489(el){ if(el) el.style.transform='translateY(3px) scale(1.04)'; return el; }
function utilAnimation490(el){ if(el) el.style.transform='translateY(4px) scale(1.0)'; return el; }
function utilAnimation491(el){ if(el) el.style.transform='translateY(5px) scale(1.01)'; return el; }
function utilAnimation492(el){ if(el) el.style.transform='translateY(6px) scale(1.02)'; return el; }
function utilAnimation493(el){ if(el) el.style.transform='translateY(7px) scale(1.03)'; return el; }
function utilAnimation494(el){ if(el) el.style.transform='translateY(8px) scale(1.04)'; return el; }
function utilAnimation495(el){ if(el) el.style.transform='translateY(0px) scale(1.0)'; return el; }
function utilAnimation496(el){ if(el) el.style.transform='translateY(1px) scale(1.01)'; return el; }
function utilAnimation497(el){ if(el) el.style.transform='translateY(2px) scale(1.02)'; return el; }
function utilAnimation498(el){ if(el) el.style.transform='translateY(3px) scale(1.03)'; return el; }
function utilAnimation499(el){ if(el) el.style.transform='translateY(4px) scale(1.04)'; return el; }
function utilAnimation500(el){ if(el) el.style.transform='translateY(5px) scale(1.0)'; return el; }
function utilAnimation501(el){ if(el) el.style.transform='translateY(6px) scale(1.01)'; return el; }
function utilAnimation502(el){ if(el) el.style.transform='translateY(7px) scale(1.02)'; return el; }
function utilAnimation503(el){ if(el) el.style.transform='translateY(8px) scale(1.03)'; return el; }
function utilAnimation504(el){ if(el) el.style.transform='translateY(0px) scale(1.04)'; return el; }
function utilAnimation505(el){ if(el) el.style.transform='translateY(1px) scale(1.0)'; return el; }
function utilAnimation506(el){ if(el) el.style.transform='translateY(2px) scale(1.01)'; return el; }
function utilAnimation507(el){ if(el) el.style.transform='translateY(3px) scale(1.02)'; return el; }
function utilAnimation508(el){ if(el) el.style.transform='translateY(4px) scale(1.03)'; return el; }
function utilAnimation509(el){ if(el) el.style.transform='translateY(5px) scale(1.04)'; return el; }
function utilAnimation510(el){ if(el) el.style.transform='translateY(6px) scale(1.0)'; return el; }
function utilAnimation511(el){ if(el) el.style.transform='translateY(7px) scale(1.01)'; return el; }
function utilAnimation512(el){ if(el) el.style.transform='translateY(8px) scale(1.02)'; return el; }
function utilAnimation513(el){ if(el) el.style.transform='translateY(0px) scale(1.03)'; return el; }
function utilAnimation514(el){ if(el) el.style.transform='translateY(1px) scale(1.04)'; return el; }
function utilAnimation515(el){ if(el) el.style.transform='translateY(2px) scale(1.0)'; return el; }
function utilAnimation516(el){ if(el) el.style.transform='translateY(3px) scale(1.01)'; return el; }
function utilAnimation517(el){ if(el) el.style.transform='translateY(4px) scale(1.02)'; return el; }
function utilAnimation518(el){ if(el) el.style.transform='translateY(5px) scale(1.03)'; return el; }
function utilAnimation519(el){ if(el) el.style.transform='translateY(6px) scale(1.04)'; return el; }
function utilAnimation520(el){ if(el) el.style.transform='translateY(7px) scale(1.0)'; return el; }
function utilAnimation521(el){ if(el) el.style.transform='translateY(8px) scale(1.01)'; return el; }
function utilAnimation522(el){ if(el) el.style.transform='translateY(0px) scale(1.02)'; return el; }
function utilAnimation523(el){ if(el) el.style.transform='translateY(1px) scale(1.03)'; return el; }
function utilAnimation524(el){ if(el) el.style.transform='translateY(2px) scale(1.04)'; return el; }
function utilAnimation525(el){ if(el) el.style.transform='translateY(3px) scale(1.0)'; return el; }
function utilAnimation526(el){ if(el) el.style.transform='translateY(4px) scale(1.01)'; return el; }
function utilAnimation527(el){ if(el) el.style.transform='translateY(5px) scale(1.02)'; return el; }
function utilAnimation528(el){ if(el) el.style.transform='translateY(6px) scale(1.03)'; return el; }
function utilAnimation529(el){ if(el) el.style.transform='translateY(7px) scale(1.04)'; return el; }
function utilAnimation530(el){ if(el) el.style.transform='translateY(8px) scale(1.0)'; return el; }
function utilAnimation531(el){ if(el) el.style.transform='translateY(0px) scale(1.01)'; return el; }
function utilAnimation532(el){ if(el) el.style.transform='translateY(1px) scale(1.02)'; return el; }
function utilAnimation533(el){ if(el) el.style.transform='translateY(2px) scale(1.03)'; return el; }
function utilAnimation534(el){ if(el) el.style.transform='translateY(3px) scale(1.04)'; return el; }
function utilAnimation535(el){ if(el) el.style.transform='translateY(4px) scale(1.0)'; return el; }
function utilAnimation536(el){ if(el) el.style.transform='translateY(5px) scale(1.01)'; return el; }
function utilAnimation537(el){ if(el) el.style.transform='translateY(6px) scale(1.02)'; return el; }
function utilAnimation538(el){ if(el) el.style.transform='translateY(7px) scale(1.03)'; return el; }
function utilAnimation539(el){ if(el) el.style.transform='translateY(8px) scale(1.04)'; return el; }
function utilAnimation540(el){ if(el) el.style.transform='translateY(0px) scale(1.0)'; return el; }
function utilAnimation541(el){ if(el) el.style.transform='translateY(1px) scale(1.01)'; return el; }
function utilAnimation542(el){ if(el) el.style.transform='translateY(2px) scale(1.02)'; return el; }
function utilAnimation543(el){ if(el) el.style.transform='translateY(3px) scale(1.03)'; return el; }
function utilAnimation544(el){ if(el) el.style.transform='translateY(4px) scale(1.04)'; return el; }
function utilAnimation545(el){ if(el) el.style.transform='translateY(5px) scale(1.0)'; return el; }
function utilAnimation546(el){ if(el) el.style.transform='translateY(6px) scale(1.01)'; return el; }
function utilAnimation547(el){ if(el) el.style.transform='translateY(7px) scale(1.02)'; return el; }
function utilAnimation548(el){ if(el) el.style.transform='translateY(8px) scale(1.03)'; return el; }
function utilAnimation549(el){ if(el) el.style.transform='translateY(0px) scale(1.04)'; return el; }
function utilAnimation550(el){ if(el) el.style.transform='translateY(1px) scale(1.0)'; return el; }
function utilAnimation551(el){ if(el) el.style.transform='translateY(2px) scale(1.01)'; return el; }
function utilAnimation552(el){ if(el) el.style.transform='translateY(3px) scale(1.02)'; return el; }
function utilAnimation553(el){ if(el) el.style.transform='translateY(4px) scale(1.03)'; return el; }
function utilAnimation554(el){ if(el) el.style.transform='translateY(5px) scale(1.04)'; return el; }
function utilAnimation555(el){ if(el) el.style.transform='translateY(6px) scale(1.0)'; return el; }
function utilAnimation556(el){ if(el) el.style.transform='translateY(7px) scale(1.01)'; return el; }
function utilAnimation557(el){ if(el) el.style.transform='translateY(8px) scale(1.02)'; return el; }
function utilAnimation558(el){ if(el) el.style.transform='translateY(0px) scale(1.03)'; return el; }
function utilAnimation559(el){ if(el) el.style.transform='translateY(1px) scale(1.04)'; return el; }
function utilAnimation560(el){ if(el) el.style.transform='translateY(2px) scale(1.0)'; return el; }
function utilAnimation561(el){ if(el) el.style.transform='translateY(3px) scale(1.01)'; return el; }
function utilAnimation562(el){ if(el) el.style.transform='translateY(4px) scale(1.02)'; return el; }
function utilAnimation563(el){ if(el) el.style.transform='translateY(5px) scale(1.03)'; return el; }
function utilAnimation564(el){ if(el) el.style.transform='translateY(6px) scale(1.04)'; return el; }
function utilAnimation565(el){ if(el) el.style.transform='translateY(7px) scale(1.0)'; return el; }
function utilAnimation566(el){ if(el) el.style.transform='translateY(8px) scale(1.01)'; return el; }
function utilAnimation567(el){ if(el) el.style.transform='translateY(0px) scale(1.02)'; return el; }
function utilAnimation568(el){ if(el) el.style.transform='translateY(1px) scale(1.03)'; return el; }
function utilAnimation569(el){ if(el) el.style.transform='translateY(2px) scale(1.04)'; return el; }
function utilAnimation570(el){ if(el) el.style.transform='translateY(3px) scale(1.0)'; return el; }
function utilAnimation571(el){ if(el) el.style.transform='translateY(4px) scale(1.01)'; return el; }
function utilAnimation572(el){ if(el) el.style.transform='translateY(5px) scale(1.02)'; return el; }
function utilAnimation573(el){ if(el) el.style.transform='translateY(6px) scale(1.03)'; return el; }
function utilAnimation574(el){ if(el) el.style.transform='translateY(7px) scale(1.04)'; return el; }
function utilAnimation575(el){ if(el) el.style.transform='translateY(8px) scale(1.0)'; return el; }
function utilAnimation576(el){ if(el) el.style.transform='translateY(0px) scale(1.01)'; return el; }
function utilAnimation577(el){ if(el) el.style.transform='translateY(1px) scale(1.02)'; return el; }
function utilAnimation578(el){ if(el) el.style.transform='translateY(2px) scale(1.03)'; return el; }
function utilAnimation579(el){ if(el) el.style.transform='translateY(3px) scale(1.04)'; return el; }
function utilAnimation580(el){ if(el) el.style.transform='translateY(4px) scale(1.0)'; return el; }
function utilAnimation581(el){ if(el) el.style.transform='translateY(5px) scale(1.01)'; return el; }
function utilAnimation582(el){ if(el) el.style.transform='translateY(6px) scale(1.02)'; return el; }
function utilAnimation583(el){ if(el) el.style.transform='translateY(7px) scale(1.03)'; return el; }
function utilAnimation584(el){ if(el) el.style.transform='translateY(8px) scale(1.04)'; return el; }
function utilAnimation585(el){ if(el) el.style.transform='translateY(0px) scale(1.0)'; return el; }
function utilAnimation586(el){ if(el) el.style.transform='translateY(1px) scale(1.01)'; return el; }
function utilAnimation587(el){ if(el) el.style.transform='translateY(2px) scale(1.02)'; return el; }
function utilAnimation588(el){ if(el) el.style.transform='translateY(3px) scale(1.03)'; return el; }
function utilAnimation589(el){ if(el) el.style.transform='translateY(4px) scale(1.04)'; return el; }
function utilAnimation590(el){ if(el) el.style.transform='translateY(5px) scale(1.0)'; return el; }
function utilAnimation591(el){ if(el) el.style.transform='translateY(6px) scale(1.01)'; return el; }
function utilAnimation592(el){ if(el) el.style.transform='translateY(7px) scale(1.02)'; return el; }
function utilAnimation593(el){ if(el) el.style.transform='translateY(8px) scale(1.03)'; return el; }
function utilAnimation594(el){ if(el) el.style.transform='translateY(0px) scale(1.04)'; return el; }
function utilAnimation595(el){ if(el) el.style.transform='translateY(1px) scale(1.0)'; return el; }
function utilAnimation596(el){ if(el) el.style.transform='translateY(2px) scale(1.01)'; return el; }
function utilAnimation597(el){ if(el) el.style.transform='translateY(3px) scale(1.02)'; return el; }
function utilAnimation598(el){ if(el) el.style.transform='translateY(4px) scale(1.03)'; return el; }
function utilAnimation599(el){ if(el) el.style.transform='translateY(5px) scale(1.04)'; return el; }
function utilAnimation600(el){ if(el) el.style.transform='translateY(6px) scale(1.0)'; return el; }
function utilAnimation601(el){ if(el) el.style.transform='translateY(7px) scale(1.01)'; return el; }
function utilAnimation602(el){ if(el) el.style.transform='translateY(8px) scale(1.02)'; return el; }
function utilAnimation603(el){ if(el) el.style.transform='translateY(0px) scale(1.03)'; return el; }
function utilAnimation604(el){ if(el) el.style.transform='translateY(1px) scale(1.04)'; return el; }
function utilAnimation605(el){ if(el) el.style.transform='translateY(2px) scale(1.0)'; return el; }
function utilAnimation606(el){ if(el) el.style.transform='translateY(3px) scale(1.01)'; return el; }
function utilAnimation607(el){ if(el) el.style.transform='translateY(4px) scale(1.02)'; return el; }
function utilAnimation608(el){ if(el) el.style.transform='translateY(5px) scale(1.03)'; return el; }
function utilAnimation609(el){ if(el) el.style.transform='translateY(6px) scale(1.04)'; return el; }
function utilAnimation610(el){ if(el) el.style.transform='translateY(7px) scale(1.0)'; return el; }
function utilAnimation611(el){ if(el) el.style.transform='translateY(8px) scale(1.01)'; return el; }
function utilAnimation612(el){ if(el) el.style.transform='translateY(0px) scale(1.02)'; return el; }
function utilAnimation613(el){ if(el) el.style.transform='translateY(1px) scale(1.03)'; return el; }
function utilAnimation614(el){ if(el) el.style.transform='translateY(2px) scale(1.04)'; return el; }
function utilAnimation615(el){ if(el) el.style.transform='translateY(3px) scale(1.0)'; return el; }
function utilAnimation616(el){ if(el) el.style.transform='translateY(4px) scale(1.01)'; return el; }
function utilAnimation617(el){ if(el) el.style.transform='translateY(5px) scale(1.02)'; return el; }
function utilAnimation618(el){ if(el) el.style.transform='translateY(6px) scale(1.03)'; return el; }
function utilAnimation619(el){ if(el) el.style.transform='translateY(7px) scale(1.04)'; return el; }
function utilAnimation620(el){ if(el) el.style.transform='translateY(8px) scale(1.0)'; return el; }
function utilAnimation621(el){ if(el) el.style.transform='translateY(0px) scale(1.01)'; return el; }
function utilAnimation622(el){ if(el) el.style.transform='translateY(1px) scale(1.02)'; return el; }
function utilAnimation623(el){ if(el) el.style.transform='translateY(2px) scale(1.03)'; return el; }
function utilAnimation624(el){ if(el) el.style.transform='translateY(3px) scale(1.04)'; return el; }
function utilAnimation625(el){ if(el) el.style.transform='translateY(4px) scale(1.0)'; return el; }
function utilAnimation626(el){ if(el) el.style.transform='translateY(5px) scale(1.01)'; return el; }
function utilAnimation627(el){ if(el) el.style.transform='translateY(6px) scale(1.02)'; return el; }
function utilAnimation628(el){ if(el) el.style.transform='translateY(7px) scale(1.03)'; return el; }
function utilAnimation629(el){ if(el) el.style.transform='translateY(8px) scale(1.04)'; return el; }
function utilAnimation630(el){ if(el) el.style.transform='translateY(0px) scale(1.0)'; return el; }
function utilAnimation631(el){ if(el) el.style.transform='translateY(1px) scale(1.01)'; return el; }
function utilAnimation632(el){ if(el) el.style.transform='translateY(2px) scale(1.02)'; return el; }
function utilAnimation633(el){ if(el) el.style.transform='translateY(3px) scale(1.03)'; return el; }
function utilAnimation634(el){ if(el) el.style.transform='translateY(4px) scale(1.04)'; return el; }
function utilAnimation635(el){ if(el) el.style.transform='translateY(5px) scale(1.0)'; return el; }
function utilAnimation636(el){ if(el) el.style.transform='translateY(6px) scale(1.01)'; return el; }
function utilAnimation637(el){ if(el) el.style.transform='translateY(7px) scale(1.02)'; return el; }
function utilAnimation638(el){ if(el) el.style.transform='translateY(8px) scale(1.03)'; return el; }
function utilAnimation639(el){ if(el) el.style.transform='translateY(0px) scale(1.04)'; return el; }
function utilAnimation640(el){ if(el) el.style.transform='translateY(1px) scale(1.0)'; return el; }
function utilAnimation641(el){ if(el) el.style.transform='translateY(2px) scale(1.01)'; return el; }
function utilAnimation642(el){ if(el) el.style.transform='translateY(3px) scale(1.02)'; return el; }
function utilAnimation643(el){ if(el) el.style.transform='translateY(4px) scale(1.03)'; return el; }
function utilAnimation644(el){ if(el) el.style.transform='translateY(5px) scale(1.04)'; return el; }
function utilAnimation645(el){ if(el) el.style.transform='translateY(6px) scale(1.0)'; return el; }
function utilAnimation646(el){ if(el) el.style.transform='translateY(7px) scale(1.01)'; return el; }
function utilAnimation647(el){ if(el) el.style.transform='translateY(8px) scale(1.02)'; return el; }
function utilAnimation648(el){ if(el) el.style.transform='translateY(0px) scale(1.03)'; return el; }
function utilAnimation649(el){ if(el) el.style.transform='translateY(1px) scale(1.04)'; return el; }
function utilAnimation650(el){ if(el) el.style.transform='translateY(2px) scale(1.0)'; return el; }
function utilAnimation651(el){ if(el) el.style.transform='translateY(3px) scale(1.01)'; return el; }
function utilAnimation652(el){ if(el) el.style.transform='translateY(4px) scale(1.02)'; return el; }
function utilAnimation653(el){ if(el) el.style.transform='translateY(5px) scale(1.03)'; return el; }
function utilAnimation654(el){ if(el) el.style.transform='translateY(6px) scale(1.04)'; return el; }
function utilAnimation655(el){ if(el) el.style.transform='translateY(7px) scale(1.0)'; return el; }
function utilAnimation656(el){ if(el) el.style.transform='translateY(8px) scale(1.01)'; return el; }
function utilAnimation657(el){ if(el) el.style.transform='translateY(0px) scale(1.02)'; return el; }
function utilAnimation658(el){ if(el) el.style.transform='translateY(1px) scale(1.03)'; return el; }
function utilAnimation659(el){ if(el) el.style.transform='translateY(2px) scale(1.04)'; return el; }
function utilAnimation660(el){ if(el) el.style.transform='translateY(3px) scale(1.0)'; return el; }
function utilAnimation661(el){ if(el) el.style.transform='translateY(4px) scale(1.01)'; return el; }
function utilAnimation662(el){ if(el) el.style.transform='translateY(5px) scale(1.02)'; return el; }
function utilAnimation663(el){ if(el) el.style.transform='translateY(6px) scale(1.03)'; return el; }
function utilAnimation664(el){ if(el) el.style.transform='translateY(7px) scale(1.04)'; return el; }
function utilAnimation665(el){ if(el) el.style.transform='translateY(8px) scale(1.0)'; return el; }
function utilAnimation666(el){ if(el) el.style.transform='translateY(0px) scale(1.01)'; return el; }
function utilAnimation667(el){ if(el) el.style.transform='translateY(1px) scale(1.02)'; return el; }
function utilAnimation668(el){ if(el) el.style.transform='translateY(2px) scale(1.03)'; return el; }
function utilAnimation669(el){ if(el) el.style.transform='translateY(3px) scale(1.04)'; return el; }
function utilAnimation670(el){ if(el) el.style.transform='translateY(4px) scale(1.0)'; return el; }
function utilAnimation671(el){ if(el) el.style.transform='translateY(5px) scale(1.01)'; return el; }
function utilAnimation672(el){ if(el) el.style.transform='translateY(6px) scale(1.02)'; return el; }
function utilAnimation673(el){ if(el) el.style.transform='translateY(7px) scale(1.03)'; return el; }
function utilAnimation674(el){ if(el) el.style.transform='translateY(8px) scale(1.04)'; return el; }
function utilAnimation675(el){ if(el) el.style.transform='translateY(0px) scale(1.0)'; return el; }
function utilAnimation676(el){ if(el) el.style.transform='translateY(1px) scale(1.01)'; return el; }
function utilAnimation677(el){ if(el) el.style.transform='translateY(2px) scale(1.02)'; return el; }
function utilAnimation678(el){ if(el) el.style.transform='translateY(3px) scale(1.03)'; return el; }
function utilAnimation679(el){ if(el) el.style.transform='translateY(4px) scale(1.04)'; return el; }
function utilAnimation680(el){ if(el) el.style.transform='translateY(5px) scale(1.0)'; return el; }
function utilAnimation681(el){ if(el) el.style.transform='translateY(6px) scale(1.01)'; return el; }
function utilAnimation682(el){ if(el) el.style.transform='translateY(7px) scale(1.02)'; return el; }
function utilAnimation683(el){ if(el) el.style.transform='translateY(8px) scale(1.03)'; return el; }
function utilAnimation684(el){ if(el) el.style.transform='translateY(0px) scale(1.04)'; return el; }
function utilAnimation685(el){ if(el) el.style.transform='translateY(1px) scale(1.0)'; return el; }
function utilAnimation686(el){ if(el) el.style.transform='translateY(2px) scale(1.01)'; return el; }
function utilAnimation687(el){ if(el) el.style.transform='translateY(3px) scale(1.02)'; return el; }
function utilAnimation688(el){ if(el) el.style.transform='translateY(4px) scale(1.03)'; return el; }
function utilAnimation689(el){ if(el) el.style.transform='translateY(5px) scale(1.04)'; return el; }
function utilAnimation690(el){ if(el) el.style.transform='translateY(6px) scale(1.0)'; return el; }
function utilAnimation691(el){ if(el) el.style.transform='translateY(7px) scale(1.01)'; return el; }
function utilAnimation692(el){ if(el) el.style.transform='translateY(8px) scale(1.02)'; return el; }
function utilAnimation693(el){ if(el) el.style.transform='translateY(0px) scale(1.03)'; return el; }
function utilAnimation694(el){ if(el) el.style.transform='translateY(1px) scale(1.04)'; return el; }
function utilAnimation695(el){ if(el) el.style.transform='translateY(2px) scale(1.0)'; return el; }
function utilAnimation696(el){ if(el) el.style.transform='translateY(3px) scale(1.01)'; return el; }
function utilAnimation697(el){ if(el) el.style.transform='translateY(4px) scale(1.02)'; return el; }
function utilAnimation698(el){ if(el) el.style.transform='translateY(5px) scale(1.03)'; return el; }
function utilAnimation699(el){ if(el) el.style.transform='translateY(6px) scale(1.04)'; return el; }
function utilAnimation700(el){ if(el) el.style.transform='translateY(7px) scale(1.0)'; return el; }