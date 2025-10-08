from __future__ import annotations

from aiogram import F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .start import router
from app.database import SessionLocal
from app.models.user import User
from app.models.sleep_log import SleepLog
from app.services.i18n import t
from app.services.sleep_tips import get_random_tip, get_sleep_stats, get_electronics_feedback, get_quality_emoji_and_text, RECOMMENDED_SLEEP_SCHEDULE


class SleepStates(StatesGroup):
    waiting_sleep_time = State()
    waiting_wake_time = State()
    waiting_electronics = State()
    waiting_quality = State()


def _get_lang(user_id: int) -> str:
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == user_id).first()
        return (user.language or "ru") if user else "ru"


def _build_sleep_menu_kb(lang: str) -> InlineKeyboardBuilder:
    """Build main sleep menu keyboard."""
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "sleep.log_sleep"), callback_data="sleep:log")
    kb.button(text=t(lang, "sleep.daily_tip"), callback_data="sleep:tip")
    kb.adjust(1)
    return kb


def _build_sleep_time_kb(lang: str) -> InlineKeyboardBuilder:
    """Build sleep time selection keyboard."""
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "sleep.time_21"), callback_data="sleep:time:21:00")
    kb.button(text=t(lang, "sleep.time_22"), callback_data="sleep:time:22:00")
    kb.button(text=t(lang, "sleep.time_23"), callback_data="sleep:time:23:00")
    kb.button(text=t(lang, "sleep.later"), callback_data="sleep:time:later")
    kb.button(text=t(lang, "sleep.enter_manually"), callback_data="sleep:time:manual")
    kb.adjust(2, 2, 1)
    return kb


def _build_wake_time_kb(lang: str) -> InlineKeyboardBuilder:
    """Build wake time selection keyboard."""
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "sleep.time_06"), callback_data="sleep:wake:06:00")
    kb.button(text=t(lang, "sleep.time_07"), callback_data="sleep:wake:07:00")
    kb.button(text=t(lang, "sleep.time_08"), callback_data="sleep:wake:08:00")
    kb.button(text=t(lang, "sleep.later"), callback_data="sleep:wake:later")
    kb.button(text=t(lang, "sleep.enter_manually"), callback_data="sleep:wake:manual")
    kb.adjust(2, 2, 1)
    return kb


def _build_electronics_kb(lang: str) -> InlineKeyboardBuilder:
    """Build electronics usage keyboard."""
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "sleep.yes"), callback_data="sleep:electronics:yes")
    kb.button(text=t(lang, "sleep.no"), callback_data="sleep:electronics:no")
    kb.adjust(2)
    return kb


def _build_quality_kb(lang: str) -> InlineKeyboardBuilder:
    """Build sleep quality rating keyboard."""
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "sleep.quality_1"), callback_data="sleep:quality:1")
    kb.button(text=t(lang, "sleep.quality_2"), callback_data="sleep:quality:2")
    kb.button(text=t(lang, "sleep.quality_3"), callback_data="sleep:quality:3")
    kb.button(text=t(lang, "sleep.quality_4"), callback_data="sleep:quality:4")
    kb.button(text=t(lang, "sleep.quality_5"), callback_data="sleep:quality:5")
    kb.adjust(5)
    return kb


def _build_tip_kb(lang: str) -> InlineKeyboardBuilder:
    """Build tip keyboard with another tip button and back to sleep menu."""
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "sleep.want_another_tip"), callback_data="sleep:tip")
    kb.button(text=t(lang, "menu.back"), callback_data="sleep:back_to_menu")
    kb.adjust(1)  # One button per row
    return kb


def _calculate_duration(sleep_time: str, wake_time: str) -> float:
    """Calculate sleep duration in hours."""
    def time_to_minutes(time_str: str) -> int:
        try:
            # Handle different time formats
            if ':' in time_str:
                parts = time_str.split(':')
                if len(parts) == 2:
                    h, m = map(int, parts)
                    return h * 60 + m
                elif len(parts) == 1:
                    # Just hours, no minutes
                    h = int(parts[0])
                    return h * 60
            else:
                # No colon, assume it's just hours
                h = int(time_str)
                return h * 60
        except (ValueError, IndexError):
            # Default to 8 hours if parsing fails
            return 8 * 60
    
    sleep_minutes = time_to_minutes(sleep_time)
    wake_minutes = time_to_minutes(wake_time)
    
    # Handle overnight sleep
    if wake_minutes < sleep_minutes:
        wake_minutes += 24 * 60
    
    duration_minutes = wake_minutes - sleep_minutes
    return round(duration_minutes / 60, 1)


async def show_sleep_summary(message: Message, lang: str, reply_markup=None):
    """Show sleep section main menu."""
    text = f"{t(lang, 'sleep.section_title')}\n\n"
    text += f"{t(lang, 'sleep.section_desc')}\n\n"
    text += f"{t(lang, 'sleep.choose_action')}"
    
    if reply_markup:
        await message.answer("🔽", reply_markup=reply_markup)
    await message.answer(text, reply_markup=_build_sleep_menu_kb(lang).as_markup())


@router.callback_query(F.data == "sleep:log")
async def start_sleep_logging(call: CallbackQuery, state: FSMContext):
    """Start sleep logging process."""
    lang = _get_lang(call.from_user.id)
    await state.set_state(SleepStates.waiting_sleep_time)
    await call.message.edit_text(t(lang, "sleep.when_did_you_sleep"), reply_markup=_build_sleep_time_kb(lang).as_markup())
    await call.answer()


@router.callback_query(F.data.startswith("sleep:time:"))
async def handle_sleep_time(call: CallbackQuery, state: FSMContext):
    """Handle sleep time selection."""
    lang = _get_lang(call.from_user.id)
    time_choice = call.data.split(":")[2]
    
    if time_choice == "manual":
        await call.message.edit_text(t(lang, "sleep_ask_sleep"))
        await call.answer()
        return
    elif time_choice == "later":
        await call.message.edit_text(t(lang, "sleep_ask_sleep"))
        await call.answer()
        return
    else:
        await state.update_data(sleep_time=time_choice)
        await state.set_state(SleepStates.waiting_wake_time)
        await call.message.edit_text(t(lang, "sleep.when_did_you_wake"), reply_markup=_build_wake_time_kb(lang).as_markup())
        await call.answer()


@router.message(SleepStates.waiting_sleep_time)
async def handle_manual_sleep_time(message: Message, state: FSMContext):
    """Handle manual sleep time input."""
    lang = _get_lang(message.from_user.id)
    text = (message.text or "").strip()
    
    # Simple time validation
    try:
        h, m = map(int, text.split(":"))
        if 0 <= h <= 23 and 0 <= m <= 59:
            await state.update_data(sleep_time=text)
            await state.set_state(SleepStates.waiting_wake_time)
            await message.answer(t(lang, "sleep.when_did_you_wake"), reply_markup=_build_wake_time_kb(lang).as_markup())
        else:
            await message.answer(t(lang, "onb_invalid_time"))
    except:
        await message.answer(t(lang, "onb_invalid_time"))


@router.callback_query(F.data.startswith("sleep:wake:"))
async def handle_wake_time(call: CallbackQuery, state: FSMContext):
    """Handle wake time selection."""
    lang = _get_lang(call.from_user.id)
    time_choice = call.data.split(":")[2]
    
    if time_choice == "manual":
        await call.message.edit_text(t(lang, "sleep_ask_wake"))
        await call.answer()
        return
    elif time_choice == "later":
        await call.message.edit_text(t(lang, "sleep_ask_wake"))
        await call.answer()
        return
    else:
        await state.update_data(wake_time=time_choice)
        await state.set_state(SleepStates.waiting_electronics)
        await call.message.edit_text(t(lang, "sleep.electronics_question"), reply_markup=_build_electronics_kb(lang).as_markup())
        await call.answer()


@router.message(SleepStates.waiting_wake_time)
async def handle_manual_wake_time(message: Message, state: FSMContext):
    """Handle manual wake time input."""
    lang = _get_lang(message.from_user.id)
    text = (message.text or "").strip()
    
    # Simple time validation
    try:
        h, m = map(int, text.split(":"))
        if 0 <= h <= 23 and 0 <= m <= 59:
            await state.update_data(wake_time=text)
            await state.set_state(SleepStates.waiting_electronics)
            await message.answer(t(lang, "sleep.electronics_question"), reply_markup=_build_electronics_kb(lang).as_markup())
        else:
            await message.answer(t(lang, "onb_invalid_time"))
    except:
        await message.answer(t(lang, "onb_invalid_time"))


@router.callback_query(F.data.startswith("sleep:electronics:"))
async def handle_electronics(call: CallbackQuery, state: FSMContext):
    """Handle electronics usage question."""
    lang = _get_lang(call.from_user.id)
    choice = call.data.split(":")[2]
    
    await state.update_data(electronics_used=choice)
    await state.set_state(SleepStates.waiting_quality)
    await call.message.edit_text(t(lang, "sleep.quality_question"), reply_markup=_build_quality_kb(lang).as_markup())
    await call.answer()


@router.callback_query(F.data.startswith("sleep:quality:"))
async def handle_quality_rating(call: CallbackQuery, state: FSMContext):
    """Handle sleep quality rating and save the log."""
    lang = _get_lang(call.from_user.id)
    rating = int(call.data.split(":")[2])
    
    data = await state.get_data()
    sleep_time = data.get("sleep_time")
    wake_time = data.get("wake_time")
    electronics_used = data.get("electronics_used")
    
    if not all([sleep_time, wake_time, electronics_used]):
        await call.answer("Error: Missing data")
        return
    
    # Calculate duration
    duration = _calculate_duration(sleep_time, wake_time)
    
    # Save to database
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == call.from_user.id).first()
        if user:
            log = SleepLog(
                user_id=user.id,
                sleep_time=sleep_time,
                wake_time=wake_time,
                duration_hours=duration,
                electronics_used=electronics_used,
                quality_rating=rating
            )
            session.add(log)
            session.commit()
    
    # Get quality emoji and text
    emoji, quality_text_key = get_quality_emoji_and_text(rating)
    quality_text = t(lang, quality_text_key)
    
    # Build response
    response = f"{t(lang, 'sleep.recorded')}\n\n"
    duration_text = f"{duration:.1f}h"
    response += f"{t(lang, 'sleep.duration', duration=duration_text)}\n"
    response += f"{t(lang, 'sleep.quality', emoji=emoji, rating=quality_text)}\n\n"
    
    # Electronics feedback
    if electronics_used == "yes":
        response += f"{t(lang, 'sleep.electronics_yes')}\n\n"
    else:
        response += f"{t(lang, 'sleep.electronics_no')}\n\n"
    
    response += f"{t(lang, 'sleep.recommended_schedule', schedule=RECOMMENDED_SLEEP_SCHEDULE)}\n\n"
    response += f"{t(lang, 'sleep.keep_it_up')}"
    
    await call.message.edit_text(response)
    await state.clear()
    await call.answer()




@router.callback_query(F.data == "sleep:back_to_menu")
async def handle_back_to_sleep_menu(call: CallbackQuery):
    """Handle back to sleep menu button."""
    lang = _get_lang(call.from_user.id)
    text = f"{t(lang, 'sleep.section_title')}\n\n"
    text += f"{t(lang, 'sleep.section_desc')}\n\n"
    text += f"{t(lang, 'sleep.choose_action')}"
    
    await call.message.edit_text(text, reply_markup=_build_sleep_menu_kb(lang).as_markup())
    await call.answer()


@router.callback_query(F.data == "sleep:tip")
async def show_sleep_tip(call: CallbackQuery):
    """Show a random sleep tip."""
    lang = _get_lang(call.from_user.id)
    tip = get_random_tip(lang)
    
    text = f"{t(lang, 'sleep.daily_tip_title')}\n\n{tip}"
    
    await call.message.edit_text(text, reply_markup=_build_tip_kb(lang).as_markup())
    await call.answer()


@router.callback_query(F.data == "sleep:morning:no")
async def handle_morning_no(call: CallbackQuery):
    """Handle morning reminder 'No' response."""
    await call.answer("OK, maybe next time!")


@router.message(Command("sleep"))
async def sleep_start(message: Message, state: FSMContext) -> None:
    """Handle /sleep command."""
    lang = _get_lang(message.from_user.id)
    await show_sleep_summary(message, lang)