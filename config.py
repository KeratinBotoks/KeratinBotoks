import os
from datetime import time
from dotenv import load_dotenv # type: ignore

# Загружаем переменные окружения
load_dotenv()

# Токен бота (ОБЯЗАТЕЛЬНО из переменных окружения)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    print("⚠️ ВНИМАНИЕ: BOT_TOKEN не установлен!")

# ID канала для статистики
CHANNEL_ID = os.getenv("CHANNEL_ID", "")

# Настройки базы данных
DB_FILE = "/app/data/tycoon_complete.db"

# Создаем папку для базы данных
os.makedirs("/app/data", exist_ok=True)

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
        "max_level": 10
    },
    "street_vendor": {
        "name": "🛒 Уличный торговец",
        "price": 5000,
        "income_per_hour": 50,
        "upgrade_cost": 2500,
        "max_level": 15
    },
    "kiosk": {
        "name": "🏪 Киоск",
        "price": 25000,
        "income_per_hour": 200,
        "upgrade_cost": 12500,
        "max_level": 20
    },
    "coffee_shop": {
        "name": "☕ Кофейня",
        "price": 100000,
        "income_per_hour": 500,
        "upgrade_cost": 50000,
        "max_level": 25
    },
    "supermarket": {
        "name": "🏪 Супермаркет",
        "price": 500000,
        "income_per_hour": 2000,
        "upgrade_cost": 250000,
        "max_level": 30
    }
}

# Биржа
STOCKS = {
    "TYCOON": {"name": "Тайкун Инк", "base_price": 100, "volatility": 0.1},
    "METAL": {"name": "Металл Групп", "base_price": 250, "volatility": 0.15},
    "OIL": {"name": "Нефть РФ", "base_price": 500, "volatility": 0.2},
    "TECH": {"name": "ТехноКорп", "base_price": 150, "volatility": 0.25},
    "FOOD": {"name": "Агропром", "base_price": 80, "volatility": 0.08}
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

# Время публикации статистики (Московское время)
STATS_PUBLISH_TIMES = [
    time(12, 0),  # 12:00 МСК
    time(20, 0),  # 20:00 МСК
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

# Проверка обязательных настроек
if __name__ == "__main__":
    if not BOT_TOKEN:
        print("❌ ОШИБКА: BOT_TOKEN не установлен!")
        print("ℹ️ Создайте файл .env или установите переменную окружения")
    else:
        print("✅ Конфигурация загружена успешно")