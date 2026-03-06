import os
import asyncio
import threading
import google.generativeai as genai
from flask import Flask
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError

# ================== 1. إعدادات Gemini والبيئة ==================
GEMINI_KEY = os.environ.get("GEMINI_KEY")
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    ai_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    ai_model = None

# ================== 2. قوائم الفلترة الشاملة ==================
ALL_KEYWORDS = [
    'حد', 'مين', 'كيف', 'متى', 'سؤال', 'استفسار', 'يعرف', 'يفيدني', 'احتاج', 'ممكن',
    'أبغى', 'ابي', 'وش', 'ايش', 'شنو', 'تكفون', 'ساعدوني', 'بالله', 'لو سمحتو',
    'واجب', 'حل', 'كويز', 'اختبار', 'مشروع', 'بحث', 'تخرج', 'ميد', 'فاينل', 'تقرير',
    'شرح', 'مادة', 'دكتور', 'جامعة', 'برمجة', 'تصميم', 'كود', 'إحصاء', 'رياضيات',
    'فيزياء', 'كيمياء', 'سي شارب', 'C#', 'داتابيز', 'SQL', 'باكيت تريسر', 'بوربوينت'
]

FORBIDDEN_WORDS = ['تواصل', 'واتساب', 'ارباح', 'استثمار', 'ضمان', 'فحص دوري', 'تأشيرات']

# ================== 3. الإعدادات الأساسية ==================
API_ID = 2040 
API_HASH = "b18441a1ff607e10a989891a5462e627"
TARGET_CHANNEL = "student1_admin"
MY_USER_ID = 6190186046 # حسابك لتلقي إشعارات الأعطال

app = Flask(__name__)
@app.route('/')
def home(): return "Radar with Gemini + Auto-Fallback is Live"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

threading.Thread(target=run_flask, daemon=True).start()

accounts = [{'name': '1', 'session': 'session_name'}, {'name': '2', 'session': 'session_2'}]
processed_ids = set()
gemini_working = True # متغير لمراقبة حالة الذكاء الاصطناعي

# ================== 4. التحليل الذكي مع نظام التنبيه بالأعطال ==================
async def analyze_message(client, text):
    global gemini_working
    if not (5 <= len(text) <= 150): return False
    
    text_lower = text.lower()
    if any(bad in text_lower for bad in FORBIDDEN_WORDS): return False
    if not any(word in text_lower for word in ALL_KEYWORDS): return False

    if ai_model:
        try:
            loop = asyncio.get_event_loop()
            prompt = f"هل هذا طالب يطلب مساعدة دراسية؟ أجب بـ YES أو NO فقط: {text}"
            response = await loop.run_in_executor(None, lambda: ai_model.generate_content(prompt))
            
            if not gemini_working:
                gemini_working = True
                await client.send_message(MY_USER_ID, "✅ **أبشر! عاد نظام Gemini للعمل بنجاح.**")
            
            return "yes" in response.text.lower()
        except Exception as e:
            if gemini_working:
                gemini_working = False
                # إرسال تنبيه لك عند توقف الذكاء الاصطناعي
                await client.send_message(MY_USER_ID, f"⚠️ **تنبيه: توقف Gemini عن العمل مؤقتاً.**\nسيستمر الرادار بالعمل بنظام الكلمات المفتاحية لضمان استمرار الطلبات.")
            return True # العودة التلقائية لنظام الكلمات (Fallback)
    return True

# ================== 5. تشغيل الرصد بالتنسيق المعتمد ==================
async def start_radar(acc):
    client = TelegramClient(acc['session'], API_ID, API_HASH)
    @client.on(events.NewMessage)
    async def handler(event):
        if event.is_private or not event.raw_text: return
        msg_id = f"{event.chat_id}_{event.id}"
        if msg_id in processed_ids: return
        processed_ids.add(msg_id)

        # نمرر الكلاينت للدالة لكي يتمكن من مراسلتك عند العطل
        if await analyze_message(client, event.raw_text):
            sender = await event.get_sender()
            username = getattr(sender, 'username', None)
            user_id = getattr(sender, 'id', 'غير معروف')
            
            buttons = []
            if username:
                buttons.append([Button.url("💬 مراسلة الطالب (خاص)", f"https://t.me/{username}")])

            # التنسيق النظيف الذي اخترته
            clean_msg = (
                f"💗 خدمات طلابيه\n"
                f"⚡️ طلب خدمة طلابية جديد\n"
                f"‏━━━━━━━━━━━━━━━━━━\n"
                f"👤 العميل: @{username if username else 'بدون_يوزر'}\n"
                f"🆔 ID: `{user_id}`\n"
                f"📍 المصدر: {getattr(event.chat, 'title', 'مجموعة')}\n"
                f"🔗 [انتقل للرسالة الأصلية](https://t.me/c/{str(event.chat_id).replace('-100', '')}/{event.id})\n"
                f"‏━━━━━━━━━━━━━━━━━━\n"
                f"📝 نص الطلب:\n"
                f"{event.raw_text}\n"
                f"‏━━━━━━━━━━━━━━━━━━\n"
                f"👇 تواصل مع العميل مباشرة:"
            )

            try:
                await client.send_message(TARGET_CHANNEL, clean_msg, buttons=buttons, link_preview=False)
                await asyncio.sleep(6) # منع الـ FloodWait
            except FloodWaitError as e:
                await asyncio.sleep(e.seconds)
            except: pass

    await client.start()
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(asyncio.gather(*(start_radar(acc) for acc in accounts)))
