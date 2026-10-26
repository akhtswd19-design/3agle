import os
import sys
import asyncio
import json
import sqlite3
from typing import List, Dict, Any
from fastapi import FastAPI, File, UploadFile, Form, Header, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn
from telegram import Update, LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, PreCheckoutQueryHandler, MessageHandler, filters, ContextTypes

# Configurations from Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-app.onrender.com")
ADMIN_USER_IDS = [int(i.strip()) for i in os.getenv("ADMIN_USER_IDS", "123456789").split(",") if i.strip()]
SAR_TO_STARS_RATE = 5  # 1 SAR = 5 Telegram Stars

# Initialize FastAPI App
app = FastAPI(title="متجر العاقل")

# Database Setup
DB_FILE = "store.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Products
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            price_sar REAL NOT NULL,
            price_stars INTEGER NOT NULL,
            description TEXT,
            group_link TEXT NOT NULL,
            image_url TEXT NOT NULL
        )
    ''')
    # Orders
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            stars_paid INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Reviews
    c.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT NOT NULL,
            rating INTEGER NOT NULL,
            comment TEXT NOT NULL
        )
    ''')
    # Support Tickets
    c.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            user_id INTEGER PRIMARY KEY,
            status TEXT DEFAULT "open",
            messages TEXT DEFAULT "[]"
        )
    ''')
    # Customers List for Broadcast
    c.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            user_id INTEGER PRIMARY KEY
        )
    ''')
    
    # Insert Sample Data if empty
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        c.execute('''
            INSERT INTO products (title, price_sar, price_stars, description, group_link, image_url)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            "دليل الملفات العسكرية الشامل",
            20.0,
            100,
            "ملف متكامل يحتوي على كل ما تحتاجه من تنظيمات وإرشادات وتدريبات عسكرية.",
            "https://t.me/+ExampleMilitaryGroupLink",
            "/uploads/sample_military.jpg"
        ))
        c.execute('''
            INSERT INTO reviews (user_name, rating, comment)
            VALUES (?, ?, ?)
        ''', ("فهد العتيبي", 5, "متجر ممتاز وسريع في التسليم، والملفات جداً قيمة."))

    conn.commit()
    conn.close()

init_db()

# Telegram Bot Setup
bot_app = Application.builder().token(BOT_TOKEN).build()

# Store uploaded images
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# --- Telegram Bot Handlers ---
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Save user
    conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT OR IGNORE INTO customers (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

    keyboard = [
        [InlineKeyboardButton("🛡️ فتح متجر العاقل", web_app=WebAppInfo(url=WEBAPP_URL))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
          "مرحباً بك في متجر العاقل للملفات العسكرية! 🛡️ اضغط على الزر أدناه لفتح التطبيق المصغر للمتجر.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("❌ عذراً، هذا الأمر مخصص للإدارة فقط.")
        return

    admin_keyboard = [
        [InlineKeyboardButton("⚙️ فتح لوحة تحكم الأدمن", web_app=WebAppInfo(url=f"{WEBAPP_URL}?admin=true"))]
    ]
    await update.message.reply_text(
        "أهلاً بك يا مدير المتجر 👑 من هنا يمكنك التحكم بالمنتجات، الإحصائيات، الرسائل الجماعية، والدعم الفني.",
        reply_markup=InlineKeyboardMarkup(admin_keyboard)
    )

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    # Approve pre-checkout query
    await query.answer(ok=True)

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    payload = payment.invoice_payload # product_id
    user_id = update.effective_user.id

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT title, group_link FROM products WHERE id = ?", (payload,))
    prod = c.fetchone()
    if prod:
        title, link = prod
        c.execute("INSERT INTO orders (user_id, product_id, stars_paid) VALUES (?, ?, ?)",
                  (user_id, payload, payment.total_amount))
        conn.commit()
        
        await update.message.reply_text(
            f"🎉 *تم الشراء بنجاح!\n\nالمنتج: *{title}**\n\nرابط الانضمام واستلام الملفات:\n{link}",
            parse_mode="Markdown"
        )
conn.close()

bot_app.add_handler(CommandHandler("start", start_cmd))
bot_app.add_handler(CommandHandler("admin", admin_cmd))
bot_app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
bot_app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))

# --- API Models ---
class ReviewModel(BaseModel):
    user_name: str
    rating: int
    comment: str

class BroadcastModel(BaseModel):
    message: str

class TicketMsgModel(BaseModel):
    user_id: int
    text: str

class AdminReplyModel(BaseModel):
    target_user_id: int
    text: str

class InvoiceReqModel(BaseModel):
    product_id: int
    user_id: int

# --- API Endpoints ---
@app.get("/api/products")
def get_products():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, title, price_sar, price_stars, description, group_link, image_url FROM products ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return [
        {
            "id": r[0], "title": r[1], "price_sar": r[2], "price_stars": r[3],
            "description": r[4], "group_link": r[5], "image_url": r[6]
        } for r in rows
    ]

@app.get("/api/check-admin")
def check_admin(user_id: int):
    return {"is_admin": user_id in ADMIN_USER_IDS}

@app.post("/api/create-invoice-link")
async def create_invoice_link(req: InvoiceReqModel):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT title, description, price_stars, group_link FROM products WHERE id = ?", (req.product_id,))
    prod = c.fetchone()
    conn.close()

    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")

    title, desc, stars, group_link = prod
    
    try:
        prices = [LabeledPrice(label=title, amount=stars)]
        link = await bot_app.bot.create_invoice_link(
            title=title,
            description=desc,
            payload=str(req.product_id),
            provider_token="", # Empty for Telegram Stars (XTR)
            currency="XTR",
            prices=prices
        )
        return {"invoice_link": link, "group_link": group_link}
    except Exception as e:
        # Return link as fallback if token isn't linked yet
        return {"invoice_link": "", "group_link": group_link}

@app.get("/api/reviews")
def get_reviews():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, user_name, rating, comment FROM reviews ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "user_name": r[1], "rating": r[2], "comment": r[3]} for r in rows]

@app.post("/api/reviews")
def add_review(rev: ReviewModel):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO reviews (user_name, rating, comment) VALUES (?, ?, ?)",
              (rev.user_name, rev.rating, rev.comment))
    conn.commit()
    conn.close()
    return {"success": True}

# --- Admin APIs ---
def verify_admin(x_user_id: int):
    if x_user_id not in ADMIN_USER_IDS:
        raise HTTPException(status_code=403, detail="Unauthorized Admin Access")

@app.post("/api/admin/add-product")
async def admin_add_product(
    title: str = Form(...),
    price_sar: float = Form(...),
    description: str = Form(...),
    group_link: str = Form(...),
    image: UploadFile = File(...),
    x_user_id: int = Header(...)
):
    verify_admin(x_user_id)
    
    # Save Image to local filesystem
    image_path = f"uploads/{image.filename}"
    with open(image_path, "wb") as f:
        f.write(await image.read())
    
    price_stars = int(price_sar * SAR_TO_STARS_RATE)
    image_url = f"/{image_path}"

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO products (title, price_sar, price_stars, description, group_link, image_url)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (title, price_sar, price_stars, description, group_link, image_url))
    conn.commit()
    conn.close()

    # Broadcast new product to all clients automatically
asyncio.create_task(broadcast_to_all(f"📢 *منتج جديد في متجر العاقل!\n\n📌 *{title}**\n\n💰 السعر: {price_sar} ر.س ({price_stars} ⭐)\n\n📝 الوصف: {description}"))

@app.delete("/api/admin/delete-product/{prod_id}")
def delete_product(prod_id: int, x_user_id: int = Header(...)):
    verify_admin(x_user_id)
    conn = sqlite3.connect(DB_FILE)
    conn.execute("DELETE FROM products WHERE id = ?", (prod_id,))
    conn.commit()
    conn.close()
    return {"success": True}

@app.delete("/api/admin/delete-review/{rev_id}")
def delete_review(rev_id: int, x_user_id: int = Header(...)):
    verify_admin(x_user_id)
    conn = sqlite3.connect(DB_FILE)
    conn.execute("DELETE FROM reviews WHERE id = ?", (rev_id,))
    conn.commit()
    conn.close()
    return {"success": True}

@app.get("/api/admin/stats")
def get_admin_stats(user_id: int):
    verify_admin(user_id)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT SUM(stars_paid), COUNT(*) FROM orders")
    sum_stars, total_orders = c.fetchone()
    c.execute("SELECT COUNT(*) FROM products")
    total_products = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM tickets")
    total_tickets = c.fetchone()[0]
    conn.close()
    return {
        "total_sales": sum_stars or 0,
        "total_orders": total_orders or 0,
        "total_products": total_products,
        "total_tickets": total_tickets
    }

@app.post("/api/admin/broadcast")
async def broadcast_msg(data: BroadcastModel, x_user_id: int = Header(...)):
    verify_admin(x_user_id)
    count = await broadcast_to_all(data.message)
    return {"success": True, "sent_count": count}

async def broadcast_to_all(message_text: str) -> int:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id FROM customers")
    users = c.fetchall()
    conn.close()

    count = 0
    for u in users:
        try:
            await bot_app.bot.send_message(chat_id=u[0], text=message_text, parse_mode="Markdown")
            count += 1
            await asyncio.sleep(0.05) # Rate limiting
        except Exception:
            pass
    return count

# Support System APIs
@app.get("/api/support/ticket")
def get_user_ticket(user_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT messages, status FROM tickets WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"messages": json.loads(row[0]), "status": row[1]}
    return {"messages": [], "status": "new"}

@app.post("/api/support/message")
def add_support_message(msg: TicketMsgModel):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT messages FROM tickets WHERE user_id = ?", (msg.user_id,))
    row = c.fetchone()
    messages = json.loads(row[0]) if row else []
    messages.append({"sender": "user", "text": msg.text})

    c.execute("INSERT OR REPLACE INTO tickets (user_id, status, messages) VALUES (?, 'open', ?)",
              (msg.user_id, json.dumps(messages)))
    conn.commit()
    conn.close()
    return {"success": True}

@app.get("/api/admin/tickets")
def get_admin_tickets(user_id: int):
    verify_admin(user_id)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id, status, messages FROM tickets")
    rows = c.fetchall()
    conn.close()
    return [{"user_id": r[0], "status": r[1], "messages": json.loads(r[2])} for r in rows]

@app.post("/api/admin/reply-ticket")
async def admin_reply_ticket(data: AdminReplyModel, x_user_id: int = Header(...)):
    verify_admin(x_user_id)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT messages FROM tickets WHERE user_id = ?", (data.target_user_id,))
    row = c.fetchone()
    if row:
        messages = json.loads(row[0])
        messages.append({"sender": "admin", "text": data.text})
        c.execute("UPDATE tickets SET messages = ? WHERE user_id = ?", (json.dumps(messages), data.target_user_id))
        conn.commit()

        # Send Telegram notification to user
        try:
              await bot_app.bot.send_message(
                chat_id=data.target_user_id,
                text=f"💬 **رد من الدعم الفني (متجر العاقل):**\n\n{data.text}",
                parse_mode="Markdown"
            )
        except Exception:
            pass
    conn.close()
    return {"success": True}

# Mount WebApp Static Files
app.mount("/", StaticFiles(directory=".", html=True), name="static")

# Lifespan Runner for Bot + FastAPI
@app.on_event("startup")
async def on_startup():
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling()

@app.on_event("shutdown")
async def on_shutdown():
    await bot_app.updater.stop()
    await bot_app.stop()
    await bot_app.shutdown()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)), reload=False)
