import os
import asyncio
import threading
import google.generativeai as genai
from flask import Flask
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError

# ================== 1. إعدادات الحماية والذكاء ==================
# سحب المفتاح سرياً من Render لحمايتك من الحظر
GEMINI_KEY = os.environ.get("GEMINI_KEY")
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    ai_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    ai_model = None

# ================== 2. قاعدة بيانات الكلمات الشاملة ==================

# كلمات البحث (المطلوبة) - تشمل كل ما يحتاجه الطلاب
ALL_KEYWORDS = [
    # كلمات عامية وطلبات مساعدة
    'حد', 'مين', 'كيف', 'متى', 'سؤال', 'استفسار', 'يعرف', 'يفيدني', 'احتاج', 'ممكن',
    'أبغى', 'ابي', 'وش', 'ايش', 'شنو', 'تكفون', 'ساعدوني', 'بالله', 'لو سمحتو',
    'تكفى', 'يا جماعة', 'شباب', 'يا عيال', 'مين يقدر', 'مساعدة', 'عاجل', 'ضروري',
    
    # كلمات دراسية وأكاديمية
    'واجب', 'حل', 'كويز', 'اختبار', 'مشروع', 'بحث', 'تخرج', 'ميد', 'فاينل', 'تقرير',
    'تلخيص', 'شرح', 'مادة', 'دكتور', 'استاذ', 'محاضرة', 'جامعة', 'كلية', 'تخصص',
    
    # كلمات تقنية (تخصصك)
    'برمجة', 'تصميم', 'كود', 'إحصاء', 'رياضيات', 'فيزياء', 'كيمياء', 'ترجمة', 'محاسبة',
    'اقتصاد', 'هندسة', 'سي شارب', 'داتابيز', 'شبكات', 'باكيت تريسر', 'بايثون', 'عرض', 'بوربوينت'
]

# كلمات الإقصاء (الممنوعة) - لتنظيف القناة من الإعلانات
FORBIDDEN_WORDS = [
    'تواصل', 'واتساب', 'واتس', 'للتواصل', 'ارباح', 'استثمار', 'ضمان', 'سعرنا',
    'راسلني خاص', 'درجة كاملة', 'جميع القطاعات', 'فحص دوري', 'تأشيرات', 
    'موجود حل', 'يوجد حل', 'متوفر حل', 'عقد ايجار', 'كشف طبي', 'قوى', 'حافز'
]

# ================== 3. الإعدادات الأساسية ==================
API_ID = 2040 
API_HASH = "b18441a1ff607e10a989891a5462e627"
TARGET_CHANNEL = "student1_admin"
MY_USER_ID = 6190186046 

app = Flask(__name__)
@app.route('/')
def home(): return "الرادار الشامل (Gemini + All Keywords) يعمل بنجاح!"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

threading.Thread(target=run_flask, daemon=True).start()

accounts = [
    {'name': 'رادار [1]', 'session': 'session_name'},
    {'name': 'رادار [2]', 'session': 'session_2'}
]

processed_ids = set()
gemini_working = True 

# ================== 4. منطق التحليل الذكي ==================
async def analyze_message(client, text):
    global gemini_working
    
    # أ. شرط الطول (5-150 حرف)
    if not (5 <= len(text) <= 150):
        return False
        
    text_lower = text.lower()

    # ب. فلترة الإعلانات الممنوعة
    if any(forbidden in text_lower for forbidden in FORBIDDEN_WORDS):
        return False

    # ج. التأكد من وجود كلمة مفتاحية واحدة على الأقل
    if not any(keyword in text_lower for keyword in ALL_KEYWORDS):
        return False

    # د. التحقق عبر Gemini (إذا كان متاحاً)
    if ai_model:
        try:
            loop = asyncio.get_event_loop()
            prompt = (
                "أنت خبير تصنيف. أجب بـ YES فقط إذا كان النص هو طالب يطلب مساعدة دراسية.\n"
                "أجب بـ NO إذا كان النص إعلان لشخص يقدم حلولاً أو مجرد دردشة.\n"
                f"النص: '{text}'"
            )
            response = await loop.run_in_executor(None, lambda: ai_model.generate_content(prompt))
            
            if not gemini_working:
                gemini_working = True
                await client.send_message(MY_USER_ID, "✅ تم استعادة اتصال Gemini بأمان!")
                
            return "yes" in response.text.lower()
            
        except Exception:
            if gemini_working:
                gemini_working = False
                await client.send_message(MY_USER_ID, "⚠️ تعطل Gemini! الرادار يعمل بالكلمات حالياً.")
            return True # الاستمرار بنظام الكلمات عند تعطل الذكاء
    
    return True

# ================== 5. تشغيل الرصد ==================
async def start_radar(acc):
    client = TelegramClient(acc['session'], API_ID, API_HASH)
    
    @client.on(events.NewMessage)
    async def handler(event):
        if event.is_private or not event.raw_text: return
        
        msg_id = f"{event.chat_id}_{event.id}"
        if msg_id in processed_ids: return
        processed_ids.add(msg_id)

        if await analyze_message(client, event.raw_text):
            sender = await event.get_sender()
            username = getattr(sender, 'username', None)
            
            buttons = []
            if username:
                buttons.append([Button.url("💬 مراسلة خاصة", f"https://t.me/{username}")])
            buttons.append([Button.url("⤴️ الرد في المجموعة", f"https://t.me/c/{event.chat_id}/{event.id}")])

            tag = "🤖 Gemini" if gemini_working else "📡 كلمات"
            msg = (
                f"✅ **رصد جديد عبر {tag}**\n"
                f"👤 **العميل:** {getattr(sender, 'first_name', 'مستخدم')}\n"
                f"📍 **المصدر:** `{getattr(event.chat, 'title', 'مجموعة')}`\n"
                f"‏━━━━━━━━━━━━━━━━━━\n"
                f"📝 **الطلب:**\n_{event.raw_text}_\n"
                f"‏━━━━━━━━━━━━━━━━━━\n"
                f"📏 **الطول:** {len(event.raw_text)} حرف"
            )
            
            try:
                await client.send_message(TARGET_CHANNEL, msg, buttons=buttons)
                # زيادة التأخير لتجنب الحظر (FloodWait)
                await asyncio.sleep(6) 
            except FloodWaitError as e:
                await asyncio.sleep(e.seconds)
            except: pass

    await client.start()
    await client.run_until_disconnected()

async def main():
    await asyncio.gather(*(start_radar(acc) for acc in accounts))

if __name__ == '__main__':
    asyncio.run(main())

