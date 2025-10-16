import asyncio
import logging
import threading
from flask import Flask, render_template, jsonify, request
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from app.config import TOKEN
from app.database import Base, engine
from app.models import user, admin, notification_log
from app.handlers import start
from app.services.reminders import load_and_schedule_all, start_scheduler, set_bot_instance

# Flask приложение
app = Flask(__name__)

# Глобальные переменные для бота
bot = None
dp = None
bot_thread = None

def run_bot():
    """Запуск бота в отдельном потоке"""
    global bot, dp
    
    # Создаём таблицы в базе, если их ещё нет
    Base.metadata.create_all(bind=engine)
    
    bot = Bot(
        token=TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    
    # Подключаем все роутеры
    dp.include_router(start.router)
    
    # Планировщик напоминаний
    start_scheduler()
    set_bot_instance(bot)
    load_and_schedule_all()
    
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.info("Бот запущен через Flask...")
    
    # Запускаем бота
    asyncio.run(dp.start_polling(bot))

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')

@app.route('/admin')
def admin():
    """Админ панель"""
    return render_template('admin.html')

@app.route('/health')
def health():
    """Проверка здоровья бота"""
    if bot and dp:
        return jsonify({
            'status': 'running',
            'bot': 'active',
            'dispatcher': 'active'
        })
    return jsonify({'status': 'error', 'message': 'Bot not initialized'})

@app.route('/stats')
def stats():
    """Статистика бота"""
    try:
        # Здесь можно добавить логику получения статистики из БД
        return jsonify({
            'users': 'N/A',  # TODO: получить из БД
            'workouts': 'N/A',
            'meals': 'N/A'
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/start_bot', methods=['POST'])
def start_bot():
    """Запуск бота (если не запущен)"""
    global bot_thread
    
    if bot_thread and bot_thread.is_alive():
        return jsonify({'status': 'already_running'})
    
    try:
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
        return jsonify({'status': 'started'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/stop_bot', methods=['POST'])
def stop_bot():
    """Остановка бота"""
    global bot, dp
    
    if bot and dp:
        # Здесь можно добавить логику остановки бота
        return jsonify({'status': 'stopped'})
    
    return jsonify({'status': 'not_running'})

if __name__ == '__main__':
    # Запускаем бота в отдельном потоке при старте Flask
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Запускаем Flask сервер
    app.run(host='0.0.0.0', port=5000, debug=False)
