import re
from datetime import datetime

@client.on(events.NewMessage)
async def handler(event):
    try:
        if event.is_private: return 
        
        text = event.raw_text.strip()
        length = len(text)
        
        # 1. الفلاتر الصارمة ضد الإعلانات والمروجين
        # تجاهل أي رسالة تحتوي على يوزر، روابط، أو تطبيقات أخرى
        if any(x in text for x in ['@', 'http', 'wa.me', 't.me', 'snapchat', 'instagram']):
            return
        
        # تجاهل الرسائل التي تحتوي على أرقام هواتف طويلة
        if re.search(r'\d{8,}', text):
            return

        # 2. القائمة الشاملة (طلبات + أعذار + "حد")
        keywords = [
            'حد', 'واجب', 'حل', 'كويز', 'اختبار', 'مشروع', 'بحث', 'تخرج', 
            'عذر', 'اعذار', 'إجازة مرضية', 'تقرير طبي', 'سكليف', 'غياب',
            'ممكن حل', 'أحتاج مساعدة', 'ميد ترم', 'فاينل', 'مين يعرف'
        ]
        
        # 3. كلمات الاستبعاد لضمان "نظافة" القناة
        forbidden = ['ثقة', 'دقة', 'انجاز', 'ضمان', 'تواصل', 'واتساب', 'سعر', 'متوفر']

        # 4. شروط الدقة (الطول المناسب لطلب الطالب)
        if any(word in text.lower() for word in keywords):
            # تم ضبط الطول ليكون بين 20 و 65 حرفاً لالتقاط الجمل القصيرة مثل "حد يحل واجب؟"
            if 20 <= length <= 65:
                if not any(bad in text for bad in forbidden):
                    
                    # --- واجهة العرض الاحترافية ---
                    chat = await event.get_chat()
                    chat_title = chat.title if hasattr(chat, 'title') else "مجموعة غير معروفة"
                    time_now = datetime.now().strftime("%I:%M %p")
                    
                    display_message = (
                        f"**🌟 رصد جديد (طلب/استفسار)**\n"
                        f"‏━━━━━━━━━━━━━━━━━━\n"
                        f"**📍 المصدر:** `{chat_title}`\n"
                        f"**⏰ الوقت:** `{time_now}`\n"
                        f"‏━━━━━━━━━━━━━━━━━━\n"
                        f"**📝 نص الرسالة:**\n"
                        f"_{text}_\n"
                        f"‏━━━━━━━━━━━━━━━━━━\n"
                        f"**🔗 الإجراء:** [الانتقال للمحادثة](https://t.me/c/{chat.id}/{event.id})"
                    )
                    
                    # إرسال الرسالة للقناة
                    await client.send_message('student1_admin', display_message, link_preview=False)
                    print(f"✅ تم رصد طلب يحتوي على كلمة (حد) من: {chat_title}")
                
    except Exception as e:
        print(f"⚠️ خطأ: {e}")
