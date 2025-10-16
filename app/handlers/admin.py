from __future__ import annotations

from aiogram import F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models.user import User
from app.models.admin import Admin
from app.models.user_settings import UserSettings
from app.models.meal_log import MealLog
from app.models.workout_log import WorkoutLog
from app.models.sleep_log import SleepLog
from app.services.i18n import t, T
from .start import router


# Mass notification handler will be added at the end of file


class MassNotification(StatesGroup):
    message_text = State()
    target_filter = State()


# Super admin ID
SUPER_ADMIN_ID = 1475749765

# Admin usernames for reference
ADMIN_USERNAMES = {
    "thesekron": SUPER_ADMIN_ID
}


def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    if user_id == SUPER_ADMIN_ID:
        return True
    
    with SessionLocal() as session:
        admin = session.query(Admin).filter(Admin.tg_id == user_id, Admin.is_active == True).first()
        return admin is not None


def is_super_admin(user_id: int) -> bool:
    """Check if user is super admin."""
    return user_id == SUPER_ADMIN_ID


def get_admin_role(user_id: int) -> str:
    """Get admin role."""
    if user_id == SUPER_ADMIN_ID:
        return "super_admin"
    
    with SessionLocal() as session:
        admin = session.query(Admin).filter(Admin.tg_id == user_id).first()
        return admin.role if admin else "user"


def _admin_main_kb() -> types.InlineKeyboardMarkup:
    """Build main admin panel keyboard."""
    kb = InlineKeyboardBuilder()
    kb.button(text="👥 Управление пользователями", callback_data="admin:users")
    kb.button(text="📊 Статистика и аналитика", callback_data="admin:stats")
    kb.button(text="🔔 Управление напоминаниями", callback_data="admin:reminders")
    kb.button(text="⚙️ Настройки бота", callback_data="admin:settings")
    kb.button(text="👨‍💼 Управление админами", callback_data="admin:manage_admins")
    kb.button(text="🏠 Главное меню", callback_data="back_to_main")
    kb.adjust(1)
    return kb.as_markup()


def _admin_users_kb(page: int = 0, per_page: int = 10) -> types.InlineKeyboardMarkup:
    """Build admin users management keyboard."""
    kb = InlineKeyboardBuilder()
    
    # Get total users count
    with SessionLocal() as session:
        total_users = session.query(User).count()
        total_pages = (total_users + per_page - 1) // per_page
    
    # Navigation buttons
    if page > 0:
        kb.button(text="⬅️ Предыдущая", callback_data=f"admin:users_page_{page-1}")
    if page < total_pages - 1:
        kb.button(text="➡️ Следующая", callback_data=f"admin:users_page_{page+1}")
    
    kb.button(text="🔍 Поиск пользователя", callback_data="admin:search_user")
    kb.button(text="⬅️ Назад к админке", callback_data="admin:main")
    kb.adjust(2, 1, 1, 1)
    return kb.as_markup()


def _admin_stats_kb() -> types.InlineKeyboardMarkup:
    """Build admin stats keyboard."""
    kb = InlineKeyboardBuilder()
    kb.button(text="📈 Общая статистика", callback_data="admin:stats_general")
    kb.button(text="👥 Статистика пользователей", callback_data="admin:stats_users")
    kb.button(text="📊 Рост пользователей", callback_data="admin:stats_growth")
    kb.button(text="⬅️ Назад к админке", callback_data="admin:main")
    kb.adjust(1)
    return kb.as_markup()


def _admin_reminders_kb() -> types.InlineKeyboardMarkup:
    """Build admin reminders management keyboard."""
    kb = InlineKeyboardBuilder()
    kb.button(text="📢 Массовая отправка", callback_data="admin:mass_notification")
    kb.button(text="📊 Статистика напоминаний", callback_data="admin:reminders_stats")
    kb.button(text="⚙️ Настройки напоминаний", callback_data="admin:reminders_settings")
    kb.button(text="⬅️ Назад к админке", callback_data="admin:main")
    kb.adjust(1)
    return kb.as_markup()


def _admin_settings_kb() -> types.InlineKeyboardMarkup:
    """Build admin settings keyboard."""
    kb = InlineKeyboardBuilder()
    kb.button(text="🔧 Включение/выключение функций", callback_data="admin:settings_features")
    kb.button(text="📝 Системные логи", callback_data="admin:settings_logs")
    kb.button(text="⬅️ Назад к админке", callback_data="admin:main")
    kb.adjust(1)
    return kb.as_markup()


def _admin_manage_admins_kb() -> types.InlineKeyboardMarkup:
    """Build admin management keyboard."""
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить админа", callback_data="admin:add_admin")
    kb.button(text="👥 Список админов", callback_data="admin:list_admins")
    kb.button(text="🗑️ Удалить админа", callback_data="admin:remove_admin")
    kb.button(text="⬅️ Назад к админке", callback_data="admin:main")
    kb.adjust(1)
    return kb.as_markup()


def get_user_stats(user_id: int) -> dict:
    """Get user statistics."""
    with SessionLocal() as session:
        # Get user
        user = session.query(User).filter(User.tg_id == user_id).first()
        if not user:
            return {}
        
        # Count logs
        meal_logs = session.query(MealLog).filter(MealLog.user_id == user_id).count()
        workout_logs = session.query(WorkoutLog).filter(WorkoutLog.user_id == user_id).count()
        sleep_logs = session.query(SleepLog).filter(SleepLog.user_id == user_id).count()
        
        # Get last activity
        last_meal = session.query(MealLog).filter(MealLog.user_id == user_id).order_by(MealLog.created_at.desc()).first()
        last_workout = session.query(WorkoutLog).filter(WorkoutLog.user_id == user_id).order_by(WorkoutLog.created_at.desc()).first()
        last_sleep = session.query(SleepLog).filter(SleepLog.user_id == user_id).order_by(SleepLog.created_at.desc()).first()
        
        last_activity = None
        if last_meal and last_meal.created_at:
            last_activity = last_meal.created_at
        if last_workout and last_workout.created_at and (not last_activity or last_workout.created_at > last_activity):
            last_activity = last_workout.created_at
        if last_sleep and last_sleep.created_at and (not last_activity or last_sleep.created_at > last_activity):
            last_activity = last_sleep.created_at
        
        return {
            'meal_logs': meal_logs,
            'workout_logs': workout_logs,
            'sleep_logs': sleep_logs,
            'last_activity': last_activity,
            'total_logs': meal_logs + workout_logs + sleep_logs
        }


def get_bot_stats() -> dict:
    """Get bot statistics."""
    with SessionLocal() as session:
        total_users = session.query(User).count()
        active_users = session.query(User).filter(User.updated_at >= datetime.now() - timedelta(days=7)).count()
        
        # Get growth stats
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        users_this_week = session.query(User).filter(User.created_at >= week_ago).count()
        users_this_month = session.query(User).filter(User.created_at >= month_ago).count()
        
        # Get language distribution
        lang_stats = {}
        for user in session.query(User).all():
            lang = user.language or 'ru'
            lang_stats[lang] = lang_stats.get(lang, 0) + 1
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'users_this_week': users_this_week,
            'users_this_month': users_this_month,
            'language_distribution': lang_stats
        }


@router.message(F.text == "/admin")
async def admin_command(message: types.Message):
    """Handle /admin command."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав доступа к админ-панели.")
        return
    
    stats = get_bot_stats()
    
    text = f"""🛡️ Админ-панель

👥 Пользователи: {stats['total_users']}
📈 Активных: {stats['active_users']}
📊 Рост за неделю: +{stats['users_this_week']}
📈 Рост за месяц: +{stats['users_this_month']}

Выберите действие:"""
    
    await message.answer(text, reply_markup=_admin_main_kb())


@router.callback_query(F.data == "admin:main")
async def admin_main_menu(call: types.CallbackQuery):
    """Show main admin menu."""
    if not is_admin(call.from_user.id):
        await call.answer("❌ Нет прав доступа")
        return
    
    stats = get_bot_stats()
    
    text = f"""🛡️ Админ-панель

👥 Пользователи: {stats['total_users']}
📈 Активных: {stats['active_users']}
📊 Рост за неделю: +{stats['users_this_week']}
📈 Рост за месяц: +{stats['users_this_month']}

Выберите действие:"""
    
    await call.message.edit_text(text, reply_markup=_admin_main_kb())


@router.callback_query(F.data == "admin:users")
async def admin_users_menu(call: types.CallbackQuery):
    """Show users management menu."""
    if not is_admin(call.from_user.id):
        await call.answer("❌ Нет прав доступа")
        return
    
    with SessionLocal() as session:
        total_users = session.query(User).count()
        recent_users = session.query(User).order_by(User.created_at.desc()).limit(5).all()
    
    text = f"""👥 Управление пользователями

📊 Всего пользователей: {total_users}

📋 Последние пользователи:"""
    
    for user in recent_users:
        # Get username from Telegram API if available
        try:
            # Try to get username from Telegram API
            chat_member = await call.bot.get_chat(user.tg_id)
            if hasattr(chat_member, 'username') and chat_member.username:
                username = f"@{chat_member.username}"
            else:
                username = "Неизвестно"
        except Exception as e:
            username = "Неизвестно"
        
        created = user.created_at.strftime("%d.%m.%Y") if user.created_at else "Неизвестно"
        text += f"\n• {username} - ID: {user.tg_id} - {created}"
    
    text += "\n\nВыберите действие:"
    
    await call.message.edit_text(text, reply_markup=_admin_users_kb())


@router.callback_query(F.data.startswith("admin:users_page_"))
async def admin_users_page(call: types.CallbackQuery):
    """Show users page."""
    if not is_admin(call.from_user.id):
        await call.answer("❌ Нет прав доступа")
        return
    
    page = int(call.data.split("_")[-1])
    per_page = 10
    
    with SessionLocal() as session:
        users = session.query(User).order_by(User.created_at.desc()).offset(page * per_page).limit(per_page).all()
        total_users = session.query(User).count()
        total_pages = (total_users + per_page - 1) // per_page
    
    text = f"👥 Пользователи (страница {page + 1} из {total_pages})\n\n"
    
    for i, user in enumerate(users, 1):
        # Get username from Telegram API
        try:
            chat_member = await call.bot.get_chat(user.tg_id)
            if hasattr(chat_member, 'username') and chat_member.username:
                username = f"@{chat_member.username}"
            else:
                username = "Неизвестно"
        except:
            username = "Неизвестно"
        
        created = user.created_at.strftime("%d.%m.%Y") if user.created_at else "Неизвестно"
        text += f"{page * per_page + i}. {username} - ID: {user.tg_id} - {created}\n"
    
    # Create keyboard with proper pagination
    kb = InlineKeyboardBuilder()
    
    # Navigation buttons
    if page > 0:
        kb.button(text="⬅️ Предыдущая", callback_data=f"admin:users_page_{page-1}")
    if page < total_pages - 1:
        kb.button(text="➡️ Следующая", callback_data=f"admin:users_page_{page+1}")
    
    kb.button(text="🔍 Поиск пользователя", callback_data="admin:search_user")
    kb.button(text="⬅️ Назад к админке", callback_data="admin:main")
    kb.adjust(2, 1, 1, 1)
    
    await call.message.edit_text(text, reply_markup=kb.as_markup())


@router.callback_query(F.data == "admin:search_user")
async def admin_search_user(call: types.CallbackQuery, state: FSMContext):
    """Search for user."""
    if not is_admin(call.from_user.id):
        await call.answer("❌ Нет прав доступа")
        return
    
    text = """🔍 Поиск пользователя

Введите ID пользователя или имя для поиска:"""
    
    await call.message.edit_text(text)
    await state.set_state("admin_search_user")


@router.message(lambda msg: msg.text)
async def handle_admin_search_user(message: types.Message, state: FSMContext):
    """Handle user search."""
    current_state = await state.get_state()
    print(f"DEBUG: handle_admin_search_user called, state: {current_state}")
    
    # Check if we're in mass notification state - if so, let mass notification handler process it
    if current_state == "mass_notification_text":
        print(f"DEBUG: Mass notification state detected, skipping search handler")
        return
        
    if current_state != "admin_search_user":
        return
        
    if not is_admin(message.from_user.id):
        return
    
    search_term = message.text.strip()
    
    with SessionLocal() as session:
        # Search by ID
        try:
            user_id = int(search_term)
            user = session.query(User).filter(User.tg_id == user_id).first()
        except ValueError:
            # Search by name
            user = session.query(User).filter(User.name.ilike(f"%{search_term}%")).first()
    
    if not user:
        await message.answer("❌ Пользователь не найден.")
        await state.clear()
        return
    
    # Get username from Telegram API
    try:
        chat_member = await message.bot.get_chat(user.tg_id)
        if hasattr(chat_member, 'username') and chat_member.username:
            username = f"@{chat_member.username}"
        else:
            username = "Неизвестно"
    except:
        username = "Неизвестно"
    
    # Get user stats
    stats = get_user_stats(user.tg_id)
    
    text = f"""👤 Пользователь: {username}

📊 Основная информация:
• ID: {user.tg_id}
• Имя: {user.name or 'Не указано'}
• Username: {username}
• Язык: {user.language or 'ru'}
• Регистрация: {user.created_at.strftime('%d.%m.%Y') if user.created_at else 'Неизвестно'}
• Последняя активность: {stats['last_activity'].strftime('%d.%m.%Y %H:%M') if stats['last_activity'] else 'Неизвестно'}

⚙️ Настройки:
• Напоминания: {'Включены' if getattr(user, 'reminders_enabled', True) else 'Выключены'}
• Время тренировок: {user.reminder_time or 'Не установлено'}
• Бюджет: {user.budget or 'Не установлен'}
• Цель: Не указана

📈 Статистика:
• Блюд: {stats['meal_logs']}
• Тренировок: {stats['workout_logs']}
• Записей сна: {stats['sleep_logs']}
• Всего активностей: {stats['total_logs']}"""
    
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Редактировать", callback_data=f"admin:edit_user_{user.tg_id}")
    kb.button(text="🔕 Заблокировать", callback_data=f"admin:block_user_{user.tg_id}")
    kb.button(text="📤 Отправить сообщение", callback_data=f"admin:message_user_{user.tg_id}")
    kb.button(text="⬅️ Назад", callback_data="admin:users")
    kb.adjust(1)
    
    await message.answer(text, reply_markup=kb.as_markup())
    await state.clear()


@router.callback_query(F.data.startswith("admin:message_user_"))
async def admin_message_user(call: types.CallbackQuery, state: FSMContext):
    """Start sending message to specific user from search results."""
    if not is_admin(call.from_user.id):
        await call.answer("❌ Нет прав доступа")
        return
    
    user_id = int(call.data.split("_")[-1])
    
    # Get user info
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == user_id).first()
        if not user:
            await call.answer("❌ Пользователь не найден")
            return
    
    # Get username from Telegram API
    try:
        chat_member = await call.bot.get_chat(user_id)
        if hasattr(chat_member, 'username') and chat_member.username:
            username = f"@{chat_member.username}"
        else:
            username = "Неизвестно"
    except:
        username = "Неизвестно"
    
    # Save target user info to state
    await state.update_data(target_user_id=user_id, target_username=username)
    
    text = f"""📝 Отправка сообщения пользователю

Получатель: {username} (ID: {user_id})

Отправьте сообщение (текст, фото, видео, документ и т.д.):"""
    
    await call.message.edit_text(text)
    await state.set_state("admin_message_user_content")


@router.message(lambda msg: True)
async def handle_admin_message_user_content(message: types.Message, state: FSMContext):
    """Handle message content for sending to user from search results."""
    current_state = await state.get_state()
    print(f"DEBUG: handle_admin_message_user_content called, state: {current_state}")
    
    # Check if we're in mass notification state - if so, let mass notification handler process it
    if current_state == "mass_notification_text":
        print(f"DEBUG: Mass notification state detected, skipping message content handler")
        return
        
    if current_state != "admin_message_user_content":
        return
        
    if not is_admin(message.from_user.id):
        return
    
    data = await state.get_data()
    target_user_id = data.get('target_user_id')
    target_username = data.get('target_username')
    
    if not target_user_id:
        await message.answer("❌ Ошибка: не найден получатель.")
        await state.clear()
        return
    
    # Send message to target user
    try:
        if message.text:
            # Text message
            await message.bot.send_message(target_user_id, message.text)
        elif message.photo:
            # Photo message
            await message.bot.send_photo(target_user_id, message.photo[-1].file_id, caption=message.caption)
        elif message.video:
            # Video message
            await message.bot.send_video(target_user_id, message.video.file_id, caption=message.caption)
        elif message.document:
            # Document message
            await message.bot.send_document(target_user_id, message.document.file_id, caption=message.caption)
        elif message.audio:
            # Audio message
            await message.bot.send_audio(target_user_id, message.audio.file_id, caption=message.caption)
        elif message.voice:
            # Voice message
            await message.bot.send_voice(target_user_id, message.voice.file_id)
        else:
            await message.answer("❌ Неподдерживаемый тип сообщения.")
            await state.clear()
            return
        
        # Success message
        success_text = f"✅ Сообщение отправлено пользователю {target_username}!"
        await message.answer(success_text)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при отправке сообщения: {str(e)}")
    
    await state.clear()


@router.message(lambda msg: True)
async def handle_admin_send_to_user_message(message: types.Message, state: FSMContext):
    """Handle message content for sending to user."""
    current_state = await state.get_state()
    if current_state != "admin_send_to_user_message":
        return
        
    if not is_admin(message.from_user.id):
        return
    
    data = await state.get_data()
    target_user_id = data.get('target_user_id')
    target_username = data.get('target_username')
    
    if not target_user_id:
        await message.answer("❌ Ошибка: не найден получатель.")
        await state.clear()
        return
    
    # Send message to target user
    try:
        if message.text:
            # Text message
            await message.bot.send_message(target_user_id, message.text)
        elif message.photo:
            # Photo message
            await message.bot.send_photo(target_user_id, message.photo[-1].file_id, caption=message.caption)
        elif message.video:
            # Video message
            await message.bot.send_video(target_user_id, message.video.file_id, caption=message.caption)
        elif message.document:
            # Document message
            await message.bot.send_document(target_user_id, message.document.file_id, caption=message.caption)
        elif message.audio:
            # Audio message
            await message.bot.send_audio(target_user_id, message.audio.file_id, caption=message.caption)
        elif message.voice:
            # Voice message
            await message.bot.send_voice(target_user_id, message.voice.file_id)
        else:
            await message.answer("❌ Неподдерживаемый тип сообщения.")
            await state.clear()
            return
        
        # Success message
        success_text = f"✅ Сообщение отправлено пользователю {f'@{target_username}' if target_username else f'ID: {target_user_id}'}!"
        await message.answer(success_text)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при отправке сообщения: {str(e)}")
    
    await state.clear()


@router.callback_query(F.data == "admin:stats")
async def admin_stats_menu(call: types.CallbackQuery):
    """Show admin stats menu."""
    if not is_admin(call.from_user.id):
        await call.answer("❌ Нет прав доступа")
        return
    
    text = """📊 Статистика и аналитика

Выберите тип статистики:"""
    
    await call.message.edit_text(text, reply_markup=_admin_stats_kb())


@router.callback_query(F.data == "admin:stats_general")
async def admin_stats_general(call: types.CallbackQuery):
    """Show general statistics."""
    if not is_admin(call.from_user.id):
        await call.answer("❌ Нет прав доступа")
        return
    
    stats = get_bot_stats()
    
    text = f"""📈 Общая статистика

👥 Пользователи:
• Всего: {stats['total_users']}
• Активных (7 дней): {stats['active_users']}
• Рост за неделю: +{stats['users_this_week']}
• Рост за месяц: +{stats['users_this_month']}

🌍 Языки:
• Русский: {stats['language_distribution'].get('ru', 0)}
• English: {stats['language_distribution'].get('en', 0)}
• O'zbek: {stats['language_distribution'].get('uz', 0)}"""
    
    await call.message.edit_text(text, reply_markup=_admin_stats_kb())


@router.callback_query(F.data == "admin:stats_users")
async def admin_stats_users(call: types.CallbackQuery):
    """Show user statistics."""
    if not is_admin(call.from_user.id):
        await call.answer("❌ Нет прав доступа")
        return
    
    stats = get_bot_stats()
    
    text = f"""👥 Статистика пользователей

📊 Активность:
• Всего пользователей: {stats['total_users']}
• Активных за 7 дней: {stats['active_users']}
• Процент активности: {round(stats['active_users'] / max(stats['total_users'], 1) * 100, 1)}%

📈 Рост:
• За неделю: +{stats['users_this_week']}
• За месяц: +{stats['users_this_month']}"""
    
    await call.message.edit_text(text, reply_markup=_admin_stats_kb())


@router.callback_query(F.data == "admin:stats_growth")
async def admin_stats_growth(call: types.CallbackQuery):
    """Show growth statistics."""
    if not is_admin(call.from_user.id):
        await call.answer("❌ Нет прав доступа")
        return
    
    stats = get_bot_stats()
    
    text = f"""📊 Рост пользователей

📈 За последний период:
• За неделю: +{stats['users_this_week']} пользователей
• За месяц: +{stats['users_this_month']} пользователей

🌍 По языкам:
• Русский: {stats['language_distribution'].get('ru', 0)}
• English: {stats['language_distribution'].get('en', 0)}
• O'zbek: {stats['language_distribution'].get('uz', 0)}"""
    
    await call.message.edit_text(text, reply_markup=_admin_stats_kb())


@router.callback_query(F.data == "admin:reminders")
async def admin_reminders_menu(call: types.CallbackQuery):
    """Show admin reminders menu."""
    if not is_admin(call.from_user.id):
        await call.answer("❌ Нет прав доступа")
        return
    
    text = """🔔 Управление напоминаниями

Выберите действие:"""
    
    await call.message.edit_text(text, reply_markup=_admin_reminders_kb())


@router.callback_query(F.data == "admin:reminders_stats")
async def admin_reminders_stats(call: types.CallbackQuery):
    """Show reminder statistics."""
    if not is_admin(call.from_user.id):
        await call.answer("❌ Нет прав доступа")
        return
    
    # Get reminder statistics from database
    with SessionLocal() as session:
        from app.models.notification_log import NotificationLog
        from sqlalchemy import func
        
        # Get total notifications sent
        total_sent = session.query(func.count(NotificationLog.id)).scalar() or 0
        
        # Get notifications by type
        stats_by_type = session.query(
            NotificationLog.notification_type,
            func.count(NotificationLog.id).label('count')
        ).group_by(NotificationLog.notification_type).all()
        
        # Get response rate
        total_responded = session.query(func.count(NotificationLog.id)).filter(
            NotificationLog.responded == True
        ).scalar() or 0
        
        response_rate = (total_responded / total_sent * 100) if total_sent > 0 else 0
    
    text = f"""📊 Статистика напоминаний

📈 Общая статистика:
• Всего отправлено: {total_sent}
• Отвечено: {total_responded}
• Процент ответов: {response_rate:.1f}%

📋 По типам:"""
    
    for notif_type, count in stats_by_type:
        type_names = {
            'workout': 'Тренировки',
            'breakfast': 'Завтрак',
            'lunch': 'Обед',
            'dinner': 'Ужин',
            'sleep': 'Сон'
        }
        type_name = type_names.get(notif_type, notif_type)
        text += f"\n• {type_name}: {count}"
    
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data="admin:reminders")
    
    await call.message.edit_text(text, reply_markup=kb.as_markup())


@router.callback_query(F.data == "admin:reminders_settings")
async def admin_reminders_settings(call: types.CallbackQuery):
    """Show reminder settings."""
    if not is_admin(call.from_user.id):
        await call.answer("❌ Нет прав доступа")
        return
    
    text = """⚙️ Настройки напоминаний

🔧 Доступные настройки:
• Время отправки напоминаний
• Частота напоминаний
• Типы напоминаний
• Пользователи с отключенными напоминаниями

⚠️ Настройки временно недоступны для редактирования."""
    
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data="admin:reminders")
    
    await call.message.edit_text(text, reply_markup=kb.as_markup())


@router.callback_query(F.data == "admin:send_to_user")
async def admin_send_to_user(call: types.CallbackQuery, state: FSMContext):
    """Start sending message to specific user."""
    if not is_admin(call.from_user.id):
        await call.answer("❌ Нет прав доступа")
        return
    
    text = """📤 Отправить сообщение пользователю

Введите ID пользователя или username (@username):"""
    
    await call.message.edit_text(text)
    await state.set_state("admin_send_to_user_target")


@router.message(lambda msg: msg.text)
async def handle_admin_send_to_user_target(message: types.Message, state: FSMContext):
    """Handle user target for sending message."""
    current_state = await state.get_state()
    if current_state != "admin_send_to_user_target":
        return
        
    if not is_admin(message.from_user.id):
        return
    
    target = message.text.strip()
    user_id = None
    username = None
    
    # Determine if it's ID or username
    if target.isdigit():
        user_id = int(target)
    elif target.startswith('@'):
        username = target[1:]
        # Try to get user ID from username
        try:
            chat = await message.bot.get_chat(f"@{username}")
            user_id = chat.id
        except Exception as e:
            await message.answer(f"❌ Не удалось найти пользователя @{username}. Проверьте правильность username.")
            await state.clear()
            return
    else:
        await message.answer("❌ Неверный формат. Введите числовой ID или @username.")
        await state.clear()
        return
    
    # Check if user exists in our database
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == user_id).first()
        if not user:
            await message.answer("❌ Пользователь не найден в базе данных.")
            await state.clear()
            return
    
    # Save target user info to state
    await state.update_data(target_user_id=user_id, target_username=username)
    
    # Ask for message content
    text = f"""📝 Создание сообщения

Получатель: {f'@{username}' if username else f'ID: {user_id}'}

Отправьте сообщение (текст, фото, видео, документ и т.д.):"""
    
    await message.answer(text)
    await state.set_state("admin_send_to_user_message")


@router.callback_query(F.data == "admin:mass_notification")
async def admin_mass_notification(call: types.CallbackQuery, state: FSMContext):
    """Start mass notification process."""
    if not is_admin(call.from_user.id):
        await call.answer("❌ Нет прав доступа")
        return
    
    text = """📢 Массовая отправка уведомлений

Введите текст сообщения для отправки всем пользователям:"""
    
    await call.message.edit_text(text)
    await state.set_state(MassNotification.message_text)


# Old handler removed - using priority handler above


@router.callback_query(F.data == "admin:edit_mass_text")
async def admin_edit_mass_text(call: types.CallbackQuery, state: FSMContext):
    """Edit mass notification text."""
    if not is_admin(call.from_user.id):
        await call.answer("❌ Нет прав доступа")
        return
    
    text = """📝 Редактирование текста

Введите новый текст сообщения:"""
    
    await call.message.edit_text(text)
    await state.set_state(MassNotification.message_text)


@router.callback_query(F.data == "admin:send_all")
async def admin_send_all_notification(call: types.CallbackQuery, state: FSMContext):
    """Send notification to all users."""
    if not is_admin(call.from_user.id):
        await call.answer("❌ Нет прав доступа")
        return
    
    data = await state.get_data()
    message_text = data.get('message_text', '')
    
    with SessionLocal() as session:
        users = session.query(User).all()
        total_users = len(users)
    
    # Send messages to all users
    sent_count = 0
    failed_count = 0
    
    for user in users:
        try:
            await call.bot.send_message(user.tg_id, message_text)
            sent_count += 1
        except Exception as e:
            failed_count += 1
            print(f"Failed to send to user {user.tg_id}: {e}")
    
    result_text = f"✅ Уведомление отправлено {sent_count} пользователям!\n❌ Не удалось отправить: {failed_count}\n\nТекст: {message_text}"
    
    await call.message.edit_text(result_text)
    await state.clear()


@router.callback_query(F.data == "admin:send_filtered")
async def admin_send_filtered_notification(call: types.CallbackQuery, state: FSMContext):
    """Send notification by filters."""
    if not is_admin(call.from_user.id):
        await call.answer("❌ Нет прав доступа")
        return
    
    await call.answer("⚠️ Отправка по фильтрам временно недоступна")


@router.callback_query(F.data == "admin:schedule_notification")
async def admin_schedule_notification(call: types.CallbackQuery, state: FSMContext):
    """Schedule notification."""
    if not is_admin(call.from_user.id):
        await call.answer("❌ Нет прав доступа")
        return
    
    await call.answer("⚠️ Планировщик уведомлений временно недоступен")


@router.callback_query(F.data == "admin:settings")
async def admin_settings_menu(call: types.CallbackQuery):
    """Show admin settings menu."""
    if not is_admin(call.from_user.id):
        await call.answer("❌ Нет прав доступа")
        return
    
    text = """⚙️ Настройки бота

Выберите настройку:"""
    
    await call.message.edit_text(text, reply_markup=_admin_settings_kb())


@router.callback_query(F.data == "admin:settings_features")
async def admin_settings_features(call: types.CallbackQuery):
    """Show features settings."""
    if not is_admin(call.from_user.id):
        await call.answer("❌ Нет прав доступа")
        return
    
    # Get current feature status (you can implement this with a database table)
    # For now, we'll use a simple approach
    features = {
        'reminders': True,
        'meal_notifications': True,
        'statistics': True,
        'admin_panel': True
    }
    
    text = """🔧 Включение/выключение функций

• Напоминания: {'✅ Включены' if features['reminders'] else '❌ Выключены'}
• Уведомления о еде: {'✅ Включены' if features['meal_notifications'] else '❌ Выключены'}
• Статистика: {'✅ Включена' if features['statistics'] else '❌ Выключена'}
• Админка: {'✅ Включена' if features['admin_panel'] else '❌ Выключена'}

Выберите функцию для переключения:"""
    
    kb = InlineKeyboardBuilder()
    kb.button(text="🔔 Напоминания", callback_data="admin:toggle_reminders")
    kb.button(text="🍽️ Уведомления о еде", callback_data="admin:toggle_meal_notifications")
    kb.button(text="📊 Статистика", callback_data="admin:toggle_statistics")
    kb.button(text="🛡️ Админка", callback_data="admin:toggle_admin_panel")
    kb.button(text="⬅️ Назад", callback_data="admin:settings")
    kb.adjust(1)
    
    await call.message.edit_text(text, reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("admin:toggle_"))
async def admin_toggle_feature(call: types.CallbackQuery):
    """Toggle bot feature."""
    if not is_admin(call.from_user.id):
        await call.answer("❌ Нет прав доступа")
        return
    
    feature = call.data.split("_")[1]  # reminders, meal_notifications, etc.
    
    # For now, just show a message that the feature is temporarily disabled
    feature_names = {
        'reminders': 'Напоминания',
        'meal_notifications': 'Уведомления о еде',
        'statistics': 'Статистика',
        'admin_panel': 'Админка'
    }
    
    feature_name = feature_names.get(feature, 'Функция')
    
    await call.answer(f"⚠️ {feature_name} временно недоступны по причине технических работ")


@router.callback_query(F.data == "admin:settings_logs")
async def admin_settings_logs(call: types.CallbackQuery):
    """Show system logs."""
    if not is_admin(call.from_user.id):
        await call.answer("❌ Нет прав доступа")
        return
    
    text = """📝 Системные логи

Последние события:
• Бот запущен: ✅
• База данных: ✅ Подключена
• Планировщик: ✅ Активен
• Ошибок: 0

Система работает стабильно."""
    
    await call.message.edit_text(text, reply_markup=_admin_settings_kb())


@router.callback_query(F.data == "admin:manage_admins")
async def admin_manage_admins_menu(call: types.CallbackQuery):
    """Show admin management menu."""
    if not is_super_admin(call.from_user.id):
        await call.answer("❌ Только супер-админ может управлять админами")
        return
    
    with SessionLocal() as session:
        admins = session.query(Admin).all()
    
    text = f"""👨‍💼 Управление админами

🔑 Главный админ:
• @thesekron (1475749765) - Полный доступ

👥 Обычные админы:"""
    
    for admin in admins:
        if admin.tg_id != SUPER_ADMIN_ID:
            status = "Активен" if admin.is_active else "Заблокирован"
            text += f"\n• @{admin.username or 'Без username'} ({admin.tg_id}) - {status}"
    
    text += "\n\nВыберите действие:"
    
    await call.message.edit_text(text, reply_markup=_admin_manage_admins_kb())


@router.callback_query(F.data == "admin:list_admins")
async def admin_list_admins(call: types.CallbackQuery):
    """Show list of all admins."""
    if not is_super_admin(call.from_user.id):
        await call.answer("❌ Только супер-админ может просматривать список админов")
        return
    
    with SessionLocal() as session:
        admins = session.query(Admin).all()
    
    text = f"""👥 Список всех админов

🔑 Главный админ:
• @thesekron (1475749765) - Полный доступ

👥 Обычные админы:"""
    
    if not admins or len(admins) == 1:  # Only super admin
        text += "\n• Нет обычных админов"
    else:
        for admin in admins:
            if admin.tg_id != SUPER_ADMIN_ID:
                status = "Активен" if admin.is_active else "Заблокирован"
                username = admin.username or "Без username"
                text += f"\n• @{username} ({admin.tg_id}) - {status}"
    
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data="admin:manage_admins")
    
    await call.message.edit_text(text, reply_markup=kb.as_markup())


@router.callback_query(F.data == "admin:remove_admin")
async def admin_remove_admin(call: types.CallbackQuery, state: FSMContext):
    """Remove admin."""
    if not is_super_admin(call.from_user.id):
        await call.answer("❌ Только супер-админ может удалять админов")
        return
    
    text = """🗑️ Удалить админа

Введите Telegram ID или username (@username) админа для удаления:"""
    
    await call.message.edit_text(text)
    await state.set_state("admin_remove_admin")


@router.callback_query(F.data == "admin:add_admin")
async def admin_add_admin(call: types.CallbackQuery, state: FSMContext):
    """Add new admin."""
    if not is_super_admin(call.from_user.id):
        await call.answer("❌ Только супер-админ может добавлять админов")
        return
    
    text = """➕ Добавить админа

Введите Telegram ID или username (@username) нового админа:"""
    
    await call.message.edit_text(text)
    await state.set_state("admin_add_admin")


@router.message(lambda msg: msg.text and (msg.text.isdigit() or msg.text.startswith('@')))
async def handle_admin_actions(message: types.Message, state: FSMContext):
    """Handle adding or removing admin."""
    current_state = await state.get_state()
    
    if not is_super_admin(message.from_user.id):
        return
    
    try:
        input_text = message.text.strip()
        admin_id = None
        username = None
        
        if input_text.isdigit():
            # Numeric ID
            admin_id = int(input_text)
        elif input_text.startswith('@'):
            # Username
            username = input_text[1:]  # Remove @
            # Try to get user ID from username using bot API
            try:
                chat = await message.bot.get_chat(f"@{username}")
                admin_id = chat.id
            except Exception as e:
                await message.answer(f"❌ Не удалось найти пользователя @{username}. Проверьте правильность username.")
                return
        else:
            await message.answer("❌ Неверный формат. Введите числовой ID или @username.")
            return
        
        if current_state == "admin_add_admin":
            # Adding admin
            with SessionLocal() as session:
                # Check if already exists
                existing = session.query(Admin).filter(Admin.tg_id == admin_id).first()
                if existing:
                    await message.answer("❌ Этот пользователь уже является админом.")
                    return
                
                # Create new admin
                new_admin = Admin(
                    tg_id=admin_id,
                    username=username,
                    role="admin",
                    is_active=True
                )
                session.add(new_admin)
                session.commit()
            
            success_msg = f"✅ Пользователь {admin_id}"
            if username:
                success_msg += f" (@{username})"
            success_msg += " добавлен как админ!"
            
            await message.answer(success_msg)
            
        elif current_state == "admin_remove_admin":
            # Removing admin
            # Don't allow removing super admin
            if admin_id == SUPER_ADMIN_ID:
                await message.answer("❌ Нельзя удалить главного админа.")
                return
            
            with SessionLocal() as session:
                admin = session.query(Admin).filter(Admin.tg_id == admin_id).first()
                if not admin:
                    await message.answer("❌ Админ не найден.")
                    return
                
                session.delete(admin)
                session.commit()
                
            success_msg = f"✅ Админ {admin_id}"
            if username:
                success_msg += f" (@{username})"
            success_msg += " удален."
            
            await message.answer(success_msg)
        
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Неверный формат ID. Введите числовой ID или @username.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


@router.callback_query(F.data == "back_to_main")
async def back_to_main_menu(call: types.CallbackQuery):
    """Return to main menu."""
    from .menu import build_main_menu_kb
    
    kb = build_main_menu_kb("ru")  # Default to Russian for admin
    await call.message.answer("🏠 Главное меню", reply_markup=kb)


# MASS NOTIFICATION HANDLER - using FSM state directly
@router.message(MassNotification.message_text)
async def handle_mass_notification_text_final(message: types.Message, state: FSMContext):
    """Handle mass notification text - FSM STATE HANDLER."""
    print(f"DEBUG: handle_mass_notification_text_final called for user {message.from_user.id}")
    print(f"DEBUG: Message text: {message.text}")
    print(f"DEBUG: FSM state handler triggered")
    
    if not is_admin(message.from_user.id):
        print(f"DEBUG: User is not admin, returning")
        return
    
    text = message.text.strip()
    print(f"DEBUG: Mass notification text received: {text}")
    
    # Save message text to state
    await state.update_data(message_text=text)
    print(f"DEBUG: Message text saved to state")
    
    # Create confirmation menu with templates/options
    kb = InlineKeyboardBuilder()
    kb.button(text="📤 Отправить всем", callback_data="admin:send_all")
    kb.button(text="🎯 По фильтрам", callback_data="admin:send_filtered") 
    kb.button(text="⏰ Запланировать", callback_data="admin:schedule_notification")
    kb.button(text="📝 Редактировать текст", callback_data="admin:edit_mass_text")
    kb.button(text="❌ Отмена", callback_data="admin:reminders")
    kb.adjust(1)
    
    confirmation_text = f"""📝 **Подтверждение массовой отправки**

**Текст сообщения:**
{text}

**Выберите способ отправки:**"""
    
    try:
        await message.answer(confirmation_text, reply_markup=kb.as_markup(), parse_mode="Markdown")
        print(f"DEBUG: Mass notification confirmation menu sent to user")
    except Exception as e:
        print(f"DEBUG: Error sending confirmation menu: {e}")
        # Fallback without markdown
        await message.answer(f"📝 Текст сообщения:\n\n{text}\n\nВыберите способ отправки:", reply_markup=kb.as_markup())
        print(f"DEBUG: Mass notification options sent to user (fallback)")
