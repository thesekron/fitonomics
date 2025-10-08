import json
import random
from pathlib import Path
from typing import List

def load_sleep_tips() -> List[dict]:
    """Load sleep tips from JSON file."""
    tips_file = Path(__file__).parent.parent.parent / "data" / "sleep_tips.json"
    try:
        with open(tips_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return [{
            "ru": "Старайся ложиться спать и вставать в одно и то же время — так твоё тело легче высыпается.",
            "uz": "Uxlagan va uyg'onish vaqtini bir xil qilib turing — shunda tanangiz osonroq uyquga ketadi.",
            "en": "Try to go to bed and wake up at the same time — this way your body falls asleep more easily."
        }]

def get_random_tip(lang: str = "ru") -> str:
    """Get a random sleep tip in the specified language."""
    tips = load_sleep_tips()
    tip = random.choice(tips)
    return tip.get(lang, tip.get("ru", "Sleep tip not available"))

def get_sleep_stats(user_id: int) -> dict:
    """Get sleep statistics for the last 7 days."""
    from app.database import SessionLocal
    from app.models.user import User
    from app.models.sleep_log import SleepLog
    from datetime import datetime, timedelta
    
    with SessionLocal() as session:
        user = session.query(User).filter(User.tg_id == user_id).first()
        if not user:
            return {}
        
        week_ago = datetime.now() - timedelta(days=7)
        logs = (
            session.query(SleepLog)
            .filter(SleepLog.user_id == user.id)
            .filter(SleepLog.created_at >= week_ago)
            .order_by(SleepLog.created_at.desc())
            .all()
        )
        
        if not logs:
            return {"logs": [], "avg_duration": 0, "avg_quality": 0, "electronics_count": 0, "streak": 0}
        
        # Calculate statistics
        total_duration = sum(log.duration_hours for log in logs)
        avg_duration = round(total_duration / len(logs), 1)
        
        # Handle quality rating (may not exist in old records)
        quality_logs = [log for log in logs if hasattr(log, 'quality_rating') and log.quality_rating]
        avg_quality = round(sum(log.quality_rating for log in quality_logs) / len(quality_logs), 1) if quality_logs else 0
        
        # Handle electronics usage (may not exist in old records)
        electronics_count = sum(1 for log in logs if hasattr(log, 'electronics_used') and log.electronics_used == "yes")
        
        # Calculate streak of >7h sleep
        streak = 0
        for log in logs:
            if log.duration_hours > 7:
                streak += 1
            else:
                break
        
        return {
            "logs": logs,
            "avg_duration": avg_duration,
            "avg_quality": avg_quality,
            "electronics_count": electronics_count,
            "streak": streak
        }

def get_electronics_feedback(count: int) -> str:
    """Get feedback based on electronics usage count."""
    if count <= 2:
        return "sleep.electronics_great"
    elif count <= 5:
        return "sleep.electronics_ok"
    else:
        return "sleep.electronics_bad"

def get_quality_emoji_and_text(rating: int) -> tuple:
    """Get emoji and text for quality rating."""
    quality_map = {
        1: ("😴", "sleep.quality_1_text"),
        2: ("🙂", "sleep.quality_2_text"),
        3: ("😀", "sleep.quality_3_text"),
        4: ("🤩", "sleep.quality_4_text"),
        5: ("🦸", "sleep.quality_5_text"),
    }
    return quality_map.get(rating, ("😴", "sleep.quality_1_text"))

# Configuration for easy changes
RECOMMENDED_SLEEP_SCHEDULE = "23:00 - 06:00"
EVENING_REMINDER_TIME = "22:30"
MORNING_REMINDER_TIME = "07:00"
