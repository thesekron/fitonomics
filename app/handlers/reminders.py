from __future__ import annotations

from aiogram import F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.user import User
from app.models.user_settings import UserSettings
from app.services.i18n import t, T
from .start import router


class ReminderSettings(StatesGroup):
    workout_time = State()
    sleep_reminder_time = State()
    breakfast_time = State()
    lunch_time = State()
    dinner_time = State()


def get_lang(user_id: int) -> str:
    db: Session = SessionLocal()
    u = db.query(User).filter(User.tg_id == user_id).first()
    lang = u.language if u and u.language else "ru"
    db.close()
    return lang


def _back_to_menu_kb(lang: str) -> types.InlineKeyboardMarkup:
    """Build back to main menu keyboard."""
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "btn_back"), callback_data="back_to_main")
    kb.adjust(1)
    return kb.as_markup()


def _reminders_main_kb(lang: str) -> types.InlineKeyboardMarkup:
    """Build main reminders menu keyboard."""
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "reminders.settings"), callback_data="reminders:settings")
    kb.button(text=t(lang, "reminders.toggle_all"), callback_data="reminders:toggle_all")
    kb.adjust(1)
    return kb.as_markup()


def _reminders_settings_kb(lang: str) -> types.InlineKeyboardMarkup:
    """Build reminders settings keyboard."""
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "reminders.workout_time"), callback_data="reminders:set_workout")
    kb.button(text=t(lang, "reminders.sleep_reminder"), callback_data="reminders:set_sleep")
    kb.button(text=t(lang, "reminders.breakfast_time"), callback_data="reminders:set_breakfast")
    kb.button(text=t(lang, "reminders.lunch_time"), callback_data="reminders:set_lunch")
    kb.button(text=t(lang, "reminders.dinner_time"), callback_data="reminders:set_dinner")
    kb.button(text=t(lang, "btn_back"), callback_data="reminders:main")
    kb.adjust(1)
    return kb.as_markup()


def get_user_reminder_settings(user_id: int) -> dict:
    """Get user's reminder settings."""
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == user_id).first()
        settings = session.query(UserSettings).filter(UserSettings.user_id == user.tg_id).first()
        
        if not user:
            return {}
            
        return {
            'workout_time': user.reminder_time or 'morning',
            'sleep_reminder_time': settings.sleep_time if settings else '22:00',
            'breakfast_time': settings.breakfast_time if settings else '08:00',
            'lunch_time': settings.lunch_time if settings else '13:00',
            'dinner_time': settings.dinner_time if settings else '19:00',
            'reminders_enabled': getattr(user, 'reminders_enabled', 'true').lower() == 'true'
        }


def format_time_display(time_str: str, default: str = None, lang: str = "ru") -> str:
    """Format time for display with default indicator."""
    if time_str and time_str != default:
        return time_str
    standard_text = t(lang, "reminders.standard")
    return f"{time_str} ({standard_text})" if time_str else f"{default} ({standard_text})"


async def show_reminders_menu_from_message(message: types.Message, lang: str):
    """Show reminders menu from message (not callback)."""
    # Get fresh settings from database
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == message.from_user.id).first()
        settings = session.query(UserSettings).filter(UserSettings.user_id == message.from_user.id).first()
        
        if not user:
            return
            
        # Get fresh status (handle string values)
        reminders_enabled_str = getattr(user, 'reminders_enabled', 'true')
        reminders_enabled = reminders_enabled_str.lower() == 'true'
        
        # Build settings dict
        settings_dict = {
            'workout_time': user.reminder_time or 'morning',
            'sleep_reminder_time': settings.sleep_time if settings else '22:00',
            'breakfast_time': settings.breakfast_time if settings else '08:00',
            'lunch_time': settings.lunch_time if settings else '13:00',
            'dinner_time': settings.dinner_time if settings else '19:00',
            'reminders_enabled': reminders_enabled
        }
    
    # Format workout time display
    workout_display = {
        'morning': '08:00',
        'day': '13:00', 
        'evening': '19:00'
    }.get(settings_dict.get('workout_time', 'morning'), '08:00')
    
    # Use proper translations
    text = f"""🔔 {t(lang, 'menu.reminders')}

⏰ {t(lang, 'reminders.workout_time')}: {workout_display}
😴 {t(lang, 'reminders.sleep_reminder')}: {format_time_display(settings_dict.get('sleep_reminder_time'), '22:00', lang)}
🌅 {t(lang, 'reminders.breakfast_time')}: {format_time_display(settings_dict.get('breakfast_time'), '08:00', lang)}
🍽️ {t(lang, 'reminders.lunch_time')}: {format_time_display(settings_dict.get('lunch_time'), '13:00', lang)}
🌙 {t(lang, 'reminders.dinner_time')}: {format_time_display(settings_dict.get('dinner_time'), '19:00', lang)}

{t(lang, 'reminders.toggle_all')}: {'✅ ' + t(lang, 'reminders.enabled') if settings_dict.get('reminders_enabled', True) else '❌ ' + t(lang, 'reminders.disabled')}"""

    # Show ReplyKeyboard for navigation first (like other menus)
    from .menu import build_back_to_menu_kb
    kb = build_back_to_menu_kb(lang)
    await message.answer("🔽", reply_markup=kb)
    
    # Then show inline buttons for settings and toggle
    await message.answer(text, reply_markup=_reminders_main_kb(lang))


async def show_reminders_menu_from_menu(message: types.Message, lang: str, reply_markup=None):
    """Show reminders menu from main menu."""
    # Get fresh settings from database
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == message.from_user.id).first()
        settings = session.query(UserSettings).filter(UserSettings.user_id == message.from_user.id).first()
        
        if not user:
            return
            
        # Get fresh status (handle string values)
        reminders_enabled_str = getattr(user, 'reminders_enabled', 'true')
        reminders_enabled = reminders_enabled_str.lower() == 'true'
        
        # Build settings dict
        settings_dict = {
            'workout_time': user.reminder_time or 'morning',
            'sleep_reminder_time': settings.sleep_time if settings else '22:00',
            'breakfast_time': settings.breakfast_time if settings else '08:00',
            'lunch_time': settings.lunch_time if settings else '13:00',
            'dinner_time': settings.dinner_time if settings else '19:00',
            'reminders_enabled': reminders_enabled
        }
    
    # Format workout time display
    workout_display = {
        'morning': '08:00',
        'day': '13:00', 
        'evening': '19:00'
    }.get(settings_dict.get('workout_time', 'morning'), '08:00')
    
    # Use proper translations
    text = f"""🔔 {t(lang, 'menu.reminders')}

⏰ {t(lang, 'reminders.workout_time')}: {workout_display}
😴 {t(lang, 'reminders.sleep_reminder')}: {format_time_display(settings_dict.get('sleep_reminder_time'), '22:00', lang)}
🌅 {t(lang, 'reminders.breakfast_time')}: {format_time_display(settings_dict.get('breakfast_time'), '08:00', lang)}
🍽️ {t(lang, 'reminders.lunch_time')}: {format_time_display(settings_dict.get('lunch_time'), '13:00', lang)}
🌙 {t(lang, 'reminders.dinner_time')}: {format_time_display(settings_dict.get('dinner_time'), '19:00', lang)}

{t(lang, 'reminders.toggle_all')}: {'✅ ' + t(lang, 'reminders.enabled') if settings_dict.get('reminders_enabled', True) else '❌ ' + t(lang, 'reminders.disabled')}"""

    # Show ReplyKeyboard for navigation first (like other menus)
    from .menu import build_back_to_menu_kb
    kb = build_back_to_menu_kb(lang)
    await message.answer("🔽", reply_markup=kb)
    
    # Then show inline buttons for settings and toggle
    await message.answer(text, reply_markup=_reminders_main_kb(lang))


@router.callback_query(F.data == "reminders:main")
async def reminders_main_menu(call: types.CallbackQuery):
    """Show main reminders menu."""
    lang = get_lang(call.from_user.id)
    settings = get_user_reminder_settings(call.from_user.id)
    
    # Format workout time display
    workout_display = {
        'morning': '08:00',
        'day': '13:00', 
        'evening': '19:00'
    }.get(settings_dict.get('workout_time', 'morning'), '08:00')
    
    # Use proper translations
    text = f"""🔔 {t(lang, 'menu.reminders')}

⏰ {t(lang, 'reminders.workout_time')}: {workout_display}
😴 {t(lang, 'reminders.sleep_reminder')}: {format_time_display(settings_dict.get('sleep_reminder_time'), '22:00', lang)}
🌅 {t(lang, 'reminders.breakfast_time')}: {format_time_display(settings_dict.get('breakfast_time'), '08:00', lang)}
🍽️ {t(lang, 'reminders.lunch_time')}: {format_time_display(settings_dict.get('lunch_time'), '13:00', lang)}
🌙 {t(lang, 'reminders.dinner_time')}: {format_time_display(settings_dict.get('dinner_time'), '19:00', lang)}

{t(lang, 'reminders.toggle_all')}: {'✅ ' + t(lang, 'reminders.enabled') if settings_dict.get('reminders_enabled', True) else '❌ ' + t(lang, 'reminders.disabled')}"""

    await call.message.edit_text(text, reply_markup=_reminders_main_kb(lang))


@router.callback_query(F.data == "reminders:settings")
async def reminders_settings_menu(call: types.CallbackQuery):
    """Show reminders settings menu."""
    lang = get_lang(call.from_user.id)
    
    text = """⚙️ Настройка напоминаний

Выберите, что хотите настроить:"""
    
    await call.message.edit_text(text, reply_markup=_reminders_settings_kb(lang))


@router.callback_query(F.data == "reminders:set_workout")
async def set_workout_time(call: types.CallbackQuery, state: FSMContext):
    """Set workout reminder time."""
    lang = get_lang(call.from_user.id)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="🌅 Утром (08:00)", callback_data="reminders:workout_morning")
    kb.button(text="☀️ Днем (13:00)", callback_data="reminders:workout_day")
    kb.button(text="🌙 Вечером (19:00)", callback_data="reminders:workout_evening")
    kb.button(text=t(lang, "btn_back"), callback_data="reminders:settings")
    kb.adjust(1)
    
    text = """⏰ Время тренировок

Выберите время напоминания о тренировках:"""
    
    await call.message.edit_text(text, reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("reminders:workout_"))
async def save_workout_time(call: types.CallbackQuery):
    """Save workout time setting."""
    lang = get_lang(call.from_user.id)
    time_setting = call.data.split("_")[-1]  # morning, day, evening
    
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == call.from_user.id).first()
        if user:
            user.reminder_time = time_setting
            session.commit()
    
    await call.answer("✅ Время тренировок сохранено!")
    await reminders_main_menu(call)


@router.callback_query(F.data == "reminders:set_sleep")
async def set_sleep_reminder_time(call: types.CallbackQuery, state: FSMContext):
    """Set sleep reminder time."""
    lang = get_lang(call.from_user.id)
    
    text = f"""😴 {t(lang, 'reminders.sleep_reminder')}

{t(lang, 'reminders.sleep_reminder_enter_time')} (например: 22:30):"""
    
    await call.message.edit_text(text)
    await state.set_state(ReminderSettings.sleep_reminder_time)


@router.message(ReminderSettings.sleep_reminder_time)
async def save_sleep_reminder_time(message: types.Message, state: FSMContext):
    """Save sleep reminder time."""
    lang = get_lang(message.from_user.id)
    time_str = message.text.strip()
    
    # Validate time format
    try:
        hour, minute = map(int, time_str.split(':'))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except:
        await message.answer(f"❌ {t(lang, 'reminders.time_format_error')}")
        return
    
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == message.from_user.id).first()
        if user:
            settings = session.query(UserSettings).filter(UserSettings.user_id == user.tg_id).first()
            if not settings:
                settings = UserSettings(user_id=user.tg_id)
                session.add(settings)
            settings.sleep_time = time_str
            session.commit()
    
    await message.answer(f"✅ {t(lang, 'reminders.time_saved')}")
    await state.clear()
    
    # Show main reminders menu
    settings_dict = get_user_reminder_settings(message.from_user.id)
    workout_display = {
        'morning': '08:00',
        'day': '13:00', 
        'evening': '19:00'
    }.get(settings_dict.get('workout_time', 'morning'), '08:00')
    
    text = f"""🔔 Напоминания

⏰ Время тренировок: {workout_display}
😴 Напоминание о сне: {format_time_display(settings_dict.get('sleep_reminder_time'), '22:00', lang)}
🌅 Завтрак: {format_time_display(settings_dict.get('breakfast_time'), '08:00', lang)}
🍽️ Обед: {format_time_display(settings_dict.get('lunch_time'), '13:00', lang)}
🌙 Ужин: {format_time_display(settings_dict.get('dinner_time'), '19:00', lang)}

Статус: {'✅ ' + t(lang, 'reminders.enabled') if settings_dict.get('reminders_enabled', True) else '❌ ' + t(lang, 'reminders.disabled')}"""

    await message.answer(text, reply_markup=_reminders_main_kb(lang))


@router.callback_query(F.data == "reminders:set_breakfast")
async def set_breakfast_time(call: types.CallbackQuery, state: FSMContext):
    """Set breakfast reminder time."""
    lang = get_lang(call.from_user.id)
    
    text = f"""🌅 {t(lang, 'reminders.breakfast_time')}

{t(lang, 'reminders.breakfast_enter_time')} (например: 08:30):"""
    
    await call.message.edit_text(text)
    await state.set_state(ReminderSettings.breakfast_time)


@router.message(ReminderSettings.breakfast_time)
async def save_breakfast_time(message: types.Message, state: FSMContext):
    """Save breakfast time."""
    lang = get_lang(message.from_user.id)
    time_str = message.text.strip()
    
    # Validate time format
    try:
        hour, minute = map(int, time_str.split(':'))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except:
        await message.answer("❌ Неверный формат времени. Используйте ЧЧ:ММ (например: 08:30)")
        return
    
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == message.from_user.id).first()
        if user:
            settings = session.query(UserSettings).filter(UserSettings.user_id == user.tg_id).first()
            if not settings:
                settings = UserSettings(user_id=user.tg_id)
                session.add(settings)
            settings.breakfast_time = time_str
            session.commit()
    
    await message.answer(f"✅ {t(lang, 'reminders.time_saved')}")
    await state.clear()
    
    # Schedule meal reminders for this user
    from app.services.reminders import schedule_meal_reminders
    schedule_meal_reminders(message.from_user.id)
    
    await show_reminders_menu_from_message(message, lang)


@router.callback_query(F.data == "reminders:set_lunch")
async def set_lunch_time(call: types.CallbackQuery, state: FSMContext):
    """Set lunch reminder time."""
    lang = get_lang(call.from_user.id)
    
    text = f"""🍽️ {t(lang, 'reminders.lunch_time')}

{t(lang, 'reminders.lunch_enter_time')} (например: 13:30):"""
    
    await call.message.edit_text(text)
    await state.set_state(ReminderSettings.lunch_time)


@router.message(ReminderSettings.lunch_time)
async def save_lunch_time(message: types.Message, state: FSMContext):
    """Save lunch time."""
    lang = get_lang(message.from_user.id)
    time_str = message.text.strip()
    
    # Validate time format
    try:
        hour, minute = map(int, time_str.split(':'))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except:
        await message.answer("❌ Неверный формат времени. Используйте ЧЧ:ММ (например: 13:30)")
        return
    
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == message.from_user.id).first()
        if user:
            settings = session.query(UserSettings).filter(UserSettings.user_id == user.tg_id).first()
            if not settings:
                settings = UserSettings(user_id=user.tg_id)
                session.add(settings)
            settings.lunch_time = time_str
            session.commit()
    
    await message.answer(f"✅ {t(lang, 'reminders.time_saved')}")
    await state.clear()
    
    # Schedule meal reminders for this user
    from app.services.reminders import schedule_meal_reminders
    schedule_meal_reminders(message.from_user.id)
    
    await show_reminders_menu_from_message(message, lang)


@router.callback_query(F.data == "reminders:set_dinner")
async def set_dinner_time(call: types.CallbackQuery, state: FSMContext):
    """Set dinner reminder time."""
    lang = get_lang(call.from_user.id)
    
    text = f"""🌙 {t(lang, 'reminders.dinner_time')}

{t(lang, 'reminders.dinner_enter_time')} (например: 19:30):"""
    
    await call.message.edit_text(text)
    await state.set_state(ReminderSettings.dinner_time)


@router.message(ReminderSettings.dinner_time)
async def save_dinner_time(message: types.Message, state: FSMContext):
    """Save dinner time."""
    lang = get_lang(message.from_user.id)
    time_str = message.text.strip()
    
    # Validate time format
    try:
        hour, minute = map(int, time_str.split(':'))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except:
        await message.answer("❌ Неверный формат времени. Используйте ЧЧ:ММ (например: 19:30)")
        return
    
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == message.from_user.id).first()
        if user:
            settings = session.query(UserSettings).filter(UserSettings.user_id == user.tg_id).first()
            if not settings:
                settings = UserSettings(user_id=user.tg_id)
                session.add(settings)
            settings.dinner_time = time_str
            session.commit()
    
    await message.answer(f"✅ {t(lang, 'reminders.time_saved')}")
    await state.clear()
    
    # Schedule meal reminders for this user
    from app.services.reminders import schedule_meal_reminders
    schedule_meal_reminders(message.from_user.id)
    
    await show_reminders_menu_from_message(message, lang)


@router.callback_query(F.data == "reminders:toggle_all")
async def toggle_all_reminders(call: types.CallbackQuery):
    """Toggle all reminders on/off."""
    lang = get_lang(call.from_user.id)
    
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == call.from_user.id).first()
        if not user:
            await call.answer("❌ User not found!")
            return
            
        # Get current state (handle string values)
        current_state_str = getattr(user, 'reminders_enabled', 'true')
        current_state = current_state_str.lower() == 'true'
        
        # Toggle the state
        new_state = not current_state
        user.reminders_enabled = 'true' if new_state else 'false'
        session.commit()
        
        # Get fresh data after commit
        user = session.query(User).filter(User.tg_id == call.from_user.id).first()
        settings = session.query(UserSettings).filter(UserSettings.user_id == call.from_user.id).first()
        
        # Build fresh settings dict
        settings_dict = {
            'workout_time': user.reminder_time or 'morning',
            'sleep_reminder_time': settings.sleep_time if settings else '22:00',
            'breakfast_time': settings.breakfast_time if settings else '08:00',
            'lunch_time': settings.lunch_time if settings else '13:00',
            'dinner_time': settings.dinner_time if settings else '19:00',
            'reminders_enabled': new_state
        }
        
        # Format workout time display
        workout_display = {
            'morning': '08:00',
            'day': '13:00', 
            'evening': '19:00'
        }.get(settings_dict.get('workout_time', 'morning'), '08:00')
        
        # Build text with fresh data
        text = f"""🔔 {t(lang, 'menu.reminders')}

⏰ {t(lang, 'reminders.workout_time')}: {workout_display}
😴 {t(lang, 'reminders.sleep_reminder')}: {format_time_display(settings_dict.get('sleep_reminder_time'), '22:00', lang)}
🌅 {t(lang, 'reminders.breakfast_time')}: {format_time_display(settings_dict.get('breakfast_time'), '08:00', lang)}
🍽️ {t(lang, 'reminders.lunch_time')}: {format_time_display(settings_dict.get('lunch_time'), '13:00', lang)}
🌙 {t(lang, 'reminders.dinner_time')}: {format_time_display(settings_dict.get('dinner_time'), '19:00', lang)}

{t(lang, 'reminders.toggle_all')}: {'✅ ' + t(lang, 'reminders.enabled') if new_state else '❌ ' + t(lang, 'reminders.disabled')}"""

        # Show status change
        status_text = t(lang, 'reminders.enabled') if new_state else t(lang, 'reminders.disabled')
        await call.answer(f"✅ {t(lang, 'reminders.toggle_all')}: {status_text}!")
        
        # Update message
        try:
            await call.message.edit_text(text, reply_markup=_reminders_main_kb(lang))
        except Exception as e:
            print(f"Error updating message: {e}")
            # If edit fails, just show the answer
            pass

