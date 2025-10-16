#!/usr/bin/env python3
"""
Скрипт для проверки переменных окружения
Запустите этот скрипт чтобы проверить настройки
"""

import os
from dotenv import load_dotenv

# Загружаем .env файл
load_dotenv()

print("🔍 Проверка переменных окружения:")
print("=" * 50)

# Проверяем BOT_TOKEN
bot_token = os.getenv("BOT_TOKEN")
if bot_token:
    print(f"✅ BOT_TOKEN: {bot_token[:10]}... (найден)")
else:
    print("❌ BOT_TOKEN: НЕ НАЙДЕН!")
    print("   Добавьте BOT_TOKEN в переменные окружения Render")

# Проверяем другие переменные
db_url = os.getenv("DB_URL")
channel_username = os.getenv("CHANNEL_USERNAME", "@fitonomics_uz")

print(f"📊 DB_URL: {db_url if db_url else 'не установлен (будет использована SQLite)'}")
print(f"📢 CHANNEL_USERNAME: {channel_username}")

print("\n🌐 Проверка доступности интернета:")
try:
    import requests
    response = requests.get("https://api.telegram.org", timeout=5)
    print("✅ Telegram API доступен")
except Exception as e:
    print(f"❌ Ошибка подключения к Telegram API: {e}")

print("\n📋 Инструкции для Render:")
print("1. Зайдите в настройки вашего сервиса на Render")
print("2. Перейдите в раздел 'Environment'")
print("3. Добавьте переменную: BOT_TOKEN = ваш_токен_бота")
print("4. Сохраните и перезапустите сервис")

if not bot_token:
    print("\n⚠️  ВАЖНО: Без BOT_TOKEN бот не будет работать!")
    print("   Получите токен у @BotFather в Telegram")
