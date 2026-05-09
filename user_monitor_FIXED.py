#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎓 رادار الخدمات الطلابية - النسخة المحسّنة 3.0 (محسّن الأداء)
المطور: متولي الوصابي
التاريخ: 2026

التحسينات:
✓ تحسين Flask Thread Management
✓ تحسين Telethon Polling Loop
✓ تقليل Cold Start من Render
"""

import os
import sys
import re
import asyncio
import logging
from datetime import datetime
from collections import deque
from concurrent.futures import ThreadPoolExecutor  # ← تحسين 1

from flask import Flask, jsonify
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession

# ================== إعداد التسجيل ==================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ================== سيرفر الويب ==================
app = Flask(__name__)

@app.route('/')
def home():
    return f"<h1>🎓 رادار الخدمات الطلابية 3.0</h1><p>✅ يعمل {datetime.now().strftime('%H:%M:%S')}</p>"

@app.route('/health')
def health():
    return jsonify(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="3.0",
        uptime="active"
    )

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False, threaded=True)

# ✓ تحسين 1: استخدام ThreadPoolExecutor بدلاً من daemon thread
executor = ThreadPoolExecutor(max_workers=1)
flask_future = executor.submit(run_flask)
logger.info(f"✅ سيرفر الويب يعمل على المنفذ {os.environ.get('PORT', 10000)}")

# ================== تحميل متغيرات البيئة ==================
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
TARGET_CHANNEL = os.environ.get("TARGET_CHANNEL")

if not all([API_ID, API_HASH, TARGET_CHANNEL]):
    logger.error("❌ خطأ: أحد المتغيرات الأساسية مفقود!")
    sys.exit(1)

try:
    API_ID = int(API_ID)
except ValueError:
    logger.error(f"❌ خطأ: API_ID يجب أن يكون رقماً صحيحاً")
    sys.exit(1)

SESSION_1 = os.environ.get("SESSION_1", "").strip()
SESSION_2 = os.environ.get("SESSION_2", "").strip()

# ================== إعدادات التصفية ==================
MIN_MSG_LENGTH = int(os.environ.get("MIN_MSG_LENGTH", "10"))
MAX_MSG_LENGTH = int(os.environ.get("MAX_MSG_LENGTH", "800"))

# ================== إعداد حسابات التليجرام ==================
accounts = []
if SESSION_1:
    accounts.append({'name': 'رادار-1', 'api_id': API_ID, 'api_hash': API_HASH, 'session': SESSION_1})
if SESSION_2:
    accounts.append({'name': 'رادار-2', 'api_id': API_ID, 'api_hash': API_HASH, 'session': SESSION_2})
if not accounts:
    logger.error("❌ لم يتم توفير أي جلسة!")
    sys.exit(1)

logger.info(f"📊 إجمالي الحسابات النشطة: {len(accounts)}")

# ================== إعدادات خاصة ==================
SPECIAL_CHANNEL_ID = int(os.environ.get("SPECIAL_CHANNEL_ID", "-1"))
INVITE_LINKS = {}
DEFAULT_INVITE_LINK = os.environ.get("DEFAULT_INVITE_LINK", "")

# ================== القائمة السوداء ==================
BLACKLIST_KEYWORDS = {
    # إعلانات وترويج
    'للتواصل', 'للتسجيل', 'واتساب', 'واتس', 'راسلني', 'لبيع',
    'سعر', 'ريال', 'دولار', 'خصم', 'ضمان', 'استثمار', 'ربح',
    'تسويق', 'اعلان', 'معلن', 'احجز', 'مقعد', 'سارع', 'محدود',
    'نحل الواجب', 'نحل التكليف', 'نضمن', 'درجة كاملة', 'نجاح مضمون',
    'توظيف', 'مطلوب معلمين', 'مطلوب مدرسين', 'وظيفة', 'مكتب خدمات',
    'قناة التيليجرام', 'لدينا', 'عندنا', 'نقدم', 'خدماتنا', 'لشراء', 'للبيع',
    'جنيه', 'دفع', 'دفعات', 'حل جميع المواد', 'حلول جاهزة',
    'ضمان النجاح', 'توثيق رسائل', 'تحضير عروض', 'خدمة مدفوعة',
    'للاشتراك', 'اشترك', 'انشر', 'نشر', 'ترويج', 'إشهار', 'متوفر حل',
    'يوجد حل', 'نخلص', 'ننجز', 'ننفذ', 'نقدم أفضل', 'أسعار مميزة',
    'الاختبار متى', 'المحاضرة متى', 'الدكتور فلان', 'شعبة كم',
    'رابط القروب', 'ملزمة المادة', 'من وين اذاكر', 'اليوم دوام', 'نزلت الدرجات',
    'جدول المحاضرات', 'جدول الاختبارات', 'موعد الاختبار', 'موعد المحاضرة',
    '[إعلان]', '🔴 هام', '📢 يعلن', 'فرصة عمل', 'مطلوب للعمل',
    'كيف حالك', 'وش اخبار', 'ايش مسوين', 'شو رأيكم', 'ايش رأيكم',
    'نحل', 'نسوي', 'نعطيك', 'تواصل معنا', 'تواصلوا', 'قدم طلبك',
    'اطلب الان', 'اطلب الآن', 'خدمات متنوعة', 'أفضل الأسعار',
    'شركة', 'مؤسسة', 'أكاديمية', 'مركز',
}

# ================== أنماط الطلبات ==================
EXECUTION_PATTERNS = [
    r'(احتاج|احتجاج|محتاج|ابي|ابغى|ابقى|ابا|أبي|أبغى|أحتاج|بدي|حابب|بغيت)\s+(حد|شخص|واحد|أحد|احد|من|مين|مني|احد)\s+(يسوي|يسوى|يشوي|يكمل|ينفذ|يعمل|يجهز|يخلص|يرسل|يحل|يصلح|يكتب|يصمم|يبرمج|يترجم|يعدل|يساعد|يساعدي|يدبر|يضبط|يظبط|يشرح|يذاكر|يحضر|يلخص|يعبي|يرسم|يحسب|يسجل)',
    r'(اللي|الي|الذي)\s+(يقدر|يعرف|يفهم|فيه|عنده|معاه|يقدر)\s+(يسوي|يسوى|يكمل|ينفذ|يعمل|يجهز|يخلص|يرسل|يحل|يكتب|يصمم|يبرمج|يترجم|يعدل|يساعد|يشرح|يلخص)',
    r'(مين|من|مني)\s+(يسوي|يسوى|يشوي|يكمل|ينفذ|يعمل|يجهز|يخلص|يرسل|يحل|يصلح|يكتب|يصمم|يبرمج|يترجم|يعدل|يساعد|يعرف|يفهم|يشرح|يلخص)\s*(لي|لنا|لي ضرة|لينا)?',
    r'(حد|شخص|واحد|أحد|احد)\s+(يسوي|يسوى|يشوي|يكمل|ينفذ|يعمل|يجهز|يخلص|يرسل|يحل|يصلح|يكتب|يصمم|يبرمج|يترجم|يعدل|يساعد|يعرف|يفهم|يضبط|يشرح|يذاكر|يلخص|يحضر)',
    r'(احتاج|احتجاج|محتاج|ابي|ابغى|ابقى|ابا|بدي|حابب|عندي|مطلوب|بغيت)\s+(عرض|بوربوينت|بور بوينت|ppt|واجب|واجبات|مشروع|تقرير|تقارير|بحث|بحوث|تلخيص|ملخص|ترجمه|ترجمة|برمجه|برمجة|اكسل|excel|وورد|word|تصميم|خصوصي|عذر\s+طبي|تقرير\s+طبي|شهادة\s+صحيه|مدرس\s+خصوصي|حل\s+واجب|حل\s+اسايمنت|اسايمنت|assignment|مشروع\s+تخرج|بروجكت|project|حل\s+تمارين|شرح\s+مادة|حل\s+اختبار|نموذج)',
]

SERVICE_SPECIFIC_PATTERNS = [
    r'(مشروع|بروجكت|project)\s+(برمجه|برمجة|python|java|c\+\+|web|موبايل|تطبيق|app|website)',
    r'(برمجه|برمجة|كود|code)\s+(جاهز|كامل|مكتمل)',
    r'(تصميم|شعار|لوجو|logo)\s+(احتاج|محتاج|ابي|مطلوب)',
    r'(عرض|بوربوينت|ppt|presentation)\s+(احتاج|محتاج|ابي|مطلوب)',
]

URGENCY_INDICATORS = [
    r'(عاجل|ضروري|مستعجل|بسرعه|بسرعة|اليوم|الحين|هلا|على\s+طول)',
    r'(التسليم|الديدلاين|deadline)\s+(اليوم|غداً|غدا|بكره)',
]

# ================== منع تكرار ==================
MAX_SENT_IDS = 10000
sent_messages = deque(maxlen=MAX_SENT_IDS)

def is_duplicate(chat_id: int, message_id: int) -> bool:
    key = f"{chat_id}:{message_id}"
    if key in sent_messages:
        return True
    sent_messages.append(key)
    return False

# ================== دوال معالجة النصوص ==================
def normalize_arabic(text: str) -> str:
    text = re.sub(r'[إأآا]', 'ا', text)
    text = re.sub(r'[ةه]', 'ه', text)
    text = re.sub(r'[ىي]', 'ي', text)
    text = re.sub(r'[\u064B-\u065F\u0670]', '', text)
    text = re.sub(r'(.)\1{2,}', r'\1\1', text)
    return text.strip().lower()

def contains_link(text: str) -> bool:
    link_patterns = [r'https?://\S+', r'www\.\S+', r't\.me/\S+', r'wa\.me/\S+']
    for pattern in link_patterns:
        if re.search(pattern, text.lower()):
            return True
    return 'واتساب' in text.lower() or 'رقم' in text.lower()

def analyze_message(text: str) -> tuple[bool, str, str, int]:
    text_norm = normalize_arabic(text)
    text_len = len(text_norm)

    # الفحوصات الأساسية
    if text_len < MIN_MSG_LENGTH or text_len > MAX_MSG_LENGTH:
        return False, "طول_غير_مناسب", "", 0
    
    for bad_word in BLACKLIST_KEYWORDS:
        if normalize_arabic(bad_word) in text_norm:
            return False, "مرفوض_قائمة_سوداء", "", 0
    
    if contains_link(text):
        return False, "يحتوي_رابط", "", 0

    # البحث عن نمط الطلب
    has_execution = any(re.search(p, text_norm) for p in EXECUTION_PATTERNS)
    has_service = any(re.search(p, text_norm) for p in SERVICE_SPECIFIC_PATTERNS)

    if not has_execution and not has_service:
        return False, "لا_طلب_تنفيذ", "", 0

    # حساب الاستعجال
    urgency = sum(1 for p in URGENCY_INDICATORS if re.search(p, text_norm))

    return True, "طلب_تنفيذ_مؤكد", "📌 خدمة طلابية", min(urgency, 3)

# ================== دالة الرصد ==================
async def start_monitoring(acc_info: dict):
    client = TelegramClient(
        StringSession(acc_info['session']),
        acc_info['api_id'],
        acc_info['api_hash'],
        auto_reconnect=True,
        connection_retries=5,
        retry_delay=2  # ✓ تحسين 2: تقليل retry delay
    )
    radar_name = acc_info['name']

    @client.on(events.NewMessage)
    async def message_handler(event):
        try:
            if event.is_private or is_duplicate(event.chat_id, event.id):
                return
            text = event.raw_text.strip()
            if not text:
                return

            is_valid, classification, service_type, urgency = analyze_message(text)
            if not is_valid:
                return

            sender = await event.get_sender()
            chat = await event.get_chat()
            
            username = getattr(sender, 'username', None)
            first_name = getattr(sender, 'first_name', 'مستخدم')
            full_name = f"{first_name} {getattr(sender, 'last_name', '')}".strip() or first_name
            
            urgency_icon = {0: "", 1: "⚡", 2: "🔥", 3: "🚨"}.get(urgency, "")
            
            msg = (
                f"{urgency_icon}⚡️ **طلب خدمة طلابية** {urgency_icon}\n"
                f"🕐 `{datetime.now().strftime('%H:%M:%S')}` | {radar_name}\n"
                f"👤 **الطالب:** {full_name}\n"
                f"🔖 **اليوزر:** @{username or 'بدون'}\n"
                f"📍 **المصدر:** {getattr(chat, 'title', 'مجموعة')}\n"
                f"📝 **الطلب:** {text[:250]}\n"
            )
            
            buttons = []
            if username:
                buttons.append([Button.url("💬 مراسلة الطالب", f"https://t.me/{username}")])

            try:
                await client.send_message(target=TARGET_CHANNEL, message=msg, buttons=buttons or None, silent=False)
                logger.info(f"✅ [{radar_name}] {classification} | {text[:40]}...")
            except Exception as send_err:
                logger.error(f"❌ خطأ الإرسال: {send_err}")

        except Exception as e:
            logger.error(f"❌ [{radar_name}] خطأ: {e}")

    # ✓ تحسين 3: Polling loop محسّن مع timeouts أقصر
    while True:
        try:
            await client.start()
            logger.info(f"✅ {radar_name} متصل | بدأ الرصد!")
            
            # بدلاً من run_until_disconnected، استخدم loop مخصص
            disconnect_event = asyncio.Event()
            
            @client.on(events.Raw)
            async def handle_disconnect(event):
                disconnect_event.set()
            
            # انتظر مع timeout قصير
            await asyncio.wait_for(
                client.run_until_disconnected(),
                timeout=300  # 5 دقاىق max قبل reconnect
            )
        except asyncio.TimeoutError:
            logger.info(f"⏱️ [{radar_name}] timeout - reconnecting...")
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"⚠️ [{radar_name}] انقطاع: {e}")
            await asyncio.sleep(5)
        finally:
            try:
                if client.is_connected():
                    await client.disconnect()
            except:
                pass

# ================== البداية ==================
async def main():
    logger.info("🚀 بدء رادار الخدمات 3.0...")
    logger.info(f"📊 الحسابات: {len(accounts)} | القناة: {TARGET_CHANNEL}")
    
    tasks = [start_monitoring(acc) for acc in accounts]
    await asyncio.gather(*tasks, return_exceptions=True)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 تم الإيقاف")
        sys.exit(0)
    except Exception as e:
        logger.error(f"💥 خطأ: {e}")
        sys.exit(1)
