# app/handlers/__init__.py
# ВАЖНО: main.py импортирует ИМЕННО пакет handlers (from app.handlers import start)
# Этот файл выполнится и подтянет все модули, которые сами «подпишутся» на общий router.

from . import start  # создаёт router
# Подключаем модули, которые добавят свои хендлеры в тот же router:
from . import menu     # главное меню
from . import workouts # тренировки (пошагово)
from . import settings # настройки и онбординг
from . import meals    # прототип блюд
from . import progress # прогресс
from . import onboarding  # канал-гейт после выбора языка
from . import sleep      # сон и статистика
from . import reminders  # напоминания
from . import help       # помощь
from . import profile    # профиль пользователя
# позже добавим onboarding, meals, progress — без изменения main.py