# ================== رادار الرصد الذكي لطلبات الطلاب ==================
# ================== النسخة النهائية لـ Render ==================

import os
import sys
import re
import asyncio
import threading
import logging
from datetime import datetime
from collections import deque
from flask import Flask, jsonify
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession

# ================== 1. إعداد التسجيل (Logging) ==================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ================== 2. سيرفر الويب (Flask) ==================
app = Flask(__name__)

@app.route('/')
def home():
    return f"""
    <h1>🎓 رادار الرصد الذكي</h1>
    <p>✅ النظام يعمل على Render!</p>
    <p>🕐 الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <p>📊 الحالة: متصل ويعمل</p>
    """

@app.route('/health')
def health():
    return jsonify(status="healthy", timestamp=datetime.now().isoformat())

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

threading.Thread(target=run_flask, daemon=True).start()
logger.info(f"✅ سيرفر الويب يعمل على المنفذ {os.environ.get('PORT', 10000)}")

# ================== 3. متغيرات البيئة ==================
logger.info("📋 جاري تحميل متغيرات البيئة...")

API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
TARGET_CHANNEL = os.environ.get("TARGET_CHANNEL")

# التحقق من المتغيرات الأساسية
if not API_ID or not API_HASH or not TARGET_CHANNEL:
    logger.error("❌ أحد المتغيرات الأساسية مفقود!")
    logger.error(f"API_ID: {'✅' if API_ID else '❌'}")
    logger.error(f"API_HASH: {'✅' if API_HASH else '❌'}")
    logger.error(f"TARGET_CHANNEL: {'✅' if TARGET_CHANNEL else '❌'}")
    sys.exit(1)

try:
    API_ID = int(API_ID)
except ValueError:
    logger.error(f"❌ API_ID يجب أن يكون رقماً: {API_ID}")
    sys.exit(1)

logger.info("✅ تم تحميل المتغيرات الأساسية بنجاح!")

# الجلسات النصية
SESSION_1 = os.environ.get("SESSION_1")
SESSION_2 = os.environ.get("SESSION_2")

# إعدادات الرصد
SCORE_THRESHOLD = int(os.environ.get("SCORE_THRESHOLD", "4"))
MIN_MESSAGE_LENGTH = int(os.environ.get("MIN_MSG_LENGTH", "5"))
MAX_MESSAGE_LENGTH = int(os.environ.get("MAX_MSG_LENGTH", "70"))

logger.info(f"📋 الإعدادات: عتبة={SCORE_THRESHOLD}, طول={MIN_MESSAGE_LENGTH}-{MAX_MESSAGE_LENGTH}")

# ================== 4. إعداد الحسابات ==================
accounts = []

if SESSION_1 and SESSION_1.strip():
    accounts.append({
        'name': 'رادار [1]',
        'id': API_ID,
        'hash': API_HASH,
        'session': SESSION_1.strip()
    })
    logger.info("✅ الحساب الأول تم تحميله")

if SESSION_2 and SESSION_2.strip():
    accounts.append({
        'name': 'رادار [2]',
        'id': API_ID,
        'hash': API_HASH,
        'session': SESSION_2.strip()
    })
    logger.info("✅ الحساب الثاني تم تحميله")
if not accounts:
    logger.error("❌ لم يتم توفير أي جلسة! أضف SESSION_1 في متغيرات البيئة.")
    sys.exit(1)

logger.info(f"📊 إجمالي الحسابات: {len(accounts)}")

# ================== 5. قوائم الكلمات ==================
request_keywords = {
    'عالي': {
        'مطلوب': 5, 'ابغى': 4, 'ابي': 4, 'احتاج': 4, 'أحتاج': 4, 
        'بحث': 4, 'ابحث': 4, 'دور': 3, 'عندي': 3, 'صعوبة': 3, 'ما فهمت': 3
    },
    'متوسط': {
        'واجب': 3, 'حل': 3, 'مشروع': 3, 'بحث': 3, 'كويز': 3, 'اختبار': 3,
        'تخرج': 3, 'مهندس': 3, 'تصميم': 3, 'برمجة': 3, 'كود': 3, 'ترجمة': 3,
        'خصوصي': 3, 'معلم': 3, 'مدرس': 3, 'مقرر': 3, 'كتاب': 3, 'مرجع': 3,
        'عذر': 3, 'غياب': 3, 'مرضية': 3, 'سكليف': 4, 'تجسير': 4,
        'تأجيل': 3, 'انسحاب': 4, 'استاذ': 2, 'دكتور': 2, 'دروس': 2
    },
    'خفيف': {
        'مين': 1, 'كيف': 1, 'متى': 1, 'وش': 1, 'ايش': 1, 'شنو': 1,
        'تكفون': 1, 'ساعدوني': 1, 'بالله': 1, 'لو سمحتو': 1, 'حد': 1,
        'يعرف': 1, 'يفيد': 1, 'ممكن': 1
    }
}

ad_killers = {
    'للتواصل', 'للتسجيل', 'واتساب', 'واتس', 'تواصل', 'راسلني', 'لبيع', 
    'سعر', 'ريال', 'دولار', 'عرض', 'خصم', 'ضمان', 'استثمار', 'ربح', 
    'تسويق', 'اعلان', 'معلن', 'احجز', 'مقعد', 'سارع', 'محدود',
    'يوجد حل', 'متوفر حل', 'موجود حل', 'نحل', 'نحل الواجب', 'نحل التكليف',
    'نضمن', 'درجة كاملة', 'نجاح مضمون', 'توظيف', 'مطلوب معلمين', 
    'مطلوب مدرسين', 'وظيفة', 'مكتب', 'مجموعة', 'قناة', 'لدينا', 'عندنا',
    'نقدم', 'خدماتنا', 'لشراء', 'للبيع', 'سعر', 'ريال', 'دولار', 'جنيه'
}

inquiry_keywords = {
    'أدوات استفهام': {
        'كيف': 3, 'متى': 3, 'كم': 2, 'أين': 2, 'من': 2, 'هل': 2,
        'وش': 2, 'ايش': 2, 'شنو': 2, 'ليه': 2, 'لماذا': 2, 'مين': 2
    },
    'أفعال استفسار': {
        'يعرف': 3, 'يفيدني': 3, 'تشرح': 3, 'تشرحون': 3, 'تساعد': 3,
        'أفهم': 2, 'أعرف': 2, 'أتأكد': 2, 'استفسر': 3, 'سؤال': 2, 'سؤالي': 2
    },
    'كلمات إجراء أكاديمي': {
        'أسجل': 4, 'التسجيل': 4, 'شعبة': 3, 'جدول': 3, 'موعد': 3,
        'اختبار': 3, 'امتحان': 3, 'نتيجة': 3, 'رصد': 3, 'غياب': 3,
        'عذر': 3, 'انسحاب': 3, 'تأجيل': 3, 'نظام': 2, 'بوابة': 2, 'منصة': 2    }
}

academic_context = [
    'فيزياء', 'كيمياء', 'رياضيات', 'أحياء', 'عربي', 'انجليزي', 'لغة',
    'تاريخ', 'جغرافيا', 'فلسفة', 'منطق', 'إحصاء', 'محاسبة', 'اقتصاد',
    'قانون', 'طب', 'هندسة', 'تقنية', 'برمجة', 'كمبيوتر', 'حاسب',
    'مادة', 'مقرر', 'كتاب', 'مرجع', 'دروس', 'محاضرة', 'محاضرات',
    'واجب', 'تكليف', 'سكليف', 'تجسير', 'دوام', 'تسجيل', 'شعبة', 'جدول',
    'اختبار', 'امتحان', 'نتيجة', 'رصد', 'درجة', 'علامة', 'نسبة', 'معدل',
    'تراكمي', 'فصل', 'ترم', 'سنة', 'سنه', 'جامعة', 'كلية', 'معهد'
]

LINK_PATTERNS = [
    r'https?://\S+', r'www\.\S+', r't\.me/\S+', r'telegram\.me/\S+',
    r'wa\.me/\S+', r'whatsapp\.com/\S+', r'bit\.ly/\S+', r'goo\.gl/\S+',
    r'[a-zA-Z0-9.-]+\.(com|net|org|info|biz|me|io|co|sa|ae|eg)\S*',
    r'\.[a-zA-Z]{2,}(/\S*)?', r'\S+@\S+\.\S+',
]

PHONE_PATTERNS = [
    r'\+?\d{1,3}[\s\-]?\(?\d{1,4}\)?[\s\-]?\d{3,4}[\s\-]?\d{3,4}',
    r'05\d{8}', r'00966\d{9}', r'\+966\d{9}', r'01\d{8}',
    r'0020\d{9}', r'\+20\d{9}', r'07\d{8}', r'00964\d{9}',
    r'\+964\d{9}', r'\d{10,15}',
]

CONTACT_WORDS = [
    'تواصل', 'للتواصل', 'راسلني', 'واتساب', 'واتس', 'wb',
    'سناب', 'انستقرام', 'انستا', 'تويتر', 'فيسبوك',
    'ايميل', 'بريد', 'email', 'call', 'رقم', 'جوال', 'موبايل',
    'للتحميل', 'للتسجيل', 'اضغط هنا', 'link', 'رابط'
]

# ================== 6. منع التكرار ==================
MAX_SENT_IDS = 10000
sent_messages = deque(maxlen=MAX_SENT_IDS)

def is_duplicate(chat_id, message_id):
    key = f"{chat_id}:{message_id}"
    if key in sent_messages:
        return True
    sent_messages.append(key)
    return False

# ================== 7. دوال المعالجة النصية ==================
def normalize_arabic(text):
    text = re.sub(r'[إأآا]', 'ا', text)
    text = re.sub(r'[ةه]', 'ه', text)
    text = re.sub(r'[ىي]', 'ي', text)   
    text = re.sub(r'[\u064B-\u065F\u0670]', '', text)
    return text.strip().lower()

def contains_link(text):
    text_lower = text.lower()
    for pattern in LINK_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    for word in CONTACT_WORDS:
        if word in text_lower:
            return True
    return False

def contains_phone(text):
    cleaned = re.sub(r'[^\d]', '', text)
    return len(cleaned) >= 10

# ================== 8. نظام التحليل والفرز ==================
def calculate_score(text):
    text_norm = normalize_arabic(text)
    words_set = set(text_norm.split())
    
    score = 0
    matched = []
    classification = "غير_مصنف"
    
    # فحص الإعلانات
    for ad_word in ad_killers:
        if ad_word in text_norm:
            return -100, "إعلان", [f"🚫{ad_word}"]
    
    # فحص الاستفسارات
    inquiry_score = 0
    for word in words_set:
        for k, v in inquiry_keywords['أدوات استفهام'].items():
            if word == k:
                inquiry_score += v
                matched.append(f"❓{k}")
                break
    
    for k, v in inquiry_keywords['أفعال استفسار'].items():
        if k in text_norm:
            inquiry_score += v
            matched.append(f"💡{k}")
            break
    
    for k, v in inquiry_keywords['كلمات إجراء أكاديمي'].items():
        if k in text_norm:
            inquiry_score += v
            matched.append(f"📋{k}")
            break
    
    if inquiry_score > 0:
        has_context = any(ctx in text_norm for ctx in academic_context)
        if has_context:
            score += inquiry_score + 2
            classification = "استفسار_أكاديمي"
        else:
            score += inquiry_score
            classification = "استفسار_عام"
    
    # فحص الطلبات
    for word in words_set:
        for level, keywords in request_keywords.items():
            if word in keywords:
                score += keywords[word]
                matched.append(f"🎯{word}")
                if classification == "غير_مصنف":
                    classification = "طلب_مباشر"
                break
    
    # تعزيز السياق
    if any(ctx in text_norm for ctx in academic_context):
        score += 2
        if not any("سياق" in m for m in matched):
            matched.append("[سياق]")
    
    # طلب + استفسار
    if score > 3 and inquiry_score > 0:
        score += 3
        matched.append("✅مؤكد")
        classification = "طلب_مؤكّد"
    
    # تعديلات إضافية
    if 15 <= len(text_norm) <= 70:
        score += 1
    if text.endswith('?') or text.endswith('؟'):
        score += 1
    if len(text_norm) < 8:
        score -= 2
    
    return score, classification, matched

# ================== 9. تنسيق الرسالة ==================
def format_message(event, sender, chat, radar_name, score, classification, matched, text):
    username = getattr(sender, 'username', None)
    first_name = getattr(sender, 'first_name', 'مستخدم')
    user_id = sender.id
    chat_title = getattr(chat, 'title', 'مجموعة')
    cid = str(chat.id)
    if cid.startswith('-100'):
        link = f"https://t.me/c/{cid[4:]}/{event.id}"
    else:
        link = f"https://t.me/c/{abs(chat.id)}/{event.id}"
    
    display_text = text[:150] + "..." if len(text) > 150 else text
    
    msg = (
        f"⚡️ **طلب جديد** | {radar_name}\n"
        f"🕐 `{datetime.now().strftime('%H:%M')}`\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"👤 **من:** {first_name} (`{user_id}`)\n"
        f"🔖 **يوزر:** @{username or 'بدون'}\n"
        f"📍 **في:** {chat_title}\n"
        f"🔗 [الرسالة]({link})\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📝 **النص:**\n_{display_text}_\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📊 **التحليل:** {classification} | نقاط: {score}\n"
        f"🔍 **الكلمات:** {', '.join(matched[:5])}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"👇 **إجراءات:**"
    )
    
    buttons = []
    if username:
        buttons.append([Button.url("💬 مراسلة", f"t.me/{username}")])
    buttons.append([Button.url("🔗 الانتقال", link)])
    
    return msg, buttons

# ================== 10. دالة الرصد الرئيسية ==================
async def start_monitoring(acc_info):
    client = TelegramClient(
        StringSession(acc_info['session']),
        acc_info['id'],
        acc_info['hash'],
        auto_reconnect=True,
        connection_retries=5
    )
    radar_name = acc_info['name']
    
    @client.on(events.NewMessage)
    async def handler(event):
        try:
            if event.is_private:
                return
            if is_duplicate(event.chat_id, event.id):
                return            
            text = event.raw_text.strip()
            if not text:
                return
            
            text_len = len(text)
            if text_len < MIN_MESSAGE_LENGTH or text_len > MAX_MESSAGE_LENGTH:
                return
            
            if contains_link(text) or contains_phone(text):
                return
            
            score, classification, matched = calculate_score(text)
            is_academic = any(ctx in normalize_arabic(text) for ctx in academic_context)
            
            should_forward = (
                score >= SCORE_THRESHOLD or
                (classification == "استفسار_أكاديمي" and score >= 3) or
                classification == "طلب_مؤكّد" or
                (classification.startswith("استفسار") and is_academic and score >= 4)
            )
            
            if not should_forward:
                return
            
            sender = await event.get_sender()
            chat = await event.get_chat()
            
            msg, buttons = format_message(
                event, sender, chat, radar_name,
                score, classification, matched, text
            )
            
            await client.send_message(TARGET_CHANNEL, msg, buttons=buttons, silent=False)
            logger.info(f"✅ [{radar_name}] {classification} ({score})")
            
        except Exception as e:
            logger.error(f"❌ [{radar_name}] خطأ: {e}")
    
    while True:
        try:
            await client.start()
            logger.info(f"✅ {radar_name} متصل!")
            await client.run_until_disconnected()
        except Exception as e:
            logger.error(f"⚠️ {radar_name} انقطع: {e}")
            await asyncio.sleep(5)
        finally:
            if client.is_connected():
                await client.disconnect()
# ================== 11. التشغيل الرئيسي ==================
async def main():
    logger.info("🚀 بدء رادار الرصد على Render...")
    logger.info(f"📊 الحسابات: {len(accounts)} | القناة: {TARGET_CHANNEL}")
    
    tasks = [start_monitoring(acc) for acc in accounts]
    await asyncio.gather(*tasks, return_exceptions=True)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 إيقاف يدوي")
    except Exception as e:
        logger.error(f"💥 خطأ فادح: {e}")
        import traceback
        traceback.print_exc()
