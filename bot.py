import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

API_TOKEN = '8954721701:AAE4-O4DlVLWMtk4Cs4VumpFrSpto2VZbI0'
CHANNEL_ID = -1003933523058
PUNYO_TG_USERNAME = "@Punyo_Education"
PUNYO_TG_URL = "https://t.me/Punyo_Education"
PUNYO_INSTA_URL = "https://www.instagram.com/punyo_education?igsh=aG5uYmJuemR1OWk3&utm_source=qr"
SUBMITTED_PHONES_FILE = "submitted_phones.txt"

def is_phone_submitted(phone: str) -> bool:
    if not os.path.exists(SUBMITTED_PHONES_FILE):
        return False
    with open(SUBMITTED_PHONES_FILE, 'r') as f:
        phones = f.read().splitlines()
    normalized_phone = phone.lstrip('+')
    for p in phones:
        if p.lstrip('+') == normalized_phone:
            return True
    return False

def add_submitted_phone(phone: str):
    with open(SUBMITTED_PHONES_FILE, 'a') as f:
        f.write(f"{phone}\n")

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()

class Form(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_subscription = State()
    waiting_for_letter = State()

async def delete_messages(chat_id, message_ids):
    for msg_id in message_ids:
        if msg_id:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except Exception as e:
                logging.error(f"Failed to delete message {msg_id}: {e}")

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    
    # Delete the /start command
    asyncio.create_task(delete_messages(message.chat.id, [message.message_id]))
    
    sent_msg = await message.answer("Assalomu alaykum! Iltimos, ism va familiyangizni kiriting:")
    
    await state.update_data(msg_name_prompt=sent_msg.message_id)
    await state.set_state(Form.waiting_for_name)

@router.message(Form.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    if not message.text:
        asyncio.create_task(delete_messages(message.chat.id, [message.message_id]))
        sent = await message.answer("Iltimos, ism va familiyangizni matn ko'rinishida kiriting:")
        await asyncio.sleep(3)
        asyncio.create_task(delete_messages(message.chat.id, [sent.message_id]))
        return

    data = await state.get_data()
    
    # Delete user's name message and the previous prompt
    msgs_to_delete = [message.message_id, data.get('msg_name_prompt')]
    asyncio.create_task(delete_messages(message.chat.id, msgs_to_delete))

    await state.update_data(name=message.text)
    
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True))
    
    sent_msg = await message.answer(
        "Rahmat! Endi telefon raqamingizni tasdiqlashingiz kerak. Quyidagi tugmani bosing:",
        reply_markup=builder.as_markup(resize_keyboard=True, one_time_keyboard=True)
    )
    
    await state.update_data(msg_phone_prompt=sent_msg.message_id)
    await state.set_state(Form.waiting_for_phone)

@router.message(Form.waiting_for_phone, F.contact)
async def process_phone(message: Message, state: FSMContext):
    data = await state.get_data()
    
    # Delete user's contact message and the previous prompt
    msgs_to_delete = [message.message_id, data.get('msg_phone_prompt')]
    asyncio.create_task(delete_messages(message.chat.id, msgs_to_delete))

    phone = message.contact.phone_number
    
    if is_phone_submitted(phone):
        await message.answer("Bu telefon raqamdan motivatsion xat yuborilgan.")
        await state.clear()
        return

    await state.update_data(phone=phone)
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Telegram kanalimiz", url=PUNYO_TG_URL))
    builder.row(InlineKeyboardButton(text="Instagram sahifamiz", url=PUNYO_INSTA_URL))
    builder.row(InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="check_sub"))
    
    msg1 = await message.answer(
        "Telefon raqam qabul qilindi!",
        reply_markup=ReplyKeyboardRemove()
    )
    
    msg2 = await message.answer(
        "Motivatsion xat yuborish uchun bizning Telegram va Instagram sahifalarimizga obuna bo'ling.\n\n"
        "Obuna bo'lib qaytgach, pastdagi <b>'Tasdiqlash'</b> tugmasini bosing.",
        reply_markup=builder.as_markup()
    )
    
    await state.update_data(
        msg_phone_accepted=msg1.message_id,
        msg_sub_prompt=msg2.message_id
    )
    await state.set_state(Form.waiting_for_subscription)

@router.message(Form.waiting_for_phone)
async def process_phone_invalid(message: Message):
    asyncio.create_task(delete_messages(message.chat.id, [message.message_id]))
    sent = await message.answer("Iltimos, pastdagi 'Telefon raqamni yuborish' tugmasi orqali raqamingizni yuboring.")
    await asyncio.sleep(3)
    asyncio.create_task(delete_messages(message.chat.id, [sent.message_id]))

@router.callback_query(F.data == "check_sub", Form.waiting_for_subscription)
async def process_check_sub(call: CallbackQuery, state: FSMContext):
    try:
        chat_member = await bot.get_chat_member(chat_id=PUNYO_TG_USERNAME, user_id=call.from_user.id)
        if chat_member.status in ["left", "kicked"]:
            tg_subbed = False
        else:
            tg_subbed = True
    except Exception as e:
        logging.error(f"Error checking chat member: {e}")
        await call.answer("Xatolik: Bot Telegram kanalga admin qilinmagan!", show_alert=True)
        return
        
    if not tg_subbed:
        await call.answer("Siz Telegram kanalimizga obuna bo'lmagansiz! Obuna bo'ling.", show_alert=True)
        return
        
    # All good, delete old messages
    data = await state.get_data()
    msgs_to_delete = [
        data.get('msg_phone_accepted'),
        data.get('msg_sub_prompt')
    ]
    asyncio.create_task(delete_messages(call.message.chat.id, msgs_to_delete))
    
    sent_msg = await call.message.answer(
        "Tasdiqlandi!\n\nEndi motivatsion xat yuborishingiz mumkin. Xatingizni yozib yuboring:"
    )
    await state.update_data(msg_letter_prompt=sent_msg.message_id)
    await state.set_state(Form.waiting_for_letter)

@router.message(Form.waiting_for_letter)
async def process_letter(message: Message, state: FSMContext):
    data = await state.get_data()
    name = data.get('name')
    phone = data.get('phone')
    letter = message.text
    
    if not letter:
        asyncio.create_task(delete_messages(message.chat.id, [message.message_id]))
        sent = await message.answer("Iltimos, motivatsion xatni matn ko'rinishida yuboring.")
        await asyncio.sleep(3)
        asyncio.create_task(delete_messages(message.chat.id, [sent.message_id]))
        return

    # Delete letter prompt and the user's letter message
    msgs_to_delete = [message.message_id, data.get('msg_letter_prompt')]
    asyncio.create_task(delete_messages(message.chat.id, msgs_to_delete))

    text_to_send = (
        f"🌟 <b>Yangi motivatsion xat</b> 🌟\n\n"
        f"👤 <b>Ism Familya:</b> {name}\n"
        f"📞 <b>Telefon raqam:</b> {phone}\n"
        f"📝 <b>Motivatsion xat:</b>\n<i>{letter}</i>"
    )
    
    try:
        await bot.send_message(chat_id=CHANNEL_ID, text=text_to_send)
        add_submitted_phone(phone)
    except Exception as e:
        logging.error(f"Failed to forward letter to private channel: {e}")
        await message.answer("Xatolik: Xatingizni maxfiy kanalga yuborishda muammo yuz berdi.")
        return
        
    await message.answer("Yuborganingiz uchun raxmat, Sog' Salomat bo'ling!")
    await state.clear()

async def main():
    dp.include_router(router)
    print("Bot is running...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
