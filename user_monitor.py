import os
import asyncio
import threading
import google.generativeai as genai
from flask import Flask
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError

# ================== إعدادات Gemini والكلمات ==================
GEMINI_KEY = "AIzaSyDenjy_-AcZAYpBQWpFGAbqgMoS6UiPPnA" 
genai.configure(api_key=GEMINI_KEY)
ai_model = genai.GenerativeModel('gemini-1.5-flash')

# --- 1. القائمة الشاملة للكلمات المطلوبة (المأخوذة من كودك السابق) ---
ALL_KEYWORDS = [
    'حد', 'مين', 'كيف', 'متى', 'سؤال', 'استفسار', 'يعرف', 'يفيدني', 'احتاج', 'ممكن',
    'أبغى', 'ابي', 'وش', 'ايش', 'شنو', 'تكفون', 'ساعدوني', 'بالله', 'لو سمحتو',
    'واجب', 'حل', 'كويز', 'اختبار', 'مشروع', 'بحث', 'تخرج', 'مهندس', 'تصميم', 'برمجة',
    'كود', 'إحصاء', 'رياضيات', 'فيزياء', 'كيمياء', 'ترجمة', 'محاسبة', 'اقتصاد', 'ميد', 'فاينل',
    'عذر', 'غياب', 'سكليف', 'مرضية', 'تجسير', 'دوام', 'تدريب', 'صيفي', 'مادة', 'دكتور',
    'شرح', 'ملخص', 'مساعدة', 'عاجل', 'ضروري', 'تكفى', 'يا جماعة', 'شباب', 'جامعة'
]

# --- 2. القائمة السوداء (التي يتجاهلها البوت تماماً) ---
FORBIDDEN_WORDS = [
    'تواصل', 'واتساب', 'واتس', 'للتواصل', 'ارباح', 'استثمار', 'ضمان', 'سعرنا',
    'راسلني خاص', 'درجة كاملة', 'جميع القطاعات', 'فحص دوري',
    'تأشيرات', 'موجود حل', 'يوجد حل', 'متوفر حل', 'عقد ايجار', 'كشف طبي',
    'نقل كفالة', 'تجديد اقامة', 'منصة قوى', 'تسجيل في حافز'
]

# ================== الإعدادات الأساسية ==================
API_ID = 2040 
API_HASH = "b18441a1ff607e10a989891a5462e627"
TARGET_CHANNEL = "student1_admin"
MY_USER_ID = 6190186046 

app = Flask(__name__)
@app.route('/')
def home(): return "الرادار الشامل (Gemini + All Keywords) يعمل!"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

threading.Thread(target=run_flask, daemon=True).start()

accounts = [
    {'name': 'رادار [1]', 'session': 'session_name'},
    {'name': 'رادار [2]', 'session': 'session_2'}
]

processed_ids = set()
gemini_working = True 

# ================== دالة التحليل الذكية ==================
async def analyze_message(client, text):
    global gemini_working
    
    # أ. شرط الطول (5-150 حرف)
    if not (5 <= len(text) <= 150):
        return False
        
    text_lower = text.lower()

    # ب. الفلترة المسبقة (تجاهل الكلمات الممنوعة فوراً)
    if any(forbidden in text_lower for forbidden in FORBIDDEN_WORDS):
        return False

    # ج. التأكد من وجود إحدى الكلمات المطلوبة
    if not any(keyword in text_lower for keyword in ALL_KEYWORDS):
        return False

    # د. محاولة استخدام Gemini للتحليل النهائي
    try:
        loop = asyncio.get_event_loop()
        prompt = (
            "أنت خبير تصنيف. حلل النص بعناية:\n"
            f"النص: '{text}'\n"
            "القواعد:\n"
            "1. أجب 'YES' إذا كان الشخص (طالب) يطلب مساعدة دراسية.\n"
            "2. أجب 'NO' إذا كان النص إعلان لشخص يقدم حلولاً أو دردشة عادية.\n"
            "أجب بكلمة واحدة فقط: YES أو NO."
        )
        response = await loop.run_in_executor(None, lambda: ai_model.generate_content(prompt))
        
        if not gemini_working:
            gemini_working = True
            await client.send_message(MY_USER_ID, "✅ Gemini عاد للعمل!")
            
        return "yes" in response.text.lower()
        
    except Exception:
        if gemini_working:
            gemini_working = False
            await client.send_message(MY_USER_ID, "⚠️ تعطل Gemini! الرادار يعمل بالكلمات فقط.")
        # في حال تعطل الذكاء الاصطناعي، نعتمد على الكلمات المفتاحية التي وجدناها في الخطوة (ج)
        return True

# ================== تشغيل الرصد ==================
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

            status = "🤖 Gemini" if gemini_working else "📡 كلمات"
            msg = (
                f"⚡️ **رصد نشط عبر {status}**\n"
                f"👤 **العميل:** {getattr(sender, 'first_name', 'مستخدم')}\n"
                f"📍 **المصدر:** `{getattr(event.chat, 'title', 'مجموعة')}`\n"
                f"‏━━━━━━━━━━━━━━━━━━\n"
                f"📝 **الطلب:**\n_{event.raw_text}_\n"
                f"‏━━━━━━━━━━━━━━━━━━\n"
                f"📏 **الطول:** {len(event.raw_text)} حرف"
            )
            
            try:
                await client.send_message(TARGET_CHANNEL, msg, buttons=buttons)
                await asyncio.sleep(4) 
            except FloodWaitError as e:
                await asyncio.sleep(e.seconds)
            except: pass

    await client.start()
    await client.run_until_disconnected()

async def main():
    await asyncio.gather(*(start_radar(acc) for acc in accounts))

if __name__ == '__main__':
    asyncio.run(main())
