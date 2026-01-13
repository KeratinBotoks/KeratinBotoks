#!/bin/bash

echo "🚀 Запуск Tycoon Simulator Bot..."

# Активация Python окружения
python -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install --upgrade pip
pip install -r requirements.txt

# Создание базы данных если нет
if [ ! -f "tycoon_complete.db" ]; then
    echo "📁 Создание базы данных..."
    python -c "from database import db; print('✅ База данных инициализирована')"
fi

# Запуск бота
echo "🤖 Запуск бота..."
python bot.py