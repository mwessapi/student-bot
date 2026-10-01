#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎓 رادار الخدمات الطلابية 4.0
- رصد الطلبات → القناة
- رد ذكي من OpenRouter
- إرسال حساب الأكاديمية عند الرد
- إشعار لك عند رد الطالب
"""

# ================== 1. المكتبات ==================
import os
import sys
import re
import json
import random
import asyncio
import threading
import logging
from datetime import datetime, date
from collections import deque

from flask import Flask, jsonify
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# ================== 2. التسجيل ==================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ================== 3. سيرفر الويب ==================
app = Flask(__name__)

@app.route('/')
def home():
    return f"<h1>🎓 رادار الخدمات</h1><p>✅ {datetime.now().strftime('%H:%M:%S')}</p>"

@app.route('/health')
def health():
    return jsonify(status="healthy", timestamp=datetime.now().isoformat())

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# ================== 4. متغيرات البيئة ==================
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
TARGET_CHANNEL = os.environ.get("TARGET_CHANNEL")

if not all([API_ID, API_HASH, TARGET_CHANNEL]):
    logger.error("❌ متغير أساسي مفقود!")
    sys.exit(1)

try:
    API_ID = int(API_ID)
except ValueError:
    logger.error("❌ API_ID يجب أن يكون رقماً")
    sys.exit(1)

SESSION_1 = os.environ.get("SESSION_1", "").strip()
SESSION_2 = os.environ.get("SESSION_2", "").strip()
SESSION_3 = os.environ.get("SESSION_3", "").strip()

MIN_MSG_LENGTH = int(os.environ.get("MIN_MSG_LENGTH", "10"))
MAX_MSG_LENGTH = int(os.environ.get("MAX_MSG_LENGTH", "150"))

# ================== 5. ⭐ الإعدادات الثابتة ==================
REPLIER_ACCOUNT = "رادار-2"
AUTO_REPLY_ENABLED = True
AUTO_REPLY_DAILY_LIMIT = 40

ACADEMY_USERNAME = "m_7_1_1_m"
ACADEMY_NAME = "أكاديمية خدمات طلابية فورية"
ACADEMY_TAGLINE = "⚡ سرعة | 🏆 جودة | ✅ موثوقية"

# ================== 6. متغيرات البيئة (أسرار) ==================
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
AI_MODEL_NAME = os.environ.get("AI_MODEL_NAME", "google/gemini-flash-1.5:free")
OWNER_CHAT_ID = int(os.environ.get("OWNER_CHAT_ID", "0"))

# ================== 7. OpenRouter ==================
ai_client = None
if OPENROUTER_KEY and OPENAI_AVAILABLE:
    try:
        ai_client = AsyncOpenAI(
            api_key=OPENROUTER_KEY,
            base_url="https://openrouter.ai/api/v1",
        )
        logger.info(f"✅ OpenRouter متصل | {AI_MODEL_NAME}")
    except Exception as e:
        logger.error(f"❌ فشل OpenRouter: {e}")
        ai_client = None
elif not OPENAI_AVAILABLE:
    logger.warning("⚠️ مكتبة openai غير مثبتة")
else:
    logger.warning("⚠️ OPENROUTER_API_KEY غير محدد")

# ================== 8. تخزين ==================
REPLIED_STUDENTS = {}
daily_counter = {"date": None, "count": 0}

def can_reply_today() -> bool:
    today = date.today()
    if daily_counter["date"] != today:
        daily_counter["date"] = today
        daily_counter["count"] = 0
    if daily_counter["count"] >= AUTO_REPLY_DAILY_LIMIT:
        return False
    daily_counter["count"] += 1
    return True

# ================== 9. الحسابات ==================
accounts = []
if SESSION_1:
    accounts.append({'name': 'رادار-1', 'api_id': API_ID, 'api_hash': API_HASH, 'session': SESSION_1})
if SESSION_2:
    accounts.append({'name': 'رادار-2', 'api_id': API_ID, 'api_hash': API_HASH, 'session': SESSION_2})
if SESSION_3:
    accounts.append({'name': 'رادار-3', 'api_id': API_ID, 'api_hash': API_HASH, 'session': SESSION_3})
if not accounts:
    logger.error("❌ لا توجد جلسات!")
    sys.exit(1)

logger.info(f"📊 الحسابات: {len(accounts)}")
logger.info(f"🎯 حساب الرد: {REPLIER_ACCOUNT}")

SPECIAL_CHANNEL_ID = int(os.environ.get("SPECIAL_CHANNEL_ID", "0"))
INVITE_LINKS = {}
DEFAULT_INVITE_LINK = os.environ.get("DEFAULT_INVITE_LINK", "")

# ================== 10. القائمة السوداء ==================
BLACKLIST_KEYWORDS = {
    'للتواصل', 'للتسجيل', 'واتساب', 'واتس', 'راسلني', 'لبيع',
    'سعر', 'ريال', 'دولار', 'خصم', 'ضمان', 'استثمار', 'ربح',
    'خدمات تسويق', 'نسوق لكم', 'تسويق منتجات', 'اعلان', 'معلن', 'احجز', 'مقعد', 'سارع', 'محدود',
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
    'تنزل الجداول', 'نزلت الجداول', 'الجداول نزلت',
    '[إعلان]', '🔴 هام', '📢 يعلن', 'فرصة عمل', 'مطلوب للعمل',
    'كيف حالك', 'وش اخبار', 'ايش مسوين', 'شو رأيكم', 'ايش رأيكم',
    'نحل', 'نسوي', 'نعطيك', 'تواصل معنا', 'تواصلوا', 'قدم طلبك',
    'اطلب الان', 'اطلب الآن', 'خدمات متنوعة', 'أفضل الأسعار',
    'شركة', 'مؤسسة', 'أكاديمية', 'مركز',
}

ACTION_VERBS = (
    r'يسوي|يسوى|يشوي|يكمل|ينفذ|يعمل|يجهز|يخلص|يرسل|يحل|يصلح|'
    r'يكتب|يصمم|يبرمج|يترجم|يعدل|يساعد|يساعدي|يدبر|يضبط|يظبط|'
    r'يشرح|يذاكر|يحضر|يلخص|يعبي|يرسم|يحسب|يسجل'
)

PERSON_REF = r'حد|شخص|واحد|أحد|احد|مين|مني|مصمم|مبرمج|مترجم|معلم|مدرس|محلل|مطور|كاتب|مذاكر'

EXECUTION_PATTERNS = [
    rf'(احتاج|احتجاج|محتاج|ابي|ابغى|ابقى|ابا|أبي|أبغى|أحتاج|بدي|حابب|بغيت)\s+({PERSON_REF})(\s+({ACTION_VERBS}))?',
    rf'(اللي|الي|الذي)\s+(يقدر|فيه|عنده|معاه)\s+({ACTION_VERBS})',
    rf'(مين|من|مني)\s+({ACTION_VERBS})\s*(لي|لنا|لي ضرة|لينا)?',
    rf'({PERSON_REF})\s+({ACTION_VERBS})',
    r'(احتاج|احتجاج|محتاج|ابي|ابغى|ابقى|ابا|بدي|حابب|عندي|مطلوب|بغيت)\s+(عرض|بوربوينت|بور بوينت|ppt|واجب|واجبات|مشروع|تقرير|تقارير|بحث|بحوث|تلخيص|ملخص|ترجمه|ترجمة|برمجه|برمجة|اكسل|excel|وورد|word|تصميم|خصوصي|عذر\s+طبي|تقرير\s+طبي|شهادة\s+صحيه|مدرس\s+خصوصي|حل\s+واجب|حل\s+اسايمنت|اسايمنت|assignment|مشروع\s+تخرج|بروجكت|project|حل\s+تمارين|شرح\s+مادة|حل\s+اختبار|نموذج)',
    r'(يصل|يصلح|يحل)\s+(واجب|تكليف|اسايمنت|مشروع|بحث|تقرير)',
    r'(يساعدي|تساعدني|يساعدني|تساعدني)\s+في\s+\w+',
    r'(تسوي|تشوي|يسوي|يشوي|يعمل|تعمل)\s+(لي|لنا|لينا)\s+(عرض|بوربوينت|واجب|تقرير|بحث|مشروع|تصميم|برمجه|برمجة)',
    r'(ابي|ابغى|احتاج|محتاج|ابا|بدي|مطلوب)\s+خصوصي\s*(في|لمادة|لماده|مادة|لـ)?',
    r'(مدرس|معلم|أستاذ|استاذ)\s+خصوصي\s*(في|لمادة|لـ)?\s*(فيزياء|رياضيات|كيمياء|احياء|انجليزي|انجليش|عربي|برمجه|برمجة|محاسبه|محاسبة|اقتصاد|احصاء|تمريض|طب|ادارة|تسويق|ماثس|كالكولس|حساب|جبر|هندسه|هندسة|فيزكس|كيم)?',
    r'(دروس|درس)\s+خصوصيه?\s*(في|لمادة|لـ)?',
    r'(يشرح|يذاكر\s+معي|يذاكر\s+معاي)\s+(مادة|ماده|مواد)?',
    r'(عذر|تقرير|شهادة)\s+(طبي|طبيه|مرضي|صحيه|صحي)\s*(بسعر|برسوم|بفلوس|رخيص)?',
    r'(ابي|احتاج|محتاج)\s+(عذر|إعفاء|اعفاء)\s+(طبي|رسمي)',
    rf'(دور|ابحث|أبحث|نبحث)\s+(لي|لنا)?\s*(عن|على)\s+(حد|شخص|واحد)\s+({ACTION_VERBS})',
    r'(يخلص|يكمل|ينهي)\s+(لي|لنا)?\s*(الواجب|التكليف|المشروع|الاسايمنت|البحث)',
    rf'(ودي|وداي|وددت|بودي)\s+(احد|حد|شخص)\s+({ACTION_VERBS})',
    rf'(فيه|في|هل\s+في|هل\s+فيه|ما\s+في)\s+(احد|حد|شخص|واحد)\s+(يقدر\s+)?({ACTION_VERBS})',
    r'(محتاج|ابي|احتاج)\s+(مساعده|مساعدة|مساعد)\s+في\s+(برمجه|برمجة|تصميم|اكسل|وورد|واجب|مشروع|بحث|تقرير|عرض)',
    r'(need|looking\s+for|want)\s+(someone|anyone|help)\s+(to|for)',
    r'(محتاج|ابي)\s+(freelancer|help|someone)',
]

NEED_WORDS = r'(احتاج|محتاج|ابي|ابغى|مطلوب|بدي|بغيت|ابا)'

SERVICE_SPECIFIC_PATTERNS = [
    r'(مشروع|بروجكت|project)\s+(برمجه|برمجة|python|java|c\+\+|web|موبايل|تطبيق|app|website)',
    r'(برمجه|برمجة|كود|code)\s+(جاهز|كامل|مكتمل)',
    r'(اسايمنت|assignment)\s+(برمجه|برمجة|python|java|html|css)',
    rf'{NEED_WORDS}\s+(تصميم|شعار|لوجو|logo|بنر|banner|انفوغراف|infographic)',
    rf'{NEED_WORDS}\s+(عرض|بوربوينت|بور\s+بوينت|ppt|presentation)\s*\w*',
    rf'{NEED_WORDS}\s+(تقرير|بحث)\s*(عن)?',
    rf'(ترجمه|ترجمة)\s+(ملف|وثيقه|نص|مقاله|مقال|بحث)\s*{NEED_WORDS}?',
    rf'{NEED_WORDS}\s+(اكسل|excel|جداول|pivot|داشبورد|dashboard)',
    rf'(مشروع\s+تخرج|graduation\s+project|مشروع\s+النهائي)\s*{NEED_WORDS}?',
]

URGENCY_INDICATORS = [
    r'(عاجل|ضروري|مستعجل|بسرعه|بسرعة|اليوم|الحين|هلا|على\s+طول)',
    r'(التسليم|الديدلاين|deadline)\s+(اليوم|غداً|غدا|بكره|بعدين)',
    r'(آخر\s+موعد|اخر\s+موعد)\s+(اليوم|غد|الساعه)',
    r'(بكره\s+اختبار|اختبار\s+بكره|غداً\s+اختبار)',
    r'(فاضل|باقي)\s+(يوم|ساعات|وقت\s+قليل)',
]

INQUIRY_PATTERNS = [
    r'^(كيف|كيفه|كيفها)\s+(تحل|تعمل|تسوي|يحل|يعمل|نعمل)',
    r'^(ايش|ايش\s+هو|ما\s+هو|ما)\s+(الفرق|الأفضل|أفضل)',
    r'^(من\s+درس|من\s+شرح|من\s+فهم)\s+\w+',
    r'^(وين|أين|من\s+وين)\s+(نلقى|نحصل|الكتاب|الملزمة|المادة)',
    r'^(هل\s+نزلت|نزلت|صدرت)\s+(الدرجات|النتائج|الجدول|الجداول)',
    r'^(متى|امتى)\s+(الاختبار|المحاضرة|التسليم|الدوام|تنزل|ينزل|تطلع|يطلع)',
    r'^(كم\s+درجة|كم\s+الدرجة|كم\s+السعر)',
    r'^(شو|ايش|وش)\s+(رأيكم|رايكم|تقولون|تقول)',
    r'^(من\s+جرب|من\s+استخدم|من\s+اخذ)\s+\w+',
    r'^(صح|صحيح|غلط)\s+(ان|إن)',
    r'^(الله\s+يعين|يا\s+حيف|حظ\s+حلو)',
]

KNOWLEDGE_QUESTION_PATTERNS = [
    r'(احد|حد|شخص|واحد|أحد)\s+(يعرف|يدري|يفهم)(?!\s+(?:' + ACTION_VERBS + r'))',
    r'(مين|من)\s+(يعرف|يدري)(?!\s+(?:' + ACTION_VERBS + r'))',
    r'(هل\s+في|هل\s+فيه|فيه|في)\s+(احد|حد|شخص)\s+(يعرف|يدري)',
    r'(ممكن|ياليت|لو\s+سمحتوا)\s+(احد|حد|شخص)?\s*(يعرف|يدري)?\s*(اذا|إذا|هل)',
    r'(اذا|إذا)\s+(احد|حد|شخص|فيه)\s+(يعرف|يدري)',
]

def is_knowledge_question(text_norm: str) -> bool:
    has_real_action = re.search(ACTION_VERBS, text_norm) is not None
    if has_real_action:
        return False
    for pattern in KNOWLEDGE_QUESTION_PATTERNS:
        if re.search(pattern, text_norm):
            return True
    return False

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

# ================== 11. منع التكرار ==================
MAX_SENT_IDS = 10000
sent_messages = deque(maxlen=MAX_SENT_IDS)

def is_duplicate(chat_id: int, message_id: int) -> bool:
    key = f"{chat_id}:{message_id}"
    if key in sent_messages:
        return True
    sent_messages.append(key)
    return False

# ================== 12. معالجة النصوص ==================
def normalize_arabic(text: str) -> str:
    text = re.sub(r'[إأآا]', 'ا', text)
    text = re.sub(r'[ةه]', 'ه', text)
    text = re.sub(r'[ىي]', 'ي', text)
    text = re.sub(r'[\u064B-\u065F\u0670]', '', text)
    text = re.sub(r'(.)\1{2,}', r'\1\1', text)
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

def is_pure_greeting(text_norm: str) -> bool:
    greetings = ['سلام عليكم', 'السلام عليكم', 'مساء الخير', 'صباح النور',
        'صباح الخير', 'مساء النور', 'اهلين', 'هلا', 'هاي', 'مرحبا',
        'هلا وغلا', 'اهلا وسهلا', 'يا هلا', 'هلا بالجميع', 'هلا شباب',
        'حياكم', 'يا اهلين', 'اهلا بكم', 'هلا فيكم']
    stripped = text_norm.strip()
    for g in greetings:
        if stripped == g or (stripped.startswith(g) and len(stripped) - len(g) < 5):
            return True
    return False

def is_pure_inquiry(text_norm: str) -> bool:
    for pattern in INQUIRY_PATTERNS:
        if re.search(pattern, text_norm, re.IGNORECASE):
            return True
    return False

def is_service_provider(text_norm: str) -> bool:
    provider_patterns = [
        r'(نحن|نقدم|نوفر|نعمل|نخلص|نسوي)\s+(خدم|عروض|واجب|مشروع)',
        r'(خدماتنا|خدماتي|بخبرة|بخبره)\s+\w+',
        r'(أنا\s+متخصص|انا\s+خبير|انا\s+مختص)\s+في',
        r'(بأسعار|باسعار)\s+(مناسبه|رمزيه|تنافسيه)',
        r'(ضمان|مضمون|مضمونة)\s+(النجاح|التسليم|الجوده)',
        r'نسوي\s+(لك|لكم|لكن)\s+(عروض|واجبات|مشاريع)',
        r'(تواصلوا|تواصل)\s+(معنا|معي|على)',
        r'(قناتنا|قناتي|قناة\s+خاصه)',
    ]
    for p in provider_patterns:
        if re.search(p, text_norm):
            return True
    return False

def get_urgency_score(text_norm: str) -> int:
    score = 0
    for pattern in URGENCY_INDICATORS:
        if re.search(pattern, text_norm):
            score += 1
    return min(score, 3)

def classify_service_type(text_norm: str) -> str:
    services = {
        '🖥️ برمجة': ['برمجه', 'برمجة', 'كود', 'code', 'python', 'java', 'html', 'css', 'تطبيق', 'app', 'website'],
        '🎨 تصميم': ['تصميم', 'شعار', 'لوجو', 'logo', 'بنر', 'انفوغراف', 'موشن'],
        '📊 عرض': ['عرض', 'بوربوينت', 'ppt', 'presentation'],
        '📝 تقرير/بحث': ['تقرير', 'بحث', 'مقال', 'مقاله', 'تلخيص', 'ملخص'],
        '🔢 اكسل/بيانات': ['اكسل', 'excel', 'جداول', 'داشبورد', 'احصاء', 'spss'],
        '📖 خصوصي': ['خصوصي', 'مدرس', 'شرح', 'درس', 'تدريس', 'ذاكرني'],
        '📋 واجب/تكليف': ['واجب', 'تكليف', 'اسايمنت', 'assignment'],
        '🎓 مشروع تخرج': ['مشروع تخرج', 'graduation', 'النهائي'],
        '🏥 عذر طبي': ['عذر طبي', 'شهادة صحيه', 'تقرير طبي', 'اعفاء'],
        '🌐 ترجمة': ['ترجمه', 'ترجمة', 'translation'],
        '📄 وورد': ['وورد', 'word', 'ملف وورد'],
    }
    found = []
    for service_name, keywords in services.items():
        for kw in keywords:
            if kw in text_norm:
                found.append(service_name)
                break
    return ' | '.join(found) if found else '📌 خدمة طلابية'

def analyze_message(text: str):
    text_norm = normalize_arabic(text)
    text_len = len(text_norm)
    if text_len < MIN_MSG_LENGTH or text_len > MAX_MSG_LENGTH:
        return False, "طول_غير_مناسب", "", 0

    for bad_word in BLACKLIST_KEYWORDS:
        if normalize_arabic(bad_word) in text_norm:
            return False, "مرفوض", "", 0

    if contains_link(text) or contains_phone(text):
        return False, "رابط_أو_هاتف", "", 0
    if is_pure_greeting(text_norm):
        return False, "تحية", "", 0
    if is_service_provider(text_norm):
        return False, "مزود", "", 0
    if is_knowledge_question(text_norm):
        return False, "سؤال_معلوماتي", "", 0
    if is_pure_inquiry(text_norm):
        if not any(re.search(p, text_norm) for p in EXECUTION_PATTERNS):
            return False, "استفسار", "", 0

    has_exec = any(re.search(p, text_norm) for p in EXECUTION_PATTERNS)
    has_spec = any(re.search(p, text_norm) for p in SERVICE_SPECIFIC_PATTERNS)
    if not has_exec and not has_spec:
        return False, "لا_طلب", "", 0

    urgency = get_urgency_score(text_norm)
    service_type = classify_service_type(text_norm)
    classification = "طلب_مؤكد" if has_exec else "طلب_محتمل"
    return True, classification, service_type, urgency

# ================== 13. ⭐ الرد الذكي من OpenRouter ==================
async def generate_reply_from_ai(text: str, fallback: str) -> str:
    """
    يطلب من AI كتابة الرد كامل.
    لو فشل → يرجع للقالب الاحتياطي.
    """
    if not ai_client:
        return build_fallback_reply(fallback)

    prompt = f"""أنت موظف خدمة عملاء في "أكاديمية خدمات طلابية فورية".
شعارنا: ⚡ سرعة | 🏆 جودة | ✅ موثوقية

رسالة الطالب: "{text}"

اكتب رد بشري قصير جداً (سطر أو سطرين فقط)، باللهجة الخليجية المبسطة.

قواعد صارمة:
1. ابدأ بـ "هلا 🌟" أو "هلا والله" أو "هلا" فقط
2. بعدها "أبشر بسعدك في [نوع الخدمة]" أو "أبشر، خله علينا"
3. اذكر نوع الخدمة بدقة (واجب رياضيات / تصميم شعار / درس فيزياء...)
4. ممنوع منعاً باتاً: ذكر أسعار، وعود بمواعيد، كلمة "بوت"، كلمة "AI"، إطالة
5. لا تضع توقيع
6. لا تستخدم أكثر من إيموجي واحد

أمثلة:
- "أبي أحد يحل واجب رياضيات" → "هلا 🌟
أبشر بسعدك في واجب رياضيات"
- "ابغى تصميم شعار" → "هلا والله
أبشر بسعدك في تصميم شعار"
- "محتاج بحث عن التلوث" → "هلا
أبشر، بحث التلوث خله علينا"

اكتب الرد فقط بدون أي شرح إضافي:"""

    try:
        response = await ai_client.chat.completions.create(
            model=AI_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=100,
        )

        reply = response.choices[0].message.content.strip()
        reply = reply.strip('"').strip("'").strip()

        # فلاتر أمان
        forbidden = ["بوت", "AI", "ذكاء اصطناعي", "سعر", "ريال", "دولار", "دفع", "موعد التسليم"]
        for word in forbidden:
            if word.lower() in reply.lower():
                logger.warning(f"⚠️ AI كتب كلمة ممنوعة: {word}")
                return build_fallback_reply(fallback)

        if len(reply) > 150:
            logger.warning(f"⚠️ AI رد طويل: {len(reply)}")
            return build_fallback_reply(fallback)

        if not reply or len(reply) < 5:
            return build_fallback_reply(fallback)

        logger.info(f"🤖 AI كتب: {reply[:60]}")
        return reply

    except Exception as e:
        logger.error(f"❌ فشل AI: {e}")
        return build_fallback_reply(fallback)


def build_fallback_reply(fallback: str) -> str:
    """رد احتياطي لو AI فشل"""
    return random.choice([
        f"هلا 🌟\nأبشر بسعدك في {fallback}",
        f"هلا\nأبشر، {fallback} خله علينا",
        f"هلا والله\nأبشر بسعدك في {fallback} ✅",
        f"هلا 🌟\nطلبك {fallback} عندنا",
    ])

def extract_summary(service_type: str, text: str) -> str:
    if service_type and service_type != "📌 خدمة طلابية":
        return service_type.replace("📌", "").replace("|", "").strip()
    keywords = ["واجب", "بحث", "تقرير", "مشروع", "تصميم", "برمجة",
                "ترجمة", "عرض", "بوربوينت", "اكسل", "درس", "شرح",
                "اختبار", "عذر", "شعار", "لوجو"]
    t = normalize_arabic(text)
    for kw in keywords:
        if kw in t:
            return kw
    return "طلبك"

async def reply_like_human(client, user_id: int, text: str, fallback: str):
    """يرد على الطالب برد من AI"""
    try:
        await asyncio.sleep(random.uniform(4, 10))

        reply = await generate_reply_from_ai(text, fallback)

        async with client.action(user_id, 'typing'):
            await asyncio.sleep(max(2, len(reply) / 15))

        await client.send_message(user_id, reply)
        logger.info(f"✅ رد → {user_id} | {reply[:60]}")
    except Exception as e:
        logger.error(f"فشل الرد: {e}")

# ================== 14. إرسال حساب الأكاديمية ==================
async def send_academy_account(client, user_id: int, student_name: str):
    """يرسل للزبون حساب الأكاديمية الرسمي"""
    try:
        await asyncio.sleep(random.uniform(2, 5))

        message = (
            f"هلا {student_name} 🌟\n"
            f"\n"
            f"شكراً لتواصلك معنا.\n"
            f"\n"
            f"📌 *حساب {ACADEMY_NAME} الرسمي:*\n"
            f"@{ACADEMY_USERNAME}\n"
            f"\n"
            f"👈 تواصل معه مباشرة، وسيقدم لك خدمتك بأفضل شكل.\n"
            f"\n"
            f"{ACADEMY_TAGLINE}"
        )

        async with client.action(user_id, 'typing'):
            await asyncio.sleep(2)

        await client.send_message(user_id, message)
        logger.info(f"📌 حساب الأكاديمية → {user_id}")

    except Exception as e:
        logger.error(f"فشل إرسال حساب الأكاديمية: {e}")

# ================== 15. الإشعار ==================
async def notify_owner_reply(client, student, reply_text: str):
    if not OWNER_CHAT_ID:
        return

    student_name = getattr(student, 'first_name', 'طالب') or 'طالب'
    username = getattr(student, 'username', None)
    user_id = student.id

    info = REPLIED_STUDENTS.get(user_id, {})
    original = info.get('text', '')[:120]
    service = info.get('service', 'طلب')

    notification = (
        f"💬 *الطالب رد عليك!*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 *الاسم:* {student_name}\n"
        f"🔖 *اليوزر:* @{username or 'بدون'}\n"
        f"🎯 *الخدمة:* {service}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📝 *طلبه الأصلي:*\n_{original}_\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💬 *ردّه الآن:*\n_{reply_text[:200]}_\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔥 *تدخّل الآن!*"
    )

    buttons = []
    if username:
        buttons.append([Button.url("💬 فتح المحادثة", f"https://t.me/{username}")])
    else:
        buttons.append([Button.url("💬 فتح المحادثة", f"tg://user?id={user_id}")])

    try:
        await client.send_message(OWNER_CHAT_ID, notification, buttons=buttons)
        logger.info(f"🔔 إشعار → {student_name}")
    except Exception as e:
        logger.error(f"فشل الإشعار: {e}")

# ================== 16. الروابط ==================
def get_smart_links(chat, event_id: int):
    chat_id = chat.id
    chat_username = getattr(chat, 'username', None)
    group_link = INVITE_LINKS.get(chat_id) or (f"https://t.me/{chat_username}" if chat_username else DEFAULT_INVITE_LINK or "#")

    msg_link = "#"
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

# ================== 17. تنسيق الرسالة ==================
def format_forward_message(event, sender, chat, radar_name, classification, service_type, text, urgency=0, is_special=False):
    username = getattr(sender, 'username', None)
    first_name = getattr(sender, 'first_name', 'مستخدم')
    last_name = getattr(sender, 'last_name', '')
    full_name = f"{first_name} {last_name}".strip() or "مستخدم"
    user_id = sender.id
    chat_title = getattr(chat, 'title', 'مجموعة')
    group_link, msg_link = get_smart_links(chat, event.id)

    display_text = text[:350] + "..." if len(text) > 350 else text
    urgency_icons = {0: "", 1: "⚡", 2: "🔥", 3: "🚨"}
    urgency_icon = urgency_icons.get(urgency, "")

    if is_special:
        msg = (
            f"🔴 **تحويل فوري**\n"
            f"🕐 `{datetime.now().strftime('%H:%M:%S')}` | {radar_name}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 **المرسل:** {full_name}\n"
            f"🔖 **اليوزر:** @{username or 'بدون'}\n"
            f"📍 **المصدر:** {chat_title} ⭐\n"
            f"🔗 [الرسالة]({msg_link})\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📝 الطلب:\n_{display_text}_\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👇 **الطلب👇🏻:**"
        )
    else:
        msg = (
            f"{urgency_icon}⚡️ **طلب خدمة طلابية** {urgency_icon}\n"
            f"🕐 `{datetime.now().strftime('%H:%M:%S')}` | {radar_name}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 **الطالب:** {full_name}\n"
            f"🔖 **اليوزر:** @{username or 'بدون'}\n"
            f"📍 **المصدر:** {chat_title}\n"
            f"🔗 [الرسالة]({msg_link})\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🎯 **نوع الخدمة:** {service_type}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📝 الطلب:\n_{display_text}_\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👇 **الطلب👇🏻:**"
        )

    buttons = []
    if username:
        buttons.append([Button.url("💬 مراسلة الطالب", f"https://t.me/{username}")])
    else:
        buttons.append([Button.url("💬 مراسلة الطالب", f"tg://user?id={user_id}")])

    if group_link and group_link != "#":
        buttons.append([Button.url("👥 الانضمام للمجموعة", group_link)])

    if msg_link and msg_link != "#":
        btn_text = "🔗 رؤية الرسالة" if getattr(chat, 'username', None) else "🔗 الرسالة"
        buttons.append([Button.url(btn_text, msg_link)])

    return msg, buttons

# ================== 18. الرصد ==================
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
    is_replier = (radar_name == REPLIER_ACCOUNT)

    # ── مستمع الخاص ──
    if is_replier:
        @client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
        async def private_handler(event):
            try:
                sender = await event.get_sender()
                user_id = sender.id

                if user_id == OWNER_CHAT_ID:
                    return
                me = await client.get_me()
                if user_id == me.id:
                    return

                text = event.raw_text.strip()
                if not text:
                    return

                if user_id in REPLIED_STUDENTS:
                    info = REPLIED_STUDENTS[user_id]

                    await notify_owner_reply(client, sender, text)

                    if not info.get('academy_sent'):
                        await send_academy_account(
                            client,
                            user_id,
                            getattr(sender, 'first_name', 'عزيزنا')
                        )
                        info['academy_sent'] = True

            except Exception as e:
                logger.error(f"خطأ الخاص: {e}")

    # ── مستمع الرسائل العامة ──
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

            if SPECIAL_CHANNEL_ID != 0 and chat_id == SPECIAL_CHANNEL_ID:
                logger.info(f"⭐ [{radar_name}] تحويل فوري")
                msg, buttons = format_forward_message(
                    event, sender, chat, radar_name,
                    "تحويل_فوري", "خدمة خاصة", text, 0, is_special=True
                )
                await client.send_message(TARGET_CHANNEL, msg, buttons=buttons)
                return

            is_valid, classification, service_type, urgency = analyze_message(text)
            if not is_valid:
                logger.debug(f"🚫 [{radar_name}] {classification}")
                return

            # إرسال للقناة (كل الحسابات ما عدا حساب الرد)
            if not is_replier:
                msg, buttons = format_forward_message(
                    event, sender, chat, radar_name,
                    classification, service_type, text, urgency
                )
                await client.send_message(TARGET_CHANNEL, msg, buttons=buttons)
                logger.info(f"✅ [{radar_name}] {classification} | {service_type}")

            # الرد الذكي (حساب الرد فقط)
            if is_replier and AUTO_REPLY_ENABLED and can_reply_today():
                try:
                    summary = extract_summary(service_type, text)

                    asyncio.create_task(
                        reply_like_human(client, sender.id, text, summary)
                    )

                    REPLIED_STUDENTS[sender.id] = {
                        'name': getattr(sender, 'first_name', ''),
                        'username': getattr(sender, 'username', None),
                        'text': text,
                        'service': summary,
                        'time': datetime.now(),
                        'academy_sent': False,
                    }

                    logger.info(f"📤 [{radar_name}] رد على {sender.id}")

                except Exception as e:
                    logger.error(f"فشل الرد: {e}")

        except Exception as e:
            logger.error(f"❌ [{radar_name}]: {e}", exc_info=True)

    # ── الحلقة ──
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

# ================== 19. التشغيل ==================
async def main():
    logger.info("🚀 بدء الرادار 4.0...")
    logger.info(f"📊 الحسابات: {len(accounts)}")
    logger.info(f"🎯 القناة: {TARGET_CHANNEL}")
    logger.info(f"🎯 حساب الرد: {REPLIER_ACCOUNT}")
    logger.info(f"📩 الإشعارات: {OWNER_CHAT_ID or 'غير محدد!'}")
    logger.info(f"🏫 الأكاديمية: @{ACADEMY_USERNAME}")
    logger.info(f"🤖 AI: {'مفعّل' if ai_client else 'معطّل'} | {AI_MODEL_NAME}")

    tasks = [start_monitoring(acc) for acc in accounts]
    await asyncio.gather(*tasks, return_exceptions=True)

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    logger.info(f"✅ Web على {os.environ.get('PORT', 10000)}")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 إيقاف يدوي")
    except Exception as e:
        logger.error(f"💥 خطأ: {e}", exc_info=True)
