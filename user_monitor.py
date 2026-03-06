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

# ================== 2. القائمة الشاملة للكلمات والاستفسارات ==================
ALL_KEYWORDS = [
    # طلبات عامة واستفسارات
    'حد', 'مين', 'كيف', 'متى', 'سؤال', 'استفسار', 'يعرف', 'يفيدني', 'احتاج', 'ممكن',
    'أبغى', 'ابي', 'وش', 'ايش', 'شنو', 'تكفون', 'ساعدوني', 'بالله', 'لو سمحتو',
    'تكفى', 'يا جماعة', 'شباب', 'يا عيال', 'مين يقدر', 'مساعدة', 'عاجل', 'ضروري',
    
    # كلمات دراسية وأكاديمية
    'واجب', 'حل', 'كويز', 'اختبار', 'مشروع', 'بحث', 'تخرج', 'ميد', 'فاينل', 'تقرير',
    'تلخيص', 'شرح', 'مادة', 'دكتور', 'استاذ', 'محاضرة', 'جامعة', 'كلية', 'تخصص',
    'سلايدات', 'ملخص', 'نماذج', 'اسئلة', 'مراجعة', 'مذاكرة', 'تاسك', 'هومورك',
    
    # كلمات تقنية وبرمجية (تخصصك IT)
    'برمجة', 'تصميم', 'كود', 'إحصاء', 'رياضيات', 'فيزياء', 'كيمياء', 'ترجمة', 'محاسبة',
    'اقتصاد', 'هندسة', 'سي شارب', 'C#', 'داتابيز', 'SQL', 'شبكات', 'باكيت تريسر', 
    'Packet Tracer', 'بايثون', 'عرض', 'بوربوينت', 'لوغو', 'هوية بصرية', 'فوتوشوب',
    'اندرويد', 'تطبيق', 'موقع', 'سيرفر', 'فرونت', 'باك'
]

FORBIDDEN_WORDS = ['تواصل', 'واتساب', 'ارباح', 'استثمار', 'ضمان', 'فحص دوري', 'تأشيرات']

# ================== 3. الإعدادات الأساسية ==================
API_ID = 2040 
API_HASH = "b18441a1ff607e10a989891a5462e627"
TARGET_CHANNEL = "student1_admin"
MY_USER_ID = 6190186046 

app = Flask(__name__)
@app.route('/')
def home(): return "Full-Radar is Online"

# ================== 4. التحليل الذكي مع نظام Fallback ==================
async def analyze_message(client, text):
    if not (5 <= len(text) <= 150): return False
    text_lower = text.lower()
    
    # استبعاد الإعلانات
    if any(bad in text_lower for bad in FORBIDDEN_WORDS): return False
    
    # البحث عن أي كلمة من القائمة الشاملة
    if not any(word in text_lower for word in ALL_KEYWORDS): return False

    # التحقق عبر Gemini لضمان أنه "طلب" وليس "دردشة"
    if ai_model:
        try:
            loop = asyncio.get_event_loop()
            prompt = f"أجب بـ YES فقط إذا كان النص هو طالب يطلب مساعدة في دراسة أو مشروع، وإلا NO: {text}"
            response = await loop.run_in_executor(None, lambda: ai_model.generate_content(prompt))
            return "yes" in response.text.lower()
        except:
            return True # إذا تعطل Gemini، نعتمد على الكلمات
    return True

# ================== 5. نظام التشغيل المستقر ==================
async def start_radar(acc):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(acc['session'], API_ID, API_HASH, loop=loop)
    
    @client.on(events.NewMessage)
    async def handler(event):
        if event.is_private or not event.raw_text: return
        if await analyze_message(client, event.raw_text):
            sender = await event.get_sender()
            username = getattr(sender, 'username', None)
            user_id = getattr(sender, 'id', 'غير معروف')
            
            buttons = [[Button.url("💬 مراسلة الطالب (خاص)", f"https://t.me/{username}")]] if username else []
            
            clean_msg = (
                f"💗 خدمات طلابيه\n⚡️ طلب خدمة طلابية جديد\n━━━━━━━━━━━━━━━━━━\n"
                f"👤 العميل: @{username if username else 'بدون_يوزر'}\n🆔 ID: `{user_id}`\n"
                f"📍 المصدر: {getattr(event.chat, 'title', 'مجموعة')}\n"
                f"🔗 [انتقل للرسالة الأصلية](https://t.me/c/{str(event.chat_id).replace('-100', '')}/{event.id})\n"
                f"━━━━━━━━━━━━━━━━━━\n📝 نص الطلب:\n{event.raw_text}\n━━━━━━━━━━━━━━━━━━\n👇 تواصل مع العميل مباشرة:"
            )
            try:
                await client.send_message(TARGET_CHANNEL, clean_msg, buttons=buttons, link_preview=False)
                await asyncio.sleep(6) # تأخير لمنع الحظر
            except: pass

    await client.start()
    await client.run_until_disconnected()

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    accounts = [{'session': 'session_name'}, {'session': 'session_2'}]
    for acc in accounts:
        threading.Thread(target=lambda: asyncio.run(start_radar(acc)), daemon=True).start()
    
    while True:
        import time
        time.sleep(10)
