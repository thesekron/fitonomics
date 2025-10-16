from __future__ import annotations

import logging
from datetime import time as dtime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from tzlocal import get_localzone
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types

from app.database import SessionLocal
from app.models.user import User
from app.models.user_settings import UserSettings
from app.models.meal_log import UserMealSettings
from app.models.notification_log import NotificationLog
from app.services.i18n import t
from app.services.sleep_tips import EVENING_REMINDER_TIME, MORNING_REMINDER_TIME


logger = logging.getLogger(__name__)

def log_notification(user_id: int, notification_type: str, action: str = None):
    """Log notification to database."""
    try:
        with SessionLocal() as session:
            from datetime import datetime
            log_entry = NotificationLog(
                user_id=user_id,
                notification_type=notification_type,
                sent_at=datetime.now(),
                responded=action is not None,
                action=action,
                created_at=datetime.now()
            )
            session.add(log_entry)
            session.commit()
    except Exception as e:
        logger.error("Failed to log notification: %s", e)

_scheduler: Optional[BackgroundScheduler] = None
_bot_instance = None


def set_bot_instance(bot):
    global _bot_instance
    _bot_instance = bot


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(timezone=get_localzone())
    return _scheduler


def start_scheduler() -> None:
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler started")


_TIME_MAP = {
    "morning": 8,
    "day": 13,
    "evening": 19,
}


def _get_user_language(user_id: int) -> str:
    """Get user's language from database."""
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == user_id).first()
        if user:
            return user.language or "ru"
        return "ru"


def _reminder_job(user_id: int) -> None:
    if not _bot_instance:
        logger.warning("Bot instance not set, cannot send workout reminder")
        return
    try:
        with SessionLocal() as session:
            user = session.query(User).filter(User.tg_id == user_id).first()
            if not user:
                return
            lang = user.language or "ru"
        kb = InlineKeyboardBuilder()
        kb.button(text=t(lang, "btn_start_workout"), callback_data="w:start_workout")
        kb.adjust(1)
        text = f"{t(lang, 'notif.workout.line1')}\n{t(lang, 'notif.workout.line2')}"
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(_bot_instance.send_message(user_id, text, reply_markup=kb.as_markup()))
            else:
                loop.run_until_complete(_bot_instance.send_message(user_id, text, reply_markup=kb.as_markup()))
        except Exception as e:
            logger.error("Failed to send workout reminder to user_id=%s: %s", user_id, e)
        logger.info("Sent workout reminder to user_id=%s", user_id)
    except Exception as e:
        logger.error("Failed to send workout reminder to user_id=%s: %s", user_id, e)


def _sleep_evening_job(user_id: int) -> None:
    if not _bot_instance:
        logger.warning("Bot instance not set, cannot send sleep evening notification")
        return
    
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == user_id).first()
        if not user:
            return
        
        lang = user.language or "ru"
        name = user.name or "Friend"
        
        kb = InlineKeyboardBuilder()
        kb.button(text=t(lang, "sleep.log_now"), callback_data="sleep:log")
        kb.adjust(1)
        
        text = t(lang, "sleep.evening_reminder")
        
        try:
            import requests
            import json
            
            # Get bot token from environment
            import os
            from dotenv import load_dotenv
            load_dotenv()
            bot_token = os.getenv("BOT_TOKEN")
            
            if not bot_token:
                logger.error("BOT_TOKEN not found in environment")
                return
                
            # Send message directly via Telegram API
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                "chat_id": user_id,
                "text": text,
                "reply_markup": json.dumps(kb.as_markup().model_dump())
            }
            
            response = requests.post(url, data=data, timeout=10)
            if response.status_code == 200:
                logger.info("Sent workout reminder to user_id=%s", user_id)
            else:
                logger.error("Failed to send workout reminder: %s", response.text)
        except Exception as e:
            logger.error("Failed to send workout reminder to user_id=%s: %s", user_id, e)
            logger.info("Sent sleep evening notification to user_id=%s", user_id)
        except Exception as e:
            logger.error("Failed to send sleep evening notification to user_id=%s: %s", user_id, e)


def _sleep_morning_job(user_id: int) -> None:
    if not _bot_instance:
        logger.warning("Bot instance not set, cannot send sleep morning notification")
        return
    
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == user_id).first()
        if not user:
            return
        
        lang = user.language or "ru"
        name = user.name or "Friend"
        
        kb = InlineKeyboardBuilder()
        kb.button(text=t(lang, "sleep.yes_log"), callback_data="sleep:log")
        kb.button(text=t(lang, "sleep.no_log"), callback_data="sleep:morning:no")
        kb.adjust(2)
        
        text = t(lang, "sleep.morning_reminder")
        
        try:
            import requests
            import json
            
            # Get bot token from environment
            import os
            from dotenv import load_dotenv
            load_dotenv()
            bot_token = os.getenv("BOT_TOKEN")
            
            if not bot_token:
                logger.error("BOT_TOKEN not found in environment")
                return
                
            # Send message directly via Telegram API
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                "chat_id": user_id,
                "text": text,
                "reply_markup": json.dumps(kb.as_markup().model_dump())
            }
            
            response = requests.post(url, data=data, timeout=10)
            if response.status_code == 200:
                logger.info("Sent workout reminder to user_id=%s", user_id)
            else:
                logger.error("Failed to send workout reminder: %s", response.text)
        except Exception as e:
            logger.error("Failed to send workout reminder to user_id=%s: %s", user_id, e)
            logger.info("Sent sleep morning notification to user_id=%s", user_id)
        except Exception as e:
            logger.error("Failed to send sleep morning notification to user_id=%s: %s", user_id, e)


def schedule_daily_reminder(user_id: int, when: str) -> None:
    hour = _TIME_MAP.get(when)
    if hour is None:
        raise ValueError(f"Unknown reminder time: {when}")
    scheduler = get_scheduler()
    job_id = f"reminder:{user_id}"
    trigger = CronTrigger(hour=hour, minute=0)
    scheduler.add_job(_reminder_job, trigger=trigger, id=job_id, replace_existing=True, kwargs={"user_id": user_id})
    logger.info("Scheduled daily reminder for user_id=%s at %02d:00", user_id, hour)


def load_and_schedule_all() -> None:
    """Load all users that have reminder_time set and schedule their jobs."""
    start_scheduler()
    with SessionLocal() as session:
        users = session.query(User).filter(User.reminder_time.isnot(None)).all()
        for u in users:
            try:
                schedule_daily_reminder(u.tg_id, u.reminder_time)
            except Exception as exc:
                logger.exception("Failed to schedule reminder for user_id=%s: %s", u.tg_id, exc)

        # Sleep schedules from user settings
        settings = session.query(UserSettings).all()
        for s in settings:
            try:
                schedule_sleep_notifications(s.user_id, s.sleep_time, s.wake_time)
                # Also schedule meal reminders for this user
                schedule_meal_reminders(s.user_id)
            except Exception as exc:
                logger.exception("Failed to schedule sleep/meals for user_id=%s: %s", s.user_id, exc)


def schedule_sleep_notifications(user_id: int, sleep_time: str | None, wake_time: str | None) -> None:
    """Schedule sleep notifications: evening (1 hour before sleep), morning (+5 min after wake)."""
    if not sleep_time and not wake_time:
        return
    scheduler = get_scheduler()
    # cancel existing
    for suffix in ("sleep_evening", "sleep_morning"):
        job_id = f"{suffix}:{user_id}"
        try:
            scheduler.remove_job(job_id)
        except Exception:
            pass

    if sleep_time:
        sh, sm = [int(x) for x in sleep_time.split(":")]
        # 1 hour before
        hour = (sh - 1) % 24
        minute = sm
        scheduler.add_job(
            _sleep_evening_job,
            trigger=CronTrigger(hour=hour, minute=minute),
            id=f"sleep_evening:{user_id}",
            replace_existing=True,
            kwargs={"user_id": user_id},
        )
        logger.info("Scheduled sleep-evening for user=%s at %02d:%02d", user_id, hour, minute)

    if wake_time:
        wh, wm = [int(x) for x in wake_time.split(":")]
        minute = (wm + 5) % 60
        hour = (wh + (wm + 5) // 60) % 24
        scheduler.add_job(
            _sleep_morning_job,
            trigger=CronTrigger(hour=hour, minute=minute),
            id=f"sleep_morning:{user_id}",
            replace_existing=True,
            kwargs={"user_id": user_id},
        )
        logger.info("Scheduled sleep-morning for user=%s at %02d:%02d", user_id, hour, minute)


# Meal reminder functions - connected to new reminder system
def _meal_breakfast_job(user_id: int):
    """Send breakfast reminder."""
    if not _bot_instance:
        return
    
    lang = _get_user_language(user_id)
    text = f"☀️ {t(lang, 'meals.reminder.breakfast')}"
    
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "meals.reminder.mark_now"), callback_data="meals:reminder:breakfast")
    kb.button(text=t(lang, "meals.reminder.later"), callback_data="meals:reminder:later")
    kb.adjust(1)
    
    try:
        import requests
        import json
        
        # Get bot token from environment
        import os
        from dotenv import load_dotenv
        load_dotenv()
        bot_token = os.getenv("BOT_TOKEN")
        
        if not bot_token:
            logger.error("BOT_TOKEN not found in environment")
            return
            
        # Send message directly via Telegram API
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        # Convert keyboard to proper format
        keyboard_data = kb.as_markup().model_dump()
        # Clean up the keyboard data to avoid parsing errors
        inline_keyboard = keyboard_data.get("inline_keyboard", [])
        
        # Remove null values from buttons
        clean_keyboard = []
        for row in inline_keyboard:
            clean_row = []
            for button in row:
                clean_button = {k: v for k, v in button.items() if v is not None}
                clean_row.append(clean_button)
            clean_keyboard.append(clean_row)
        
        keyboard_data = {"inline_keyboard": clean_keyboard}
        
        data = {
            "chat_id": user_id,
            "text": text,
            "reply_markup": json.dumps(keyboard_data)
        }
        
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            logger.info("Sent breakfast reminder to user=%s", user_id)
            log_notification(user_id, "breakfast")
        else:
            logger.error("Failed to send breakfast reminder: %s", response.text)
    except Exception as e:
        logger.error("Failed to send breakfast reminder to user=%s: %s", user_id, e)


def _meal_lunch_job(user_id: int):
    """Send lunch reminder."""
    if not _bot_instance:
        return
    
    lang = _get_user_language(user_id)
    text = f"☀️ {t(lang, 'meals.reminder.lunch')}"
    
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "meals.reminder.mark_now"), callback_data="meals:reminder:lunch")
    kb.button(text=t(lang, "meals.reminder.later"), callback_data="meals:reminder:later")
    kb.adjust(1)
    
    try:
        import requests
        import json
        
        # Get bot token from environment
        import os
        from dotenv import load_dotenv
        load_dotenv()
        bot_token = os.getenv("BOT_TOKEN")
        
        if not bot_token:
            logger.error("BOT_TOKEN not found in environment")
            return
            
        # Send message directly via Telegram API
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        # Convert keyboard to proper format
        keyboard_data = kb.as_markup().model_dump()
        # Clean up the keyboard data to avoid parsing errors
        inline_keyboard = keyboard_data.get("inline_keyboard", [])
        
        # Remove null values from buttons
        clean_keyboard = []
        for row in inline_keyboard:
            clean_row = []
            for button in row:
                clean_button = {k: v for k, v in button.items() if v is not None}
                clean_row.append(clean_button)
            clean_keyboard.append(clean_row)
        
        keyboard_data = {"inline_keyboard": clean_keyboard}
        
        data = {
            "chat_id": user_id,
            "text": text,
            "reply_markup": json.dumps(keyboard_data)
        }
        
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            logger.info("Sent lunch reminder to user=%s", user_id)
            log_notification(user_id, "lunch")
        else:
            logger.error("Failed to send lunch reminder: %s", response.text)
    except Exception as e:
        logger.error("Failed to send lunch reminder to user=%s: %s", user_id, e)


def _meal_dinner_job(user_id: int):
    """Send dinner reminder."""
    if not _bot_instance:
        return
    
    lang = _get_user_language(user_id)
    text = f"🌙 {t(lang, 'meals.reminder.dinner')}"
    
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "meals.reminder.mark_now"), callback_data="meals:reminder:dinner")
    kb.button(text=t(lang, "meals.reminder.later"), callback_data="meals:reminder:later")
    kb.adjust(1)
    
    try:
        import requests
        import json
        
        # Get bot token from environment
        import os
        from dotenv import load_dotenv
        load_dotenv()
        bot_token = os.getenv("BOT_TOKEN")
        
        if not bot_token:
            logger.error("BOT_TOKEN not found in environment")
            return
            
        # Send message directly via Telegram API
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        # Convert keyboard to proper format
        keyboard_data = kb.as_markup().model_dump()
        # Clean up the keyboard data to avoid parsing errors
        inline_keyboard = keyboard_data.get("inline_keyboard", [])
        
        # Remove null values from buttons
        clean_keyboard = []
        for row in inline_keyboard:
            clean_row = []
            for button in row:
                clean_button = {k: v for k, v in button.items() if v is not None}
                clean_row.append(clean_button)
            clean_keyboard.append(clean_row)
        
        keyboard_data = {"inline_keyboard": clean_keyboard}
        
        data = {
            "chat_id": user_id,
            "text": text,
            "reply_markup": json.dumps(keyboard_data)
        }
        
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            logger.info("Sent dinner reminder to user=%s", user_id)
            log_notification(user_id, "dinner")
        else:
            logger.error("Failed to send dinner reminder: %s", response.text)
    except Exception as e:
        logger.error("Failed to send dinner reminder to user=%s: %s", user_id, e)


def schedule_meal_reminders(user_id: int):
    """Schedule meal reminders for user based on their settings."""
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == user_id).first()
        if not user:
            return
        
        settings = session.query(UserSettings).filter(UserSettings.user_id == user.tg_id).first()
        if not settings:
            return
    
    scheduler = get_scheduler()
    
    # Remove existing meal reminders
    try:
        scheduler.remove_job(f"meal_breakfast:{user_id}")
    except:
        pass
    try:
        scheduler.remove_job(f"meal_lunch:{user_id}")
    except:
        pass
    try:
        scheduler.remove_job(f"meal_dinner:{user_id}")
    except:
        pass
    
    # Schedule new reminders based on user settings
    if settings.breakfast_time:
        try:
            hour, minute = map(int, settings.breakfast_time.split(':'))
            scheduler.add_job(
                _meal_breakfast_job,
                trigger=CronTrigger(hour=hour, minute=minute),
                id=f"meal_breakfast:{user_id}",
                replace_existing=True,
                kwargs={"user_id": user_id},
            )
            logger.info("Scheduled breakfast reminder for user=%s at %02d:%02d", user_id, hour, minute)
        except Exception as e:
            logger.error("Failed to schedule breakfast reminder for user=%s: %s", user_id, e)
    
    if settings.lunch_time:
        try:
            hour, minute = map(int, settings.lunch_time.split(':'))
            scheduler.add_job(
                _meal_lunch_job,
                trigger=CronTrigger(hour=hour, minute=minute),
                id=f"meal_lunch:{user_id}",
                replace_existing=True,
                kwargs={"user_id": user_id},
            )
            logger.info("Scheduled lunch reminder for user=%s at %02d:%02d", user_id, hour, minute)
        except Exception as e:
            logger.error("Failed to schedule lunch reminder for user=%s: %s", user_id, e)
    
    if settings.dinner_time:
        try:
            hour, minute = map(int, settings.dinner_time.split(':'))
            scheduler.add_job(
                _meal_dinner_job,
                trigger=CronTrigger(hour=hour, minute=minute),
                id=f"meal_dinner:{user_id}",
                replace_existing=True,
                kwargs={"user_id": user_id},
            )
            logger.info("Scheduled dinner reminder for user=%s at %02d:%02d", user_id, hour, minute)
        except Exception as e:
            logger.error("Failed to schedule dinner reminder for user=%s: %s", user_id, e)



