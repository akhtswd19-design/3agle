# متجر العاقل - تطبيق مصغر للتليجرام (Telegram Mini App)

متجر إلكتروني متكامل لبيع الملفات العسكرية عبر تليجرام مع دعم يدعم نجوم تليجرام (Telegram Stars - XTR).

## 🚀 طريقة التشغيل على Render (مبسطة وسريعة):

1. **فك الضغط** عن ملف ZIP هذا على جهاز الكمبيوتر.
2. قم بإنشاء مستودع جديد على **GitHub** و ارفع جميع هذه الملفات فيه.
3. توجه إلى موقع [Render.com](https://render.com) وسجل الدخول.
4. اضغط على **New +** ثم اختر **Web Service**.
5. اربط حساب Render بـ GitHub واختر المستودع.
6. في إعدادات Render ضع الاتي:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
7. أضف متغيرات البيئة (**Environment Variables**):
   - `BOT_TOKEN`: التوكن الخاص بـ BotFather.
   - `WEBAPP_URL`: رابط الخدمة من Render بعد إنشائها (مثال: `https://al-aaqil-store.onrender.com`).
   - `ADMIN_USER_IDS`: الآيدي الخاص بك في تليجرام (مثل: `123456789`).

8. انسخ رابط الموقع وضع بـ BotFather في تليجرام لتفعيل الـ Mini App عبر أمر `/newapp` أو أزرار الـ Bot.

مبروك! المتجر الآن يعمل 24 ساعة مجاناً.
