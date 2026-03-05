import os
import re
import asyncio
import threading
from datetime import datetime
from flask import Flask
from telethon import TelegramClient, events, Button

# --- 1. إعداد سيرفر الويب (Flask) لإبقاء الخدمة تعمل ---
app = Flask(__name__)

@app.route('/')
def home():
    return "الرصد يعمل بنجاح!"

def run_flask():
    # Render يحتاج ربط الخدمة بمنفذ (Port)
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# تشغيل Flask في خيط مستقل
threading.Thread(target=run_flask, daemon=True).start()

# --- 2. إعدادات حسابك (تأكد من وجود ملف .session) ---
api_id = 2040
api_hash = 'b18441a1ff607e10a989891a5462e627'
session_name = 'session_name' 

client = TelegramClient(session_name, api_id, api_hash)

# --- 3. الكلمات المفتاحية الموسعة والشاملة ---
keywords = [
    'حد', 'مين', 'واجب', 'حل', 'كويز', 'اختبار', 'مشروع', 'بحث', 'تخرج', 'تلخيص', 
    'ممكن حل', 'أحتاج مساعدة', 'ميد ترم', 'فاينل', 'تصميم', 'برمجة', 'كود',
    'إحصاء', 'احصاء', 'رياضيات', 'فيزياء', 'كيمياء', 'ترجمة', 'عذر', 'اعذار', 
    'إجازة مرضية', 'تقرير طبي', 'سكليف', 'غياب', 'مستشفى'
]

forbidden = ['استثمار', 'ارباح', 'دخل', 'ضمان', 'رخيص', 'سعر خاص']

# --- 4. وظيفة الرصد المعدلة لحل مشكلة الـ Loop ---
@client.on(events.NewMessage)
async def handler(event):
    try:
        if event.is_private: return 
        
        text = event.raw_text.strip()
        length = len(text)
        
        # فلاتر الروابط والجوال
        if any(x in text for x in ['http', 'wa.me', 't.me/+', 'snapchat.com']): return
        if re.search(r'\d{9,}', text): return

        if any(word in text.lower() for word in keywords):
            if 15 <= length <= 130:
                if not any(bad in text for bad in forbidden):
                    
                    chat = await event.get_chat()
                    chat_title = chat.title if hasattr(chat, 'title') else "مجموعة غير معروفة"
                    time_now = datetime.now().strftime("%I:%M %p")
                    
                    # الواجهة الاحترافية
                    display_message = (
                        f"**🚀 رصد طلب/عذر جديد**\n"
                        f"‏━━━━━━━━━━━━━━━━━━\n"
                        f"**📍 المصدر:** `{chat_title}`\n"
                        f"**⏰ الوقت:** `{time_now}`\n"
                        f"‏━━━━━━━━━━━━━━━━━━\n"
                        f"**📝 النص المرصود:**\n"
                        f"_{text}_\n"
                        f"‏━━━━━━━━━━━━━━━━━━"
                    )
                    
                    # إرسال الرسالة مع زر الانتقال المباشر
                    await client.send_message(
                        'student1_admin', 
                        display_message, 
                        link_preview=False,
                        buttons=[[Button.url("🔗 اذهب للطلب الآن", f"https://t.me/c/{chat.id}/{event.id}")]]
                    )
    except Exception as e:
        print(f"⚠️ خطأ أثناء المعالجة: {e}")

# --- 5. تشغيل البوت بطريقة متوافقة مع Asyncio ---
async def main():
    print("جاري بدء الرصد الشامل...")
    await client.start()
    await client.run_until_disconnected()

if __name__ == '__main__':
    # حل مشكلة RuntimeError: no running event loop
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
