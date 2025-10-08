from __future__ import annotations

from aiogram import F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.user import User
from app.models.user_settings import UserSettings
from app.services.i18n import t, T
from .start import router


class ProfileEditStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_age = State()
    waiting_for_height = State()
    waiting_for_weight = State()
    waiting_for_budget = State()


def get_lang(user_id: int) -> str:
    db: Session = SessionLocal()
    u = db.query(User).filter(User.tg_id == user_id).first()
    lang = u.language if u and u.language else "ru"
    db.close()
    return lang


def _back_to_menu_kb(lang: str) -> types.InlineKeyboardMarkup:
    """Inline back removed."""
    return types.InlineKeyboardMarkup(inline_keyboard=[])


def _profile_edit_kb(lang: str) -> types.InlineKeyboardMarkup:
    """Build profile edit inline keyboard."""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=t(lang, "profile.edit"), callback_data="profile:edit:name")]
    ])


def get_user_profile_data(user_id: int) -> dict:
    """Get user profile data from database."""
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == user_id).first()
        if not user:
            return {}
        
        settings = session.query(UserSettings).filter(UserSettings.user_id == user.id).first()
        
        return {
            "user": user,
            "settings": settings
        }


def format_profile_text(lang: str, data: dict) -> str:
    """Format profile text with user data."""
    user = data.get("user")
    
    if not user:
        return t(lang, "profile.no_data")
    
    text = f"{t(lang, 'profile.title')}\n\n"
    
    # Basic info
    text += f"{t(lang, 'profile.field.name')}: {user.name or t(lang, 'profile.not_set')}\n"
    text += f"{t(lang, 'profile.field.age')}: {user.age or t(lang, 'profile.not_set')}\n"
    text += f"{t(lang, 'profile.field.height')}: {user.height or t(lang, 'profile.not_set')}\n"
    text += f"{t(lang, 'profile.field.weight')}: {user.weight or t(lang, 'profile.not_set')}\n"
    budget_txt = t(lang, f"budget_{user.budget}") if getattr(user, 'budget', None) else t(lang, 'profile.not_set')
    text += f"{t(lang, 'profile.field.budget')}: {budget_txt}\n"
    
    # Language
    text += f"{t(lang, 'profile.field.language')}: {user.language or 'ru'}"
    
    return text


@router.message(Command("profile"))
async def show_profile(message: types.Message):
    """Show user profile."""
    lang = get_lang(message.from_user.id)
    data = get_user_profile_data(message.from_user.id)
    
    if not data:
        await message.answer(t(lang, "profile.no_data"), reply_markup=_back_to_menu_kb(lang))
        return
    
    text = format_profile_text(lang, data)
    await message.answer(text, reply_markup=_profile_edit_kb(lang))


async def show_profile_from_menu(message: types.Message, lang: str, reply_markup=None):
    """Show user profile - called from main menu."""
    data = get_user_profile_data(message.from_user.id)

    if not data:
        if reply_markup:
            await message.answer("🔽", reply_markup=reply_markup)
        await message.answer(t(lang, "profile.no_data"), reply_markup=_back_to_menu_kb(lang))
        return
    
    text = format_profile_text(lang, data)
    if reply_markup:
        await message.answer("🔽", reply_markup=reply_markup)
    await message.answer(text, reply_markup=_profile_edit_kb(lang))


# inline back removed


@router.callback_query(F.data.startswith("profile:edit:"))
async def profile_edit_field(call: types.CallbackQuery, state: FSMContext):
    """Start editing a profile field."""
    lang = get_lang(call.from_user.id)
    field = call.data.split(":")[2]
    
    if field == "name":
        await state.set_state(ProfileEditStates.waiting_for_name)
        prompt = t(lang, "profile.edit_prompt_name")
    elif field == "age":
        await state.set_state(ProfileEditStates.waiting_for_age)
        prompt = t(lang, "profile.edit_prompt_age")
    elif field == "height":
        await state.set_state(ProfileEditStates.waiting_for_height)
        prompt = t(lang, "profile.edit_prompt_height")
    elif field == "weight":
        await state.set_state(ProfileEditStates.waiting_for_weight)
        prompt = t(lang, "profile.edit_prompt_weight")
    elif field == "budget":
        await state.set_state(ProfileEditStates.waiting_for_budget)
        prompt = t(lang, "profile.edit_prompt_budget")
    else:
        await call.answer("Field not supported")
        return
    
    await call.message.edit_text(prompt)
    await call.answer()


@router.message(ProfileEditStates.waiting_for_name)
async def profile_save_name(message: types.Message, state: FSMContext):
    """Save user name."""
    lang = get_lang(message.from_user.id)
    name = message.text.strip()
    
    if not name:
        await message.answer(t(lang, "profile.invalid_name"))
        return
    
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == message.from_user.id).first()
        if user:
            user.name = name
            session.commit()
    
    # Delete user message
    await message.delete()
    
    # Update profile display
    data = get_user_profile_data(message.from_user.id)
    text = format_profile_text(lang, data)
    await message.answer(text, reply_markup=_profile_edit_kb(lang))
    
    await state.clear()


@router.message(ProfileEditStates.waiting_for_age)
async def profile_save_age(message: types.Message, state: FSMContext):
    """Save user age."""
    lang = get_lang(message.from_user.id)
    try:
        age = int(message.text.strip())
        if age < 1 or age > 120:
            raise ValueError("Invalid age")
    except:
        await message.answer(t(lang, "profile.invalid_age"))
        return
    
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == message.from_user.id).first()
        if user:
            user.age = age
            session.commit()
    
    # Delete user message
    await message.delete()
    
    # Update profile display
    data = get_user_profile_data(message.from_user.id)
    text = format_profile_text(lang, data)
    await message.answer(text, reply_markup=_profile_edit_kb(lang))
    
    await state.clear()


@router.message(ProfileEditStates.waiting_for_height)
async def profile_save_height(message: types.Message, state: FSMContext):
    """Save user height."""
    lang = get_lang(message.from_user.id)
    try:
        height = int(message.text.strip())
        if height < 50 or height > 250:
            raise ValueError("Invalid height")
    except:
        await message.answer(t(lang, "profile.invalid_height"))
        return
    
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == message.from_user.id).first()
        if user:
            user.height = height
            session.commit()
    
    # Delete user message
    await message.delete()
    
    # Update profile display
    data = get_user_profile_data(message.from_user.id)
    text = format_profile_text(lang, data)
    await message.answer(text, reply_markup=_profile_edit_kb(lang))
    
    await state.clear()


@router.message(ProfileEditStates.waiting_for_weight)
async def profile_save_weight(message: types.Message, state: FSMContext):
    """Save user weight."""
    lang = get_lang(message.from_user.id)
    try:
        weight = float(message.text.strip())
        if weight < 20 or weight > 300:
            raise ValueError("Invalid weight")
    except:
        await message.answer(t(lang, "profile.invalid_weight"))
        return
    
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == message.from_user.id).first()
        if user:
            user.weight = weight
            session.commit()
    
    # Delete user message
    await message.delete()
    
    # Update profile display
    data = get_user_profile_data(message.from_user.id)
    text = format_profile_text(lang, data)
    await message.answer(text, reply_markup=_profile_edit_kb(lang))
    
    await state.clear()


@router.message(ProfileEditStates.waiting_for_budget)
async def profile_save_budget(message: types.Message, state: FSMContext):
    """Save user budget."""
    lang = get_lang(message.from_user.id)
    budget = message.text.strip().lower()
    
    if budget not in ["low", "mid", "high"]:
        await message.answer(t(lang, "profile.invalid_budget"))
        return
    
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == message.from_user.id).first()
        if user:
            user.budget = budget
            session.commit()
    
    # Delete user message
    await message.delete()
    
    # Update profile display
    data = get_user_profile_data(message.from_user.id)
    text = format_profile_text(lang, data)
    await message.answer(text, reply_markup=_profile_edit_kb(lang))
    
    await state.clear()
