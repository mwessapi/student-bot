import os
import re
import asyncio
import threading
from datetime import datetime
from flask import Flask
from telethon import TelegramClient, events, Button

# --- 1. سيرفر الويب لإبقاء البوت حياً على Render ---
app = Flask(__name__)
@app.route('/')
def home(): return "نظام رصد الخدمات الطلابية يعمل!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_flask, daemon=True).start()

# --- 2. إعدادات الحساب ---
api_id = 2040
api_hash = 'b18441a1ff607e10a989891a5462e627'
session_name = 'session_name' 

client = TelegramClient(session_name, api_id, api_hash)

# --- 3. الكلمات المفتاحية الموسعة ---
keywords = [
    'حد', 'مين', 'واجب', 'حل', 'كويز', 'اختبار', 'مشروع', 'بحث', 'تخرج', 'تلخيص', 
    'عذر', 'اعذار', 'إجازة مرضية', 'تقرير طبي', 'سكليف', 'غياب',
    'تصميم', 'برمجة', 'كود', 'إحصاء', 'احصاء', 'رياضيات', 'فيزياء', 'ترجمة'
]

# --- 4. معالج الرسائل بتنسيق الصورة المطلوبة ---
@client.on(events.NewMessage)
async def handler(event):
    try:
        if event.is_private: return 
        
        text = event.raw_text.strip()
        length = len(text)
        
        # منع الروابط التسويقية الصريحة
        if any(x in text for x in ['http', 'wa.me', 't.me/+', 'snapchat.com']): return

        if any(word in text.lower() for word in keywords):
            # نطاق الطول المثالي للطلبات
            if 5 <= length <= 150:
                
                # جلب بيانات المرسل والمجموعة
                sender = await event.get_sender()
                sender_id = sender.id
                username = f"@{sender.username}" if getattr(sender, 'username', None) else "بدون يوزر"
                
                chat = await event.get_chat()
                chat_title = chat.title if hasattr(chat, 'title') else "مجموعة غير معروفة"
                
                # تصميم الواجهة المطابق للصورة
                display_message = (
                    f"✨ **طلب خدمة طلابية جديد**\n"
                    f"‏━━━━━━━━━━━━━━━━━━\n"
                    f"👤 **العميل:** {username}\n"
                    f"🆔 **ID:** `{sender_id}`\n"
                    f"📍 **المصدر:** `{chat_title}`\n"
                    f"🔗 [انتقل للرسالة الأصلية](https://t.me/c/{chat.id}/{event.id})\n"
                    f"‏━━━━━━━━━━━━━━━━━━\n"
                    f"📝 **نص الطلب:**\n"
                    f"_{text}_\n"
                    f"‏━━━━━━━━━━━━━━━━━━\n"
                    f"👇 **تواصل مع العميل مباشرة:**"
                )
                
                # إضافة الأزرار الشفافة
                buttons = []
                if getattr(sender, 'username', None):
                    buttons.append([Button.url("💬 مراسلة الطالب (خاص)", f"https://t.me/{sender.username}")])
                else:
                    buttons.append([Button.url("⤴️ الرد عبر المجموعة", f"https://t.me/c/{chat.id}/{event.id}")])

                await client.send_message('student1_admin', display_message, buttons=buttons)
                
    except Exception as e:
        print(f"⚠️ خطأ: {e}")

# --- 5. التشغيل ---
async def main():
    await client.start()
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
