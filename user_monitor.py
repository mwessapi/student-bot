import os
import asyncio
import threading
import logging
import re
from flask import Flask
from telethon import TelegramClient, events, Button

# ================== إعداد التسجيل (Logging) ==================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ================== سيرفر الويب ==================
app = Flask(__name__)

@app.route('/')
def home():
    return "رادار الرصد الذكي (حسابين) يعمل بنجاح!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_flask, daemon=True).start()

# ================== متغيرات البيئة (آمنة) ==================
API_ID = int(os.environ.get("API_ID", 2040))
API_HASH = os.environ.get("API_HASH", "b18441a1ff607e10a989891a5462e627")
TARGET_CHANNEL = os.environ.get("TARGET_CHANNEL", "student1_admin")  # يفضل استخدام ID

# ================== الحسابات (يمكن جعل الجلسات من env أيضاً) ==================
accounts = [
    {'name': 'رادار [1]', 'id': API_ID, 'hash': API_HASH, 'session': 'session_name'},
    {'name': 'رادار [2]', 'id': API_ID, 'hash': API_HASH, 'session': 'session_2'}
]

# ================== قوائم الكلمات المحسّنة ==================
# قائمة موسعة للكلمات المطلوبة (حساسية عالية)
all_keywords = [
    'حد', 'مين', 'كيف', 'متى', 'سؤال', 'استفسار', 'يعرف', 'يفيدني', 'احتاج', 'ممكن',
    'أبغى', 'ابي', 'وش', 'ايش', 'شنو', 'تكفون', 'ساعدوني', 'بالله', 'لو سمحتو',
    'واجب', 'حل', 'كويز', 'اختبار', 'مشروع', 'بحث', 'تخرج', 'مهندس', 'تصميم', 'برمجة',
    'كود', 'إحصاء', 'رياضيات', 'فيزياء', 'كيمياء', 'ترجمة', 'محاسبة', 'اقتصاد', 'ميد', 'فاينل',
    'عذر', 'غياب', 'سكليف', 'مرضية', 'تجسير', 'دوام', 'تدريب', 'صيفي', 'مادة', 'دكتور',
    'شرح', 'ملخص', 'مذكرة', 'كتاب', 'مرجع', 'تمارين', 'نموذج', 'سابق', 'قديم', 'جديد',
    'مساعدة', 'عاجل', 'ضروري', 'بسرعة', 'الله يجزاك خير', 'تكفى', 'يا جماعة', 'شباب'
]

# كلمات إعلانية للإقصاء (يمكن تقليل حدتها إن أردت)
forbidden_words = [
    'تواصل', 'واتساب', 'واتس', 'للتواصل', 'ارباح', 'استثمار', 'ضمان', 'سعرنا',
    'راسلني خاص', 'راسلني', 'درجة كاملة', 'درجة كامله', 'جميع القطاعات', 'فحص دوري',
    'تأشيرات', 'موجود حل', 'يوجد حل', 'متوفر حل', 'أبشر بالخير', 'عقد ايجار', 'كشف طبي'
]

# ================== قائمة سوداء للمجموعات ==================
# ضع معرفات المجموعات التي تريد تجاهلها (تعبئة يدوية)
BLACKLIST_GROUPS = []  # مثال: [-1001234567890, -1009876543210]

# ================== دوال مساعدة للفلترة الذكية ==================
def normalize_arabic(text):
    """توحيد الحروف العربية وإزالة التشكيل"""
    text = re.sub(r'[إأآ]', 'ا', text)
    text = re.sub(r'[ة]', 'ه', text)
    text = re.sub(r'[ًٌٍَُِّْ]', '', text)  # إزالة التشكيل
    return text

def contains_question_pattern(text):
    """الكشف عن صيغ الأسئلة باستخدام regex"""
    patterns = [
        r'(هل|ما|من|متى|أين|كيف|لماذا|كم)\s+\S+',
        r'(مين|وش|ايش|شنو)\s+\S+',
        r'(\S+\s+)?(يعرف|يفيدني|يشرح)\s+\S+',
        r'(تكفون|ساعدوني|بالله|لو سمحتو)'
    ]
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

def is_potential_request(text):
    """تقرير ما إذا كانت الرسالة تستحق الإرسال (حساسية عالية)"""
    if not text or len(text) < 3:
        return False
    text_norm = normalize_arabic(text.lower())
    
    # إذا احتوت على كلمة من قائمة الطلبات -> فوراً تعتبر طلباً
    if any(word in text_norm for word in all_keywords):
        return True
    
    # إذا كانت سؤالاً واضحاً -> تعتبر طلباً
    if contains_question_pattern(text):
        return True
    
    # إذا كان النص قصيراً جداً ولكن يحتمل (مثل "حد" أو "؟") -> نرسله على سبيل الاحتياط
    if len(text) <= 10 and ('?' in text or '؟' in text):
        return True
    
    return False

def is_advertisement(text):
    """الكشف عن الإعلانات (يمكن تخفيفها لعدم فقدان الطلبات)"""
    text_lower = text.lower()
    # إذا احتوى على كلمات إعلانية قوية فقط نعتبره إعلاناً
    strong_ads = ['تواصل', 'واتساب', 'درجة كاملة', 'عرض خاص']
    if any(ad in text_lower for ad in strong_ads):
        return True
    # إذا احتوى على رابط مشبوه (روابط واتساب أو روابط دعوات)
    if 'wa.me' in text_lower or 't.me/+' in text_lower:
        return True
    return False

# ================== دالة الرصد الرئيسية مع تحسينات ==================
async def start_monitoring(acc_info):
    client = TelegramClient(acc_info['session'], acc_info['id'], acc_info['hash'])
    radar_name = acc_info['name']

    @client.on(events.NewMessage)
    async def handler(event):
        try:
            if event.is_private:
                return

            chat = await event.get_chat()
            # تجاهل المجموعات السوداء
            if BLACKLIST_GROUPS and chat.id in BLACKLIST_GROUPS:
                return

            text = event.raw_text.strip()
            if not text:
                return

            # فلتر الإعلانات القوية (مع الاحتفاظ بالطلبات المحتملة)
            if is_advertisement(text):
                return

            # التحقق من أن الرسالة تستحق الرصد
            if not is_potential_request(text):
                return

            # اقتطاع النص الطويل جداً
            display_text = text if len(text) <= 300 else text[:300] + "..."

            sender = await event.get_sender()
            username = getattr(sender, 'username', None)
            user_display = f"@{username}" if username else "بدون يوزر"
            first_name = getattr(sender, 'first_name', 'مستخدم')
            chat_title = getattr(chat, 'title', 'مجموعة')

            # تنسيق الرسالة مع شريط جميل
            display_message = (
                f"⚡️ **رصد جديد عبر {radar_name}**\n"
                f"‏━━━━━━━━━━━━━━━━━━\n"
                f"👤 **العميل:** {first_name} ( {user_display} )\n"
                f"🆔 **ID:** `{sender.id}`\n"
                f"📍 **المصدر:** `{chat_title}`\n"
                f"🔗 [انتقل للرسالة الأصلية](https://t.me/c/{chat.id}/{event.id})\n"
                f"‏━━━━━━━━━━━━━━━━━━\n"
                f"📝 **النص المرصود:**\n"
                f"_{display_text}_\n"
                f"‏━━━━━━━━━━━━━━━━━━\n"
                f"👇 **تواصل مع العميل مباشرة:**"
            )

            buttons_list = []
            if username:
                buttons_list.append([Button.url("💬 مراسلة خاصة", f"https://t.me/{username}")])
            buttons_list.append([Button.url("⤴️ الرد في المجموعة", f"https://t.me/c/{chat.id}/{event.id}")])

            await client.send_message(TARGET_CHANNEL, display_message, buttons=buttons_list, silent=False)

        except Exception as e:
            logger.error(f"خطأ في {radar_name}: {e}")

    # بدء العميل مع إعادة اتصال تلقائية
    while True:
        try:
            await client.start()
            logger.info(f"✅ {radar_name} بدأ العمل...")
            await client.run_until_disconnected()
        except Exception as e:
            logger.error(f"❗ {radar_name} انقطع: {e}. إعادة المحاولة بعد 5 ثوان...")
            await asyncio.sleep(5)
        finally:
            await client.disconnect()

# ================== التشغيل الرئيسي ==================
async def main():
    tasks = [start_monitoring(acc) for acc in accounts]
    # تجميع المهام مع الاستمرار حتى لو فشل أحدها
    await asyncio.gather(*tasks, return_exceptions=True)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("تم إيقاف البوت يدوياً.")
