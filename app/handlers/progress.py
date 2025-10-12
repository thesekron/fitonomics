from __future__ import annotations

from aiogram import F, types
from aiogram.filters import Command
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models.user import User
from app.models.sleep_log import SleepLog
from app.services.i18n import t, T
from app.services.progress import get_comprehensive_progress_stats
from .start import router


def get_lang(user_id: int) -> str:
    db: Session = SessionLocal()
    u = db.query(User).filter(User.tg_id == user_id).first()
    lang = u.language if u and u.language else "ru"
    db.close()
    return lang


def _back_to_menu_kb(lang: str) -> types.InlineKeyboardMarkup:
    """Inline back removed."""
    return types.InlineKeyboardMarkup(inline_keyboard=[])


def _details_kb(lang: str) -> types.InlineKeyboardMarkup:
    """Build details inline keyboard."""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text=t(lang, "progress.details.workouts"), callback_data="progress:details:workouts"),
            types.InlineKeyboardButton(text=t(lang, "progress.details.sleep"), callback_data="progress:details:sleep")
        ],
        [
            types.InlineKeyboardButton(text=t(lang, "progress.details.meals"), callback_data="progress:details:meals"),
            types.InlineKeyboardButton(text=t(lang, "progress.details.weight"), callback_data="progress:details:weight")
        ]
    ])


def get_progress_stats(user_id: int) -> dict:
    """Get aggregated progress statistics for the user."""
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == user_id).first()
        if not user:
            return {}
        
        # Get sleep stats (last 7 days)
        week_ago = datetime.now() - timedelta(days=7)
        sleep_logs = (
            session.query(SleepLog)
            .filter(SleepLog.user_id == user.id)
            .filter(SleepLog.created_at >= week_ago)
            .all()
        )
        
        sleep_stats = {
            "total_nights": len(sleep_logs),
            "avg_duration": 0,
            "optimal_nights": 0,
            "deviation": 0
        }
        
        if sleep_logs:
            sleep_stats["avg_duration"] = round(sum(l.duration_hours for l in sleep_logs) / len(sleep_logs), 1)
            sleep_stats["optimal_nights"] = sum(1 for l in sleep_logs if l.evaluation in ["7_8_correct", "optimal"])
            sleep_stats["deviation"] = len(sleep_logs) - sleep_stats["optimal_nights"]
        
        # Get meal stats (last 7 days)
        from app.models.meal_log import MealLog
        meal_logs = session.query(MealLog).filter(
            MealLog.user_id == user.tg_id,
            MealLog.created_at >= week_ago
        ).all()
        
        total_meals = len(meal_logs)
        pack_meals = [log for log in meal_logs if log.is_pack]
        custom_meals = [log for log in meal_logs if not log.is_pack]
        
        # Health ratings for custom meals
        healthy_custom = len([log for log in custom_meals if log.health_rating == "healthy"])
        normal_custom = len([log for log in custom_meals if log.health_rating == "normal"])
        unhealthy_custom = len([log for log in custom_meals if log.health_rating == "unhealthy"])
        
        # All pack meals are considered healthy
        total_healthy = len(pack_meals) + healthy_custom
        total_unhealthy = unhealthy_custom
        total_unsure = normal_custom
        
        # Calculate overall healthiness percentage
        if total_meals > 0:
            healthiness_percentage = round((total_healthy / total_meals) * 100)
        else:
            healthiness_percentage = 0
        
        meal_stats = {
            "this_week": total_meals,
            "healthy": total_healthy,
            "unsure": total_unsure,
            "unhealthy": total_unhealthy,
            "healthiness_percentage": healthiness_percentage,
            "custom_meals": len(custom_meals)
        }
        
        # Workout stats (placeholder)
        workout_stats = {
            "this_week": 0,
            "total": 0
        }
        
        return {
            "sleep": sleep_stats,
            "workouts": workout_stats,
            "meals": meal_stats,
            "user": user
        }


@router.message(Command("progress"))
async def show_progress_summary(message: types.Message):
    """Show progress summary with aggregated statistics."""
    lang = get_lang(message.from_user.id)
    stats = get_progress_stats(message.from_user.id)
    
    if not stats:
        await message.answer(t(lang, "progress.no_data"), reply_markup=_back_to_menu_kb(lang))
        return
    
    # Build summary text
    text = f"{t(lang, 'progress.title')}\n\n"
    
    # Sleep summary
    sleep = stats["sleep"]
    if sleep["total_nights"] > 0:
        text += f"😴 {t(lang, 'progress.sleep.title')}:\n"
        text += f"   • {t(lang, 'progress.sleep.avg_duration')}: {sleep['avg_duration']:.1f}h\n"
        text += f"   • {t(lang, 'progress.sleep.optimal_nights')}: {sleep['optimal_nights']}/{sleep['total_nights']}\n"
        if sleep.get("electronics_used", 0) > 0:
            text += f"   • {t(lang, 'progress.sleep.electronics')}: {sleep['electronics_used']} {t(lang, 'progress.sleep.nights')}\n"
    else:
        text += f"😴 {t(lang, 'progress.sleep.no_data')}\n"
    
    # Workout summary
    workouts = stats["workouts"]
    text += f"\n🏋️ {t(lang, 'progress.workouts.title')}:\n"
    text += f"   • {t(lang, 'progress.workouts.this_week')}: {workouts['total']}\n"
    
    # Meal summary
    meals = stats["meals"]
    text += f"\n🍽️ {t(lang, 'progress.meals.title')}:\n"
    text += f"   • {t(lang, 'progress.meals.this_week')}: {meals['this_week']}\n"
    text += f"   • {t(lang, 'progress.meals.healthy')}: {meals['healthy']}\n"
    text += f"   • {t(lang, 'progress.meals.unsure')}: {meals['unsure']}\n"
    text += f"   • {t(lang, 'progress.meals.unhealthy')}: {meals['unhealthy']}\n"
    text += f"   • {t(lang, 'progress.meals.healthiness')}: {meals['healthiness_percentage']}%\n"
    text += f"   • {t(lang, 'progress.meals.custom')}: {meals['custom_meals']}\n"
    
    await message.answer(text, reply_markup=_details_kb(lang))


async def show_progress_summary_from_menu(message: types.Message, lang: str, reply_markup=None):
    """Show progress summary - called from main menu."""
    stats = get_progress_stats(message.from_user.id)
    
    if not stats:
        if reply_markup:
            await message.answer("🔽", reply_markup=reply_markup)
        await message.answer(t(lang, "progress.no_data"), reply_markup=_back_to_menu_kb(lang))
        return
    
    # Build summary text
    text = f"{t(lang, 'progress.title')}\n\n"
    
    # Sleep summary
    sleep = stats["sleep"]
    if sleep["total_nights"] > 0:
        text += f"😴 {t(lang, 'progress.sleep.title')}:\n"
        text += f"   • {t(lang, 'progress.sleep.avg_duration')}: {sleep['avg_duration']}h\n"
        text += f"   • {t(lang, 'progress.sleep.optimal_nights')}: {sleep['optimal_nights']}/{sleep['total_nights']}\n"
        if sleep["deviation"] > 0:
            text += f"   • {t(lang, 'progress.sleep.deviation')}: {sleep['deviation']} {t(lang, 'progress.sleep.nights')}\n"
    else:
        text += f"😴 {t(lang, 'progress.sleep.no_data')}\n"
    
    # Workout summary
    workouts = stats["workouts"]
    text += f"\n🏋️ {t(lang, 'progress.workouts.title')}:\n"
    text += f"   • {t(lang, 'progress.workouts.this_week')}: {workouts['this_week']}\n"
    text += f"   • {t(lang, 'progress.workouts.total')}: {workouts['total']}\n"
    
    # Meal summary
    meals = stats["meals"]
    text += f"\n🍽️ {t(lang, 'progress.meals.title')}:\n"
    text += f"   • {t(lang, 'progress.meals.this_week')}: {meals['this_week']}\n"
    text += f"   • {t(lang, 'progress.meals.healthy')}: {meals['healthy']}\n"
    text += f"   • {t(lang, 'progress.meals.unsure')}: {meals['unsure']}\n"
    text += f"   • {t(lang, 'progress.meals.unhealthy')}: {meals['unhealthy']}\n"
    text += f"   • {t(lang, 'progress.meals.healthiness')}: {meals['healthiness_percentage']}%\n"
    text += f"   • {t(lang, 'progress.meals.custom')}: {meals['custom_meals']}\n"
    
    if reply_markup:
        await message.answer("🔽", reply_markup=reply_markup)
    await message.answer(text, reply_markup=_details_kb(lang))


# inline back removed


@router.callback_query(F.data.startswith("progress:details:"))
async def show_details(call: types.CallbackQuery):
    """Show detailed progress for specific category."""
    lang = get_lang(call.from_user.id)
    detail_type = call.data.split(":")[2]
    
    stats = get_progress_stats(call.from_user.id)
    if not stats:
        await call.answer(t(lang, "progress.no_data"))
        return
    
    text = f"{t(lang, f'progress.details.{detail_type}.title')}\n\n"
    
    if detail_type == "sleep":
        sleep = stats["sleep"]
        if sleep["total_nights"] > 0:
            text += f"📊 {t(lang, 'progress.details.sleep.last_7_days')}:\n"
            text += f"   • {t(lang, 'progress.details.sleep.nights_tracked')}: {sleep['total_nights']}\n"
            text += f"   • {t(lang, 'progress.details.sleep.avg_duration')}: {sleep['avg_duration']}h\n"
            text += f"   • {t(lang, 'progress.details.sleep.optimal_pct')}: {round(100 * sleep['optimal_nights'] / sleep['total_nights'])}%\n"
        else:
            text += t(lang, "progress.details.sleep.no_data")
    
    elif detail_type == "workouts":
        workouts = stats["workouts"]
        text += f"📊 {t(lang, 'progress.details.workouts.summary')}:\n"
        text += f"   • {t(lang, 'progress.details.workouts.this_week')}: {workouts['this_week']}\n"
        text += f"   • {t(lang, 'progress.details.workouts.total')}: {workouts['total']}\n"
        # Note: by_group data not available in current stats structure
    
    elif detail_type == "meals":
        meals = stats["meals"]
        text += f"📊 {t(lang, 'progress.details.meals.summary')}:\n"
        text += f"   • {t(lang, 'progress.details.meals.this_week')}: {meals['this_week']}\n"
        text += f"   • {t(lang, 'progress.details.meals.healthy')}: {meals['healthy']}\n"
        text += f"   • {t(lang, 'progress.details.meals.unsure')}: {meals['unsure']}\n"
        text += f"   • {t(lang, 'progress.details.meals.unhealthy')}: {meals['unhealthy']}\n"
        text += f"   • {t(lang, 'progress.details.meals.healthiness')}: {meals['healthiness_percentage']}%\n"
        text += f"   • {t(lang, 'progress.details.meals.custom')}: {meals['custom_meals']}\n"
    
    elif detail_type == "weight":
        user = stats["user"]
        if user.weight:
            text += f"📊 {t(lang, 'progress.details.weight.current')}: {user.weight} kg\n"
            # TODO: Add weight tracking history when implemented
        else:
            text += t(lang, "progress.details.weight.no_data")
    
    await call.message.edit_text(text, reply_markup=_details_kb(lang))
    await call.answer()
