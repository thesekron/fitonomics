from __future__ import annotations

from aiogram import F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database import SessionLocal
from app.models.user import User
from app.services.i18n import t, T
from app.services.settings import (
    build_settings_menu_kb,
    build_language_kb,
    build_budget_kb,
    build_reminder_kb,
    parse_profile_text,
)
from .start import router
from app.services.reminders import start_scheduler, schedule_daily_reminder


class OnboardingStates(StatesGroup):
    waiting_for_name = State()


class ProfileStates(StatesGroup):
    name = State()
    age = State()
    height = State()
    weight = State()
    waiting_for_budget = State()


SETTINGS_BTNS = {T[x]["btn_settings"] for x in T.keys()}


async def open_settings_menu(message: Message, lang: str, reply_markup=None):
    """Open settings menu - called from main menu."""
    user = _get_or_create_user(message.from_user.id)
    # Onboarding: ask the name if missing
    if not user.name:
        if reply_markup:
            await message.answer("🔽", reply_markup=reply_markup)
        await message.answer(t(lang, "ask_name"))
        return

    if reply_markup:
        await message.answer("🔽", reply_markup=reply_markup)
    await message.answer(
        t(lang, "settings_title"),
        reply_markup=build_settings_menu_kb(lang).as_markup(),
    )


def _get_or_create_user(telegram_user_id: int) -> User:
    """Fetch user by Telegram id or create a new one with defaults."""
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == telegram_user_id).first()
        if user is None:
            user = User(tg_id=telegram_user_id)
            session.add(user)
            session.commit()
            session.refresh(user)
        return user


@router.message(Command("settings"))
async def cmd_settings(message: Message, state: FSMContext) -> None:
    user = _get_or_create_user(message.from_user.id)
    # Onboarding: ask the name if missing
    if not user.name:
        await state.set_state(OnboardingStates.waiting_for_name)
        await message.answer(t(user.language or "ru", "ask_name"))
        return

    lang = user.language or "ru"
    await message.answer(
        t(lang, "settings_title"),
        reply_markup=build_settings_menu_kb(lang).as_markup(),
    )


@router.message(F.text.in_(SETTINGS_BTNS))
async def open_settings_from_menu(message: Message, state: FSMContext) -> None:
    await cmd_settings(message, state)


@router.callback_query(F.data == "settings:back_to_menu")
async def settings_back_to_menu(call: CallbackQuery):
    """Return to main menu from settings."""
    from .menu import build_main_menu_kb
    # use stored language, not Telegram UI language
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == call.from_user.id).first()
        lang = (user.language or "ru") if user else "ru"
    kb = build_main_menu_kb(lang)
    # send a new message with ReplyKeyboard (can't attach to edit_text)
    await call.message.answer(t(lang, "menu.welcome"), reply_markup=kb)
    await call.answer()


@router.message(OnboardingStates.waiting_for_name)
async def onboarding_name(message: Message, state: FSMContext) -> None:
    new_name = (message.text or "").strip()
    if not new_name:
        await message.answer("✏️")
        return

    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == message.from_user.id).first()
        lang = (user.language or "ru") if user else "ru"
        if user:
            user.name = new_name
            session.commit()
        await message.answer(t(lang, "saved_name", name=new_name))

    await state.clear()
    # Show settings menu after name saved
    user = _get_or_create_user(message.from_user.id)
    lang = user.language or "ru"
    await message.answer(
        t(lang, "settings_title"),
        reply_markup=build_settings_menu_kb(lang).as_markup(),
    )


@router.callback_query(F.data == "settings:lang")
async def settings_change_lang(call: CallbackQuery) -> None:
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == call.from_user.id).first()
        lang = (user.language or "ru") if user else "ru"
    await call.message.edit_text(
        t(lang, "choose_language"),
        reply_markup=build_language_kb(lang).as_markup(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("lang:"))
async def pick_language(call: CallbackQuery) -> None:
    new_lang = call.data.split(":", 1)[1]
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == call.from_user.id).first()
        if user:
            user.language = new_lang
            session.commit()
    await call.message.edit_text(
        t(new_lang, "settings_title"),
        reply_markup=build_settings_menu_kb(new_lang).as_markup(),
    )
    await call.answer(t(new_lang, "saved_language"))





@router.callback_query(F.data == "settings:profile")
async def settings_set_profile(call: CallbackQuery, state: FSMContext) -> None:
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == call.from_user.id).first()
        lang = (user.language or "ru") if user else "ru"
    await state.clear()
    # Show current profile summary first
    if user:
        name = user.name or t(lang, "profile.not_set")
        age = str(user.age) if user.age is not None else t(lang, "profile.not_set")
        height = str(user.height) if user.height is not None else t(lang, "profile.not_set")
        weight = str(user.weight) if user.weight is not None else t(lang, "profile.not_set")
        budget = t(lang, f"budget_{user.budget}") if user.budget else t(lang, "profile.not_set")
        lines = [
            f"<b>{t(lang, 'profile.title')}</b>",
            f"{t(lang, 'profile.field.name')}: {name}",
            f"{t(lang, 'profile.field.age')}: {age}",
            f"{t(lang, 'profile.field.height')}: {height}",
            f"{t(lang, 'profile.field.weight')}: {weight}",
            f"{t(lang, 'profile.field.budget')}: {budget}",
        ]
        text = "\n".join(lines)
    else:
        text = t(lang, "profile.no_data")

    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "profile.edit"), callback_data="settings:profile:renew")
    kb.adjust(1)
    await call.message.edit_text(text, reply_markup=kb.as_markup())
    await call.answer()


@router.callback_query(F.data == "settings:profile:renew")
async def settings_profile_renew(call: CallbackQuery, state: FSMContext) -> None:
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == call.from_user.id).first()
        lang = (user.language or "ru") if user else "ru"
    await state.set_state(ProfileStates.name)
    await call.message.edit_text(t(lang, "profile.edit_prompt_name"))
    await call.answer()


@router.message(ProfileStates.name)
async def profile_set_name(message: Message, state: FSMContext) -> None:
    new_name = (message.text or "").strip()
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == message.from_user.id).first()
        lang = (user.language or "ru") if user else "ru"
        if not new_name:
            await message.answer(t(lang, "profile.invalid_name"))
            return
        if user:
            user.name = new_name
            session.commit()
    await state.set_state(ProfileStates.age)
    await message.answer(t(lang, "profile.edit_prompt_age"))


@router.message(ProfileStates.age)
async def profile_set_age(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == message.from_user.id).first()
        lang = (user.language or "ru") if user else "ru"
    try:
        age = int(txt)
        if not (0 < age < 120):
            raise ValueError
    except Exception:
        await message.answer(t(lang, "profile.invalid_age"))
        return
    await state.update_data(age=age)
    await state.set_state(ProfileStates.height)
    await message.answer(t(lang, "profile.edit_prompt_height"))


@router.message(ProfileStates.height)
async def profile_set_height(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == message.from_user.id).first()
        lang = (user.language or "ru") if user else "ru"
    try:
        height = int(txt)
        if not (50 < height < 260):
            raise ValueError
    except Exception:
        await message.answer(t(lang, "profile.invalid_height"))
        return
    await state.update_data(height=height)
    await state.set_state(ProfileStates.weight)
    await message.answer(t(lang, "profile.edit_prompt_weight"))


@router.message(ProfileStates.weight)
async def profile_set_weight(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == message.from_user.id).first()
        lang = (user.language or "ru") if user else "ru"
    try:
        weight = int(txt)
        if not (20 < weight < 400):
            raise ValueError
    except Exception:
        await message.answer(t(lang, "profile.invalid_weight"))
        return
    await state.update_data(weight=weight)
    data = await state.get_data()
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == message.from_user.id).first()
        if user:
            user.age = int(data.get("age"))
            user.height = int(data.get("height"))
            user.weight = int(data.get("weight"))
            session.commit()
    await state.set_state(ProfileStates.waiting_for_budget)
    await message.answer(
        t(lang, "choose_budget"),
        reply_markup=build_budget_kb(lang).as_markup(),
    )


@router.callback_query(ProfileStates.waiting_for_budget, F.data.startswith("budget:"))
async def pick_budget(call: CallbackQuery, state: FSMContext) -> None:
    budget = call.data.split(":", 1)[1]
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == call.from_user.id).first()
        lang = (user.language or "ru") if user else "ru"
        if user:
            user.budget = budget
            session.commit()

    await state.clear()
    await call.message.edit_text(
        t(lang, "profile_saved"),
        reply_markup=build_settings_menu_kb(lang).as_markup(),
    )
    await call.answer()


@router.callback_query(F.data == "settings:reminder")
async def settings_reminder(call: CallbackQuery) -> None:
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == call.from_user.id).first()
        lang = (user.language or "ru") if user else "ru"
    await call.message.edit_text(
        t(lang, "choose_reminder_time"),
        reply_markup=build_reminder_kb(lang).as_markup(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("reminder:"))
async def pick_reminder(call: CallbackQuery) -> None:
    choice = call.data.split(":", 1)[1]
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == call.from_user.id).first()
        lang = (user.language or "ru") if user else "ru"
        if user:
            user.reminder_time = choice
            session.commit()

    start_scheduler()
    schedule_daily_reminder(call.from_user.id, choice)

    await call.message.edit_text(
        t(lang, "reminder_saved", time=t(lang, f"rem_{choice}")),
        reply_markup=build_settings_menu_kb(lang).as_markup(),
    )
    await call.answer()

