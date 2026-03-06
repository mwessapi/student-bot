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

# ================== سيرفر الويب (لإبقاء البوت حياً) ==================
app = Flask(__name__)

@app.route('/')
def home():
    return "رادار الرصد الذكي (حسابين) يعمل بنجاح!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_flask, daemon=True).start()

# ================== متغيرات البيئة والإعدادات ==================
# نستخدم القيم الثابتة التي أرفقتها لضمان العمل المباشر
API_ID = 2040 
API_HASH = "b18441a1ff607e10a989891a5462e627"
TARGET_CHANNEL = "student1_admin" 

# إعداد الحسابين (حسابك وحساب صديقك)
accounts = [
    {'name': 'رادار [1]', 'id': API_ID, 'hash': API_HASH, 'session': 'session_name'},
    {'name': 'رادار [2]', 'id': API_ID, 'hash': API_HASH, 'session': 'session_2'}
]

# ================== قوائم الكلمات المحسّنة ==================
all_keywords = [
    'حد', 'مين', 'كيف', 'متى', 'سؤال', 'استفسار', 'يعرف', 'يفيدني', 'احتاج', 'ممكن',
    'أبغى', 'ابي', 'وش', 'ايش', 'شنو', 'تكفون', 'ساعدوني', 'بالله', 'لو سمحتو',
    'واجب', 'حل', 'كويز', 'اختبار', 'مشروع', 'بحث', 'تخرج', 'مهندس', 'تصميم', 'برمجة',
    'كود', 'إحصاء', 'رياضيات', 'فيزياء', 'كيمياء', 'ترجمة', 'محاسبة', 'اقتصاد', 'ميد', 'فاينل',
    'عذر', 'غياب', 'سكليف', 'مرضية', 'تجسير', 'دوام', 'تدريب', 'صيفي', 'مادة', 'دكتور',
    'شرح', 'ملخص', 'مساعدة', 'عاجل', 'ضروري', 'تكفى', 'يا جماعة', 'شباب'
]

# كلمات إعلانية للإقصاء (لمنع المزعجين)
forbidden_words = [
    'تواصل', 'واتساب', 'واتس', 'للتواصل', 'ارباح', 'استثمار', 'ضمان', 'سعرنا',
    'راسلني خاص', 'درجة كاملة', 'جميع القطاعات', 'فحص دوري',
    'تأشيرات', 'موجود حل', 'يوجد حل', 'متوفر حل', 'عقد ايجار', 'كشف طبي'
]

# ================== دوال الفلترة الذكية ==================
def normalize_arabic(text):
    """توحيد الحروف العربية لزيادة دقة الرصد"""
    text = re.sub(r'[إأآ]', 'ا', text)
    text = re.sub(r'[ة]', 'ه', text)
    text = re.sub(r'[ًٌٍَُِّْ]', '', text) 
    return text

def is_potential_request(text):
    """تقرير ما إذا كانت الرسالة تستحق الرصد"""
    if not text or len(text) < 5:
        return False
    
    text_norm = normalize_arabic(text.lower())
    
    # منع الإعلانات الصريحة
    if any(ad in text_norm for ad in forbidden_words):
        return False
    if 'wa.me' in text_norm or 't.me/+' in text_norm:
        return False

    # قبول الرسالة إذا احتوت على أي كلمة من القائمة الشاملة
    if any(word in text_norm for word in all_keywords):
        return True
    
    return False

# ================== دالة الرصد الرئيسية ==================
async def start_monitoring(acc_info):
    client = TelegramClient(acc_info['session'], acc_info['id'], acc_info['hash'])
    radar_name = acc_info['name']

    @client.on(events.NewMessage)
    async def handler(event):
        try:
            if event.is_private:
                return

            text = event.raw_text.strip()
            if not is_potential_request(text):
                return

            chat = await event.get_chat()
            sender = await event.get_sender()
            
            username = getattr(sender, 'username', None)
            user_display = f"@{username}" if username else "بدون يوزر"
            first_name = getattr(sender, 'first_name', 'مستخدم')
            
            # تنسيق الرسالة الاحترافي
            display_message = (
                f"⚡️ **رصد جديد عبر {radar_name}**\n"
                f"‏━━━━━━━━━━━━━━━━━━\n"
                f"👤 **العميل:** {first_name} ( {user_display} )\n"
                f"🆔 **ID:** `{sender.id}`\n"
                f"📍 **المصدر:** `{getattr(chat, 'title', 'مجموعة')}`\n"
                f"🔗 [انتقل للرسالة الأصلية](https://t.me/c/{chat.id}/{event.id})\n"
                f"‏━━━━━━━━━━━━━━━━━━\n"
                f"📝 **النص المرصود:**\n"
                f"_{text[:400]}_\n"
                f"‏━━━━━━━━━━━━━━━━━━\n"
                f"👇 **تواصل مع العميل مباشرة:**"
            )

            # إعداد الأزرار لضمان الوصول للعميل
            buttons_list = []
            if username:
                buttons_list.append([Button.url("💬 مراسلة خاصة", f"https://t.me/{username}")])
            buttons_list.append([Button.url("⤴️ الرد في المجموعة", f"https://t.me/c/{chat.id}/{event.id}")])

            await client.send_message(TARGET_CHANNEL, display_message, buttons=buttons_list)

        except Exception as e:
            logger.error(f"خطأ في {radar_name}: {e}")

    # محاولة الاتصال المستمر (Auto-Reconnect)
    while True:
        try:
            await client.start()
            logger.info(f"✅ {radar_name} متصل الآن...")
            await client.run_until_disconnected()
        except Exception as e:
            logger.error(f"❗ انقطع {radar_name}: {e}. إعادة المحاولة...")
            await asyncio.sleep(10)

# ================== التشغيل الرئيسي ==================
async def main():
    logger.info("🚀 جاري تشغيل الرادارات...")
    tasks = [start_monitoring(acc) for acc in accounts]
    await asyncio.gather(*tasks, return_exceptions=True)

if __name__ == '__main__':
    asyncio.run(main())
