from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

def main_menu():
    """Главное меню"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 Заработать"), KeyboardButton(text="🏪 Бизнес")],
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="🏆 Топ")],
            [KeyboardButton(text="ℹ️ Помощь")]
        ],
        resize_keyboard=True
    )
    return keyboard