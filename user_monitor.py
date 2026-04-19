#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎓 رادار الخدمات الطلابية أونلاين - النسخة النهائية المُحسَّنة للسعودية
الوظيفة: رصد أي طلب طالب لخدمة تُنفَّذ عن بُعد (عروض، واجبات، أعذار طبية، برمجة، إكسل)
المطور: [اسمك]
التاريخ: 2026
الوصف: بوت يراقب مجموعات تيليجرام سعودية، يلتقط فقط رسائل طلب الخدمة (وليس الاستفسارات العامة).
"""

# ================== 1. استيراد المكتبات ==================
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

# ================== 2. إعداد التسجيل (Logging) ==================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ================== 3. سيرفر الويب (Flask) للبقاء متصلًا ==================
app = Flask(__name__)

@app.route('/')
def home():
    return f"""
    <h1>🎓 رادار الخدمات الطلابية أونلاين</h1>
    <p>✅ النظام يعمل بنجاح!</p>
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

# ================== 4. تحميل متغيرات البيئة ==================
logger.info("📋 جاري تحميل متغيرات البيئة...")

API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
TARGET_CHANNEL = os.environ.get("TARGET_CHANNEL")

if not all([API_ID, API_HASH, TARGET_CHANNEL]):
    logger.error("❌ خطأ: أحد المتغيرات الأساسية مفقود!")
    logger.error(f"   API_ID: {'✅' if API_ID else '❌ مفقود'}")
    logger.error(f"   API_HASH: {'✅' if API_HASH else '❌ مفقود'}")
    logger.error(f"   TARGET_CHANNEL: {'✅' if TARGET_CHANNEL else '❌ مفقود'}")
    sys.exit(1)

try:
    API_ID = int(API_ID)
except ValueError:
    logger.error(f"❌ خطأ: API_ID يجب أن يكون رقماً صحيحاً، القيمة الحالية: {API_ID}")
    sys.exit(1)

logger.info("✅ تم تحميل المتغيرات الأساسية بنجاح")

# جلسات الحسابات
SESSION_1 = os.environ.get("SESSION_1", "").strip()
SESSION_2 = os.environ.get("SESSION_2", "").strip()

# ================== 5. إعدادات التصفية ==================
MIN_MSG_LENGTH = int(os.environ.get("MIN_MSG_LENGTH", "10"))
MAX_MSG_LENGTH = int(os.environ.get("MAX_MSG_LENGTH", "500"))

# ================== 6. إعداد حسابات التليجرام ==================
accounts = []

if SESSION_1:
    accounts.append({
        'name': 'رادار-1',
        'api_id': API_ID,
        'api_hash': API_HASH,
        'session': SESSION_1
    })
    logger.info("✅ الحساب الأول [رادار-1] تم تحميله")

if SESSION_2:
    accounts.append({
        'name': 'رادار-2',
        'api_id': API_ID,
        'api_hash': API_HASH,
        'session': SESSION_2
    })
    logger.info("✅ الحساب الثاني [رادار-2] تم تحميله")

if not accounts:
    logger.error("❌ خطأ: لم يتم توفير أي جلسة! أضف SESSION_1 في متغيرات البيئة")
    sys.exit(1)

logger.info(f"📊 إجمالي الحسابات النشطة: {len(accounts)}")

# ================== 7. إعدادات خاصة ==================
SPECIAL_CHANNEL_ID = int(os.environ.get("SPECIAL_CHANNEL_ID", "-1"))
INVITE_LINKS = {}
DEFAULT_INVITE_LINK = os.environ.get("DEFAULT_INVITE_LINK", "")

# ================== 8. ⭐ أنماط نية طلب التنفيذ (اللهجة السعودية) ⭐ ==================
EXECUTION_PATTERNS = [
    r'أبي\s+حد\s+(يسوي|يكمل|ينفذ|يعمل|يجهز|يخلص|يرسل)',
    r'ابي\s+حد\s+(يسوي|يكمل|ينفذ|يعمل|يجهز|يخلص|يرسل)',
    r'أبغى\s+حد\s+(يسوي|يكمل|ينفذ|يعمل|يجهز|يخلص)',
    r'ابغى\s+حد\s+(يسوي|يكمل|ينفذ|يعمل|يجهز|يخلص)',
    r'محتاج\s+(حد|شخص|واحد|أحد)\s+(يسوي|يكمل|ينفذ|يعمل|يجهز)',
    r'مطلوب\s+(حد|شخص|خدمة)\s+(لتنفيذ|ليسوي|ليكمل|لينجز)',
    r'حد\s+(يسوي|يكمل|ينفذ|يعمل|يجهز)\s+لي',
    r'واحد\s+(يسوي|يكمل|ينفذ|يعمل)\s+لي',
    r'شخص\s+(ينفذ|يكمل|يسوي)\s+لي',
    r'عندي\s+(واجب|مشروع|تكليف|شغل|طلب|عمل)\s+أبي\s+(حد|شخص)',
    r'عندي.+أبي.+يسوي',
    r'عندي.+أبغى.+يكمل',
    r'أبحث\s+عن\s+حد\s+يسوي',
    r'ابغى\s+أحد\s+ينجز',
    r'دور\s+لي\s+على\s+شخص',
]

# ================== 9. ⭐ القائمة السوداء الموحدة (كلمات تُستبعد فوراً) ⭐ ==================
BLACKLIST_KEYWORDS = {
    # إعلانات وخدمات تجارية
    'للتواصل', 'للتسجيل', 'واتساب', 'واتس', 'تواصل', 'راسلني', 'لبيع',
    'سعر', 'ريال', 'دولار', 'عرض', 'خصم', 'ضمان', 'استثمار', 'ربح',
    'تسويق', 'اعلان', 'معلن', 'احجز', 'مقعد', 'سارع', 'محدود',
    'نحل', 'نحل الواجب', 'نحل التكليف', 'نضمن', 'درجة كاملة', 'نجاح مضمون',
    'توظيف', 'مطلوب معلمين', 'مطلوب مدرسين', 'وظيفة', 'مكتب', 'مجموعة',
    'قناة', 'لدينا', 'عندنا', 'نقدم', 'خدماتنا', 'لشراء', 'للبيع',
    'جنيه', 'دفع', 'دفعات', 'حل جميع المواد', 'حلول جاهزة', 'مكتب خدمات',
    'ضمان النجاح', 'توثيق رسائل', 'تحضير عروض', 'خدمة مدفوعة',
    'للاشتراك', 'اشترك', 'انشر', 'نشر', 'ترويج', 'إشهار', 'متوفر حل',
    'يوجد حل', 'نخلص', 'ننجز', 'ننفذ', 'نقدم أفضل', 'أسعار مميزة',

    # استفسارات عامة (غير طلبات خدمة)
    'كيف', 'متى', 'كم', 'أين', 'من', 'هل', 'وش', 'ايش', 'شنو',
    'ليه', 'لماذا', 'مين', 'وشلون', 'ايش رأيكم', 'شو رأيكم',
    'وش يعني', 'تدرون', 'حد يعرف', 'وين', 'ليش', 'قد ايش',
    'الاختبار', 'المحاضرة', 'الدكتور', 'شعبة', 'جدول', 'رابط', 'ملزمة',
    'من وين اذاكر', 'اليوم دوام', 'نزلت الدرجات', 'تأجل', 'حذف',

    # تحيات وبدايات عامة (إذا لم يصاحبها طلب مباشر)
    '[إعلان]', '🔴 هام', '📢 يعلن', 'فرصة عمل', 'مطلوب للعمل',
    'سلام عليكم', 'مساء الخير', 'صباح النور', 'السلام عليكم',
    'هاي', 'هلا', 'مرحبا', 'أهلاً', 'يا جماعة', 'يا شباب',
}

# ================== 10. أنماط الروابط وأرقام الهواتف (للاستبعاد) ==================
LINK_PATTERNS = [
    r'https?://\S+', r'www\.\S+', r't\.me/\S+', r'telegram\.me/\S+',
    r'wa\.me/\S+', r'whatsapp\.com/\S+', r'bit\.ly/\S+', r'goo\.gl/\S+',
    r'[a-zA-Z0-9.-]+\.(com|net|org|info|biz|me|io|co|sa|ae|eg)\S*',
    r'\.[a-zA-Z]{2,}(/\S*)?', r'\S+@\S+\.\S+',
]

CONTACT_WORDS = [
    'تواصل', 'للتواصل', 'راسلني', 'واتساب', 'واتس', 'wb', 'سناب',
    'انستقرام', 'انستا', 'تويتر', 'فيسبوك', 'ايميل', 'بريد', 'email',
    'call', 'رقم', 'جوال', 'موبايل', 'للتحميل', 'للتسجيل', 'اضغط هنا', 'link', 'رابط'
]

# ================== 11. منع تكرار إرسال نفس الرسالة ==================
MAX_SENT_IDS = 10000
sent_messages = deque(maxlen=MAX_SENT_IDS)

def is_duplicate(chat_id: int, message_id: int) -> bool:
    key = f"{chat_id}:{message_id}"
    if key in sent_messages:
        return True
    sent_messages.append(key)
    return False

# ================== 12. دوال معالجة النصوص ==================
def normalize_arabic(text: str) -> str:
    text = re.sub(r'[إأآا]', 'ا', text)
    text = re.sub(r'[ةه]', 'ه', text)
    text = re.sub(r'[ىي]', 'ي', text)
    text = re.sub(r'[\u064B-\u065F\u0670]', '', text)
    return text.strip().lower()

def contains_link(text: str) -> bool:
    text_lower = text.lower()
    for pattern in LINK_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    for word in CONTACT_WORDS:
        if word in text_lower:
            return True
    return False

def contains_phone(text: str) -> bool:
    cleaned = re.sub(r'[^\d]', '', text)
    return len(cleaned) >= 10

def extract_service_description(text: str) -> str:
    request_words = [
        'أبي', 'ابي', 'أبغى', 'ابغى', 'محتاج', 'مطلوب',
        'حد يسوي', 'حد يكمل', 'واحد يسوي', 'شخص ينفذ', 'عندي'
    ]
    result = text
    for word in request_words:
        result = result.replace(word, '')
    cleaned = result.strip()
    if len(cleaned) > 120:
        cleaned = cleaned[:120] + "..."
    return cleaned if cleaned else "خدمة طلابية أونلاين"

# ================== 13. ⭐ نظام التحليل الذكي (مع القائمة السوداء) ⭐ ==================
def analyze_message(text: str) -> tuple[bool, str, str]:
    text_norm = normalize_arabic(text)

    # ❌ الفلتر 0: القائمة السوداء الموحدة (أول شيء)
    for bad_word in BLACKLIST_KEYWORDS:
        if bad_word in text_norm:
            return False, "مرفوض_قائمة_سوداء", ""

    # ❌ الفلتر 1: الروابط والهواتف
    if contains_link(text) or contains_phone(text):
        return False, "يحتوي_على_رابط_أو_هاتف", ""

    # ❌ الفلتر 2: التحية فقط بدون طلب (مع استثناء)
    words = text_norm.split()
    first_few = ' '.join(words[:3])
    for ignore in ['سلام عليكم', 'مساء الخير', 'صباح النور', 'السلام عليكم', 'هاي', 'هلا', 'مرحبا']:
        if ignore in text_norm or first_few.startswith(ignore):
            has_request = any(re.search(p, text_norm) for p in EXECUTION_PATTERNS)
            if not has_request:
                return False, "تحية_فقط", ""

    # ❌ الفلتر 3: الاستفسارات العامة (بدون نية تنفيذ)
    inquiry_starters = {'كيف', 'متى', 'كم', 'أين', 'هل', 'وش', 'ايش', 'ليه', 'مين', 'وين'}
    if words and words[0] in inquiry_starters:
        has_request = any(re.search(p, text_norm) for p in EXECUTION_PATTERNS)
        if not has_request:
            return False, "استفسار_عام", ""

    # ✅ الفلتر 4: البحث عن نية طلب التنفيذ (الشرط الأساسي)
    has_execution_intent = any(re.search(pattern, text_norm) for pattern in EXECUTION_PATTERNS)
    if not has_execution_intent:
        return False, "لا_طلب_تنفيذ", ""

    # 📏 الفلتر 5: طول الرسالة
    text_len = len(text_norm)
    if text_len < MIN_MSG_LENGTH or text_len > MAX_MSG_LENGTH:
        return False, "طول_غير_مناسب", ""

    # 🎯 القرار النهائي
    service_desc = extract_service_description(text)
    has_online_hint = any(w in text_norm for w in ['أونلاين', 'اونلاين', 'عن بعد', 'إرسال', 'تسليم', 'ملف', 'خاص'])
    classification = "طلب_أونلاين_مؤكد" if has_online_hint else "طلب_تنفيذ_محتمل"

    return True, classification, service_desc

# ================== 14. ⭐ دالة إنشاء الروابط الذكية ⭐ ==================
def get_smart_links(chat, event_id: int) -> tuple[str, str]:
    chat_id = chat.id
    chat_username = getattr(chat, 'username', None)

    group_link = "#"
    msg_link = "#"

    if chat_id in INVITE_LINKS:
        group_link = INVITE_LINKS[chat_id]
    elif chat_username:
        group_link = f"https://t.me/{chat_username}"
    elif DEFAULT_INVITE_LINK:
        group_link = DEFAULT_INVITE_LINK

    if chat_username:
        msg_link = f"https://t.me/{chat_username}/{event_id}"
    else:
        try:
            cid = str(chat_id)
            if cid.startswith('-100'):
                msg_link = f"https://t.me/c/{cid[4:]}/{event_id}"
            else:
                msg_link = f"https://t.me/c/{abs(chat_id)}/{event_id}"
        except Exception:
            pass

    return group_link, msg_link

# ================== 15. ⭐ تنسيق رسالة القناة ⭐ ==================
def format_forward_message(
    event, sender, chat, radar_name: str,
    classification: str, service_desc: str,
    text: str, is_special: bool = False
) -> tuple[str, list]:
    username = getattr(sender, 'username', None)
    first_name = getattr(sender, 'first_name', 'مستخدم')
    last_name = getattr(sender, 'last_name', '')
    full_name = f"{first_name} {last_name}".strip() or first_name
    user_id = sender.id
    chat_title = getattr(chat, 'title', 'مجموعة')
    group_link, msg_link = get_smart_links(chat, event.id)
    display_text = text[:180] + "..." if len(text) > 180 else text

    if is_special:
        msg = (
            f"🔴 **تحويل فوري | قناة خاصة**\n"
            f"🕐 `{datetime.now().strftime('%H:%M:%S')}` | عبر {radar_name}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 **المرسل:** {full_name}\n"
            f"🔖 **اليوزر:** @{username or 'بدون'}\n"
            f"🆔 **ID:** `{user_id}`\n"
            f"📍 **المصدر:** {chat_title} ⭐\n"
            f"🔗 [الرسالة الأصلية]({msg_link})\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📝 **النص:**\n_{display_text}_\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👇 **إجراءات سريعة:**"
        )
    else:
        msg = (
            f"⚡️ **طلب خدمة طلابية أونلاين**\n"
            f"🕐 `{datetime.now().strftime('%H:%M:%S')}` | عبر {radar_name}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 **الطالب:** {full_name}\n"
            f"🔖 **اليوزر:** @{username or 'بدون'}\n"
            f"🆔 **ID:** `{user_id}`\n"
            f"📍 **المصدر:** {chat_title}\n"
            f"🔗 [الرسالة الأصلية]({msg_link})\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📋 **تفاصيل الطلب:**\n_{display_text}_\n"
            f"🔍 **الخدمة:** {service_desc}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 **الحالة:** {classification}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👇 **إجراءات سريعة:**"
        )

    buttons = []
    if username:
        buttons.append([Button.url("💬 مراسلة الطالب", f"https://t.me/{username}")])
    if group_link and group_link != "#":
        buttons.append([Button.url("👥 الانضمام للمجموعة", group_link)])
    if msg_link and msg_link != "#":
        btn_text = "🔗 رؤية الرسالة" if chat.username else "🔗 الرسالة (للأعضاء فقط)"
        buttons.append([Button.url(btn_text, msg_link)])

    return msg, buttons

# ================== 16. ⭐ دالة الرصد الرئيسية ⭐ ==================
async def start_monitoring(acc_info: dict):
    client = TelegramClient(
        StringSession(acc_info['session']),
        acc_info['api_id'],
        acc_info['api_hash'],
        auto_reconnect=True,
        connection_retries=5,
        retry_delay=3
    )
    radar_name = acc_info['name']

    @client.on(events.NewMessage)
    async def message_handler(event):
        try:
            if event.is_private:
                return
            if is_duplicate(event.chat_id, event.id):
                return
            text = event.raw_text.strip()
            if not text:
                return

            sender = await event.get_sender()
            chat = await event.get_chat()
            chat_id = chat.id

            if SPECIAL_CHANNEL_ID > 0 and chat_id == SPECIAL_CHANNEL_ID:
                logger.info(f"⭐ [{radar_name}] تحويل فوري من القناة الخاصة")
                msg, buttons = format_forward_message(
                    event, sender, chat, radar_name,
                    classification="تحويل_فوري", service_desc="خدمة خاصة",
                    text=text, is_special=True
                )
                await client.send_message(TARGET_CHANNEL, msg, buttons=buttons, silent=False)
                return

            is_valid, classification, service_desc = analyze_message(text)
            if not is_valid:
                return

            msg, buttons = format_forward_message(
                event, sender, chat, radar_name,
                classification, service_desc, text, is_special=False
            )
            await client.send_message(TARGET_CHANNEL, msg, buttons=buttons, silent=False)
            logger.info(f"✅ [{radar_name}] {classification} | الخدمة: {service_desc[:30]}...")
        except Exception as e:
            logger.error(f"❌ [{radar_name}] خطأ في المعالجة: {e}", exc_info=True)

    while True:
        try:
            await client.start()
            logger.info(f"✅ {radar_name} متصل بنجاح وبدأ الرصد!")
            await client.run_until_disconnected()
        except Exception as e:
            logger.error(f"⚠️ {radar_name} انقطع الاتصال: {e}")
            await asyncio.sleep(5)
        finally:
            if client.is_connected():
                await client.disconnect()

# ================== 17. التشغيل الرئيسي للبوت ==================
async def main():
    logger.info("🚀 بدء تشغيل رادار الخدمات الطلابية أونلاين...")
    logger.info(f"📊 الحسابات النشطة: {len(accounts)}")
    logger.info(f"🎯 القناة المستهدفة: {TARGET_CHANNEL}")
    if SPECIAL_CHANNEL_ID > 0:
        logger.info(f"⭐ القناة الخاصة للتحويل الفوري: {SPECIAL_CHANNEL_ID}")

    tasks = [start_monitoring(acc) for acc in accounts]
    await asyncio.gather(*tasks, return_exceptions=True)

# ================== 18. نقطة الدخول للتطبيق ==================
if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 تم إيقاف البوت يدوياً")
    except Exception as e:
        logger.error(f"💥 خطأ فادح في التشغيل: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
