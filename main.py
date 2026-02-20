import telebot

# التوكن الخاص بك
TOKEN = "8414496098:AAEqASKbIaaPwf0OQs95tYVE3qTwJOio_Zs"

bot = telebot.TeleBot(TOKEN)

# قائمة الكلمات المفتاحية
KEYWORDS = ["حل", "واجب", "اختبار", "تصميم", "مشروع", "بحث", "اسايمنت", "تلخيص", "ترجمة", "مساعدة"]

# معرف القناة (إدارة طلبات الطلاب)
CHANNEL = "@student1_admin"

@bot.message_handler(func=lambda message: True)
def listen(message):
    if not message.text:
        return

    text = message.text.lower()
    
    if any(word in text for word in KEYWORDS):
        username = message.from_user.username if message.from_user.username else "بدون معرف"
        group = message.chat.title if message.chat.title else "دردشة"

        msg = f"📢 طلب جديد\n👤 المستخدم: @{username}\n👥 المجموعة: {group}\n\n💬 الطلب:\n{message.text}"
        
        try:
            bot.send_message(CHANNEL, msg)
        except Exception as e:
            print(f"Error: {e}")

bot.infinity_polling()

