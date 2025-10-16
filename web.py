import asyncio
import logging
import threading
import os
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
bot_running = False

def run_bot():
    """Запуск бота в отдельном потоке"""
    global bot, dp, bot_running
    
    try:
        # Проверяем токен
        if not TOKEN:
            logging.error("BOT_TOKEN не найден в переменных окружения!")
            return
            
        logging.info(f"Запуск бота с токеном: {TOKEN[:10]}...")
        
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
        
        bot_running = True
        
        # Запускаем бота в бесконечном цикле
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(dp.start_polling(bot))
        except KeyboardInterrupt:
            logging.info("Бот остановлен пользователем")
        except Exception as e:
            logging.error(f"Ошибка в работе бота: {e}")
        finally:
            bot_running = False
        
    except Exception as e:
        logging.error(f"Ошибка запуска бота: {e}")
        bot_running = False

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
    if bot and dp and bot_running:
        return jsonify({
            'status': 'running',
            'bot': 'active',
            'dispatcher': 'active',
            'token': f"{TOKEN[:10]}..." if TOKEN else 'not_set'
        })
    return jsonify({
        'status': 'error', 
        'message': 'Bot not initialized',
        'token': f"{TOKEN[:10]}..." if TOKEN else 'not_set',
        'bot_running': bot_running
    })

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
    global bot_thread, bot_running
    
    if bot_thread and bot_thread.is_alive() and bot_running:
        return jsonify({'status': 'already_running'})
    
    try:
        # Проверяем токен
        if not TOKEN:
            return jsonify({'status': 'error', 'message': 'BOT_TOKEN не найден в переменных окружения!'})
        
        bot_thread = threading.Thread(target=run_bot, daemon=False)  # Не daemon!
        bot_thread.start()
        
        # Ждем немного чтобы бот успел запуститься
        import time
        time.sleep(2)
        
        return jsonify({
            'status': 'started',
            'token': f"{TOKEN[:10]}..." if TOKEN else 'not_set',
            'bot_running': bot_running
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/stop_bot', methods=['POST'])
def stop_bot():
    """Остановка бота"""
    global bot, dp, bot_running
    
    if bot and dp and bot_running:
        bot_running = False
        # Здесь можно добавить логику остановки бота
        return jsonify({'status': 'stopped'})
    
    return jsonify({'status': 'not_running'})

@app.route('/debug')
def debug():
    """Отладочная информация"""
    return jsonify({
        'token_set': bool(TOKEN),
        'token_preview': f"{TOKEN[:10]}..." if TOKEN else 'not_set',
        'bot_exists': bot is not None,
        'dp_exists': dp is not None,
        'bot_running': bot_running,
        'thread_alive': bot_thread.is_alive() if bot_thread else False,
        'thread_daemon': bot_thread.daemon if bot_thread else None
    })

if __name__ == '__main__':
    # Автоматически запускаем бота при старте (для Render)
    if TOKEN:
        logging.info("Автоматический запуск бота...")
        bot_thread = threading.Thread(target=run_bot, daemon=False)
        bot_thread.start()
        # Ждем немного чтобы бот успел запуститься
        import time
        time.sleep(3)
    else:
        logging.warning("BOT_TOKEN не найден, бот не будет запущен автоматически")
    
    # Запускаем Flask сервер
    app.run(host='0.0.0.0', port=5000, debug=False)
