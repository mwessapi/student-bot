import os
import asyncio
import threading
from flask import Flask
from telethon import TelegramClient, events, Button

# --- 1. سيرفر الويب لإبقاء البوت حياً ---
app = Flask(__name__)
@app.route('/')
def home(): return "رادار الرصد الشامل (حسابين + أزرار) يعمل!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_flask, daemon=True).start()

# --- 2. إعدادات الحسابات المتعددة ---
accounts = [
    {'name': 'رادار [1]', 'id': 2040, 'hash': 'b18441a1ff607e10a989891a5462e627', 'session': 'session_name'},
    {'name': 'رادار [2]', 'id': 2040, 'hash': 'b18441a1ff607e10a989891a5462e627', 'session': 'session_2'}
]

# --- 3. القائمة الكاملة والضخمة للكلمات (رصد كل شيء) ---
all_keywords = [
    # كلمات الاستفسار (أدوات السؤال بكل اللهجات)
    'حد', 'مين', 'كيف', 'متى', 'سؤال', 'استفسار', 'يعرف', 'يفيدني', 'احتاج', 'ممكن', 
    'أبغى', 'ابي', 'وش', 'ايش', 'شنو', 'تكفون', 'ساعدوني', 'بالله', 'لو سمحتو', 'يا شباب', 
    'دلوني', 'تعرفون', 'أحد', 'موجود', 'يقدر', 'فزعتكم',
    # كلمات الطلب والخدمات الأكاديمية والتقنية
    'واجب', 'حل', 'كويز', 'اختبار', 'مشروع', 'بحث', 'تخرج', 'مهندس', 'تصميم', 'برمجة', 
    'كود', 'إحصاء', 'رياضيات', 'فيزياء', 'كيمياء', 'ترجمة', 'محاسبة', 'اقتصاد', 'ميد', 'فاينل',
    'عذر', 'غياب', 'سكليف', 'مرضية', 'تجسير', 'دوام', 'تدريب', 'صيفي', 'مادة', 'دكتور', 
    'تحضير', 'درجات', 'معدل', 'جامعة', 'كلية', 'بوربوينت', 'تنسيق', 'كتابة', 'مونتاج', 
    'تفريغ', 'لوقو', 'شعار', 'فوتوشوب', 'هندسة'
]

# كلمات المنع (لتصفية الإعلانات)
forbidden_words = ['تواصل', 'واتساب', 'واتس', 'للتواصل', 'ارباح', 'استثمار', 'ضمان', 'سعرنا']

# --- 4. وظيفة الرصد والمعالجة بالأزرار ---
async def start_monitoring(acc_info):
    client = TelegramClient(acc_info['session'], acc_info['id'], acc_info['hash'])
    radar_name = acc_info['name']

    @client.on(events.NewMessage)
    async def handler(event):
        try:
            if event.is_private: return 
            text = event.raw_text.strip()
            text_lower = text.lower()

            # فلتر الروابط والإعلانات
            if any(x in text_lower for x in ['http', 'wa.me', 't.me/+']): return
            if any(bad in text_lower for bad in forbidden_words): return

            # الرصد: إذا وجدت أي كلمة من القائمة الكبيرة
            if any(word in text_lower for word in all_keywords):
                if len(text) >= 10:
                    sender = await event.get_sender()
                    chat = await event.get_chat()
                    
                    username = getattr(sender, 'username', None)
                    user_display = f"@{username}" if username else "بدون يوزر"
                    
                    # تنسيق الرسالة
                    display_message = (
                        f"⚡️ **رصد جديد عبر {radar_name}**\n"
                        f"‏━━━━━━━━━━━━━━━━━━\n"
                        f"👤 **العميل:** {getattr(sender, 'first_name', 'مستخدم')} ( {user_display} )\n"
                        f"🆔 **ID:** `{sender.id}`\n"
                        f"📍 **المصدر:** `{getattr(chat, 'title', 'مجموعة')}`\n"
                        f"🔗 [انتقل للرسالة الأصلية](https://t.me/c/{chat.id}/{event.id})\n"
                        f"‏━━━━━━━━━━━━━━━━━━\n"
                        f"📝 **النص المرصود:**\n"
                        f"_{text}_\n"
                        f"‏━━━━━━━━━━━━━━━━━━\n"
                        f"👇 **تواصل مع العميل مباشرة:**"
                    )
                    
                    # نظام الأزرار لضمان الوصول للعميل
                    buttons_list = []
                    if username:
                        buttons_list.append([Button.url("💬 مراسلة خاصة", f"https://t.me/{username}")])
                    
                    # زر الرد في المجموعة يظهر دائماً كحل بديل
                    buttons_list.append([Button.url("⤴️ الرد في المجموعة", f"https://t.me/c/{chat.id}/{event.id}")])

                    await client.send_message('student1_admin', display_message, buttons=buttons_list, silent=False)
        except Exception as e:
            print(f"Error in {radar_name}: {e}")

    await client.start()
    print(f"✅ {radar_name} متصل وبدأ الرصد الشامل...")
    await client.run_until_disconnected()

async def main():
    tasks = [start_monitoring(acc) for acc in accounts]
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
