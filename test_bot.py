#!/usr/bin/env python3
"""
Тест подключения к Telegram Bot API
Запустите этот скрипт чтобы проверить работает ли бот
"""

import asyncio
import logging
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from app.config import TOKEN

async def test_bot():
    """Тест подключения к Telegram"""
    if not TOKEN:
        print("❌ BOT_TOKEN не найден!")
        return False
    
    print(f"🔍 Тестируем подключение с токеном: {TOKEN[:10]}...")
    
    try:
        bot = Bot(
            token=TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        
        # Получаем информацию о боте
        me = await bot.get_me()
        print(f"✅ Бот подключен успешно!")
        print(f"   Имя: {me.first_name}")
        print(f"   Username: @{me.username}")
        print(f"   ID: {me.id}")
        
        # Проверяем webhook
        webhook_info = await bot.get_webhook_info()
        print(f"   Webhook URL: {webhook_info.url or 'не установлен'}")
        
        await bot.session.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = asyncio.run(test_bot())
    
    if result:
        print("\n🎉 Бот готов к работе!")
    else:
        print("\n💥 Проблема с подключением!")
        print("Проверьте:")
        print("1. Правильность токена")
        print("2. Доступность интернета")
        print("3. Настройки бота у @BotFather")
