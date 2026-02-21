import telebot
from telebot import types
import os
from flask import Flask
from threading import Thread

# --- نظام إيهام Render بأن البوت "موقع ويب" لضمان عدم التوقف ---
app = Flask('')

@app.route('/')
def home():
    return "Status: Online & Monitoring"

def run():
    # Render يتطلب فتح منفذ (Port) وإلا سيوقف الخدمة بعد دقائق
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
# ---------------------------------------------------------

TOKEN = "8414496098:AAEqASKbIaaPwf0OQs95tYVE3qTwJOio_Zs"
bot = telebot.TeleBot(TOKEN)

# قائمة الكلمات المفتاحية الشاملة التي حددتها لمشروعك
KEYWORDS = [
    "واجب", "حد", "مطلوب", "أحتاج", "ابي", "بغيت", "مين يحل", "مين يسوي", "مساعدة في", 
    "عذر", "اعذار", "عذر طبي", "سكليف", "sick leave", "تقرير طبي",
    "حل واجب", "حل اختبار", "كويز", "ميد", "فاينل", "بحث", "مشروع", 
    "اسايمنت", "تخرج", "تنسيق", "كتابة", "ترجمة", "تلخيص", 
    "بوربوينت", "برزنتيشن", "عرض", "عروض", "تصميم", "سيرة ذاتية"
]

# قناتك العامة التي يجب أن يكون البوت مشرفاً فيها
CHANNEL = "@student1_admin"

@bot.message_handler(func=lambda message: True)
def listen(message):
    # تجاهل الرسائل القصيرة جداً لضمان جودة الطلبات
    if not message.text or len(message.text) < 5:
        return
    
    text = message.text.lower()
    
    # التحقق من وجود أي كلمة من القائمة في نص الرسالة
    if any(word in text for word in KEYWORDS):
        username = message.from_user.username
        user_id = message.from_user.id
        group_name = message.chat.title if message.chat.title else "مجموعة غير معروفة"
        
        # إنشاء رابط الرسالة المباشر للوصول السريع
        chat_id_str = str(message.chat.id).replace("-100", "")
        message_id = message.message_id
        
        if message.chat.username:
            msg_link = f"https://t.me/{message.chat.username}/{message_id}"
        else:
            msg_link = f"https://t.me/c/{chat_id_str}/{message_id}"

        # تنسيق الرسالة التي ستصل للقناة
        msg = f"⚡️ **طلب خدمة طلابية جديد**\n" \
              f"─────────────────\n" \
              f"👤 **العميل:** @{username if username else 'بدون معرف'}\n" \
              f"🆔 **ID:** `{user_id}`\n" \
              f"📍 **المصدر:** {group_name}\n" \
              f"🔗 [انتقل للرسالة الأصلية]({msg_link})\n\n" \
              f"📝 **نص الطلب:**\n_{message.text}_\n" \
              f"─────────────────\n" \
              f"👇 **تواصل مع العميل مباشرة:**"

        # إضافة زر المراسلة الفورية
        markup = types.InlineKeyboardMarkup()
        if username:
            btn_contact = types.InlineKeyboardButton("💬 مراسلة الطالب (خاص)", url=f"tg://resolve?domain={username}")
            markup.add(btn_contact)
        
        try:
            bot.send_message(CHANNEL, msg, reply_markup=markup, disable_web_page_preview=True, parse_mode="Markdown")
        except Exception as e:
            print(f"حدث خطأ أثناء الإرسال: {e}")

if __name__ == "__main__":
    keep_alive() # تشغيل خادم الويب الوهمي
    print("البوت يعمل الآن ويراقب الطلبات...")
    bot.infinity_polling()
