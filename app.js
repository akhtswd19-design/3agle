// Initialize Telegram WebApp
const tg = window.Telegram?.WebApp;
if (tg) {
    tg.ready();
    tg.expand();
}

// Global State
let currentUser = {
    id: tg?.initDataUnsafe?.user?.id || 12345678,
    name: tg?.initDataUnsafe?.user?.first_name || 'عميل العاقل',
    isAdmin: false
};

const SAR_TO_STARS_RATE = 5; // 1 SAR = 5 Stars

// DOM Loaded
document.addEventListener('DOMContentLoaded', () => {
    initSplash();
    initBackgroundStars();
    initNavigation();
    checkAdminPermission();
    loadProducts();
    loadReviews();
    initAdminForm();
    initSupportSystem();
});

// Splash Screen 4 seconds
function initSplash() {
    setTimeout(() => {
        const splash = document.getElementById('splash-screen');
        splash.classList.add('fade-out');
        setTimeout(() => splash.remove(), 800);
    }, 4000);
}

// Background Slow-motion Moving Gold Stars
function initBackgroundStars() {
    const canvas = document.getElementById('starsCanvas');
    const ctx = canvas.getContext('2d');
    
    function resize() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener('resize', resize);

    const stars = [];
    const count = 60;
    for (let i = 0; i < count; i++) {
        stars.push({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            radius: Math.random() * 1.8 + 0.5,
            speedY: Math.random() * 0.3 + 0.1,
            alpha: Math.random() * 0.7 + 0.3,
            pulseSpeed: Math.random() * 0.02 + 0.005
        });
    }

    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        stars.forEach(star => {
            star.y -= star.speedY;
            if (star.y < 0) star.y = canvas.height;

            star.alpha += Math.sin(Date.now() * star.pulseSpeed) * 0.01;
            const clampedAlpha = Math.max(0.2, Math.min(0.9, star.alpha));

            ctx.beginPath();
            ctx.arc(star.x, star.y, star.radius, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(255, 215, 0, ${clampedAlpha})`;
            ctx.shadowBlur = 8;
            ctx.shadowColor = '#ffd700';
            ctx.fill();
        });

        requestAnimationFrame(animate);
    }
    animate();
}

// Smooth Tab Navigation
function initNavigation() {
    const navBtns = document.querySelectorAll('.nav-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');

    navBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');

            navBtns.forEach(b => b.classList.remove('active'));
            tabPanes.forEach(p => p.classList.remove('active'));

            btn.classList.add('active');
            const targetPane = document.getElementById(targetTab);
            targetPane.classList.add('active');
        });
    });
}

// Check Admin
async function checkAdminPermission() {
    try {
        const res = await fetch(`/api/check-admin?user_id=${currentUser.id}`);
        const data = await res.json();
        if (data.is_admin) {
            currentUser.isAdmin = true;
            document.getElementById('adminTabBtn').classList.remove('hidden');
            document.getElementById('userName').innerText = currentUser.name + ' 👑 (أدمن)';
            loadAdminDashboard();
        } else {
            document.getElementById('userName').innerText = currentUser.name;
        }
    } catch (e) {
        console.error("Admin check failed", e);
    }
}

// Load Products
async function loadProducts() {
    try {
        const res = await fetch('/api/products');
        const products = await res.json();
        const grid = document.getElementById('productsGrid');
        grid.innerHTML = '';

        if (products.length === 0) {
            grid.innerHTML = '<p class="section-desc">لا توجد منتجات حالياً.</p>';
            return;
        }

        products.forEach(p => {
            const card = document.createElement('div');
            card.className = 'product-card';
            card.innerHTML = `
                <div class="product-img-wrapper">
                    <img src="${p.image_url}" class="product-img" alt="${p.title}" onerror="this.src='https://via.placeholder.com/300x200?text=العاقل'">
                </div>
                <div class="product-info">
                    <h4 class="product-title">${p.title}</h4>
                    <p class="product-desc">${p.description}</p>
                    <div class="product-price-row">
                        <div class="price-box">
                            <span class="price-sar">${p.price_sar} ر.س</span>
                            <span class="price-stars">${p.price_stars} ⭐</span>
                        </div>
                        <button class="btn-buy" onclick="buyProduct(${p.id})">شراء الآن</button>
                    </div>
                </div>
            `;
            grid.appendChild(card);
        });
    } catch (e) {
        console.error("Failed to load products", e);
    }
}

// Telegram Stars Instant Payment via tg.openInvoice
async function buyProduct(productId) {
    try {
        const res = await fetch('/api/create-invoice-link', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ product_id: productId, user_id: currentUser.id })
        });
        const data = await res.json();

        if (data.invoice_link && tg) {
            tg.openInvoice(data.invoice_link, (status) => {
                if (status === 'paid') {
                    showPurchasedModal(data.group_link);
                } else {
                    tg.showAlert('لم تكتمل عملية الدفع أو تم إلغاؤها.');
                }
            });
        } else if (data.group_link) {
            // Fallback for browser preview testing
            showPurchasedModal(data.group_link);
        }
    } catch (e) {
        alert('حدث خطأ أثناء إعداد الفاتورة');
    }
}

function showPurchasedModal(link) {
    document.getElementById('purchasedGroupLink').href = link;
    document.getElementById('purchasedModal').classList.remove('hidden');
}

document.getElementById('closePurchasedModalBtn').addEventListener('click', () => {
    document.getElementById('purchasedModal').classList.add('hidden');
});

// Admin Form & Live Price Auto-calculation
function initAdminForm() {
    const sarInput = document.getElementById('prodPrice');
    const starsCalc = document.getElementById('prodStarsCalc');
    const fileInput = document.getElementById('prodImageFile');
    const previewContainer = document.getElementById('imagePreviewContainer');
    const previewImg = document.getElementById('imagePreviewImg');

    sarInput.addEventListener('input', () => {
        const sar = parseFloat(sarInput.value) || 0;
        starsCalc.value = `${sar * SAR_TO_STARS_RATE} ⭐`;
    });

    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (event) => {
                previewImg.src = event.target.result;
                previewContainer.classList.remove('hidden');
            };
            reader.readAsDataURL(file);
        }
    });

    document.getElementById('addProductForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const file = fileInput.files[0];
        if (!file) return alert('يرجى اختيار صورة للمنتج');

        const formData = new FormData();
        formData.append('title', document.getElementById('prodTitle').value);
        formData.append('price_sar', document.getElementById('prodPrice').value);
        formData.append('description', document.getElementById('prodDesc').value);
        formData.append('group_link', document.getElementById('prodLink').value);
        formData.append('image', file);

        try {
            const res = await fetch('/api/admin/add-product', {
                method: 'POST',
                headers: { 'X-User-ID': currentUser.id },
                body: formData
            });
            const data = await res.json();
            if (data.success) {
                alert('تمت إضافة المنتج بنجاح وتم إرسال إشعار للزبائن! 🚀');
                document.getElementById('addProductForm').reset();
                previewContainer.classList.add('hidden');
                loadProducts();
                loadAdminDashboard();
            }
        } catch (err) {
            alert('حدث خطأ أثناء حفظ المنتج');
        }
    });

    document.getElementById('sendBroadcastBtn').addEventListener('click', async () => {
        const msg = document.getElementById('broadcastMsgInput').value;
        if (!msg) return alert('اكتب نص الرسالة أولاً');

        const res = await fetch('/api/admin/broadcast', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-User-ID': currentUser.id
            },
            body: JSON.stringify({ message: msg })
        });
        const data = await res.json();
        if (data.success) {
            alert(`تم إرسال الرسالة بنجاح إلى ${data.sent_count} عميل!`);
            document.getElementById('broadcastMsgInput').value = '';
        }
    });
}

// Load Admin Dashboard Details
async function loadAdminDashboard() {
    try {
        const res = await fetch(`/api/admin/stats?user_id=${currentUser.id}`);
        const stats = await res.json();
        document.getElementById('statSales').innerText = stats.total_sales + ' ⭐';
        document.getElementById('statOrders').innerText = stats.total_orders;
        document.getElementById('statProducts').innerText = stats.total_products;
        document.getElementById('statTickets').innerText = stats.total_tickets;

        // Load Products for Deletion
        const prodRes = await fetch('/api/products');
        const prods = await prodRes.json();
        const adminProdsList = document.getElementById('adminProductsList');
        adminProdsList.innerHTML = prods.map(p => `
            <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid rgba(255,255,255,0.05);">
                <span>${p.title} (${p.price_sar} SAR)</span>
                <button onclick="deleteProduct(${p.id})" style="background:#ef4444; color:white; border:none; padding:4px 8px; border-radius:6px; cursor:pointer;">حذف</button>
            </div>
        `).join('');

        // Load Tickets
        const ticketsRes = await fetch(`/api/admin/tickets?user_id=${currentUser.id}`);
        const tickets = await ticketsRes.json();
        const adminTicketsList = document.getElementById('adminTicketsList');
        adminTicketsList.innerHTML = tickets.map(t => `
            <div style="background:rgba(0,0,0,0.3); padding:10px; border-radius:8px; margin-bottom:8px;">
                <div style="display:flex; justify-content:space-between; font-size:0.85rem; color:#ffd700;">
                    <span>مستخدم: ${t.user_id}</span>
                    <span>الحالة: ${t.status}</span>
                </div>
                <div style="margin:8px 0; max-height:100px; overflow-y:auto; font-size:0.8rem;">
                    ${t.messages.map(m => `<div><b>${m.sender}:</b> ${m.text}</div>`).join('')}
                </div>
                <div style="display:flex; gap:5px;">
                    <input type="text" id="adminReplyInput_${t.user_id}" placeholder="رد الأدمن..." style="flex:1; font-size:0.8rem; padding:4px 8px;">
                    <button onclick="sendAdminReply(${t.user_id})" style="background:#22c55e; color:white; border:none; padding:4px 10px; border-radius:6px; cursor:pointer; font-size:0.8rem;">رد</button>
                </div>
            </div>
        `).join('');

    } catch (e) {
        console.error("Error loading admin dashboard", e);
    }
}

async function deleteProduct(id) {
    if (!confirm('هل انت متأكد من حذف هذا المنتج؟')) return;
    await fetch(`/api/admin/delete-product/${id}`, {
        method: 'DELETE',
        headers: { 'X-User-ID': currentUser.id }
    });
    loadProducts();
    loadAdminDashboard();
}

async function sendAdminReply(userId) {
    const input = document.getElementById(`adminReplyInput_${userId}`);
    const text = input.value;
    if (!text) return;

    await fetch('/api/admin/reply-ticket', {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'X-User-ID': currentUser.id
        },
        body: JSON.stringify({ target_user_id: userId, text: text })
    });
    input.value = '';
    loadAdminDashboard();
}

// Reviews
async function loadReviews() {
    try {
        const res = await fetch('/api/reviews');
        const reviews = await res.json();
        const list = document.getElementById('reviewsList');
        list.innerHTML = reviews.map(r => `
            <div class="review-card">
                <div class="review-header">
                    <span class="review-author">${r.user_name}</span>
                    <span class="review-stars-val">${'⭐'.repeat(r.rating)}</span>
                </div>
                <p class="review-text">${r.comment}</p>
                ${currentUser.isAdmin ? `<button class="review-admin-del" onclick="deleteReview(${r.id})">حذف التقييم</button>` : ''}
            </div>
        `).join('');
    } catch (e) {
        console.error(e);
    }
}

document.getElementById('openReviewModalBtn').addEventListener('click', () => {
    document.getElementById('reviewModal').classList.remove('hidden');
});
document.getElementById('closeReviewModalBtn').addEventListener('click', () => {
    document.getElementById('reviewModal').classList.add('hidden');
});

document.getElementById('submitReviewBtn').addEventListener('click', async () => {
    const rating = document.getElementById('reviewRating').value;
    const comment = document.getElementById('reviewComment').value;
    if (!comment) return alert('يرجى كتابة تعليق');

    await fetch('/api/reviews', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_name: currentUser.name, rating: parseInt(rating), comment })
    });

    document.getElementById('reviewModal').classList.add('hidden');
    document.getElementById('reviewComment').value = '';
    loadReviews();
});

async function deleteReview(id) {
    if (!confirm('حذف التقييم؟')) return;
    await fetch(`/api/admin/delete-review/${id}`, {
        method: 'DELETE',
        headers: { 'X-User-ID': currentUser.id }
    });
    loadReviews();
}

// Support Ticket
function initSupportSystem() {
    document.getElementById('openTicketBtn').addEventListener('click', () => {
        document.getElementById('openTicketBtn').classList.add('hidden');
        document.getElementById('activeTicketArea').classList.remove('hidden');
        loadTicketMessages();
    });

    document.getElementById('sendUserMsgBtn').addEventListener('click', async () => {
        const input = document.getElementById('userTicketMsgInput');
        const text = input.value;
        if (!text) return;

        await fetch('/api/support/message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: currentUser.id, text })
        });
        input.value = '';
        loadTicketMessages();
    });
}

async function loadTicketMessages() {
    const res = await fetch(`/api/support/ticket?user_id=${currentUser.id}`);
    const ticket = await res.json();
    const container = document.getElementById('ticketMessages');
    if (ticket && ticket.messages) {
        container.innerHTML = ticket.messages.map(m => `
            <div class="chat-msg ${m.sender === 'user' ? 'user' : 'admin'}">
                <b>${m.sender === 'user' ? 'أنت' : 'الدعم الفني'}:</b> ${m.text}
            </div>
        `).join('');
        container.scrollTop = container.scrollHeight;
    }
}
