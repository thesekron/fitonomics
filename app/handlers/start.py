from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

# DB
from app.database import SessionLocal
from app.models.user import User
from app.services.i18n import t

# Храним языки в виде словаря
messages = {
    "ru": {
        "start": "Привет! 👋 Я твой Fitonomics бот. Выбери язык:",
        "lang_chosen": "Язык установлен на Русский 🇷🇺"
    },
    "uz": {
        "start": "Salom! 👋 Men sizning Fitonomics botingizman. Tilni tanlang:",
        "lang_chosen": "Til O‘zbekcha 🇺🇿 ga o‘rnatildi"
    },
    "en": {
        "start": "Hi! 👋 I'm your Fitonomics bot. Choose your language:",
        "lang_chosen": "Language set to English 🇺🇸"
    }
}

user_lang = {}  # временно храним язык в памяти

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    # If user exists, ask confirmation before reset
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == message.from_user.id).first()
    if user:
        lang = user.language or "ru"
        kb = InlineKeyboardBuilder()
        kb.button(text=t(lang, "btn_yes"), callback_data="start:reset:yes")
        kb.button(text=t(lang, "btn_no"), callback_data="start:reset:no")
        kb.adjust(2)
        await message.answer(f"{t(lang, 'start.reset_title')}\n{t(lang, 'start.reset_desc')}", reply_markup=kb.as_markup())
        return

    kb = [
        [types.KeyboardButton(text="🇷🇺 Русский"), types.KeyboardButton(text="🇺🇿 O‘zbekcha"), types.KeyboardButton(text="🇺🇸 English")]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer(messages["en"]["start"], reply_markup=keyboard)


@router.callback_query(F.data == "start:reset:no")
async def start_reset_no(call: types.CallbackQuery):
    # Just show main menu in user's language
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == call.from_user.id).first()
        lang = (user.language or "ru") if user else "ru"
    from app.handlers.menu import build_main_menu_kb
    await call.message.edit_text(t(lang, "menu.welcome"))
    await call.message.answer(t(lang, "menu.welcome"), reply_markup=build_main_menu_kb(lang))
    await call.answer()


@router.callback_query(F.data == "start:reset:yes")
async def start_reset_yes(call: types.CallbackQuery):
    # Delete user data and restart onboarding
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == call.from_user.id).first()
        lang = (user.language or "en") if user else "en"
        if user:
            session.delete(user)
            session.commit()
    kb = [
        [types.KeyboardButton(text="🇷🇺 Русский"), types.KeyboardButton(text="🇺🇿 O‘zbekcha"), types.KeyboardButton(text="🇺🇸 English")]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await call.message.edit_text(messages[lang]["start"])
    await call.message.answer(messages[lang]["start"], reply_markup=keyboard)
    await call.answer()

@router.message(lambda m: m.text in ["🇷🇺 Русский", "🇺🇿 O‘zbekcha", "🇺🇸 English"])
async def set_language(message: types.Message):
    if message.text == "🇷🇺 Русский":
        user_lang[message.from_user.id] = "ru"
    elif message.text == "🇺🇿 O‘zbekcha":
        user_lang[message.from_user.id] = "uz"
    elif message.text == "🇺🇸 English":
        user_lang[message.from_user.id] = "en"

    lang = user_lang[message.from_user.id]
    # Persist language in DB for consistent localization
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == message.from_user.id).first()
        if user is None:
            user = User(tg_id=message.from_user.id, language=lang)
            session.add(user)
        else:
            user.language = lang
        session.commit()

    await message.answer(messages[lang]["lang_chosen"], reply_markup=types.ReplyKeyboardRemove())

    # Показать приветствие и подписку на канал в выбранном языке
    from app.services.channel_gate import send_channel_gate
    await send_channel_gate(message, lang)