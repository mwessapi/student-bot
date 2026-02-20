import telebot
from telebot import types

TOKEN = "8414496098:AAEqASKbIaaPwf0OQs95tYVE3qTwJOio_Zs"
bot = telebot.TeleBot(TOKEN)

# قائمة الكلمات المفتاحية المحدثة (تشمل "واجب" و "حد" والأعذار)
KEYWORDS = [
    "واجب", "حد", "مطلوب", "أحتاج", "ابي", "بغيت", "مين يحل", "مين يسوي", "مساعدة في", 
    "عذر", "اعذار", "عذر طبي", "سكليف", "sick leave", "تقرير طبي",
    "حل واجب", "حل اختبار", "كويز", "ميد", "فاينل", "بحث", "مشروع", 
    "اسايمنت", "تخرج", "تنسيق", "كتابة", "ترجمة", "تلخيص", 
    "بوربوينت", "برزنتيشن", "عرض", "عروض", "تصميم", "سيرة ذاتية"
]

CHANNEL = "@student1_admin"

@bot.message_handler(func=lambda message: True)
def listen(message):
    if not message.text:
        return
    
    text = message.text.lower()
    
    # التحقق من وجود الكلمات المفتاحية
    if any(word in text for word in KEYWORDS):
        username = message.from_user.username
        user_id = message.from_user.id
        group_name = message.chat.title if message.chat.title else "Group"
        
        # محاولة جلب رابط المجموعة
        try:
            if message.chat.username:
                group_link = f"https://t.me/{message.chat.username}"
            else:
                group_link = bot.export_chat_invite_link(message.chat.id)
        except:
            group_link = "Private Group"

        # تنسيق الرسالة لسرعة المنافسة بين مقدمي الخدمة
        msg = f"⚡️ **طلب جديد - سارع بالتواصل**\n" \
              f"─────────────────\n" \
              f"👤 **العميل:** @{username if username else 'بدون معرف'}\n" \
              f"🆔 **ID:** `{user_id}`\n" \
              f"📍 **المجموعة:** {group_name}\n" \
              f"🔗 **الرابط:** [اضغط لدخول المجموعة]({group_link})\n\n" \
              f"📝 **الطلب:**\n{message.text}\n" \
              f"─────────────────\n" \
              f"👇 **تواصل مع العميل مباشرة:**"

        # زر المراسلة الفورية
        markup = types.InlineKeyboardMarkup()
        if username:
            btn_contact = types.InlineKeyboardButton("💬 مراسلة الطالب (خاص)", url=f"tg://resolve?domain={username}")
            markup.add(btn_contact)
        
        try:
            bot.send_message(CHANNEL, msg, reply_markup=markup, disable_web_page_preview=True, parse_mode="Markdown")
        except Exception as e:
            print(f"Error: {e}")

bot.infinity_polling()
