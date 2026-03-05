from telethon import TelegramClient, events

# استخدام أرقام API عامة لتجاوز حظر الموقع الرسمي
API_ID = 2040 
API_HASH = 'b18441a1ff607e10a989891a5462e627'
TARGET_CHANNEL = 'student1_admin' 

client = TelegramClient('session_name', API_ID, API_HASH)

@client.on(events.NewMessage)
async def my_event_handler(event):
    if event.is_private: return 
    
    # القائمة الشاملة التي طلبتها (أكثر من 30 كلمة)
    KEYWORDS = [
        "واجب", "حل", "بحث", "مشاريع", "مشروع", "اختبار", "كويز", 
        "ميد", "فاينل", "تلخيص", "بوربوينت", "عرض", "تخرج", "أبي حل", 
        "احتاج حل", "مساعدة", "تكليف", "واجبات", "assignment", "quiz",
        "هومورك", "عملي", "نظري", "تقرير", "بحوث", "حلول", "نماذج",
        "ترجمة", "تدقيق", "تصميم", "شرح", "مسألة", "كتابة", "برمجة"
    ]
    
    message_text = event.message.message.lower()
    if any(word in message_text for word in KEYWORDS):
        sender = await event.get_sender()
        chat = await event.get_chat()
        
        alert_msg = (
            f"🚀 **طلب جديد مرصود**\n"
            f"──────────────────\n"
            f"👤 **العميل:** @{sender.username if sender.username else 'بدون يوزر'}\n"
            f"📍 **المجموعة:** {chat.title}\n\n"
            f"📝 **النص:**\n_{message_text}_\n"
            f"──────────────────\n"
            f"🔗 [اضغط لمراسلة العميل](tg://user?id={sender.id})"
        )
        await client.send_message(TARGET_CHANNEL, alert_msg)

print("الرصد الشامل يعمل الآن...")
client.start()
client.run_until_disconnected()
