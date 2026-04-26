#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎓 رادار الخدمات الطلابية - النسخة المحسّنة 2.0
المطور: [اسمك]
التاريخ: 2026
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

# ================== 2. إعداد التسجيل ==================
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
    return f"<h1>🎓 رادار الخدمات الطلابية</h1><p>✅ يعمل {datetime.now().strftime('%H:%M:%S')}</p>"

@app.route('/health')
def health():
    return jsonify(status="healthy", timestamp=datetime.now().isoformat())

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

threading.Thread(target=run_flask, daemon=True).start()
logger.info(f"✅ سيرفر الويب يعمل على المنفذ {os.environ.get('PORT', 10000)}")

# ================== 4. تحميل متغيرات البيئة ==================
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

# ================== 5. إعدادات التصفية ==================
MIN_MSG_LENGTH = int(os.environ.get("MIN_MSG_LENGTH", "10"))
MAX_MSG_LENGTH = int(os.environ.get("MAX_MSG_LENGTH", "800"))

# ================== 6. إعداد حسابات التليجرام ==================
accounts = []
if SESSION_1:
    accounts.append({'name': 'رادار-1', 'api_id': API_ID, 'api_hash': API_HASH, 'session': SESSION_1})
if SESSION_2:
    accounts.append({'name': 'رادار-2', 'api_id': API_ID, 'api_hash': API_HASH, 'session': SESSION_2})
if not accounts:
    logger.error("❌ لم يتم توفير أي جلسة!")
    sys.exit(1)

logger.info(f"📊 إجمالي الحسابات النشطة: {len(accounts)}")

# ================== 7. إعدادات خاصة ==================
SPECIAL_CHANNEL_ID = int(os.environ.get("SPECIAL_CHANNEL_ID", "-1"))
INVITE_LINKS = {}
DEFAULT_INVITE_LINK = os.environ.get("DEFAULT_INVITE_LINK", "")

# ================== 8. ⭐ القائمة السوداء - محدّثة ومُوسّعة ==================
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
    # استفسارات أكاديمية (ليست طلبات خدمة)
    'الاختبار متى', 'المحاضرة متى', 'الدكتور فلان', 'شعبة كم',
    'رابط القروب', 'ملزمة المادة', 'من وين اذاكر', 'اليوم دوام', 'نزلت الدرجات',
    'جدول المحاضرات', 'جدول الاختبارات', 'موعد الاختبار', 'موعد المحاضرة',
    # إعلانات رسمية
    '[إعلان]', '🔴 هام', '📢 يعلن', 'فرصة عمل', 'مطلوب للعمل',
    # مجرد تحيات
    'كيف حالك', 'وش اخبار', 'ايش مسوين', 'شو رأيكم', 'ايش رأيكم',
    # عروض خدمات (من مزود وليس طالب)
    'نحل', 'نسوي', 'نعطيك', 'تواصل معنا', 'تواصلوا', 'قدم طلبك',
    'اطلب الان', 'اطلب الآن', 'خدمات متنوعة', 'أفضل الأسعار',
    'شركة', 'مؤسسة', 'أكاديمية', 'مركز',
}

# ================== 9. ⭐ أنماط الطلبات - شاملة ومحسّنة ==================

# ── 9أ. أنماط النية الصريحة (الطالب يطلب شخص ينفذ) ──
EXECUTION_PATTERNS = [
    # "ابي/احتاج/محتاج حد/شخص/واحد يسوي..."
    r'(احتاج|احتجاج|محتاج|ابي|ابغى|ابقى|ابا|أبي|أبغى|أحتاج|بدي|حابب|بغيت)\s+(حد|شخص|واحد|أحد|احد|من|مين|مني|احد)\s+(يسوي|يسوى|يشوي|يكمل|ينفذ|يعمل|يجهز|يخلص|يرسل|يحل|يصلح|يكتب|يصمم|يبرمج|يترجم|يعدل|يساعد|يساعدي|يدبر|يضبط|يظبط|يشرح|يذاكر|يحضر|يلخص|يعبي|يرسم|يحسب|يسجل)',

    # "اللي يقدر يسوي..."
    r'(اللي|الي|الذي)\s+(يقدر|يعرف|يفهم|فيه|عنده|معاه|يقدر)\s+(يسوي|يسوى|يكمل|ينفذ|يعمل|يجهز|يخلص|يرسل|يحل|يكتب|يصمم|يبرمج|يترجم|يعدل|يساعد|يشرح|يلخص)',

    # "مين/من يسوي لي..."
    r'(مين|من|مني)\s+(يسوي|يسوى|يشوي|يكمل|ينفذ|يعمل|يجهز|يخلص|يرسل|يحل|يصلح|يكتب|يصمم|يبرمج|يترجم|يعدل|يساعد|يعرف|يفهم|يشرح|يلخص)\s*(لي|لنا|لي ضرة|لينا)?',

    # "حد/شخص/واحد يسوي..."
    r'(حد|شخص|واحد|أحد|احد)\s+(يسوي|يسوى|يشوي|يكمل|ينفذ|يعمل|يجهز|يخلص|يرسل|يحل|يصلح|يكتب|يصمم|يبرمج|يترجم|يعدل|يساعد|يعرف|يفهم|يضبط|يشرح|يذاكر|يلخص|يحضر)',

    # "ابي عرض/واجب/مشروع..."
    r'(احتاج|احتجاج|محتاج|ابي|ابغى|ابقى|ابا|بدي|حابب|عندي|مطلوب|بغيت)\s+(عرض|بوربوينت|بور بوينت|ppt|واجب|واجبات|مشروع|تقرير|تقارير|بحث|بحوث|تلخيص|ملخص|ترجمه|ترجمة|برمجه|برمجة|اكسل|excel|وورد|word|تصميم|خصوصي|عذر\s+طبي|تقرير\s+طبي|شهادة\s+صحيه|مدرس\s+خصوصي|حل\s+واجب|حل\s+اسايمنت|اسايمنت|assignment|مشروع\s+تخرج|بروجكت|project|حل\s+تمارين|شرح\s+مادة|حل\s+اختبار|نموذج)',

    # "يصلح/يحل واجب/تكليف..."
    r'(يصل|يصلح|يحل)\s+(واجب|تكليف|اسايمنت|مشروع|بحث|تقرير)',

    # "يساعدني في..."
    r'(يساعدي|تساعدني|يساعدني|تساعدني)\s+في\s+\w+',

    # "تسوي/يسوي لي عرض/واجب..."
    r'(تسوي|تشوي|يسوي|يشوي|يعمل|تعمل)\s+(لي|لنا|لينا)\s+(عرض|بوربوينت|واجب|تقرير|بحث|مشروع|تصميم|برمجه|برمجة)',

    # أستاذ خصوصي
    r'(ابي|ابغى|احتاج|محتاج|ابا|بدي|مطلوب)\s+خصوصي\s*(في|لمادة|لماده|مادة|لـ)?',
    r'(مدرس|معلم|أستاذ|استاذ)\s+خصوصي\s*(في|لمادة|لـ)?\s*(فيزياء|رياضيات|كيمياء|احياء|انجليزي|انجليش|عربي|برمجه|برمجة|محاسبه|محاسبة|اقتصاد|احصاء|تمريض|طب|ادارة|تسويق|ماثس|كالكولس|حساب|جبر|هندسه|هندسة|فيزكس|كيم)?',
    r'(دروس|درس)\s+خصوصيه?\s*(في|لمادة|لـ)?',
    r'(يشرح|يذاكر\s+معي|يذاكر\s+معاي)\s+(مادة|ماده|مواد)?',

    # عذر طبي
    r'(عذر|تقرير|شهادة)\s+(طبي|طبيه|مرضي|صحيه|صحي)\s*(بسعر|برسوم|بفلوس|رخيص)?',
    r'(ابي|احتاج|محتاج)\s+(عذر|إعفاء|اعفاء)\s+(طبي|رسمي)',

    # "أبحث عن حد يسوي..."
    r'(دور|ابحث|أبحث|نبحث)\s+(لي|لنا)?\s*(عن|على)\s+(حد|شخص|واحد)\s+(يسوي|يكمل|ينفذ|يعمل|يساعد)',

    # "يخلص لي الواجب..."
    r'(يخلص|يكمل|ينهي)\s+(لي|لنا)?\s*(الواجب|التكليف|المشروع|الاسايمنت|البحث)',

    # "ودي احد يسوي..."
    r'(ودي|وداي|وددت|بودي)\s+(احد|حد|شخص)\s+(يسوي|يعمل|يكمل|يحل)',

    # "فيه احد يقدر..."
    r'(فيه|في|هل\s+في|هل\s+فيه|ما\s+في)\s+(احد|حد|شخص|واحد)\s+(يقدر|يعرف|يسوي|يعمل|يكمل|يحل)',

    # "محتاج مساعدة في..."
    r'(محتاج|ابي|احتاج)\s+(مساعده|مساعدة|مساعد)\s+في\s+(برمجه|برمجة|تصميم|اكسل|وورد|واجب|مشروع|بحث|تقرير|عرض)',

    # لغة إنجليزية مع عربي
    r'(need|looking\s+for|want)\s+(someone|anyone|help)\s+(to|for)',
    r'(محتاج|ابي)\s+(freelancer|help|someone)',
]

# ── 9ب. أنماط الخدمات المحددة (حتى بدون "حد يسوي") ──
SERVICE_SPECIFIC_PATTERNS = [
    # برمجة
    r'(مشروع|بروجكت|project)\s+(برمجه|برمجة|python|java|c\+\+|web|موبايل|تطبيق|app|website)',
    r'(برمجه|برمجة|كود|code)\s+(جاهز|كامل|مكتمل)',
    r'(اسايمنت|assignment)\s+(برمجه|برمجة|python|java|html|css)',

    # تصميم
    r'(تصميم|شعار|لوجو|logo|بنر|banner|انفوغراف|infographic)\s+(احتاج|محتاج|ابي|مطلوب)',
    r'(احتاج|محتاج|ابي)\s+(تصميم|شعار|لوجو|موشن|فيديو\s+تصميم)',

    # عروض
    r'(عرض|بوربوينت|بور\s+بوينت|ppt|presentation)\s+(احتاج|محتاج|ابي|مطلوب|كامل|جاهز)',
    r'(احتاج|محتاج|ابي)\s+(عرض|بوربوينت)\s+\w+',

    # تقارير وأبحاث
    r'(تقرير|بحث)\s+(احتاج|محتاج|ابي|مطلوب|جاهز|كامل)',
    r'(احتاج|محتاج|ابي)\s+(تقرير|بحث)\s+عن',

    # ترجمة
    r'(ترجمه|ترجمة)\s+(ملف|وثيقه|نص|مقاله|مقال|بحث)\s*(احتاج|محتاج|ابي|مطلوب)?',

    # اكسل وبيانات
    r'(اكسل|excel|جداول|pivot|داشبورد|dashboard)\s*(احتاج|محتاج|ابي|مطلوب)?',

    # مشاريع تخرج
    r'(مشروع\s+تخرج|graduation\s+project|مشروع\s+النهائي)\s*(احتاج|محتاج|ابي|مطلوب)?',
]

# ── 9ج. مؤشرات الاستعجال (تزيد ثقل القرار) ──
URGENCY_INDICATORS = [
    r'(عاجل|ضروري|مستعجل|بسرعه|بسرعة|اليوم|الحين|هلا|على\s+طول)',
    r'(التسليم|الديدلاين|deadline)\s+(اليوم|غداً|غدا|بكره|بعدين)',
    r'(آخر\s+موعد|اخر\s+موعد)\s+(اليوم|غد|الساعه)',
    r'(بكره\s+اختبار|اختبار\s+بكره|غداً\s+اختبار)',
    r'(فاضل|باقي)\s+(يوم|ساعات|وقت\s+قليل)',
]

# ── 9د. أنماط استفسار صريحة يجب رفضها ──
INQUIRY_PATTERNS = [
    # أسئلة أكاديمية
    r'^(كيف|كيفه|كيفها)\s+(تحل|تعمل|تسوي|يحل|يعمل|نعمل)',
    r'^(ايش|ايش\s+هو|ما\s+هو|ما)\s+(الفرق|الأفضل|أفضل)',
    r'^(من\s+درس|من\s+شرح|من\s+فهم)\s+\w+',
    r'^(وين|أين|من\s+وين)\s+(نلقى|نحصل|الكتاب|الملزمة|المادة)',
    r'^(هل\s+نزلت|نزلت|صدرت)\s+(الدرجات|النتائج|الجدول)',
    r'^(متى|امتى)\s+(الاختبار|المحاضرة|التسليم|الدوام)',
    r'^(كم\s+درجة|كم\s+الدرجة|كم\s+السعر)',

    # استطلاع رأي
    r'^(شو|ايش|وش)\s+(رأيكم|رايكم|تقولون|تقول)',
    r'^(من\s+جرب|من\s+استخدم|من\s+اخذ)\s+\w+',

    # نقاشات
    r'^(صح|صحيح|غلط)\s+(ان|إن)',
    r'^(الله\s+يعين|يا\s+حيف|حظ\s+حلو)',
]

# ================== 10. القائمة السوداء ==================
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

# ================== 11. منع تكرار ==================
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
    """توحيد الكتابة العربية"""
    text = re.sub(r'[إأآا]', 'ا', text)
    text = re.sub(r'[ةه]', 'ه', text)
    text = re.sub(r'[ىي]', 'ي', text)
    text = re.sub(r'[\u064B-\u065F\u0670]', '', text)  # إزالة التشكيل
    text = re.sub(r'(.)\1{2,}', r'\1\1', text)  # تقليص التكرار (مثل "ابييي" → "ابي")
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
    """هل الرسالة مجرد تحية؟"""
    greetings = [
        'سلام عليكم', 'السلام عليكم', 'مساء الخير', 'صباح النور',
        'صباح الخير', 'مساء النور', 'اهلين', 'هلا', 'هاي', 'مرحبا',
        'هلا وغلا', 'اهلا وسهلا', 'يا هلا', 'هلا بالجميع', 'هلا شباب',
        'حياكم', 'يا اهلين', 'اهلا بكم', 'هلا فيكم'
    ]
    stripped = text_norm.strip()
    for g in greetings:
        if stripped == g or stripped.startswith(g) and len(stripped) - len(g) < 5:
            return True
    return False

def is_pure_inquiry(text_norm: str) -> bool:
    """هل الرسالة مجرد استفسار أكاديمي بدون طلب تنفيذ؟"""
    for pattern in INQUIRY_PATTERNS:
        if re.search(pattern, text_norm, re.IGNORECASE):
            return True
    return False

def is_service_provider(text_norm: str) -> bool:
    """هل المرسل يعرض خدمة (مزود) وليس يطلبها (طالب)؟"""
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
    """حساب درجة الاستعجال (0-3)"""
    score = 0
    for pattern in URGENCY_INDICATORS:
        if re.search(pattern, text_norm):
            score += 1
    return min(score, 3)

def classify_service_type(text_norm: str) -> str:
    """تصنيف نوع الخدمة المطلوبة"""
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
    if found:
        return ' | '.join(found)
    return '📌 خدمة طلابية'

# ================== 13. ⭐ نظام التحليل الذكي المحسّن ==================
def analyze_message(text: str) -> tuple[bool, str, str, int]:
    """
    تحليل الرسالة وإرجاع: (هل_صالح, التصنيف, نوع_الخدمة, درجة_الاستعجال)
    """
    text_norm = normalize_arabic(text)

    # ── فلتر 1: الحد الأدنى والأقصى للطول ──
    text_len = len(text_norm)
    if text_len < MIN_MSG_LENGTH or text_len > MAX_MSG_LENGTH:
        return False, "طول_غير_مناسب", "", 0

    # ── فلتر 2: القائمة السوداء ──
    for bad_word in BLACKLIST_KEYWORDS:
        if normalize_arabic(bad_word) in text_norm:
            return False, "مرفوض_قائمة_سوداء", "", 0

    # ── فلتر 3: روابط وأرقام هواتف ──
    if contains_link(text) or contains_phone(text):
        return False, "يحتوي_رابط_أو_هاتف", "", 0

    # ── فلتر 4: مجرد تحية ──
    if is_pure_greeting(text_norm):
        return False, "تحية_فقط", "", 0

    # ── فلتر 5: مزود خدمة وليس طالب ──
    if is_service_provider(text_norm):
        return False, "مزود_خدمة_وليس_طالب", "", 0

    # ── فلتر 6: استفسار صريح بدون طلب تنفيذ ──
    if is_pure_inquiry(text_norm):
        # لكن تحقق هل فيه نية تنفيذ رغم ذلك
        has_execution = any(re.search(p, text_norm) for p in EXECUTION_PATTERNS)
        if not has_execution:
            return False, "استفسار_فقط", "", 0

    # ── اكتشاف نية التنفيذ ──
    has_execution_intent = any(re.search(p, text_norm) for p in EXECUTION_PATTERNS)
    has_service_specific = any(re.search(p, text_norm) for p in SERVICE_SPECIFIC_PATTERNS)

    if not has_execution_intent and not has_service_specific:
        return False, "لا_طلب_تنفيذ", "", 0

    # ── حساب الاستعجال ──
    urgency = get_urgency_score(text_norm)

    # ── تصنيف نوع الخدمة ──
    service_type = classify_service_type(text_norm)

    # ── تحديد التصنيف النهائي ──
    if has_execution_intent:
        classification = "طلب_تنفيذ_مؤكد"
    else:
        classification = "طلب_خدمة_محتمل"

    return True, classification, service_type, urgency

# ================== 14. دالة إنشاء الروابط الذكية ==================
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

# ================== 15. ⭐ تنسيق رسالة القناة ==================
def format_forward_message(
    event, sender, chat, radar_name: str,
    classification: str, service_type: str,
    text: str, urgency: int = 0,
    is_special: bool = False
) -> tuple[str, list]:
    username = getattr(sender, 'username', None)
    first_name = getattr(sender, 'first_name', 'مستخدم')
    last_name = getattr(sender, 'last_name', '')
    full_name = f"{first_name} {last_name}".strip() or first_name
    user_id = sender.id
    chat_title = getattr(chat, 'title', 'مجموعة')
    group_link, msg_link = get_smart_links(chat, event.id)

    # عرض النص بشكل واضح
    if len(text) > 350:
        display_text = text[:350] + "..."
    else:
        display_text = text

    # أيقونة الاستعجال
    urgency_icons = {0: "", 1: "⚡", 2: "🔥", 3: "🚨"}
    urgency_icon = urgency_icons.get(urgency, "")

    if is_special:
        msg = (
            f"🔴 **تحويل فوري | قناة خاصة**\n"
            f"🕐 `{datetime.now().strftime('%H:%M:%S')}` | عبر {radar_name}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 **المرسل:** {full_name}\n"
            f"🔖 **اليوزر:** @{username or 'بدون'}\n"
            f"📍 **المصدر:** {chat_title} ⭐\n"
            f"🔗 [الرسالة الأصلية]({msg_link})\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📝 **النص:**\n_{display_text}_\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👇 **إجراءات سريعة:**"
        )
    else:
        msg = (
            f"{urgency_icon}⚡️ **طلب خدمة طلابية** {urgency_icon}\n"
            f"🕐 `{datetime.now().strftime('%H:%M:%S')}` | {radar_name}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 **الطالب:** {full_name}\n"
            f"🔖 **اليوزر:** @{username or 'بدون'}\n"
            f"📍 **المصدر:** {chat_title}\n"
            f"🔗 [الرسالة الأصلية]({msg_link})\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🎯 **نوع الخدمة:** {service_type}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📋 **الطلب:**\n_{display_text}_\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👇 **إجراءات سريعة:**"
        )

    buttons = []
    if username:
        buttons.append([Button.url("💬 مراسلة الطالب", f"https://t.me/{username}")])
    else:
        buttons.append([Button.url("💬 مراسلة الطالب (خاص)", f"tg://user?id={user_id}")])

    if group_link and group_link != "#":
        buttons.append([Button.url("👥 الانضمام للمجموعة", group_link)])

    if msg_link and msg_link != "#":
        btn_text = "🔗 رؤية الرسالة" if chat.username else "🔗 الرسالة (للأعضاء فقط)"
        buttons.append([Button.url(btn_text, msg_link)])

    return msg, buttons

# ================== 16. دالة الرصد الرئيسية ==================
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

            # تحويل فوري من القناة الخاصة
            if SPECIAL_CHANNEL_ID > 0 and chat_id == SPECIAL_CHANNEL_ID:
                logger.info(f"⭐ [{radar_name}] تحويل فوري من القناة الخاصة")
                msg, buttons = format_forward_message(
                    event, sender, chat, radar_name,
                    classification="تحويل_فوري", service_type="خدمة خاصة",
                    text=text, urgency=0, is_special=True
                )
                await client.send_message(TARGET_CHANNEL, msg, buttons=buttons, silent=False)
                return

            # تحليل الرسالة
            is_valid, classification, service_type, urgency = analyze_message(text)
            if not is_valid:
                logger.debug(f"🚫 [{radar_name}] {classification} | {text[:40]}")
                return

            msg, buttons = format_forward_message(
                event, sender, chat, radar_name,
                classification, service_type, text, urgency, is_special=False
            )
            await client.send_message(TARGET_CHANNEL, msg, buttons=buttons, silent=False)
            logger.info(f"✅ [{radar_name}] {classification} | {service_type} | ⚡{urgency} | {text[:35]}...")

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

# ================== 17. التشغيل الرئيسي ==================
async def main():
    logger.info("🚀 بدء تشغيل رادار الخدمات الطلابية 2.0...")
    logger.info(f"📊 الحسابات النشطة: {len(accounts)}")
    logger.info(f"🎯 القناة المستهدفة: {TARGET_CHANNEL}")
    if SPECIAL_CHANNEL_ID > 0:
        logger.info(f"⭐ القناة الخاصة للتحويل الفوري: {SPECIAL_CHANNEL_ID}")

    tasks = [start_monitoring(acc) for acc in accounts]
    await asyncio.gather(*tasks, return_exceptions=True)

# ================== 18. نقطة الدخول ==================
if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 تم إيقاف البوت يدوياً")
    except Exception as e:
        logger.error(f"💥 خطأ فادح في التشغيل: {e}", exc_info=True)
        import traceback
        traceback.print_exc()

