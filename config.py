import os
from datetime import time

# Токен бота из переменных окружения Railway
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не установлен! Добавьте в переменные окружения Railway")

# ID канала для публикации статистики (опционально)
CHANNEL_ID = os.getenv("CHANNEL_ID", "")

# Настройки базы данных
# В Railway используем временную папку для хранения
import tempfile
DB_FILE = os.path.join(tempfile.gettempdir(), "tycoon_complete.db")

# Остальные настройки без изменений...
START_BALANCE = 0
START_ENERGY = 100
MAX_ENERGY = 100
MAX_HEALTH = 100
ENERGY_RECOVERY_TIME = 5

INCOME_MULTIPLIERS = {
    "beginner": 1.0,
    "trader": 0.8,
    "businessman": 0.6,
    "magnate": 0.4,
    "oligarch": 0.2
}

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
    # ... остальные бизнесы
}

STOCKS = {
    "TYCOON": {"name": "Тайкун Инк", "base_price": 100, "volatility": 0.1},
    "METAL": {"name": "Металл Групп", "base_price": 250, "volatility": 0.15},
    "OIL": {"name": "Нефть РФ", "base_price": 500, "volatility": 0.2},
    "TECH": {"name": "ТехноКорп", "base_price": 1000, "volatility": 0.25},
    "CRYPTO": {"name": "КриптоБанк", "base_price": 50, "volatility": 0.3}
}

PROPERTIES = {
    "shack": {
        "name": "🏚️ Хижина",
        "price": 50000,
        "bonus": {"energy_recovery": 1.1}
    },
    # ... остальная недвижимость
}

DAILY_BONUS = {
    1: 100, 2: 200, 3: 300, 4: 500,
    5: 800, 6: 1300, 7: 2100
}

STATS_PUBLISH_TIMES = [
    time(12, 0),
    time(20, 0)
]

CHANNEL_THRESHOLDS = {
    "big_income": 100000,
    "big_loss": 50000,
    "business_purchase": 1000000,
    "property_purchase": 5000000,
    "stock_profit": 100000,
    "level_up": 10,
}

RANDOM_EVENTS_INTERVAL = (2, 4)