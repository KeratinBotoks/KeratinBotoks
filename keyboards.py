from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_menu():
    """Главное меню"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 Заработать"), KeyboardButton(text="💼 Бизнес")],
            [KeyboardButton(text="📈 Биржа"), KeyboardButton(text="🎁 Ежедневный бонус")],
            [KeyboardButton(text="📊 Моя статистика"), KeyboardButton(text="🏆 Топ игроков")],
            [KeyboardButton(text="ℹ️ Помощь")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие..."
    )
    return keyboard

def earn_menu():
    """Меню заработка"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="🔍 Сбор бутылок (15⚡)", callback_data="earn_bottles"),
        InlineKeyboardButton(text="🥫 Поиск еды (8⚡)", callback_data="earn_food"),
        InlineKeyboardButton(text="💤 Сон на вокзале", callback_data="earn_sleep"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
    )
    builder.adjust(1, 1, 1, 1)
    return builder.as_markup()

def business_menu():
    """Меню бизнеса"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="🏪 Купить бизнес", callback_data="business_buy"),
        InlineKeyboardButton(text="📊 Мои бизнесы", callback_data="business_list"),
        InlineKeyboardButton(text="💰 Собрать прибыль", callback_data="business_collect"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
    )
    builder.adjust(2, 1, 1)
    return builder.as_markup()

def stock_menu():
    """Меню биржи"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="📈 Купить акции", callback_data="stock_buy"),
        InlineKeyboardButton(text="📉 Продать акции", callback_data="stock_sell"),
        InlineKeyboardButton(text="📊 Мои акции", callback_data="stock_list"),
        InlineKeyboardButton(text="📈 Курсы акций", callback_data="stock_prices"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
    )
    builder.adjust(2, 2, 1)
    return builder.as_markup()

def buy_business_keyboard():
    """Клавиатура покупки бизнесов"""
    from config import BUSINESSES
    
    builder = InlineKeyboardBuilder()
    
    for business_type, business in BUSINESSES.items():
        builder.add(
            InlineKeyboardButton(
                text=f"{business['name']} - {business['price']:,}₽",
                callback_data=f"buy_{business_type}"
            )
        )
    
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))
    builder.adjust(1)
    return builder.as_markup()

def stock_list_keyboard(stocks):
    """Клавиатура списка акций"""
    from config import STOCKS
    
    builder = InlineKeyboardBuilder()
    
    for symbol, stock_info in STOCKS.items():
        builder.add(
            InlineKeyboardButton(
                text=f"{stock_info['name']} ({symbol})",
                callback_data=f"stock_info_{symbol}"
            )
        )
    
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))
    builder.adjust(1)
    return builder.as_markup()

def back_keyboard():
    """Кнопка возврата"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))
    return builder.as_markup()

def confirmation_keyboard(action: str, data: str = ""):
    """Клавиатура подтверждения"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_{action}_{data}"),
        InlineKeyboardButton(text="❌ Нет", callback_data="cancel_action")
    )
    return builder.as_markup()