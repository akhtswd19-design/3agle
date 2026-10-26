import os
import json
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import LabeledPrice, PreCheckoutQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Files for simple JSON DB persistence
PRODUCTS_FILE = "products.json"
REVIEWS_FILE = "reviews.json"
TICKETS_FILE = "tickets.json"

def load_data(file, default):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_data(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Initial sample data
products = load_data(PRODUCTS_FILE, [
    {
        "id": 1,
        "title": "حزمة الملفات العسكرية الشاملة",
        "description": "تتضمن نماذج مستندات، دلائل إجرائية، واللوائح الشاملة المحدثة.",
        "price_sar": 20,
        "stars_price": 30,
        "image_url": "https://images.unsplash.com/photo-1541872703-74c5e44368f9?w=600",
        "file_url": "https://t.me/example_military_group"
    }
])

reviews = load_data(REVIEWS_FILE, [
    {"id": 1, "user_name": "أبو فهد", "rating": 5, "comment": "متجر ممتاز وسريع في تقديم الملفات العسكرية المطلوب.", "date": "2026-10-20"},
    {"id": 2, "user_name": "النقيب خالد", "rating": 5, "comment": "تعامل احترافي جداً والملفات محدثة بدقة.", "date": "2026-10-22"}
])

tickets = load_data(TICKETS_FILE, [])
stats = {"total_sales": 0, "total_stars": 0}

# Webhook & Server Setup
app = web.Application()

# --- HTTP Endpoints ---
async def index_handler(request):
    return web.FileResponse('./static/index.html')

async def check_admin(request):
    user_id = int(request.query.get('user_id', 0))
    return web.json_response({"is_admin": user_id == ADMIN_ID})

async def get_products(request):
    return web.json_response(products)

async def create_invoice(request):
    data = await request.json()
    prod_id = data.get('product_id')
    user_id = data.get('user_id')

    prod = next((p for p in products if p['id'] == prod_id), None)
    if not prod:
        return web.json_response({"error": "المنتج غير موجود"}, status=404)

    try:
        prices = [LabeledPrice(label=prod['title'], amount=prod['stars_price'])]
        invoice_link = await bot.create_invoice_link(
            title=prod['title'],
            description=prod['description'],
            payload=f"prod_{prod['id']}_{user_id}",
            currency="XTR", # Telegram Stars Currency
            prices=prices
        )
        return web.json_response({"invoice_url": invoice_link})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def add_product(request):
    reader = await request.multipart()
    data = {}
    image_filename = None

    while True:
        field = await reader.next()
        if field is None:
            break
        if field.name == 'image':
            filename = field.filename
            if filename:
                os.makedirs('./uploads', exist_ok=True)
                filepath = os.path.join('./uploads', filename)
                with open(filepath, 'wb') as f:
                    while True:
                        chunk = await field.read_chunk()
                        if not chunk:
                            break
                        f.write(chunk)
                image_filename = f"/uploads/{filename}"
        else:
            value = await field.read(decode=True)
            data[field.name] = value.decode('utf-8')

    if int(data.get('admin_id', 0)) != ADMIN_ID:
        return web.json_response({"error": "غير مصرح"}, status=403)

    price_sar = float(data.get('price_sar', 0))
    stars_price = int(price_sar * 1.5)

    new_prod = {
        "id": len(products) + 1,
        "title": data.get('title'),
        "description": data.get('description'),
        "price_sar": price_sar,
        "stars_price": stars_price,
        "image_url": image_filename or "https://via.placeholder.com/400x200?text=المتجر+العسكري",
        "file_url": data.get('file_url')
    }
    products.append(new_prod)
    save_data(PRODUCTS_FILE, products)

    # Broadcast notification to all users (Simulated broadcast message)
    try:
        asyncio.create_task(broadcast_new_product(new_prod))
    except Exception as e:
        pass

    return web.json_response({"success": True})

async def delete_product(request):
    admin_id = int(request.query.get('admin_id', 0))
    prod_id = int(request.query.get('id', 0))
    if admin_id != ADMIN_ID:
        return web.json_response({"error": "Unauthorized"}, status=403)

    global products
    products = [p for p in products if p['id'] != prod_id]
    save_data(PRODUCTS_FILE, products)
    return web.json_response({"success": True})

async def get_reviews(request):
    return web.json_response(reviews)

async def add_review(request):
    data = await request.json()
    new_rev = {
        "id": len(reviews) + 1,
        "user_name": data.get('user_name'),
        "rating": data.get('rating'),
        "comment": data.get('comment'),
        "date": "2026-10-26"
    }
    reviews.insert(0, new_rev)
    save_data(REVIEWS_FILE, reviews)
    return web.json_response({"success": True})

async def delete_review(request):
    admin_id = int(request.query.get('admin_id', 0))
    rev_id = int(request.query.get('id', 0))
    if admin_id != ADMIN_ID:
        return web.json_response({"error": "Unauthorized"}, status=403)

    global reviews
    reviews = [r for r in reviews if r['id'] != rev_id]
    save_data(REVIEWS_FILE, reviews)
    return web.json_response({"success": True})

async def create_ticket(request):
    data = await request.json()
    new_t = {
        "id": len(tickets) + 1,
        "user_id": data.get("user_id"),
        "user_name": data.get("user_name"),
        "message": data.get("message")
    }
    tickets.append(new_t)
    save_data(TICKETS_FILE, tickets)

    # Send alert to Admin via Telegram
    try:
        await bot.send_message(
            ADMIN_ID,
            f"📩 **تذكرة دعم فني جديدة**\nالعميل: {new_t['user_name']} (ID: {new_t['user_id']})\nالرسالة: {new_t['message']}"
        )
    except Exception:
        pass

    return web.json_response({"success": True})

async def get_admin_tickets(request):
    admin_id = int(request.query.get('admin_id', 0))
    if admin_id != ADMIN_ID:
        return web.json_response([], status=403)
    return web.json_response(tickets)

async def get_admin_stats(request):
    admin_id = int(request.query.get('admin_id', 0))
    if admin_id != ADMIN_ID:
        return web.json_response({}, status=403)
    return web.json_response({
        "total_sales": stats["total_sales"],
        "total_stars": stats["total_stars"],
        "total_products": len(products)
    })

async def broadcast_new_product(prod):
    msg = f"🌟 **منتج جديد تم إضافته في متجر العاقل!**\n\n📌 **{prod['title']}**\n📝 {prod['description']}\n💰 السعر: {prod['price_sar']} ر.س (⭐️ {prod['stars_price']} نجمة)"
    # Sending to Admin as broadcast target for now
    await bot.send_message(ADMIN_ID, msg)

# Bot Commands & Payment Processors
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 فتح متجر العاقل المصغّر", web_app=WebAppInfo(url=WEBHOOK_URL))]
    ])
    await message.answer(
        "أهلاً بك في **متجر العاقل للملفات والخدمات العسكرية** 🎖️\n\nاضغط على الزر أدناه لفتح المتجر المصغر وتصفح المنتجات والدفع الفوري بنجوم تلجرام.",
        reply_markup=kb,
        parse_mode="Markdown"
    )

@dp.message(Command("admin"))
async def admin_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ عذراً، هذا الأمر مخصص لإدارة المتجر فقط.")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ فتح لوحة التحكم المصغرة", web_app=WebAppInfo(url=WEBHOOK_URL))]
    ])
    await message.answer(
        "🎖️ **مرحباً بك في لوحة تحكم الإدارة (متجر العاقل)**\n\nيمكنك إدارة المنتجات، التقييمات، والرد على التذاكر والإحصائيات من التطبيق المصغر.",
        reply_markup=kb,
        parse_mode="Markdown"
    )

@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(lambda msg: msg.successful_payment is not None)
async def process_successful_payment(message: types.Message):
    payment_info = message.successful_payment
    payload = payment_info.invoice_payload # format: prod_{prod_id}_{user_id}
    parts = payload.split('_')
    prod_id = int(parts[1])

    prod = next((p for p in products if p['id'] == prod_id), None)
    if prod:
        stats["total_sales"] += 1
        stats["total_stars"] += prod['stars_price']

        await message.answer(
            f"✅ **تم استلام الدفع بنجاح! شكراً لثقتك بمتجر العاقل.**\n\n"
            f"📦 **المنتج:** {prod['title']}\n"
            f"🔗 **رابط التحميل / مجموعة الملفات:**\n{prod['file_url']}",
            parse_mode="Markdown"
        )

# App Setup Routes
app.router.add_get('/', index_handler)
app.router.add_static('/uploads', './uploads')
app.router.add_get('/api/check-admin', check_admin)
app.router.add_get('/api/products', get_products)
app.router.add_post('/api/create-invoice', create_invoice)
app.router.add_post('/api/admin/add-product', add_product)
app.router.add_delete('/api/admin/delete-product', delete_product)
app.router.add_get('/api/reviews', get_reviews)
app.router.add_post('/api/reviews/add', add_review)
app.router.add_delete('/api/admin/delete-review', delete_review)
app.router.add_post('/api/tickets/create', create_ticket)
app.router.add_get('/api/admin/tickets', get_admin_tickets)
app.router.add_get('/api/admin/stats', get_admin_stats)

async def main():
    # Set Telegram Bot Webhook or Polling
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

    print(f"Server started on port {port}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
