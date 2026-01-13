from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
import config

def main_menu():
    """Главное меню"""
    builder = ReplyKeyboardBuilder()
    
    builder.row(
        KeyboardButton(text="💰 Заработать"),
        KeyboardButton(text="💼 Бизнес")
    )
    
    builder.row(
        KeyboardButton(text="📈 Биржа"),
        KeyboardButton(text="🏦 Инвестиции")
    )
    
    builder.row(
        KeyboardButton(text="🎁 Ежедневный"),
        KeyboardButton(text="📊 Статистика")
    )
    
    builder.row(
        KeyboardButton(text="🏆 Топ игроков"),
        KeyboardButton(text="ℹ️ Помощь")
    )
    
    return builder.as_markup(resize_keyboard=True)

def earn_menu():
    """Меню заработка"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🔍 Собрать бутылки", callback_data="earn_bottles"),
        InlineKeyboardButton(text="🥫 Искать еду", callback_data="earn_food")
    )
    
    builder.row(
        InlineKeyboardButton(text="💤 Спать на вокзале", callback_data="earn_sleep"),
        InlineKeyboardButton(text="💼 Работа грузчиком", callback_data="earn_loader")
    )
    
    builder.row(
        InlineKeyboardButton(text="🏠 Уборка квартир", callback_data="earn_cleaning"),
        InlineKeyboardButton(text="🚕 Таксист", callback_data="earn_taxi")
    )
    
    builder.row(
        InlineKeyboardButton(text="💼 Бизнес", callback_data="business_menu"),
        InlineKeyboardButton(text="📈 Биржа", callback_data="stock_menu")
    )
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main")
    )
    
    builder.adjust(2)
    return builder.as_markup()

def business_menu():
    """Меню бизнеса"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🏪 Купить бизнес", callback_data="business_buy"),
        InlineKeyboardButton(text="📈 Мои бизнесы", callback_data="business_list")
    )
    
    builder.row(
        InlineKeyboardButton(text="💰 Собрать прибыль", callback_data="business_profit"),
        InlineKeyboardButton(text="⬆️ Улучшить бизнес", callback_data="business_upgrade")
    )
    
    builder.row(
        InlineKeyboardButton(text="🏠 Недвижимость", callback_data="property_menu"),
        InlineKeyboardButton(text="💼 Продать бизнес", callback_data="business_sell")
    )
    
    builder.row(
        InlineKeyboardButton(text="💰 Заработать", callback_data="earn_menu"),
        InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main")
    )
    
    builder.adjust(2)
    return builder.as_markup()

def business_list_keyboard(businesses):
    """Список бизнесов игрока"""
    builder = InlineKeyboardBuilder()
    
    for business in businesses:
        business_info = config.BUSINESSES.get(business['business_type'], {})
        builder.add(InlineKeyboardButton(
            text=f"{business_info.get('name', business['business_type'])} (Ур. {business['level']})",
            callback_data=f"view_business_{business['id']}"
        ))
    
    builder.row(
        InlineKeyboardButton(text="🏪 Купить новый", callback_data="business_buy"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_business")
    )
    
    builder.adjust(1)
    return builder.as_markup()

def upgrade_business_keyboard(business_id, current_level, max_level):
    """Клавиатура улучшения бизнеса"""
    builder = InlineKeyboardBuilder()
    
    if current_level < max_level:
        builder.add(InlineKeyboardButton(
            text=f"⬆️ Улучшить до {current_level + 1} уровня",
            callback_data=f"upgrade_{business_id}"
        ))
    
    builder.row(
        InlineKeyboardButton(text="📊 Все бизнесы", callback_data="business_list"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_business")
    )
    
    return builder.as_markup()

def property_menu():
    """Меню недвижимости"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🏠 Купить недвижимость", callback_data="property_buy"),
        InlineKeyboardButton(text="📋 Моя недвижимость", callback_data="property_list")
    )
    
    builder.row(
        InlineKeyboardButton(text="💼 Продать недвижимость", callback_data="property_sell"),
        InlineKeyboardButton(text="📊 Эффекты", callback_data="property_effects")
    )
    
    builder.row(
        InlineKeyboardButton(text="💼 Бизнес", callback_data="business_menu"),
        InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main")
    )
    
    builder.adjust(2)
    return builder.as_markup()

def buy_property_keyboard():
    """Клавиатура покупки недвижимости"""
    builder = InlineKeyboardBuilder()
    
    for key, property_data in config.PROPERTIES.items():
        builder.add(InlineKeyboardButton(
            text=f"{property_data['name']} - {property_data['price']:,}₽",
            callback_data=f"buy_property_{key}"
        ))
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_property"),
        InlineKeyboardButton(text="📋 Моя недвижимость", callback_data="property_list")
    )
    
    builder.adjust(1)
    return builder.as_markup()

def stock_menu():
    """Меню биржи"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📊 Котировки", callback_data="stock_prices"),
        InlineKeyboardButton(text="💰 Купить акции", callback_data="stock_buy")
    )
    
    builder.row(
        InlineKeyboardButton(text="💸 Продать акции", callback_data="stock_sell"),
        InlineKeyboardButton(text="📈 Мои акции", callback_data="stock_my")
    )
    
    builder.row(
        InlineKeyboardButton(text="📉 История цен", callback_data="stock_history"),
        InlineKeyboardButton(text="🎯 Аналитика", callback_data="stock_analysis")
    )
    
    builder.row(
        InlineKeyboardButton(text="🏦 Инвестиции", callback_data="investment_menu"),
        InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main")
    )
    
    builder.adjust(2)
    return builder.as_markup()

def stock_list_keyboard():
    """Список акций"""
    builder = InlineKeyboardBuilder()
    
    for symbol, data in config.STOCKS.items():
        builder.add(InlineKeyboardButton(
            text=f"{data['name']} ({symbol})",
            callback_data=f"stock_info_{symbol}"
        ))
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_stock"),
        InlineKeyboardButton(text="📈 Мои акции", callback_data="stock_my")
    )
    
    builder.adjust(1)
    return builder.as_markup()

def stock_quantity_keyboard(symbol, current_price, max_quantity):
    """Выбор количества акций"""
    builder = InlineKeyboardBuilder()
    
    # Быстрые варианты
    percentages = [10, 25, 50, 75, 100]
    
    for percent in percentages:
        quantity = max(1, int(max_quantity * percent / 100))
        total_cost = quantity * current_price
        builder.add(InlineKeyboardButton(
            text=f"{percent}% ({quantity} шт.)",
            callback_data=f"stock_buy_{symbol}_{quantity}"
        ))
    
    builder.row(
        InlineKeyboardButton(text="✏️ Ввести вручную", callback_data=f"stock_manual_{symbol}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="stock_prices")
    )
    
    builder.adjust(1)
    return builder.as_markup()

def stock_sell_keyboard(player_stocks):
    """Продажа акций"""
    builder = InlineKeyboardBuilder()
    
    for stock in player_stocks:
        builder.add(InlineKeyboardButton(
            text=f"{stock['stock_symbol']} - {stock['quantity']} шт.",
            callback_data=f"sell_stock_{stock['stock_symbol']}"
        ))
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="stock_menu"),
        InlineKeyboardButton(text="📊 Котировки", callback_data="stock_prices")
    )
    
    builder.adjust(1)
    return builder.as_markup()

def investment_menu():
    """Меню инвестиций"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="⚖️ Консервативный", callback_data="invest_conservative"),
        InlineKeyboardButton(text="📊 Сбалансированный", callback_data="invest_balanced")
    )
    
    builder.row(
        InlineKeyboardButton(text="🚀 Агрессивный", callback_data="invest_aggressive"),
        InlineKeyboardButton(text="₿ Крипто-фонд", callback_data="invest_crypto")
    )
    
    builder.row(
        InlineKeyboardButton(text="📈 Мои инвестиции", callback_data="invest_my"),
        InlineKeyboardButton(text="💰 Вывод прибыли", callback_data="invest_withdraw")
    )
    
    builder.row(
        InlineKeyboardButton(text="📊 Доходность", callback_data="invest_stats"),
        InlineKeyboardButton(text="📚 О фондах", callback_data="invest_info")
    )
    
    builder.row(
        InlineKeyboardButton(text="📈 Биржа", callback_data="stock_menu"),
        InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main")
    )
    
    builder.adjust(2)
    return builder.as_markup()

def investment_amount_keyboard(fund_type, min_invest):
    """Выбор суммы инвестиций"""
    builder = InlineKeyboardBuilder()
    
    amounts = [
        min_invest,
        min_invest * 5,
        min_invest * 10,
        min_invest * 20,
        min_invest * 50
    ]
    
    for amount in amounts:
        builder.add(InlineKeyboardButton(
            text=f"{amount:,}₽",
            callback_data=f"invest_{fund_type}_{amount}"
        ))
    
    builder.row(
        InlineKeyboardButton(text="✏️ Ввести сумму", callback_data=f"invest_manual_{fund_type}"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="investment_menu")
    )
    
    builder.adjust(1)
    return builder.as_markup()

def buy_business_keyboard():
    """Клавиатура для покупки бизнеса"""
    builder = InlineKeyboardBuilder()
    
    # Группируем бизнесы по ценовым категориям
    cheap_businesses = {}
    medium_businesses = {}
    expensive_businesses = {}
    
    for key, business in config.BUSINESSES.items():
        if business['price'] < 10000:
            cheap_businesses[key] = business
        elif business['price'] < 1000000:
            medium_businesses[key] = business
        else:
            expensive_businesses[key] = business
    
    # Дешевые бизнесы
    if cheap_businesses:
        builder.row(InlineKeyboardButton(
            text="💰 НАЧАЛЬНЫЙ УРОВЕНЬ",
            callback_data="category_cheap"
        ))
        for key, business in cheap_businesses.items():
            builder.add(InlineKeyboardButton(
                text=f"{business['name']} - {business['price']:,}₽",
                callback_data=f"buy_{key}"
            ))
    
    # Средние бизнесы
    if medium_businesses:
        builder.row(InlineKeyboardButton(
            text="🏪 СРЕДНИЙ УРОВЕНЬ",
            callback_data="category_medium"
        ))
        for key, business in medium_businesses.items():
            builder.add(InlineKeyboardButton(
                text=f"{business['name']} - {business['price']:,}₽",
                callback_data=f"buy_{key}"
            ))
    
    # Дорогие бизнесы
    if expensive_businesses:
        builder.row(InlineKeyboardButton(
            text="🏦 ВЫСШИЙ УРОВЕНЬ",
            callback_data="category_expensive"
        ))
        for key, business in expensive_businesses.items():
            builder.add(InlineKeyboardButton(
                text=f"{business['name']} - {business['price']:,}₽",
                callback_data=f"buy_{key}"
            ))
    
    builder.row(
        InlineKeyboardButton(text="📊 Мои бизнесы", callback_data="business_list"),
        InlineKeyboardButton(text="💰 Заработать", callback_data="earn_menu")
    )
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main")
    )
    
    builder.adjust(1)
    return builder.as_markup()

def confirm_keyboard(action: str, amount: int = None, item: str = None):
    """Клавиатура подтверждения"""
    builder = InlineKeyboardBuilder()
    
    if amount and item:
        builder.add(InlineKeyboardButton(
            text=f"✅ Да, подтверждаю ({amount:,}₽)",
            callback_data=f"confirm_{action}"
        ))
    else:
        builder.add(InlineKeyboardButton(
            text="✅ Да, подтверждаю",
            callback_data=f"confirm_{action}"
        ))
    
    builder.add(InlineKeyboardButton(
        text="❌ Нет, отменить",
        callback_data="cancel_action"
    ))
    
    return builder.as_markup()

def back_keyboard(back_to: str = "main"):
    """Кнопка назад"""
    builder = InlineKeyboardBuilder()
    
    if back_to == "main":
        builder.add(InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main"))
    elif back_to == "business":
        builder.add(InlineKeyboardButton(text="⬅️ К бизнесам", callback_data="back_to_business"))
    elif back_to == "stock":
        builder.add(InlineKeyboardButton(text="⬅️ К бирже", callback_data="back_to_stock"))
    elif back_to == "invest":
        builder.add(InlineKeyboardButton(text="⬅️ К инвестициям", callback_data="back_to_invest"))
    elif back_to == "property":
        builder.add(InlineKeyboardButton(text="⬅️ К недвижимости", callback_data="back_to_property"))
    elif back_to == "earn":
        builder.add(InlineKeyboardButton(text="⬅️ К заработку", callback_data="back_to_earn"))
    
    return builder.as_markup()

def pagination_keyboard(current_page: int, total_pages: int, action_prefix: str):
    """Клавиатура пагинации"""
    builder = InlineKeyboardBuilder()
    
    if current_page > 1:
        builder.add(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"{action_prefix}_{current_page - 1}"
        ))
    
    if current_page < total_pages:
        builder.add(InlineKeyboardButton(
            text="Вперед ➡️",
            callback_data=f"{action_prefix}_{current_page + 1}"
        ))
    
    builder.row(InlineKeyboardButton(
        text=f"Страница {current_page}/{total_pages}",
        callback_data="current_page"
    ))
    
    builder.row(InlineKeyboardButton(
        text="⬅️ Главное меню",
        callback_data="back_to_main"
    ))
    
    return builder.as_markup()

def stats_menu():
    """Меню статистики"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="👤 Моя статистика", callback_data="stats_my"),
        InlineKeyboardButton(text="📊 Общая статистика", callback_data="stats_global")
    )
    
    builder.row(
        InlineKeyboardButton(text="💼 Статистика бизнесов", callback_data="stats_business"),
        InlineKeyboardButton(text="📈 Статистика биржи", callback_data="stats_stocks")
    )
    
    builder.row(
        InlineKeyboardButton(text="📋 История транзакций", callback_data="stats_transactions"),
        InlineKeyboardButton(text="🎯 Прогресс", callback_data="stats_progress")
    )
    
    builder.row(
        InlineKeyboardButton(text="🏆 Топ игроков", callback_data="top_players"),
        InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main")
    )
    
    builder.adjust(2)
    return builder.as_markup()

def admin_menu():
    """Меню администратора"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📊 Статистика сервера", callback_data="admin_stats"),
        InlineKeyboardButton(text="🔧 Управление игроками", callback_data="admin_players")
    )
    
    builder.row(
        InlineKeyboardButton(text="💾 Резервная копия", callback_data="admin_backup"),
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")
    )
    
    builder.row(
        InlineKeyboardButton(text="🌍 Глобальные события", callback_data="admin_events"),
        InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")
    )
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main")
    )
    
    builder.adjust(2)
    return builder.as_markup()

def profile_menu():
    """Меню профиля"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✏️ Изменить имя", callback_data="profile_name"),
        InlineKeyboardButton(text="🎭 Изменить аватар", callback_data="profile_avatar")
    )
    
    builder.row(
        InlineKeyboardButton(text="🔔 Уведомления", callback_data="profile_notifications"),
        InlineKeyboardButton(text="🔒 Безопасность", callback_data="profile_security")
    )
    
    builder.row(
        InlineKeyboardButton(text="📜 Правила", callback_data="profile_rules"),
        InlineKeyboardButton(text="💬 Поддержка", callback_data="profile_support")
    )
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main")
    )
    
    builder.adjust(2)
    return builder.as_markup()

def help_menu():
    """Меню помощи"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📚 Руководство", callback_data="help_guide"),
        InlineKeyboardButton(text="❓ Частые вопросы", callback_data="help_faq")
    )
    
    builder.row(
        InlineKeyboardButton(text="💡 Советы", callback_data="help_tips"),
        InlineKeyboardButton(text="🎮 Геймплей", callback_data="help_gameplay")
    )
    
    builder.row(
        InlineKeyboardButton(text="💰 Экономика", callback_data="help_economy"),
        InlineKeyboardButton(text="📈 Биржа", callback_data="help_stocks")
    )
    
    builder.row(
        InlineKeyboardButton(text="💼 Бизнес", callback_data="help_business"),
        InlineKeyboardButton(text="🏦 Инвестиции", callback_data="help_investments")
    )
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main"),
        InlineKeyboardButton(text="📞 Поддержка", callback_data="profile_support")
    )
    
    builder.adjust(2)
    return builder.as_markup()

def quick_actions():
    """Быстрые действия"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="💰 Собрать прибыль", callback_data="quick_profit"),
        InlineKeyboardButton(text="🎁 Бонус", callback_data="quick_bonus")
    )
    
    builder.row(
        InlineKeyboardButton(text="⚡ Проверить энергию", callback_data="quick_energy"),
        InlineKeyboardButton(text="❤️ Проверить здоровье", callback_data="quick_health")
    )
    
    builder.row(
        InlineKeyboardButton(text="📈 Проверить биржу", callback_data="quick_stocks"),
        InlineKeyboardButton(text="💼 Мои бизнесы", callback_data="quick_businesses")
    )
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_to_main")
    )
    
    builder.adjust(2)
    return builder.as_markup()

def numeric_keyboard():
    """Цифровая клавиатура"""
    builder = ReplyKeyboardBuilder()
    
    numbers = [
        ["1", "2", "3"],
        ["4", "5", "6"],
        ["7", "8", "9"],
        ["0", "⬅️ Назад"]
    ]
    
    for row in numbers:
        builder.row(*[KeyboardButton(text=num) for num in row])
    
    return builder.as_markup(resize_keyboard=True)