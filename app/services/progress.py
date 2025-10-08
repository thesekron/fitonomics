from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Tuple

from sqlalchemy import func

from app.database import SessionLocal
from app.models.workout_log import WorkoutLog
from app.models.meal_log import MealLog
from app.models.sleep_log import SleepLog


def get_progress_stats(user_id: int) -> Dict:
    """Aggregate progress statistics for a user.

    Returns dict with keys:
    - total: int
    - by_group: List[Tuple[str, int]]
    - last7: List[Tuple[str, int]]  # date string YYYY-MM-DD, count
    """
    with SessionLocal() as session:
        total = session.query(func.count(WorkoutLog.id)).filter(WorkoutLog.user_id == user_id).scalar() or 0

        by_group_rows: List[Tuple[str, int]] = (
            session.query(WorkoutLog.group, func.count(WorkoutLog.id))
            .filter(WorkoutLog.user_id == user_id)
            .group_by(WorkoutLog.group)
            .all()
        )

        since_date = (datetime.utcnow() - timedelta(days=6)).date()
        date_expr = func.date(WorkoutLog.created_at)
        last7_rows: List[Tuple[str, int]] = (
            session.query(date_expr, func.count(WorkoutLog.id))
            .filter(WorkoutLog.user_id == user_id)
            .filter(WorkoutLog.created_at >= since_date)
            .group_by(date_expr)
            .order_by(date_expr)
            .all()
        )

    # Normalize rows to plain python types
    by_group = [(g, int(c)) for g, c in by_group_rows]
    last7 = [(str(d), int(c)) for d, c in last7_rows]
    return {"total": int(total), "by_group": by_group, "last7": last7}


def get_comprehensive_progress_stats(user_id: int, days: int = 7) -> Dict:
    """Get comprehensive progress statistics including workouts, meals, and sleep."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    with SessionLocal() as session:
        # Workout stats
        workout_total = session.query(func.count(WorkoutLog.id)).filter(
            WorkoutLog.user_id == user_id,
            WorkoutLog.created_at >= start_date
        ).scalar() or 0
        
        # Sleep stats
        sleep_logs = session.query(SleepLog).filter(
            SleepLog.user_id == user_id,
            SleepLog.created_at >= start_date
        ).all()
        
        # Meal stats
        meal_logs = session.query(MealLog).filter(
            MealLog.user_id == user_id,
            MealLog.date >= start_date
        ).all()
    
    # Process sleep data
    sleep_stats = {
        "total_nights": len(sleep_logs),
        "optimal_nights": len([log for log in sleep_logs if 7 <= log.duration_hours <= 9]),
        "avg_duration": sum(log.duration_hours for log in sleep_logs) / len(sleep_logs) if sleep_logs else 0,
        "electronics_used": len([log for log in sleep_logs if log.electronics_used]),
        "avg_quality": sum(log.quality_rating for log in sleep_logs) / len(sleep_logs) if sleep_logs else 0
    }
    
    # Process meal data
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
    
    # Category breakdown
    breakfast_logs = [log for log in meal_logs if log.meal_type == "breakfast"]
    lunch_logs = [log for log in meal_logs if log.meal_type == "lunch"]
    dinner_logs = [log for log in meal_logs if log.meal_type == "dinner"]
    
    def get_category_stats(category_logs):
        pack_count = len([log for log in category_logs if log.is_pack])
        custom_healthy = len([log for log in category_logs if not log.is_pack and log.health_rating == "healthy"])
        custom_unhealthy = len([log for log in category_logs if not log.is_pack and log.health_rating == "unhealthy"])
        return {
            "healthy": pack_count + custom_healthy,
            "unhealthy": custom_unhealthy
        }
    
    meal_stats = {
        "total_meals": total_meals,
        "healthy": total_healthy,
        "unsure": total_unsure,
        "unhealthy": total_unhealthy,
        "healthiness_percentage": healthiness_percentage,
        "custom_meals": len(custom_meals),
        "breakfast": get_category_stats(breakfast_logs),
        "lunch": get_category_stats(lunch_logs),
        "dinner": get_category_stats(dinner_logs)
    }
    
    return {
        "workouts": {"total": workout_total},
        "sleep": sleep_stats,
        "meals": meal_stats
    }







