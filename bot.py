import logging
import asyncio
import openpyxl
import requests
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# === SOZLAMALAR ===
BOT_TOKEN = "9134191336:AAGQwRM2-Wi1houBfOpz3cXcdDQb_XDw2Ks"

# Bot egasi va xodimlar Telegram ID raqamlari
XODIM_IDS = [
    772922699,    
]

# Eskiz.uz ma'lumotlaringiz (SMS uchun)
ESKIZ_EMAIL = "sizning_email@gmail.com"
ESKIZ_PASSWORD = "sizning_eskiz_parolingiz"
ESKIZ_TOKEN = "" 

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

DEBTORS_DATA = []
is_sending_active = False

# Eskiz.uz dan avtomatik Token olish
def get_eskiz_token():
    global ESKIZ_TOKEN
    try:
        url = "https://notify.eskiz.uz/api/auth/login"
        payload = {'email': ESKIZ_EMAIL, 'password': ESKIZ_PASSWORD}
        res = requests.post(url, data=payload).json()
        if 'data' in res and 'token' in res['data']:
            ESKIZ_TOKEN = res['data']['token']
            return ESKIZ_TOKEN
    except Exception as e:
        print(f"Eskiz token olishda xatolik: {e}")
    return None

# SMS yuborish funksiyasi
def send_sms_via_gateway(phone: str, message_text: str):
    global ESKIZ_TOKEN
    if not ESKIZ_TOKEN:
        get_eskiz_token()
        
    try:
        clean_phone = str(phone).replace("+", "").replace(" ", "").strip()
        url = "https://notify.eskiz.uz/api/message/sms/dispatch"
        payload = {
            'mobile_phone': clean_phone,
            'message': message_text,
            'from': '4546'
        }
        headers = {'Authorization': f'Bearer {ESKIZ_TOKEN}'}
        response = requests.post(url, data=payload, headers=headers)
        res_json = response.json()
        
        if response.status_code == 401:
            get_eskiz_token()
            headers = {'Authorization': f'Bearer {ESKIZ_TOKEN}'}
            response = requests.post(url, data=payload, headers=headers)
            res_json = response.json()
            
        return res_json
    except Exception as e:
        print(f"SMS yuborishda xatolik: {e}")
        return None

# Odatiy mijozlar uchun menyu
def get_user_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📞 Ofis bilan bog'lanish", callback_data="contact_office")
    builder.button(text="💬 Murojaat qoldirish", callback_data="leave_request")
    builder.button(text="🌐 E_DOCS Rasmiy Sayti", url="https://t.me/AESEDOCS_bot")
    builder.adjust(1, 1, 1)
    return builder.as_markup()

# Bot egasi / Xodimlar uchun boshqaruv tugmalari
def get_admin_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🚀 Hozir xabar yuborish", callback_data="send_now")
    builder.button(text="⏹ To'xtatish", callback_data="stop_sending")
    builder.button(text="📊 Statusni ko'rish", callback_data="status")
    builder.adjust(2, 1)
    return builder.as_markup()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    
    if user_id in XODIM_IDS:
        await message.answer(
            "👋 Assalomu alaykum, hurmatli Bot Egasi / Xodim!\n\n"
            "📁 Yangi qarzdorlik Excel faylini (`telegram_id`, `telefon`, `mijoz_ismi`, `qarzdorlik` ustunlari bilan) istalgan vaqtda yuborib yangilashingiz mumkin.\n"
            "Xabarlar har kuni **09:00** va **19:00** da avtomatik yuboriladi.\n"
            "Boshqarish uchun quyidagi tugmalardan foydalaning:",
            reply_markup=get_admin_keyboard()
        )
    else:
        welcome_text = (
            "🇺🇿 **Assalomu alaykum, xush kelibsiz!**\n\n"
            "🏢 **E_DOCS — Buxgalteriya va Soliq Konsalting Xizmati** markazining rasmiy botiga kirdingiz.\n\n"
            "Soliq hisobotlari va buxgalteriya bo'yicha professional xizmatlarimizdan foydalanish uchun ofisimizga murojaat qilishingiz mumkin."
        )
        await message.answer(welcome_text, reply_markup=get_user_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data == "contact_office")
async def contact_office_callback(callback: types.CallbackQuery):
    text = (
        "📞 **Ofis bilan bog'lanish uchun raqamlar:**\n\n"
        "• Ofis Telegram/Tel: `+998 95 202 74 04`\n"
        "• Markaziy operator: `+998 50 203 14 14`\n"
        "• Bahtiyorjon (Ofis): `+998 90 140 14 14`\n"
        "• Elyorbek (Soliq eksperti): `+998 90 149 01 05`\n"
        "• Abdulatif (Gl. buxgalter): `+998 91 167 88 98`\n"
        "• Ilhomjon (Konsultant): `+998 91 498 15 15`"
    )
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "leave_request")
async def leave_request_callback(callback: types.CallbackQuery):
    await callback.message.answer(
        "✍️ **Murojaat qoldirish uchun:**\n\n"
        "Iltimos, savolingizni yoki murojaatingizni shu yerga yozib yuboring. Mutaxassislarimiz tez orada javob berishadi!"
    )
    await callback.answer()

@dp.message(F.document == False)
async def handle_user_text_message(message: types.Message):
    if message.from_user.id in XODIM_IDS:
        return
        
    user_name = message.from_user.full_name
    user_username = f"@{message.from_user.username}" if message.from_user.username else "Mavjud emas"
    user_text = message.text
    
    if message.text.startswith("/"):
        return

    admin_notification = (
        "💬 **E_DOCS BOTDAN YANGI MUROJAAT!**\n\n"
        f"👤 **Mijoz:** {user_name} ({user_username})\n"
        f"🆔 **ID:** `{message.from_user.id}`\n"
        f"✉️ **Xabar:** {user_text}\n\n"
        "👇 *Javob yozish uchun ushbu xabarga Reply qiling.*"
    )
    
    for admin_id in XODIM_IDS:
        try:
            await bot.send_message(chat_id=admin_id, text=admin_notification, parse_mode="Markdown")
        except Exception as e:
            print(f"Admin xabar yuborish xatosi: {e}")
            
    await message.answer("✅ Murojaatingiz qabul qilindi! Mutaxassislarimiz tez orada siz bilan bog'lanishadi.")

# Yangi Excel yuklash va eskisini yangilash
@dp.message(F.document)
async def handle_excel_upload(message: types.Message):
    global DEBTORS_DATA, is_sending_active
    if message.from_user.id not in XODIM_IDS:
        await message.answer("⛔ Kechirasiz, bu funksiya faqat bot egasi uchun.")
        return
    
    if not message.document.file_name.endswith('.xlsx'):
        await message.answer("⚠️ Faqat Excel (.xlsx) fayl yuboring.")
        return

    if is_sending_active:
        is_sending_active = False

    file_id = message.document.file_id
    file = await bot.get_file(file_id)
    downloaded_file = await bot.download_file(file.file_path)
    
    try:
        wb = openpyxl.load_workbook(downloaded_file)
        sheet = wb.active
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            await message.answer("⚠️ Excel fayl bo'sh!")
            return
            
        headers = [str(h).strip().lower() if h else "" for h in rows[0]]
        
        DEBTORS_DATA = []
        for row in rows[1:]:
            row_dict = dict(zip(headers, row))
            DEBTORS_DATA.append(row_dict)
        
        await message.answer(
            f"✅ Yangi Excel muvaffaqiyatli yuklandi va yangilandi!\n"
            f"📊 Jami mijozlar: {len(DEBTORS_DATA)} ta.\n"
            f"Xabarlar har kuni 09:00 va 19:00 da avtomatik boradi.",
            reply_markup=get_admin_keyboard()
        )
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}")

# Xabarlarni tarqatish va to'xtatish funksiyasi
async def process_sending(chat_id_to_report=None):
    global DEBTORS_DATA, is_sending_active
    if not DEBTORS_DATA:
        if chat_id_to_report:
            await bot.send_message(chat_id_to_report, "⚠️ Hali Excel fayl yuklanmagan yoki ro'yxat bo'sh!")
        return

    is_sending_active = True
    sent_count = 0

    if chat_id_to_report:
        await bot.send_message(chat_id_to_report, "🚀 Xabarlar jo'natila boshlandi...")

    for item in DEBTORS_DATA:
        if not is_sending_active:
            if chat_id_to_report:
                await bot.send_message(chat_id_to_report, f"⏹ Xabar yuborish muvaffaqiyatli to'xtatildi! (Yuborib ulgurildi: {sent_count} ta)")
            break

        try:
            tg_id = item.get('telegram_id')
            phone = item.get('telefon')
            ism = item.get('mijoz_ismi', 'Mijoz')
            qarz = item.get('qarzdorlik', 0)

            try:
                qarz_sum = float(qarz)
            except:
                qarz_sum = 0

            if qarz_sum > 0:
                text = (
                    f"Hurmatli {ism} tadbirkorimiz, sizni xizmat ko'rsatishdan mamnunmiz. "
                    f"Sizning korxonangiz hamda bizning buxgalteriya markazimiz o'rtasidagi xizmatlarimiz uchun "
                    f"to'lanishi lozim bo'lgan mablag' {qarz_sum:,.0f} so'mni tashkil qiladi. "
                    f"Siz bilan ishlash biz uchun sharaf!"
                )
                
                # 1. Telegram ID orqali xabar
                if tg_id and str(tg_id).strip() != "" and str(tg_id).lower() != "nan":
                    try:
                        await bot.send_message(chat_id=int(tg_id), text=text)
                    except Exception as ex:
                        print(f"Telegram ID xato ({tg_id}): {ex}")

                # 2. Telefon raqamga SMS
                if phone and str(phone).strip() != "" and str(phone).lower() != "nan":
                    send_sms_via_gateway(str(phone), text)

                sent_count += 1
                await asyncio.sleep(0.3)
        except Exception as e:
            print(f"Loop xatolik: {e}")

    if is_sending_active and chat_id_to_report:
        await bot.send_message(chat_id_to_report, f"✅ Barcha xabarlar muvaffaqiyatli jo'natib bo'lindi! (Jami: {sent_count} ta)")
    is_sending_active = False

async def send_scheduled_notifications():
    await process_sending()

@dp.callback_query(F.data.in_({"send_now", "stop_sending", "status"}))
async def callback_handler(callback: types.CallbackQuery):
    global is_sending_active, DEBTORS_DATA
    if callback.from_user.id not in XODIM_IDS:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    if callback.data == "send_now":
        if is_sending_active:
            await callback.answer("⚠️ Xabarlar allaqachon yuborilyapti!", show_alert=True)
        else:
            await callback.answer("Xabar yuborilishi boshlandi...", show_alert=True)
            asyncio.create_task(process_sending(callback.message.chat.id))

    elif callback.data == "stop_sending":
        if is_sending_active:
            is_sending_active = False
            await callback.answer("⏹ To'xtatish buyrug'i berildi!", show_alert=True)
        else:
            await callback.answer("ℹ️ Hozir hech qanday tarqatish jarayoni ketmayapti.", show_alert=True)

    elif callback.data == "status":
        count = len(DEBTORS_DATA)
        status_text = "Faol ravishda yuborilyapti" if is_sending_active else "Kutish holatida"
        await callback.answer(f"📊 Yuklangan mijozlar: {count} ta\n⚙️ Holat: {status_text}", show_alert=True)

async def main():
    # Har kuni soat 09:00 va 19:00 da avtomatik yuborish uchun reja
    scheduler.add_job(send_scheduled_notifications, 'cron', hour=9, minute=0)
    scheduler.add_job(send_scheduled_notifications, 'cron', hour=19, minute=0)
    
    scheduler.start()
    print("Bot muvaffaqiyatli ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
