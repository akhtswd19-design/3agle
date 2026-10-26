# متجر العاقل - Telegram Mini App & Bot

مشروع متكامل لمتجر تلجرام مصغر (Telegram Mini App) مخصص لبيع الملفات والخدمات العسكرية بدعم كامل لنجوم تلجرام (Telegram Stars).

## 🚀 طريقة التشغيل والرفع على Render

### 1. الرفع على GitHub
1. قم بفك الضغط عن هذا الملف.
2. قم بإنشاء مستودع جديد (Repository) على GitHub.
3. ارفع جميع الملفات إلى المستودع.

### 2. الإعداد على Render
1. انشئ حساب على [Render.com](https://render.com).
2. اضغط على **New +** ثم اختر **Web Service**.
3. اربط حساب GitHub واختر المستودع الخاص بك.
4. اضبط الإعدادات التالية:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
5. في قسم **Environment Variables** أضف المتغيرات التالية:
   - `BOT_TOKEN`: توكن البوت الخاص بك من @BotFather
   - `ADMIN_ID`: معرف التلجرام الخاص بك (مثال: 123456789)
   - `WEBHOOK_URL`: رابط الخدمة الخاصة بك على Render (مثال: `https://al-aaqil-store.onrender.com`)
   - `PORT`: `10000`

### 3. ضبط البوت في BotFather
1. افتح `@BotFather` في تلجرام.
2. اختر بوتك ثم ذهب إلى **Bot Settings** -> **Menu Button** -> **Configure menu button**.
3. أرسل الرابط: `https://your-render-app-name.onrender.com` واكتب الاسم (مثلاً: `المتجر`).
