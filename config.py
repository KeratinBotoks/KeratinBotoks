import os
import sys

# Токен бота из переменных окружения Railway
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8246923680:AAGKcVwu0xz0qEi-AqEqdm8EUJqNU2_h6oA")

if not BOT_TOKEN:
    print("=" * 60)
    print("❌ ОШИБКА: BOT_TOKEN не найден!")
    print("=" * 60)
    print("Добавьте переменную окружения на Railway:")
    print("1. Зайдите на railway.app")
    print("2. Ваш проект -> Сервис -> Variables")
    print("3. New Variable: BOT_TOKEN=ваш_токен")
    print("=" * 60)
    sys.exit(1)

# ID канала (опционально)
CHANNEL_ID = os.environ.get("CHANNEL_ID", "-1003360198094")

# Путь к базе данных
DB_FILE = "tycoon.db"

print("=" * 60)
print("✅ Конфигурация загружена")
print(f"🤖 Бот токен: {'✅' if BOT_TOKEN else '❌'}")
print("=" * 60)