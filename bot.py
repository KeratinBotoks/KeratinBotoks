import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

import config
from database import db
from keyboards import main_menu

# ========== НАСТРОЙКА ЛОГИРОВАНИЯ ==========
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# ========== СОЗДАНИЕ БОТА И ДИСПЕТЧЕРА ==========
# Создаем бота с токеном из config
bot = Bot(token=config.BOT_TOKEN)

# Создаем диспетчер с хранилищем в памяти
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Создаем роутер
router = Router()
dp.include_router(router)

# ========== КОМАНДЫ БОТА ==========

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    player = db.get_player(message.from_user.id)
    
    if not player:
        # Создаем нового игрока
        db.create_player(
            message.from_user.id,
            message.from_user.username or message.from_user.first_name or "Игрок"
        )
        text = (
            "🎮 <b>Добро пожаловать в Симулятор Магната!</b>\n\n"
            "💰 <b>Вы начинаете с 1000₽!</b>\n\n"
            "<b>Доступные действия:</b>\n"
            "• 💰 Заработать - быстрый заработок\n"
            "• 🏪 Бизнес - покупка бизнесов\n"
            "• 📊 Статистика - ваши показатели\n"
            "• 🏆 Топ - лучшие игроки\n"
            "• ℹ️ Помощь - инструкция по игре\n\n"
            "🚀 <b>Удачи в построении империи!</b>"
        )
    else:
        text = (
            f"👋 <b>С возвращением, {player[2] or 'игрок'}!</b>\n\n"
            f"💰 Баланс: {player[3]:,}₽\n"
            f"⭐ Уровень: {player[4]}\n\n"
            "Выберите действие:"
        )
    
    await message.answer(text, reply_markup=main_menu(), parse_mode="HTML")

@router.message(Command("help"))
@router.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: Message):
    """Помощь по игре"""
    text = (
        "🆘 <b>Помощь по игре</b>\n\n"
        "<b>Основные команды:</b>\n"
        "/start - Начать игру\n"
        "/help - Эта справка\n"
        "/stats - Ваша статистика\n\n"
        "<b>Действия:</b>\n"
        "💰 Заработать - быстрый заработок\n"
        "🏪 Бизнес - покупка бизнесов\n"
        "📊 Статистика - ваши показатели\n"
        "🏆 Топ - таблица лидеров\n\n"
        "<b>Советы:</b>\n"
        "1. Начинайте с малого\n"
        "2. Инвестируйте в бизнесы\n"
        "3. Проверяйте статистику\n"
        "4. Соревнуйтесь с другими!\n\n"
        "🚀 <b>Удачи!</b>"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(Command("stats"))
@router.message(F.text == "📊 Статистика")
async def cmd_stats(message: Message):
    """Статистика игрока"""
    player = db.get_player(message.from_user.id)
    
    if not player:
        await message.answer("❌ Сначала зарегистрируйтесь! /start")
        return
    
    text = (
        f"📊 <b>Ваша статистика</b>\n\n"
        f"👤 Имя: {player[2] or 'Игрок'}\n"
        f"💰 Баланс: {player[3]:,}₽\n"
        f"⭐ Уровень: {player[4]}\n"
        f"🆔 ID: {player[1]}\n"
        f"📅 Регистрация: {player[5][:10]}"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "💰 Заработать")
async def earn_money(message: Message):
    """Заработок денег"""
    player = db.get_player(message.from_user.id)
    
    if not player:
        await message.answer("❌ Сначала зарегистрируйтесь! /start")
        return
    
    # Простой заработок
    import random
    earnings = random.randint(10, 100)
    new_balance = player[3] + earnings
    
    # Обновляем баланс в базе
    conn = sqlite3.connect("tycoon.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE players SET balance = ? WHERE telegram_id = ?",
        (new_balance, message.from_user.id)
    )
    conn.commit()
    conn.close()
    
    await message.answer(
        f"✅ <b>Вы заработали {earnings}₽!</b>\n\n"
        f"💰 Новый баланс: {new_balance:,}₽\n\n"
        f"💡 Продолжайте в том же духе!",
        parse_mode="HTML"
    )

@router.message(F.text == "🏆 Топ")
async def top_players(message: Message):
    """Топ игроков"""
    conn = sqlite3.connect("tycoon.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT username, balance, level FROM players ORDER BY balance DESC LIMIT 10"
    )
    players = cursor.fetchall()
    conn.close()
    
    if not players:
        await message.answer("📭 Пока нет игроков в топе")
        return
    
    text = "🏆 <b>Топ-10 игроков</b>\n\n"
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    for i, (username, balance, level) in enumerate(players):
        medal = medals[i] if i < len(medals) else f"{i+1}."
        name = username or f"Игрок{i+1}"
        text += f"{medal} <b>{name}</b>\n"
        text += f"   💰 {balance:,}₽ | ⭐ {level}\n"
    
    await message.answer(text, parse_mode="HTML")

# ========== ЗАПУСК БОТА ==========

async def main():
    """Главная функция запуска бота"""
    logger.info("🚀 Запуск бота...")
    
    try:
        # Запускаем polling
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")
    finally:
        logger.info("🛑 Бот остановлен")

if __name__ == "__main__":
    import sqlite3  # Добавляем импорт здесь
    
    # Запускаем бота
    asyncio.run(main())