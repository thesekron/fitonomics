"""
Meals service for loading and filtering meal data.
"""
import json
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.meal_log import MealLog, UserMealSettings
from app.models.user import User


def _extract_calories_from_text(text_content: str) -> str:
    """Extract calories from text content."""
    if not text_content:
        return 'N/A'
    
    try:
        # Look for "Calories:" pattern in English text
        for line in text_content.split('\n'):
            if 'Calories:' in line:
                calories_text = line.split('Calories:')[1].strip()
                return calories_text
        return 'N/A'
    except Exception as e:
        print(f"Error extracting calories: {e}")
        return 'N/A'


def _extract_price_from_text(text_content: str) -> str:
    """Extract price from text content."""
    if not text_content:
        return 'N/A'
    
    try:
        # Look for "Price:" pattern in English text
        for line in text_content.split('\n'):
            if 'Price:' in line:
                price_text = line.split('Price:')[1].strip()
                return price_text
        return 'N/A'
    except Exception as e:
        print(f"Error extracting price: {e}")
        return 'N/A'


def load_meals_data() -> Dict:
    """Load meals data from JSON file."""
    try:
        json_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "meals.json")
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"budget_low": [], "budget_mid": [], "budget_high": []}
    except Exception as e:
        print(f"Error loading meals data: {e}")
        return {"budget_low": [], "budget_mid": [], "budget_high": []}


def get_user_budget(user_id: int) -> Optional[str]:
    """Get user's budget preference."""
    with SessionLocal() as session:
        # First check UserMealSettings
        settings = session.query(UserMealSettings).filter(UserMealSettings.user_id == user_id).first()
        if settings and settings.budget_level:
            return settings.budget_level
            
        # If not found, check User.budget (from onboarding)
        user = session.query(User).filter(User.tg_id == user_id).first()
        if user and user.budget:
            # Auto-sync to UserMealSettings for consistency
            set_user_budget(user_id, user.budget)
            return user.budget
            
        return None  # No budget set yet


def set_user_budget(user_id: int, budget_level: str) -> None:
    """Set user's budget preference."""
    with SessionLocal() as session:
        settings = session.query(UserMealSettings).filter(UserMealSettings.user_id == user_id).first()
        if settings:
            settings.budget_level = budget_level
        else:
            settings = UserMealSettings(user_id=user_id, budget_level=budget_level)
            session.add(settings)
        session.commit()


def get_meals_by_budget(budget_level: str) -> List[Dict]:
    """Get all meals for a specific budget level."""
    data = load_meals_data()
    budget_key = f"budget_{budget_level}"
    meals = data.get(budget_key, [])
    
    # Add media paths to each meal
    for meal in meals:
        category = meal.get("category", "")
        pack_number = meal.get("pack_number", "")
        if category and pack_number:
            # Build media path: media/meals/budget_mid/breakfast/1.png
            media_filename = f"media/meals/{budget_key}/{category}/{pack_number}.png"
            meal["image"] = media_filename
    
    return meals


def get_meals_by_category(budget_level: str, category: str) -> List[Dict]:
    """Get meals filtered by budget and category."""
    meals = get_meals_by_budget(budget_level)
    if category == "all":
        return meals
    return [meal for meal in meals if meal.get("category") == category]


def get_meal_by_id(meal_id: str) -> Optional[Dict]:
    """Get a specific meal by ID from any budget."""
    data = load_meals_data()
    for budget_key in ["budget_low", "budget_mid", "budget_high"]:
        for meal in data.get(budget_key, []):
            if meal.get("id") == meal_id:
                return meal
    return None


def log_meal_pack(user_id: int, pack_id: str, meal_type: str) -> None:
    """Log a meal pack choice."""
    meal_data = get_meal_by_id(pack_id)
    if not meal_data:
        return
    
    # Extract calories and price from text
    calories_text = _extract_calories_from_text(meal_data.get('text_en', ''))
    price_text = _extract_price_from_text(meal_data.get('text_en', ''))
    
    with SessionLocal() as session:
        meal_log = MealLog(
            user_id=user_id,
            meal_type=meal_type,
            is_pack=True,
            pack_id=pack_id,
            pack_name=meal_data.get("name_en"),  # Use English name as default
            calories=calories_text,
            price=price_text,
            prep_time=meal_data.get("prep_time_min"),
            flags=meal_data.get("flags")
        )
        session.add(meal_log)
        session.commit()


def log_custom_meal(user_id: int, description: str, category: str, health_rating: str) -> None:
    """Log a custom meal choice."""
    with SessionLocal() as session:
        meal_log = MealLog(
            user_id=user_id,
            meal_type=category,
            is_pack=False,
            custom_description=description,
            custom_category=category,
            health_rating=health_rating
        )
        session.add(meal_log)
        session.commit()


def get_meal_stats(user_id: int, days: int = 7) -> Dict:
    """Get meal statistics for the last N days."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    with SessionLocal() as session:
        logs = session.query(MealLog).filter(
            MealLog.user_id == user_id,
            MealLog.created_at >= start_date,
            MealLog.created_at <= end_date
        ).all()
    
    total_meals = len(logs)
    pack_meals = [log for log in logs if log.is_pack]
    custom_meals = [log for log in logs if not log.is_pack]
    
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
    breakfast_logs = [log for log in logs if log.meal_type == "breakfast"]
    lunch_logs = [log for log in logs if log.meal_type == "lunch"]
    dinner_logs = [log for log in logs if log.meal_type == "dinner"]
    
    def get_category_stats(category_logs):
        pack_count = len([log for log in category_logs if log.is_pack])
        custom_healthy = len([log for log in category_logs if not log.is_pack and log.health_rating == "healthy"])
        custom_unhealthy = len([log for log in category_logs if not log.is_pack and log.health_rating == "unhealthy"])
        return {
            "healthy": pack_count + custom_healthy,
            "unhealthy": custom_unhealthy
        }
    
    return {
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


def get_recent_meals(user_id: int, limit: int = 10) -> List[Dict]:
    """Get recent meal logs for display."""
    with SessionLocal() as session:
        logs = session.query(MealLog).filter(
            MealLog.user_id == user_id
        ).order_by(MealLog.created_at.desc()).limit(limit).all()
    
    result = []
    for log in logs:
        if log.is_pack:
            result.append({
                "type": "pack",
                "name": log.pack_name,
                "meal_type": log.meal_type,
                "date": log.created_at,
                "calories": log.calories,
                "price": log.price
            })
        else:
            result.append({
                "type": "custom",
                "name": log.custom_description,
                "meal_type": log.meal_type,
                "date": log.created_at,
                "health_rating": log.health_rating
            })
    
    return result