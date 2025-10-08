import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from app.config import TOKEN
from app.database import Base, engine
from app.models import user  # регистрируем модель
from app.handlers import start  # общий router создаётся и используется всеми хендлерами
from app.services.reminders import load_and_schedule_all, start_scheduler, set_bot_instance

async def main():
    # Создаём таблицы в базе, если их ещё нет
    Base.metadata.create_all(bind=engine)

    bot = Bot(
        token=TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Подключаем все роутеры
    dp.include_router(start.router)
    # All other handlers use the shared router from start.py

    # Планировщик напоминаний: после создания таблиц загрузим задания
    start_scheduler()
    set_bot_instance(bot)  # Set bot instance for sleep notifications
    load_and_schedule_all()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.info("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())