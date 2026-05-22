const $ = (id) => document.getElementById(id);
const money = (n) => Number(n || 0).toLocaleString("ru-RU") + " so‘m";

async function loadStats(){
  const s = await (await fetch('/api/admin/stats')).json();
  $('content').innerHTML = `
    <div class="cards">
      <div class="card"><h3>Users</h3><h1>${s.users}</h1></div>
      <div class="card"><h3>Mahsulotlar</h3><h1>${s.products}</h1></div>
      <div class="card"><h3>Buyurtmalar</h3><h1>${s.orders}</h1></div>
      <div class="card"><h3>Aylanma</h3><h1>${money(s.total)}</h1></div>
    </div>`;
}

async function loadOrders(){
  const list = await (await fetch('/api/admin/orders')).json();
  $('content').innerHTML = `
    <table>
      <tr><th>ID</th><th>Tel</th><th>Manzil</th><th>Jami</th><th>Status</th><th>Action</th></tr>
      ${list.map(o => `
        <tr>
          <td>#${o.id}</td>
          <td>${o.phone}</td>
          <td>${o.address}</td>
          <td>${money(o.total)}</td>
          <td>${o.status}</td>
          <td>
            <button class="ok" onclick="setStatus(${o.id}, 'accepted')">OK</button>
            <button class="no" onclick="setStatus(${o.id}, 'cancelled')">NO</button>
          </td>
        </tr>`).join('')}
    </table>`;
}

async function setStatus(id,status){
  await fetch('/api/admin/order-status',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,status})});
  loadOrders();
}

async function loadProducts(){
  const list = await (await fetch('/api/admin/products')).json();
  $('content').innerHTML = `
    <table>
      <tr><th>ID</th><th>Nomi</th><th>Kategoriya</th><th>Narx</th><th>Stock</th></tr>
      ${list.map(p => `
        <tr>
          <td>#${p.id}</td>
          <td>${p.name}</td>
          <td>${p.category_name}</td>
          <td>${money(p.price)}</td>
          <td>${p.stock}</td>
        </tr>`).join('')}
    </table>`;
}

function showAdd(){
  $('content').innerHTML = `
    <div class="form">
      <h2>Mahsulot qo‘shish</h2>
      <input id="name" placeholder="Mahsulot nomi">
      <textarea id="description" placeholder="Tavsif"></textarea>
      <input id="price" placeholder="Narx">
      <input id="old_price" placeholder="Eski narx">
      <input id="category_id" placeholder="Kategoriya ID">
      <input id="image" placeholder="Rasm URL, masalan /static/img/p1.svg">
      <input id="badge" placeholder="Badge: NEW / SALE / TOP">
      <button onclick="addProduct()">Qo‘shish</button>
    </div>`;
}

async function addProduct(){
  const body = {
    name: $('name').value,
    description: $('description').value,
    price: $('price').value,
    old_price: $('old_price').value,
    category_id: $('category_id').value || 1,
    image: $('image').value || '/static/img/p1.svg',
    badge: $('badge').value || 'NEW'
  };
  await fetch('/api/admin/add-product',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  loadProducts();
}

loadStats();
