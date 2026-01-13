import os
import sys
from datetime import time
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# ========== ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ==========

# Токен бота (ОБЯЗАТЕЛЬНО из переменных окружения)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Проверяем токен при запуске
if not BOT_TOKEN:
    print("=" * 60)
    print("❌ КРИТИЧЕСКАЯ ОШИБКА: BOT_TOKEN не установлен!")
    print("=" * 60)
    print("ℹ️ Как получить токен:")
    print("1. Откройте Telegram и найдите @BotFather")
    print("2. Создайте нового бота: /newbot")
    print("3. Скопируйте полученный токен")
    print("=" * 60)
    print("🔧 На Railway добавьте переменную окружения:")
    print("   - Зайдите в Dashboard")
    print("   - Выберите проект")
    print("   - Settings → Variables")
    print("   - Добавьте: BOT_TOKEN=ваш_токен")
    print("=" * 60)
    sys.exit(1)

# ID канала для статистики (опционально)
CHANNEL_ID = os.getenv("CHANNEL_ID", "")

# ========== НАСТРОЙКИ ПУТЕЙ ДЛЯ RAILWAY ==========

# Определяем путь для базы данных
# Railway предоставляет папку /data для постоянного хранения
if os.path.exists("/data"):
    # Используем папку /data на Railway (сохраняется между деплоями)
    DB_FILE = "/data/tycoon_complete.db"
    DATA_DIR = "/data"
else:
    # Локальная разработка
    DATA_DIR = "data"
    DB_FILE = os.path.join(DATA_DIR, "tycoon_complete.db")

# Создаем директорию для данных если её нет
os.makedirs(DATA_DIR, exist_ok=True)

print(f"✅ Конфигурация загружена:")
print(f"   🤖 Бот: {'✅ Настроен' if BOT_TOKEN else '❌ Нет токена'}")
print(f"   📢 Канал: {'✅ Настроен' if CHANNEL_ID else '⚪ Не настроен'}")
print(f"   📁 База данных: {DB_FILE}")
print(f"   📂 Директория данных: {DATA_DIR}")

# ========== НАСТРОЙКИ ИГРЫ ==========

# Начальные значения игрока
START_BALANCE = 0
START_ENERGY = 100
MAX_ENERGY = 100
MAX_HEALTH = 100

# Время восстановления энергии (в минутах)
ENERGY_RECOVERY_TIME = 5

# Сложность заработка
INCOME_MULTIPLIERS = {
    "beginner": 1.0,
    "trader": 0.8,
    "businessman": 0.6,
    "magnate": 0.4,
    "oligarch": 0.2
}

# Бизнесы
BUSINESSES = {
    "bottle_collection": {
        "name": "📦 Сбор бутылок",
        "price": 1000,
        "income_per_hour": 10,
        "upgrade_cost": 500,
        "max_level": 10,
        "description": "Начальный бизнес. Собирайте и сдавайте бутылки."
    },
    "street_vendor": {
        "name": "🛒 Уличный торговец",
        "price": 5000,
        "income_per_hour": 50,
        "upgrade_cost": 2500,
        "max_level": 15,
        "description": "Торгуйте мелочевкой на улице."
    },
    "kiosk": {
        "name": "🏪 Киоск",
        "price": 25000,
        "income_per_hour": 200,
        "upgrade_cost": 12500,
        "max_level": 20,
        "description": "Небольшой киоск с товарами первой необходимости."
    },
    "coffee_shop": {
        "name": "☕ Кофейня",
        "price": 100000,
        "income_per_hour": 500,
        "upgrade_cost": 50000,
        "max_level": 25,
        "description": "Уютная кофейня в центре города."
    },
    "supermarket": {
        "name": "🏪 Супермаркет",
        "price": 500000,
        "income_per_hour": 2000,
        "upgrade_cost": 250000,
        "max_level": 30,
        "description": "Крупный супермаркет с широким ассортиментом."
    },
    "car_dealership": {
        "name": "🚗 Автосалон",
        "price": 2500000,
        "income_per_hour": 10000,
        "upgrade_cost": 1250000,
        "max_level": 40,
        "description": "Продажа новых и подержанных автомобилей."
    },
    "real_estate": {
        "name": "🏢 Агентство недвижимости",
        "price": 10000000,
        "income_per_hour": 50000,
        "upgrade_cost": 5000000,
        "max_level": 50,
        "description": "Продажа и аренда элитной недвижимости."
    }
}

# Биржа
STOCKS = {
    "TYCOON": {
        "name": "Тайкун Инк",
        "base_price": 100,
        "volatility": 0.1,
        "description": "Корпорация в сфере технологий и инвестиций"
    },
    "METAL": {
        "name": "Металл Групп",
        "base_price": 250,
        "volatility": 0.15,
        "description": "Добыча и переработка металлов"
    },
    "OIL": {
        "name": "Нефть РФ",
        "base_price": 500,
        "volatility": 0.2,
        "description": "Добыча и экспорт нефти"
    },
    "TECH": {
        "name": "ТехноКорп",
        "base_price": 150,
        "volatility": 0.25,
        "description": "Инновационные технологии"
    },
    "FOOD": {
        "name": "Агропром",
        "base_price": 80,
        "volatility": 0.08,
        "description": "Сельское хозяйство и продукты питания"
    },
    "BANK": {
        "name": "Финанс Банк",
        "base_price": 300,
        "volatility": 0.12,
        "description": "Финансовые услуги и кредитование"
    }
}

# Ежедневный бонус
DAILY_BONUS = {
    1: 100,
    2: 200,
    3: 300,
    4: 500,
    5: 800,
    6: 1300,
    7: 2100,
}

# Время публикации статистики (Московское время UTC+3)
STATS_PUBLISH_TIMES = [
    time(9, 0),   # 12:00 МСК (9:00 UTC)
    time(17, 0),  # 20:00 МСК (17:00 UTC)
]

# Пороги для публикации в канал
CHANNEL_THRESHOLDS = {
    "big_income": 100000,
    "big_loss": 50000,
    "business_purchase": 1000000,
    "property_purchase": 5000000,
    "stock_profit": 100000,
    "level_up": 10,
}

# Случайные события
RANDOM_EVENTS_INTERVAL = (2, 4)  # часа

# Настройки логирования
LOG_FILE = os.path.join(DATA_DIR, "bot.log")
LOG_LEVEL = "INFO"

# Настройки производительности
CACHE_TTL = 300  # 5 минут в секундах
CLEANUP_INTERVAL = 3600  # 1 час в секундах

# Проверка целостности конфигурации
if __name__ == "__main__":
    print("=" * 60)
    print("🔧 ПРОВЕРКА КОНФИГУРАЦИИ ДЛЯ RAILWAY")
    print("=" * 60)
    
    # Проверяем обязательные настройки
    errors = []
    warnings = []
    
    if not BOT_TOKEN:
        errors.append("❌ BOT_TOKEN не установлен")
    
    if not CHANNEL_ID:
        warnings.append("⚠️ CHANNEL_ID не установлен (статистика не будет отправляться)")
    
    if not os.path.exists(DATA_DIR):
        warnings.append(f"⚠️ Директория данных {DATA_DIR} не существует")
    
    # Выводим результаты проверки
    if errors:
        print("❌ КРИТИЧЕСКИЕ ОШИБКИ:")
        for error in errors:
            print(f"   {error}")
        print("=" * 60)
        sys.exit(1)
    
    if warnings:
        print("⚠️ ПРЕДУПРЕЖДЕНИЯ:")
        for warning in warnings:
            print(f"   {warning}")
    
    print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО")
    print("=" * 60)
    print(f"📊 Бизнесов: {len(BUSINESSES)}")
    print(f"📈 Акций: {len(STOCKS)}")
    print(f"🎁 Уровней бонуса: {len(DAILY_BONUS)}")
    print("=" * 60)