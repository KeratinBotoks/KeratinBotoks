import asyncio
import sqlite3
import random
import logging
import os
import sys
from datetime import datetime, time, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler # type: ignore
from apscheduler.triggers.cron import CronTrigger # type: ignore

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

import config
from database import db
from keyboards import *

# ========== НАСТРОЙКА ЛОГИРОВАНИЯ ==========
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/app/data/bot.log')
    ]
)
logger = logging.getLogger(__name__)

# ========== ПРОВЕРКА ТОКЕНА ==========
if not config.BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не установлен!")
    print("=" * 50)
    print("❌ ОШИБКА: BOT_TOKEN не установлен!")
    print("ℹ️ Установите переменную окружения:")
    print("   BOT_TOKEN=ваш_токен_бота")
    print("=" * 50)
    sys.exit(1)

# ========== ИНИЦИАЛИЗАЦИЯ БОТА ==========
bot = Bot(token=config.BOT_TOKEN, parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

# ========== FSM СОСТОЯНИЯ ==========
class GameStates(StatesGroup):
    waiting_business_choice = State()
    waiting_stock_choice = State()
    waiting_stock_quantity = State()
    waiting_sell_stock = State()

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
async def send_to_channel(message: str):
    """Отправить сообщение в канал"""
    if config.CHANNEL_ID:
        try:
            await bot.send_message(config.CHANNEL_ID, message)
            logger.info(f"📢 Отправлено в канал: {message[:100]}...")
        except Exception as e:
            logger.error(f"❌ Ошибка отправки в канал: {e}")

async def publish_daily_stats():
    """Публикация ежедневной статистики"""
    try:
        stats = db.get_game_stats()
        top_players = db.get_top_players(5)
        
        text = f"📊 <b>ЕЖЕДНЕВНАЯ СТАТИСТИКА</b>\n\n"
        text += f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        
        text += f"📈 <b>Общая статистика:</b>\n"
        text += f"👥 Игроков: {stats['total_players']}\n"
        text += f"💰 Всего денег: {stats['total_money']:,}₽\n"
        text += f"🏪 Бизнесов: {stats['total_businesses']}\n"
        text += f"📊 Акций: {stats['total_stocks']:,}\n"
        text += f"💸 Транзакций: {stats['total_transactions']}\n\n"
        
        text += f"🏆 <b>Топ-5 игроков:</b>\n"
        for i, (username, balance, level, earned) in enumerate(top_players, 1):
            medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i-1]
            name = username if username else "Аноним"
            text += f"{medal} {name} - {balance:,}₽ (ур. {level})\n"
        
        text += f"\n🎮 Присоединяйтесь к игре! /start"
        
        await send_to_channel(text)
    except Exception as e:
        logger.error(f"❌ Ошибка публикации статистики: {e}")

def calculate_experience_for_level(level: int) -> int:
    """Рассчитать опыт для уровня"""
    return level * 1000

async def check_level_up(player):
    """Проверить повышение уровня"""
    exp_needed = calculate_experience_for_level(player['level'])
    
    if player['experience'] >= exp_needed:
        new_level = player['level'] + 1
        db.update_player(
            player['telegram_id'],
            level=new_level,
            experience=player['experience'] - exp_needed
        )
        
        # Отправляем сообщение в канал при достижении высокого уровня
        if new_level >= config.CHANNEL_THRESHOLDS["level_up"]:
            await send_to_channel(
                f"🎉 <b>НОВЫЙ УРОВЕНЬ!</b>\n\n"
                f"👤 {player['username']} достиг {new_level} уровня!\n"
                f"⭐ Теперь он настоящий магнат!"
            )
        
        return new_level
    return None

# ========== КОМАНДЫ БОТА ==========
@router.message(CommandStart())
async def cmd_start(message: Message):
    """Начало игры"""
    player = db.get_player(message.from_user.id)
    
    if not player:
        success = db.create_player(
            message.from_user.id,
            message.from_user.username or message.from_user.first_name or "Игрок"
        )
        if success:
            text = (
                "🎮 <b>Добро пожаловать в СИМУЛЯТОР МАГНАТА!</b>\n\n"
                "💰 <b>Вы начинаете свой путь с нуля:</b>\n"
                "• Баланс: 0₽\n"
                "• Энергия: 100⚡\n"
                "• Здоровье: 100❤️\n"
                "• Уровень: 1\n\n"
                "📈 <b>Особенности игры:</b>\n"
                "• Долгий и интересный путь к богатству\n"
                "• Реальная биржа с акциями\n"
                "• Ежедневные бонусы\n"
                "• Соревнование с другими игроками\n\n"
                "🚀 <b>Первые шаги:</b>\n"
                "1. Нажмите '💰 Заработать'\n"
                "2. Собирайте бутылки\n"
                "3. Получайте ежедневный бонус\n"
                "4. Покупайте свой первый бизнес!\n\n"
                "📢 <b>Статистика публикуется в канале 2 раза в день!</b>"
            )
        else:
            text = "❌ Ошибка при создании аккаунта. Попробуйте еще раз."
    else:
        # Проверяем восстановление энергии
        last_update = datetime.fromisoformat(player['last_energy_update'])
        now = datetime.now()
        hours_passed = (now - last_update).total_seconds() / 3600
        
        if hours_passed >= 1:
            energy_to_add = min(int(hours_passed) * 20, 100 - player['energy'])
            if energy_to_add > 0:
                new_energy = player['energy'] + energy_to_add
                db.update_player(
                    message.from_user.id,
                    energy=new_energy,
                    last_energy_update=now.isoformat()
                )
                player['energy'] = new_energy
        
        text = (
            f"👋 <b>С возвращением, {player['username'] or 'игрок'}!</b>\n\n"
            f"💰 Баланс: {player['balance']:,}₽\n"
            f"⚡ Энергия: {player['energy']}/100\n"
            f"❤️ Здоровье: {player['health']}/100\n"
            f"⭐ Уровень: {player['level']}\n"
            f"📈 Опыт: {player['experience']:,}\n\n"
            "Что будем делать сегодня?"
        )
    
    await message.answer(text, reply_markup=main_menu())

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Статистика игрока"""
    player = db.get_player(message.from_user.id)
    if not player:
        await message.answer("❌ Сначала зарегистрируйтесь! /start")
        return
    
    player_id = db.get_player_id(message.from_user.id)
    businesses = db.get_player_businesses(player_id)
    stocks = db.get_player_stocks(player_id)
    
    text = f"📊 <b>Статистика {player['username'] or 'Игрок'}</b>\n\n"
    text += f"💰 Баланс: {player['balance']:,}₽\n"
    text += f"⚡ Энергия: {player['energy']}/100\n"
    text += f"❤️ Здоровье: {player['health']}/100\n\n"
    text += f"⭐ Уровень: {player['level']}\n"
    text += f"📈 Опыт: {player['experience']:,}\n"
    text += f"🔥 Репутация: {player['reputation']}\n\n"
    text += f"🏪 Бизнесов: {len(businesses)}\n"
    text += f"📊 Акций: {len(stocks)} видов\n"
    text += f"📅 Серия бонусов: {player['daily_streak']} дней\n\n"
    text += f"💵 Всего заработано: {player['total_earned']:,}₽\n"
    text += f"💸 Всего потрачено: {player['total_spent']:,}₽"
    
    await message.answer(text)

@router.message(F.text == "💰 Заработать")
async def earn_menu_handler(message: Message):
    """Меню заработка"""
    await message.answer(
        "💼 <b>Выберите способ заработка:</b>\n\n"
        "• 🔍 Сбор бутылок - медленно, но стабильно\n"
        "• 🥫 Поиск еды - восстановление здоровья\n"
        "• 💤 Сон на вокзале - восстановление энергии\n",
        reply_markup=earn_menu()
    )

@router.message(F.text == "💼 Бизнес")
async def business_menu_handler(message: Message):
    """Меню бизнеса"""
    await message.answer(
        "🏪 <b>Управление бизнесом:</b>\n\n"
        "Бизнесы приносят пассивный доход каждый час!",
        reply_markup=business_menu()
    )

@router.message(F.text == "📈 Биржа")
async def stock_menu_handler(message: Message):
    """Меню биржи"""
    await message.answer(
        "📊 <b>Фондовая биржа:</b>\n\n"
        "Покупайте и продавайте акции компаний.\n"
        "Цены меняются каждые 5 минут.",
        reply_markup=stock_menu()
    )

@router.message(F.text == "🎁 Ежедневный бонус")
async def daily_bonus_handler(message: Message):
    """Ежедневный бонус"""
    player = db.get_player(message.from_user.id)
    if not player:
        await message.answer("❌ Сначала зарегистрируйтесь! /start")
        return
    
    today = datetime.now().date()
    
    if player['last_daily_bonus']:
        try:
            last_bonus = datetime.fromisoformat(player['last_daily_bonus']).date()
            
            if last_bonus == today:
                await message.answer("❌ Вы уже получали бонус сегодня!")
                return
            
            if (today - last_bonus).days == 1:
                new_streak = player['daily_streak'] + 1
            else:
                new_streak = 1
        except:
            new_streak = 1
    else:
        new_streak = 1
    
    if new_streak > 7:
        bonus_day = 7
    else:
        bonus_day = new_streak
    
    bonus_amount = config.DAILY_BONUS.get(bonus_day, 2100)
    
    db.update_player(
        message.from_user.id,
        balance=player['balance'] + bonus_amount,
        daily_streak=new_streak,
        last_daily_bonus=today.isoformat(),
        total_earned=player['total_earned'] + bonus_amount
    )
    
    player_id = db.get_player_id(message.from_user.id)
    if player_id:
        db.add_transaction(
            player_id,
            bonus_amount,
            "daily_bonus",
            f"Ежедневный бонус (день {new_streak})"
        )
    
    streak_text = ""
    if new_streak >= 7:
        streak_text = "\n🎉 Вы на максимальной серии!"
    elif new_streak > 1:
        streak_text = f"\n🔥 Серия: {new_streak} дней подряд!"
    
    next_bonus = config.DAILY_BONUS.get(min(new_streak + 1, 7), 2100)
    
    await message.answer(
        f"🎁 <b>Ежедневный бонус!</b>\n\n"
        f"💰 Получено: {bonus_amount}₽\n"
        f"📅 День: {new_streak}{streak_text}\n\n"
        f"🎯 Завтра: {next_bonus}₽"
    )

@router.message(F.text == "📊 Моя статистика")
async def my_stats_handler(message: Message):
    """Моя статистика"""
    await cmd_stats(message)

@router.message(F.text == "🏆 Топ игроков")
async def top_players_handler(message: Message):
    """Топ игроков"""
    top_players = db.get_top_players(10)
    
    text = "🏆 <b>Топ-10 игроков по балансу:</b>\n\n"
    
    for i, (username, balance, level, earned) in enumerate(top_players, 1):
        medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"][i-1]
        name = username if username else "Аноним"
        text += f"{medal} <b>{name}</b>\n"
        text += f"   💰 {balance:,}₽ | ⭐ Ур. {level}\n"
    
    stats = db.get_game_stats()
    text += f"\n📊 <b>Статистика игры:</b>\n"
    text += f"👥 Игроков: {stats['total_players']}\n"
    text += f"💰 Всего денег: {stats['total_money']:,}₽\n"
    text += f"🏪 Бизнесов: {stats['total_businesses']}\n"
    text += f"🏆 Самый богатый: {stats['richest']} - {stats['richest_balance']:,}₽"
    
    await message.answer(text)

@router.message(F.text == "ℹ️ Помощь")
async def help_handler(message: Message):
    """Помощь"""
    text = (
        "🆘 <b>Помощь по игре 'Симулятор Магната'</b>\n\n"
        
        "🎮 <b>Основные принципы:</b>\n"
        "• Деньги зарабатываются медленно\n"
        "• Бизнесы - основной источник дохода\n"
        "• Биржа - высокорисковый заработок\n"
        "• Ежедневные бонусы за вход\n\n"
        
        "💰 <b>Доступные действия:</b>\n"
        "• Сбор бутылок - первые медленные деньги\n"
        "• Покупка бизнесов - пассивный доход\n"
        "• Торговля на бирже - спекуляции\n"
        "• Ежедневный бонус - за вход каждый день\n\n"
        
        "📢 <b>Канал с событиями:</b>\n"
        "• Ежедневная статистика (12:00 и 20:00)\n"
        "• Крупные заработки/потери игроков\n\n"
        
        "🚀 <b>Советы:</b>\n"
        "1. Не пропускайте ежедневный бонус\n"
        "2. Покупайте бизнесы как можно раньше\n"
        "3. Диверсифицируйте инвестиции\n"
        "4. Следите за энергией\n"
        "5. Не забывайте про здоровье\n\n"
        
        "<b>Команды:</b>\n"
        "/start - Начать игру\n"
        "/stats - Ваша статистика\n"
        "/help - Эта справка"
    )
    
    await message.answer(text)

# ========== CALLBACK ОБРАБОТЧИКИ ==========
@router.callback_query(F.data == "earn_bottles")
async def earn_bottles_handler(callback: CallbackQuery):
    """Сбор бутылок"""
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Сначала зарегистрируйтесь!")
        return
    
    if player['energy'] < 15:
        await callback.message.edit_text("❌ Недостаточно энергии! Нужно 15⚡")
        await callback.answer()
        return
    
    bottles = random.randint(1, 3)
    earnings = bottles * 10
    
    # Обновляем игрока
    new_balance = player['balance'] + earnings
    new_energy = player['energy'] - 15
    new_experience = player['experience'] + 5
    new_total_earned = player['total_earned'] + earnings
    
    db.update_player(
        callback.from_user.id,
        balance=new_balance,
        energy=new_energy,
        experience=new_experience,
        total_earned=new_total_earned,
        last_energy_update=datetime.now().isoformat()
    )
    
    # Транзакция
    player_id = db.get_player_id(callback.from_user.id)
    if player_id:
        db.add_transaction(
            player_id,
            earnings,
            "bottle_collection",
            f"Собрано {bottles} бутылок"
        )
    
    # Проверяем повышение уровня
    player['experience'] = new_experience
    new_level = await check_level_up(player)
    
    level_text = f"\n⭐ Новый уровень: {new_level}!" if new_level else ""
    
    await callback.message.edit_text(
        f"✅ Собрано {bottles} бутылок\n"
        f"💰 Заработано: {earnings}₽\n"
        f"⚡ Энергии потрачено: 15\n"
        f"📈 Опыт: +5{level_text}"
    )
    
    # Проверяем на крупный заработок
    if earnings >= config.CHANNEL_THRESHOLDS["big_income"]:
        await send_to_channel(
            f"💰 <b>КРУПНЫЙ ЗАРАБОТОК!</b>\n\n"
            f"👤 {player['username']} собрал бутылок на {earnings:,}₽!\n"
            f"💼 Баланс: {new_balance:,}₽"
        )
    
    await callback.answer()

@router.callback_query(F.data == "earn_food")
async def earn_food_handler(callback: CallbackQuery):
    """Поиск еды"""
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Сначала зарегистрируйтесь!")
        return
    
    if player['energy'] < 8:
        await callback.message.edit_text("❌ Недостаточно энергии! Нужно 8⚡")
        await callback.answer()
        return
    
    db.update_player(
        callback.from_user.id,
        energy=player['energy'] - 8,
        last_energy_update=datetime.now().isoformat()
    )
    
    if random.random() < 0.6:
        foods = [("хлеб", 10), ("консервы", 15), ("фрукты", 20)]
        food, health_gain = random.choice(foods)
        
        if random.random() < 0.2:
            health_loss = random.randint(5, 15)
            new_health = max(0, player['health'] - health_loss)
            db.update_player(callback.from_user.id, health=new_health)
            await callback.message.edit_text(f"⚠️ Нашли {food}, но он испорчен!\n❤️ Здоровье: -{health_loss}")
        else:
            new_health = min(100, player['health'] + health_gain)
            db.update_player(callback.from_user.id, health=new_health)
            await callback.message.edit_text(f"✅ Нашли {food}!\n❤️ Здоровье: +{health_gain}")
    else:
        await callback.message.edit_text("❌ Ничего не нашли...")
    
    await callback.answer()

@router.callback_query(F.data == "earn_sleep")
async def earn_sleep_handler(callback: CallbackQuery):
    """Сон на вокзале"""
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Сначала зарегистрируйтесь!")
        return
    
    energy_gain = random.randint(20, 40)
    health_gain = random.randint(10, 20)
    
    if random.random() < 0.3:
        stolen = random.randint(100, 500)
        if stolen > player['balance']:
            stolen = player['balance']
        
        new_balance = player['balance'] - stolen
        new_energy = min(100, player['energy'] + energy_gain)
        new_health = min(100, player['health'] + health_gain)
        
        db.update_player(
            callback.from_user.id,
            balance=new_balance,
            energy=new_energy,
            health=new_health,
            last_energy_update=datetime.now().isoformat()
        )
        
        # Транзакция
        player_id = db.get_player_id(callback.from_user.id)
        if player_id:
            db.add_transaction(player_id, -stolen, "robbery", "Ограблен на вокзале")
        
        await callback.message.edit_text(
            f"😴 Поспали на вокзале\n"
            f"⚡ Энергия: +{energy_gain}\n"
            f"❤️ Здоровье: +{health_gain}\n"
            f"💸 Ограблены на: {stolen}₽"
        )
        
        # Проверяем на крупную потерю
        if stolen >= config.CHANNEL_THRESHOLDS["big_loss"]:
            await send_to_channel(
                f"💥 <b>КРУПНАЯ ПОТЕРЯ!</b>\n\n"
                f"👤 {player['username']} ограблен на {stolen:,}₽!\n"
                f"💼 Баланс: {new_balance:,}₽"
            )
    else:
        db.update_player(
            callback.from_user.id,
            energy=min(100, player['energy'] + energy_gain),
            health=min(100, player['health'] + health_gain),
            last_energy_update=datetime.now().isoformat()
        )
        
        await callback.message.edit_text(
            f"😴 Поспали на вокзале\n"
            f"⚡ Энергия: +{energy_gain}\n"
            f"❤️ Здоровье: +{health_gain}"
        )
    
    await callback.answer()

@router.callback_query(F.data == "business_buy")
async def business_buy_handler(callback: CallbackQuery, state: FSMContext):
    """Покупка бизнеса"""
    await state.set_state(GameStates.waiting_business_choice)
    await callback.message.edit_text(
        "🏪 <b>Выберите бизнес для покупки:</b>",
        reply_markup=buy_business_keyboard()
    )

@router.callback_query(F.data.startswith("buy_"))
async def buy_business_selected(callback: CallbackQuery, state: FSMContext):
    """Выбор конкретного бизнеса"""
    business_type = callback.data.replace("buy_", "")
    
    if business_type not in config.BUSINESSES:
        await callback.answer("❌ Бизнес не найден")
        return
    
    business = config.BUSINESSES[business_type]
    player = db.get_player(callback.from_user.id)
    
    if not player:
        await callback.answer("❌ Ошибка")
        return
    
    if player['balance'] < business['price']:
        await callback.message.edit_text(
            f"❌ <b>Недостаточно средств!</b>\n\n"
            f"🏪 {business['name']}\n"
            f"💰 Цена: {business['price']:,}₽\n"
            f"💵 Ваш баланс: {player['balance']:,}₽\n\n"
            f"Нужно еще {business['price'] - player['balance']:,}₽",
            reply_markup=back_keyboard()
        )
        await callback.answer()
        return
    
    # Покупаем бизнес
    player_id = db.get_player_id(callback.from_user.id)
    success = db.add_business(player_id, business_type)
    
    if success:
        # Списываем деньги
        new_balance = player['balance'] - business['price']
        new_total_spent = (player.get('total_spent') or 0) + business['price']
        
        db.update_player(
            callback.from_user.id,
            balance=new_balance,
            total_spent=new_total_spent
        )
        
        # Транзакция
        db.add_transaction(
            player_id,
            -business['price'],
            "business_purchase",
            f"Покупка {business['name']}"
        )
        
        await callback.message.edit_text(
            f"✅ <b>Бизнес куплен!</b>\n\n"
            f"🏪 {business['name']}\n"
            f"💰 Стоимость: {business['price']:,}₽\n"
            f"💵 Доход в час: {business['income_per_hour']}₽\n\n"
            f"💡 Прибыль можно собирать каждый час!",
            reply_markup=back_keyboard()
        )
        
        # Проверяем на крупную покупку
        if business['price'] >= config.CHANNEL_THRESHOLDS["business_purchase"]:
            await send_to_channel(
                f"🏪 <b>КРУПНАЯ ПОКУПКА!</b>\n\n"
                f"👤 {player['username']} купил {business['name']}!\n"
                f"💰 Стоимость: {business['price']:,}₽\n"
                f"💼 Баланс: {new_balance:,}₽"
            )
    else:
        await callback.message.edit_text("❌ Ошибка при покупке бизнеса")
    
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "business_list")
async def business_list_handler(callback: CallbackQuery):
    """Список бизнесов игрока"""
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Ошибка")
        return
    
    player_id = db.get_player_id(callback.from_user.id)
    businesses = db.get_player_businesses(player_id)
    
    if not businesses:
        await callback.message.edit_text("❌ У вас пока нет бизнесов!")
        await callback.answer()
        return
    
    text = "🏪 <b>Ваши бизнесы:</b>\n\n"
    total_income = 0
    
    for biz in businesses:
        business_config = config.BUSINESSES.get(biz['business_type'], {"name": "Неизвестный", "income_per_hour": 0})
        income = business_config['income_per_hour'] * biz['level']
        total_income += income
        
        text += f"{business_config['name']} (ур. {biz['level']})\n"
        text += f"   💰 Доход в час: {income}₽\n"
        text += f"   📅 Последняя прибыль: {biz['last_profit'][:19]}\n\n"
    
    text += f"💰 <b>Общий доход в час:</b> {total_income}₽"
    
    await callback.message.edit_text(text, reply_markup=back_keyboard())
    await callback.answer()

@router.callback_query(F.data == "stock_buy")
async def stock_buy_handler(callback: CallbackQuery, state: FSMContext):
    """Покупка акций"""
    await state.set_state(GameStates.waiting_stock_choice)
    
    text = "📈 <b>Выберите акции для покупки:</b>\n\n"
    
    for symbol, stock in config.STOCKS.items():
        current_price = db.get_stock_price(symbol) or stock['base_price']
        text += f"{stock['name']} ({symbol})\n"
        text += f"💰 Текущая цена: {current_price}₽\n\n"
    
    await callback.message.edit_text(text, reply_markup=stock_list_keyboard(None))
    await callback.answer()

@router.callback_query(F.data.startswith("stock_info_"))
async def stock_info_handler(callback: CallbackQuery, state: FSMContext):
    """Информация об акциях"""
    symbol = callback.data.replace("stock_info_", "")
    
    if symbol not in config.STOCKS:
        await callback.answer("❌ Акция не найдена")
        return
    
    stock = config.STOCKS[symbol]
    current_price = db.get_stock_price(symbol) or stock['base_price']
    history = db.get_stock_history(symbol, 5)
    
    text = f"📊 <b>{stock['name']} ({symbol})</b>\n\n"
    text += f"💰 Текущая цена: {current_price}₽\n"
    text += f"📈 Волатильность: {stock['volatility']*100}%\n\n"
    
    if history:
        text += "<b>История цен:</b>\n"
        for price, timestamp in history:
            time_str = timestamp[:16] if isinstance(timestamp, str) else timestamp.strftime("%d.%m %H:%M")
            text += f"• {time_str}: {price}₽\n"
    
    await callback.message.edit_text(text, reply_markup=back_keyboard())
    await callback.answer()

@router.callback_query(F.data == "back_to_main")
async def back_to_main_handler(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("Главное меню:", reply_markup=main_menu())
    await callback.answer()

# ========== ПЕРИОДИЧЕСКИЕ ЗАДАЧИ ==========
async def energy_recovery():
    """Восстановление энергии у всех игроков"""
    try:
        conn = sqlite3.connect(config.DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE players SET energy = MIN(100, energy + 5), last_energy_update = CURRENT_TIMESTAMP WHERE energy < 100"
        )
        conn.commit()
        conn.close()
        logger.info("⚡ Энергия восстановлена у всех игроков")
    except Exception as e:
        logger.error(f"❌ Ошибка восстановления энергии: {e}")

async def update_stock_prices():
    """Обновление цен на бирже"""
    try:
        for symbol, stock in config.STOCKS.items():
            current_price = db.get_stock_price(symbol) or stock['base_price']
            
            # Генерируем случайное изменение цены
            change_percent = random.uniform(-stock['volatility'], stock['volatility'])
            new_price = int(current_price * (1 + change_percent))
            
            # Не даем цене упасть ниже 10% от базовой
            min_price = int(stock['base_price'] * 0.1)
            new_price = max(min_price, new_price)
            
            db.add_stock_price(symbol, new_price)
        
        logger.info("📈 Цены на бирже обновлены")
    except Exception as e:
        logger.error(f"❌ Ошибка обновления цен на бирже: {e}")

async def business_profit_collection():
    """Сбор прибыли с бизнесов"""
    try:
        conn = sqlite3.connect(config.DB_FILE)
        cursor = conn.cursor()
        
        # Получаем все бизнесы
        cursor.execute("""
            SELECT pb.id, pb.player_id, pb.business_type, pb.level, pb.last_profit, p.telegram_id
            FROM player_businesses pb
            JOIN players p ON pb.player_id = p.id
        """)
        businesses = cursor.fetchall()
        
        for biz_id, player_id, biz_type, level, last_profit_str, telegram_id in businesses:
            try:
                last_profit = datetime.fromisoformat(last_profit_str)
                now = datetime.now()
                hours_passed = (now - last_profit).total_seconds() / 3600
                
                if hours_passed >= 1:
                    business_config = config.BUSINESSES.get(biz_type, {"income_per_hour": 0})
                    profit = int(business_config['income_per_hour'] * level * hours_passed)
                    
                    if profit > 0:
                        # Обновляем баланс игрока
                        cursor.execute(
                            "UPDATE players SET balance = balance + ?, total_earned = total_earned + ? WHERE id = ?",
                            (profit, profit, player_id)
                        )
                        
                        # Обновляем бизнес
                        cursor.execute(
                            "UPDATE player_businesses SET last_profit = ?, total_profit = total_profit + ? WHERE id = ?",
                            (now.isoformat(), profit, biz_id)
                        )
                        
                        # Добавляем транзакцию
                        cursor.execute(
                            "INSERT INTO transactions (player_id, amount, type, description) VALUES (?, ?, ?, ?)",
                            (player_id, profit, "business_profit", f"Прибыль от бизнеса {biz_type}")
                        )
                        
                        logger.info(f"💰 Игрок {telegram_id} получил {profit}₽ прибыли от бизнеса {biz_type}")
            except Exception as e:
                logger.error(f"❌ Ошибка обработки бизнеса {biz_id}: {e}")
        
        conn.commit()
        conn.close()
        logger.info("💰 Прибыль с бизнесов собрана")
    except Exception as e:
        logger.error(f"❌ Ошибка сбора прибыли с бизнесов: {e}")

async def startup_tasks():
    """Задачи при запуске"""
    logger.info("🚀 Запуск периодических задач...")
    
    try:
        # Восстановление энергии каждые 5 минут
        scheduler.add_job(
            energy_recovery,
            'interval',
            minutes=config.ENERGY_RECOVERY_TIME,
            id='energy_recovery'
        )
        
        # Обновление цен на бирже каждые 5 минут
        scheduler.add_job(
            update_stock_prices,
            'interval',
            minutes=5,
            id='update_stock_prices'
        )
        
        # Сбор прибыли с бизнесов каждый час
        scheduler.add_job(
            business_profit_collection,
            'interval',
            minutes=60,
            id='business_profit_collection'
        )
        
        # Ежедневная статистика в 12:00 и 20:00 (МСК)
        for publish_time in config.STATS_PUBLISH_TIMES:
            scheduler.add_job(
                publish_daily_stats,
                CronTrigger(hour=publish_time.hour, minute=publish_time.minute, timezone="Europe/Moscow"),
                id=f'daily_stats_{publish_time.hour}'
            )
        
        scheduler.start()
        logger.info("✅ Периодические задачи запущены")
    except Exception as e:
        logger.error(f"❌ Ошибка запуска периодических задач: {e}")

async def shutdown_tasks():
    """Задачи при завершении"""
    logger.info("🛑 Завершение работы...")
    scheduler.shutdown()
    db.close_all_connections()
    logger.info("✅ Бот остановлен")

# ========== ЗАПУСК БОТА ==========
async def on_startup():
    """Действия при запуске"""
    print("=" * 50)
    print("🚀 ЗАПУСК СИМУЛЯТОРА МАГНАТА")
    print("=" * 50)
    
    if not config.BOT_TOKEN or config.BOT_TOKEN == "ваш_токен_бота_здесь":
        print("❌ ОШИБКА: Замените BOT_TOKEN в переменных окружения!")
        print("ℹ️ На Koyeb: Settings -> Environment Variables")
        return False
    
    print(f"🤖 Бот запускается...")
    print(f"📁 База данных: {config.DB_FILE}")
    print(f"📊 Бизнесов: {len(config.BUSINESSES)}")
    print(f"📈 Акций на бирже: {len(config.STOCKS)}")
    
    if config.CHANNEL_ID:
        print(f"📢 Канал статистики: {config.CHANNEL_ID}")
    else:
        print("ℹ️ Канал статистики не настроен")
    
    print("=" * 50)
    
    # Запускаем периодические задачи
    await startup_tasks()
    
    # Приветственное сообщение в канал
    if config.CHANNEL_ID:
        try:
            await send_to_channel(
                "🎮 <b>ИГРА 'СИМУЛЯТОР МАГНАТА' ЗАПУЩЕНА!</b>\n\n"
                "📊 Статистика будет публиковаться 2 раза в день:\n"
                "• 12:00 - дневная статистика\n"
                "• 20:00 - вечерняя статистика\n\n"
                "🎯 Присоединяйтесь к игре: /start"
            )
        except Exception as e:
            print(f"⚠️ Не удалось отправить приветствие в канал: {e}")
    
    return True

async def main():
    """Основная функция"""
    if not await on_startup():
        return
    
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен по запросу пользователя")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
    finally:
        await shutdown_tasks()

if __name__ == "__main__":
    asyncio.run(main())