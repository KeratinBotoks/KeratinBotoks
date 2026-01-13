import os
from datetime import time

# Токен бота (обязательно задать в .env или окружении Railway)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8246923680:AAGKcVwu0xz0qEi-AqEqdm8EUJqNU2_h6oA")

# ID канала для публикации статистики (опционально)
CHANNEL_ID = os.getenv("CHANNEL_ID", "-1003360198094")

# Настройки базы данных
DB_FILE = os.getenv("DB_FILE", "tycoon_complete.db")

# ========== ЭКОНОМИЧЕСКИЕ НАСТРОЙКИ ==========

# Начальные значения игрока
START_BALANCE = 0
START_ENERGY = 100
MAX_ENERGY = 100
MAX_HEALTH = 100

# Время восстановления энергии (в минутах)
ENERGY_RECOVERY_TIME = 5

# Сложность заработка (множители)
INCOME_MULTIPLIERS = {
    "beginner": 1.0,      # Первые 1000₽
    "trader": 0.8,        # 1,000-10,000₽
    "businessman": 0.6,   # 10,000-100,000₽
    "magnate": 0.4,       # 100,000-1,000,000₽
    "oligarch": 0.2       # 1,000,000+₽
}

# ========== БИЗНЕСЫ (очень дорогие) ==========
BUSINESSES = {
    "bottle_collection": {
        "name": "📦 Сбор бутылок",
        "price": 1000,
        "income_per_hour": 10,
        "upgrade_cost": 500,
        "max_level": 10
    },
    # ... остальные бизнесы без изменений
}

# ========== БИРЖА ==========
STOCKS = {
    "TYCOON": {"name": "Тайкун Инк", "base_price": 100, "volatility": 0.1},
    "METAL": {"name": "Металл Групп", "base_price": 250, "volatility": 0.15},
    "OIL": {"name": "Нефть РФ", "base_price": 500, "volatility": 0.2},
    "TECH": {"name": "ТехноКорп", "base_price": 1000, "volatility": 0.25},
    "CRYPTO": {"name": "КриптоБанк", "base_price": 50, "volatility": 0.3}
}

# ... остальные настройки без изменений ...

# Случайные события (каждые 2-4 часа)
RANDOM_EVENTS_INTERVAL = (2, 4)  # часы