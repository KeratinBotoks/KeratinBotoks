import asyncio
import logging
import os
import sys
import random
from datetime import datetime
from typing import Dict, Any

# Настройка логирования перед всем остальным
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Проверяем наличие токена при запуске
if not os.getenv("BOT_TOKEN"):
    logger.error("❌ ОШИБКА: Переменная окружения BOT_TOKEN не установлена!")
    logger.error("👉 Добавьте BOT_TOKEN в Railway Dashboard: Settings → Variables")
    sys.exit(1)

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import config
from database import db
from game_logic import game
from economy import stock_market, investment_fund
from keyboards import *

# Инициализация бота и диспетчера
bot = Bot(token=config.BOT_TOKEN, parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

# Планировщик задач
scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

# Состояния FSM
class GameStates(StatesGroup):
    waiting_business_choice = State()
    waiting_stock_choice = State()
    waiting_stock_quantity = State()
    waiting_stock_sell_quantity = State()
    waiting_invest_amount = State()
    waiting_property_choice = State()
    waiting_custom_amount = State()

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

async def send_to_channel(message: str):
    """Отправить сообщение в канал"""
    if config.CHANNEL_ID:
        try:
            await bot.send_message(config.CHANNEL_ID, message)
            logger.info(f"📢 Отправлено в канал: {message[:100]}...")
        except Exception as e:
            logger.error(f"Ошибка отправки в канал: {e}")

async def check_and_publish_big_event(player_data: dict, event_type: str, amount: int, details: str = ""):
    """Проверить и опубликовать крупное событие"""
    thresholds = config.CHANNEL_THRESHOLDS
    
    if event_type == "big_income" and amount >= thresholds["big_income"]:
        await send_to_channel(
            f"💰 <b>КРУПНЫЙ ЗАРАБОТОК!</b>\n\n"
            f"👤 {player_data['username']} заработал {amount:,}₽!\n"
            f"{details}\n\n"
            f"💼 Баланс: {player_data['balance'] + amount:,}₽"
        )
    
    elif event_type == "big_loss" and abs(amount) >= thresholds["big_loss"]:
        await send_to_channel(
            f"💥 <b>КРУПНАЯ ПОТЕРЯ!</b>\n\n"
            f"👤 {player_data['username']} потерял {abs(amount):,}₽!\n"
            f"{details}\n\n"
            f"💼 Баланс: {player_data['balance'] + amount:,}₽"
        )
    
    elif event_type == "level_up" and amount >= thresholds["level_up"]:
        await send_to_channel(
            f"⭐ <b>НОВЫЙ УРОВЕНЬ!</b>\n\n"
            f"👤 {player_data['username']} достиг {amount} уровня!\n\n"
            f"Поздравляем с прогрессом! 🎉"
        )

async def publish_daily_stats():
    """Публикация ежедневной статистики"""
    try:
        stats = db.get_game_stats()
        top_players = db.get_top_players(5)
        
        text = f"📊 <b>ЕЖЕДНЕВНАЯ СТАТИСТИКА</b>\n\n"
        text += f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        
        text += f"📈 <b>Общая статистика:</b>\n"
        text += f"👥 Игроков: {stats.get('total_players', 0)}\n"
        text += f"💰 Всего денег: {stats.get('total_money', 0):,}₽\n"
        text += f"🏪 Бизнесов: {stats.get('total_businesses', 0)}\n"
        text += f"🏠 Недвижимости: {stats.get('total_properties', 0)}\n"
        text += f"📊 Акций: {stats.get('total_stocks', 0):,}\n\n"
        
        text += f"🏆 <b>Топ-5 игроков:</b>\n"
        for i, player in enumerate(top_players, 1):
            medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i-1]
            username = player.get('username') or player.get('first_name') or 'Аноним'
            text += f"{medal} {username} - {player.get('balance', 0):,}₽ (ур. {player.get('level', 1)})\n"
        
        text += f"\n🎮 Присоединяйтесь к игре! /start"
        
        await send_to_channel(text)
        
    except Exception as e:
        logger.error(f"Ошибка публикации статистики: {e}")

async def trigger_global_event():
    """Запуск глобального события"""
    events = [
        {
            "title": "💥 ЭКОНОМИЧЕСКИЙ КРИЗИС",
            "message": "Кризис на рынке! Все игроки теряют 5% баланса.",
            "effect": "all_players_lose_5percent"
        },
        {
            "title": "🎁 ЭКОНОМИЧЕСКИЙ БУМ",
            "message": "Бум на рынке! Все бизнесы приносят на 20% больше.",
            "effect": "business_income_plus_20percent"
        },
        {
            "title": "📉 ОБВАЛ НА БИРЖЕ",
            "message": "Обвал на бирже! Все акции падают на 15-30%.",
            "effect": "stocks_crash_15_30percent"
        },
        {
            "title": "📈 РОСТ НА БИРЖЕ",
            "message": "Бычий рынок! Все акции растут на 10-25%.",
            "effect": "stocks_grow_10_25percent"
        }
    ]
    
    event = random.choice(events)
    
    await send_to_channel(
        f"🌍 <b>ГЛОБАЛЬНОЕ СОБЫТИЕ</b>\n\n"
        f"📢 {event['title']}\n"
        f"📝 {event['message']}\n\n"
        f"⏱️ Длительность: 2 часа"
    )
    
    logger.info(f"Глобальное событие: {event['title']}")

async def energy_recovery():
    """Восстановление энергии у всех игроков"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE players SET energy = MIN(100, energy + 1) WHERE energy < 100"
        )
        conn.commit()
        conn.close()
        
        logger.info("⚡ Энергия восстановлена у всех игроков")
    except Exception as e:
        logger.error(f"Ошибка восстановления энергии: {e}")

async def stock_prices_update():
    """Обновление цен на бирже"""
    try:
        for symbol in config.STOCKS:
            stock_market.get_current_price(symbol)
        
        logger.info("📈 Цены на бирже обновлены")
    except Exception as e:
        logger.error(f"Ошибка обновления цен: {e}")

# ========== ОСНОВНЫЕ КОМАНДЫ ==========

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Начало игры"""
    try:
        player = db.get_player(message.from_user.id)
        
        if not player:
            db.create_player(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name
            )
            
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
                "• Инвестиционные фонды\n"
                "• Ежедневные бонусы\n"
                "• Соревнование с другими игроками\n\n"
                "🚀 <b>Первые шаги:</b>\n"
                "1. Нажмите '💰 Заработать'\n"
                "2. Собирайте бутылки\n"
                "3. Получайте ежедневный бонус\n"
                "4. Покупайте свой первый бизнес!\n\n"
                "📢 <b>Крупные события и статистика публикуются в канале!</b>"
            )
        else:
            text = (
                f"👋 <b>С возвращением, {player['username'] or player['first_name'] or 'игрок'}!</b>\n\n"
                f"💰 Баланс: {player['balance']:,}₽\n"
                f"⚡ Энергия: {player['energy']}/100\n"
                f"❤️ Здоровье: {player['health']}/100\n"
                f"⭐ Уровень: {player['level']}\n"
                f"📈 Опыт: {player['experience']:,}\n\n"
                "Что будем делать сегодня?"
            )
        
        await message.answer(text, reply_markup=main_menu())
        
    except Exception as e:
        logger.error(f"Ошибка команды /start: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

@router.message(F.text == "💰 Заработать")
async def earn_menu_handler(message: Message):
    """Меню заработка"""
    await message.answer(
        "💼 <b>Выберите способ заработка:</b>\n\n"
        "• 🔍 Сбор бутылок - медленно, но стабильно\n"
        "• 🥫 Поиск еды - восстановление здоровья\n"
        "• 💤 Сон - восстановление энергии (риск ограбления)\n"
        "• 💼 Работа - разные варианты с разной оплатой",
        reply_markup=earn_menu()
    )

@router.message(F.text == "💼 Бизнес")
async def business_menu_handler(message: Message):
    """Меню бизнеса"""
    await message.answer(
        "🏪 <b>Управление бизнесом:</b>\n\n"
        "Бизнесы приносят пассивный доход каждый час!\n"
        "Чем дороже бизнес - тем больше доход.",
        reply_markup=business_menu()
    )

@router.message(F.text == "📈 Биржа")
async def stock_menu_handler(message: Message):
    """Меню биржи"""
    await message.answer(
        "📊 <b>Фондовая биржа:</b>\n\n"
        "Покупайте и продавайте акции компаний.\n"
        "Цены меняются каждые 5 минут.\n"
        "⚠️ Высокий риск, высокая доходность!",
        reply_markup=stock_menu()
    )

@router.message(F.text == "🏦 Инвестиции")
async def investment_menu_handler(message: Message):
    """Меню инвестиций"""
    await message.answer(
        "💰 <b>Инвестиционные фонды:</b>\n\n"
        "Вкладывайте деньги в фонды с разным уровнем риска.\n"
        "Доходность начисляется ежедневно.",
        reply_markup=investment_menu()
    )

@router.message(F.text == "🎁 Ежедневный")
async def daily_bonus_handler(message: Message):
    """Ежедневный бонус"""
    player = db.get_player(message.from_user.id)
    if not player:
        await message.answer("❌ Сначала зарегистрируйтесь! /start")
        return
    
    result = await game.claim_daily_bonus(player)
    await message.answer(result["message"])

@router.message(F.text == "📊 Статистика")
async def stats_handler(message: Message):
    """Моя статистика"""
    player = db.get_player(message.from_user.id)
    if not player:
        await message.answer("❌ Сначала зарегистрируйтесь! /start")
        return
    
    stats = db.get_player_stats(message.from_user.id)
    
    text = f"📊 <b>Статистика {player['username'] or player['first_name']}</b>\n\n"
    text += f"💰 Баланс: {player['balance']:,}₽\n"
    text += f"⚡ Энергия: {player['energy']}/100\n"
    text += f"❤️ Здоровье: {player['health']}/100\n\n"
    
    text += f"⭐ Уровень: {player['level']}\n"
    text += f"📈 Опыт: {player['experience']:,}\n"
    text += f"🔥 Серия бонусов: {player['daily_streak']} дней\n\n"
    
    text += f"🏪 Бизнесов: {stats.get('business_count', 0)}\n"
    text += f"📊 Акций: {stats.get('stock_count', 0)}\n"
    text += f"🏠 Недвижимости: {stats.get('property_count', 0)}\n\n"
    
    text += f"💵 Всего заработано: {player['total_earned']:,}₽\n"
    text += f"💸 Всего потрачено: {player['total_spent'] or 0:,}₽"
    
    await message.answer(text)

@router.message(F.text == "🏆 Топ игроков")
async def top_players_handler(message: Message):
    """Топ игроков"""
    top_players = db.get_top_players(10)
    
    text = "<b>🏆 Топ-10 игроков по балансу:</b>\n\n"
    
    for i, player in enumerate(top_players, 1):
        medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"][i-1]
        username = player.get('username') or player.get('first_name') or 'Аноним'
        text += f"{medal} <b>{username}</b>\n"
        text += f"   💰 {player.get('balance', 0):,}₽ | ⭐ Ур. {player.get('level', 1)}\n"
    
    stats = db.get_game_stats()
    text += f"\n📊 <b>Статистика игры:</b>\n"
    text += f"👥 Игроков: {stats.get('total_players', 0)}\n"
    text += f"💰 Всего денег: {stats.get('total_money', 0):,}₽\n"
    text += f"🏪 Бизнесов: {stats.get('total_businesses', 0)}"
    
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
        "• Инвестиции - пассивный доход\n\n"
        
        "💰 <b>Доступные действия:</b>\n"
        "• Сбор бутылок - первые медленные деньги\n"
        "• Покупка бизнесов - пассивный доход\n"
        "• Торговля на бирже - спекуляции\n"
        "• Инвестиции - долгосрочные вложения\n"
        "• Ежедневный бонус - за вход каждый день\n\n"
        
        "📈 <b>Прогресс:</b>\n"
        "• Уровни растут медленно\n"
        "• Чем больше денег, тем сложнее зарабатывать\n"
        "• Требуется стратегия и терпение\n\n"
        
        "📢 <b>Канал с событиями:</b>\n"
        "• Крупные заработки/потери игроков\n"
        "• Ежедневная статистика (12:00 и 20:00)\n"
        "• Глобальные события\n\n"
        
        "🚀 <b>Советы:</b>\n"
        "1. Не пропускайте ежедневный бонус\n"
        "2. Покупайте бизнесы как можно раньше\n"
        "3. Диверсифицируйте инвестиции\n"
        "4. Не вкладывайте все в биржу\n"
        "5. Следите за энергией и здоровьем"
    )
    
    await message.answer(text)

# ========== CALLBACK ОБРАБОТЧИКИ ЗАРАБОТКА ==========

@router.callback_query(F.data == "earn_bottles")
async def earn_bottles_handler(callback: CallbackQuery):
    """Сбор бутылок"""
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Сначала зарегистрируйтесь!")
        return
    
    result = await game.collect_bottles(player)
    await callback.message.edit_text(result["message"])
    
    if result.get("success") and result.get("earnings", 0) >= config.CHANNEL_THRESHOLDS["big_income"]:
        await check_and_publish_big_event(
            player, "big_income", result["earnings"], "Собрал много бутылок!"
        )
    
    await callback.answer()

@router.callback_query(F.data == "earn_food")
async def earn_food_handler(callback: CallbackQuery):
    """Поиск еды"""
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Сначала зарегистрируйтесь!")
        return
    
    result = await game.search_food(player)
    await callback.message.edit_text(result["message"])
    await callback.answer()

@router.callback_query(F.data == "earn_sleep")
async def earn_sleep_handler(callback: CallbackQuery):
    """Сон на вокзале"""
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Сначала зарегистрируйтесь!")
        return
    
    result = await game.sleep_at_station(player)
    await callback.message.edit_text(result["message"])
    
    if result.get("robbed") and result.get("stolen", 0) >= config.CHANNEL_THRESHOLDS["big_loss"]:
        await check_and_publish_big_event(
            player, "big_loss", -result["stolen"], "Ограблен на вокзале!"
        )
    
    await callback.answer()

# ========== CALLBACK ОБРАБОТЧИКИ БИЗНЕСА ==========

@router.callback_query(F.data == "business_buy")
async def business_buy_handler(callback: CallbackQuery, state: FSMContext):
    """Покупка бизнеса"""
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Сначала зарегистрируйтесь!")
        return
    
    await state.set_state(GameStates.waiting_business_choice)
    await callback.message.edit_text(
        "🏪 <b>Выберите бизнес для покупки:</b>\n\n"
        "💡 Совет: Начинайте с дешевых бизнесов и постепенно улучшайте их.",
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
    success = db.add_business(callback.from_user.id, business_type)
    
    if not success:
        await callback.message.edit_text(
            f"❌ <b>Ошибка покупки бизнеса!</b>\n\n"
            f"Возможно, у вас уже есть этот бизнес.",
            reply_markup=back_keyboard()
        )
        await callback.answer()
        return
    
    # Списываем деньги
    db.add_player_balance(
        telegram_id=callback.from_user.id,
        amount=-business['price'],
        transaction_type="business_purchase",
        description=f"Покупка {business['name']}"
    )
    
    await callback.message.edit_text(
        f"✅ <b>Бизнес куплен!</b>\n\n"
        f"🏪 {business['name']}\n"
        f"💰 Стоимость: {business['price']:,}₽\n"
        f"💵 Доход в час: {business['income_per_hour']}₽\n"
        f"⭐ Уровень: 1/{business['max_level']}\n\n"
        f"💡 Прибыль можно собирать каждый час!",
        reply_markup=back_keyboard()
    )
    
    # Проверяем на крупную покупку
    if business['price'] >= config.CHANNEL_THRESHOLDS["business_purchase"]:
        await check_and_publish_big_event(
            player, 
            "business_purchase", 
            business['price'], 
            f"Купил {business['name']}!"
        )
    
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "business_profit")
async def business_profit_handler(callback: CallbackQuery):
    """Сбор прибыли с бизнесов"""
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Сначала зарегистрируйтесь!")
        return
    
    result = await game.collect_profits(player)
    await callback.message.edit_text(result["message"])
    
    if result.get("success") and result.get("profit", 0) >= config.CHANNEL_THRESHOLDS["big_income"]:
        await check_and_publish_big_event(
            player, "big_income", result["profit"], "Собрал прибыль с бизнесов!"
        )
    
    await callback.answer()

@router.callback_query(F.data == "business_list")
async def business_list_handler(callback: CallbackQuery):
    """Список бизнесов игрока"""
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Сначала зарегистрируйтесь!")
        return
    
    businesses = db.get_player_businesses(callback.from_user.id)
    
    if not businesses:
        await callback.message.edit_text(
            "❌ <b>У вас еще нет бизнесов!</b>\n\n"
            "Купите свой первый бизнес в меню покупки.",
            reply_markup=back_keyboard()
        )
        return
    
    text = "<b>🏪 Ваши бизнесы:</b>\n\n"
    total_income = 0
    
    for business in businesses:
        business_info = config.BUSINESSES.get(business['business_type'], {})
        name = business_info.get('name', business['business_type'])
        hourly_income = business_info.get('income_per_hour', 0) * business['level']
        total_income += hourly_income
        
        text += f"• {name}\n"
        text += f"  Уровень: {business['level']} | Доход в час: {hourly_income}₽\n\n"
    
    text += f"<b>📊 Итого:</b>\n"
    text += f"• Бизнесов: {len(businesses)}\n"
    text += f"• Общий доход в час: {total_income}₽\n"
    text += f"• Общий доход в день: {total_income * 24:,}₽"
    
    await callback.message.edit_text(
        text,
        reply_markup=business_list_keyboard(businesses)
    )
    await callback.answer()

# ========== CALLBACK ОБРАБОТЧИКИ БИРЖИ ==========

@router.callback_query(F.data == "stock_prices")
async def stock_prices_handler(callback: CallbackQuery):
    """Котировки акций"""
    text = "<b>📊 Текущие котировки акций:</b>\n\n"
    
    for symbol, data in config.STOCKS.items():
        try:
            stock_info = stock_market.get_stock_info(symbol)
            change_icon = "📈" if stock_info['change'] >= 0 else "📉"
            
            text += f"<b>{data['name']} ({symbol})</b>\n"
            text += f"💰 Цена: {stock_info['price']:,}₽ {change_icon} {abs(stock_info['change']):.1f}%\n"
            text += f"📊 Волатильность: {stock_info['volatility']*100:.1f}%\n\n"
        except Exception as e:
            logger.error(f"Ошибка получения информации об акции {symbol}: {e}")
            continue
    
    text += "💡 <i>Цены обновляются каждые 5 минут</i>"
    
    await callback.message.edit_text(text, reply_markup=back_keyboard())
    await callback.answer()

@router.callback_query(F.data == "stock_buy")
async def stock_buy_handler(callback: CallbackQuery, state: FSMContext):
    """Покупка акций"""
    await state.set_state(GameStates.waiting_stock_choice)
    await callback.message.edit_text(
        "💰 <b>Выберите акции для покупки:</b>",
        reply_markup=stock_list_keyboard()
    )

@router.callback_query(F.data.startswith("stock_info_"))
async def stock_info_handler(callback: CallbackQuery, state: FSMContext):
    """Информация об акции"""
    symbol = callback.data.replace("stock_info_", "")
    
    if symbol not in config.STOCKS:
        await callback.answer("❌ Акция не найдена")
        return
    
    try:
        stock_info = stock_market.get_stock_info(symbol)
        change_icon = "📈" if stock_info['change'] >= 0 else "📉"
        
        text = (
            f"<b>📊 {stock_info['name']} ({symbol})</b>\n\n"
            f"💰 Текущая цена: {stock_info['price']:,}₽\n"
            f"{change_icon} Изменение за день: {stock_info['change']:.1f}%\n"
            f"📊 Волатильность: {stock_info['volatility']*100:.1f}%\n\n"
            f"💡 <i>Введите количество акций для покупки:</i>"
        )
        
        await state.update_data(stock_symbol=symbol)
        await state.set_state(GameStates.waiting_stock_quantity)
        await callback.message.edit_text(text)
        
    except Exception as e:
        logger.error(f"Ошибка получения информации об акции {symbol}: {e}")
        await callback.message.edit_text(
            "❌ <b>Ошибка получения информации об акции</b>\n\n"
            "Попробуйте позже.",
            reply_markup=back_keyboard()
        )
    
    await callback.answer()

@router.message(GameStates.waiting_stock_quantity)
async def process_stock_quantity(message: Message, state: FSMContext):
    """Обработка количества акций"""
    try:
        quantity = int(message.text.strip())
        if quantity <= 0:
            await message.answer("❌ Введите положительное число!")
            return
        
        data = await state.get_data()
        symbol = data.get("stock_symbol")
        
        if not symbol:
            await message.answer("❌ Ошибка: символ акции не найден")
            await state.clear()
            return
        
        player = db.get_player(message.from_user.id)
        if not player:
            await message.answer("❌ Ошибка получения данных")
            await state.clear()
            return
        
        # Покупаем акции
        success, result_message = stock_market.buy_stocks(
            telegram_id=message.from_user.id,
            symbol=symbol,
            quantity=quantity
        )
        
        if success:
            await message.answer(
                f"✅ {result_message}\n\n"
                f"💰 Новый баланс: {player['balance']:,}₽",
                reply_markup=main_menu()
            )
        else:
            await message.answer(
                f"❌ {result_message}\n\n"
                f"💰 Ваш баланс: {player['balance']:,}₽",
                reply_markup=main_menu()
            )
        
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Введите число!")
    except Exception as e:
        logger.error(f"Ошибка покупки акций: {e}")
        await message.answer(f"❌ Ошибка: {str(e)}", reply_markup=main_menu())
        await state.clear()

@router.callback_query(F.data == "stock_my")
async def stock_my_handler(callback: CallbackQuery):
    """Мои акции"""
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Сначала зарегистрируйтесь!")
        return
    
    stocks = db.get_player_stocks(callback.from_user.id)
    
    if not stocks:
        await callback.message.edit_text(
            "❌ <b>У вас еще нет акций!</b>\n\n"
            "Купите свои первые акции в меню покупки.",
            reply_markup=back_keyboard()
        )
        return
    
    text = "<b>📈 Ваши акции:</b>\n\n"
    total_value = 0
    total_profit = 0
    
    for stock in stocks:
        try:
            current_price = stock_market.get_current_price(stock['stock_symbol'])
            stock_value = current_price * stock['quantity']
            total_value += stock_value
            
            if stock['average_price']:
                profit = (current_price - stock['average_price']) * stock['quantity']
                total_profit += profit
                profit_text = f"📈 Прибыль: {profit:+,}₽" if profit >= 0 else f"📉 Убыток: {profit:,}₽"
            else:
                profit_text = ""
            
            text += f"<b>{stock['stock_symbol']}</b>\n"
            text += f"Количество: {stock['quantity']:,} шт.\n"
            text += f"Текущая цена: {current_price:,}₽\n"
            text += f"Средняя цена: {stock['average_price']:,}₽\n"
            text += f"Стоимость: {stock_value:,}₽ {profit_text}\n\n"
        except Exception as e:
            logger.error(f"Ошибка расчета стоимости акции {stock['stock_symbol']}: {e}")
            continue
    
    text += f"<b>📊 Итого:</b>\n"
    text += f"• Акций: {len(stocks)}\n"
    text += f"• Общая стоимость: {total_value:,}₽\n"
    text += f"• Общая прибыль: {total_profit:+,}₽"
    
    await callback.message.edit_text(
        text,
        reply_markup=stock_sell_keyboard(stocks)
    )
    await callback.answer()

# ========== ОБРАБОТЧИКИ НАВИГАЦИИ ==========

@router.callback_query(F.data == "back_to_main")
async def back_to_main_handler(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    await callback.message.edit_text(
        "Главное меню:",
        reply_markup=main_menu()
    )
    await callback.answer()

@router.callback_query(F.data == "cancel_action")
async def cancel_action_handler(callback: CallbackQuery, state: FSMContext):
    """Отмена действия"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Действие отменено.",
        reply_markup=main_menu()
    )
    await callback.answer()

# ========== ПЕРИОДИЧЕСКИЕ ЗАДАЧИ ==========

async def startup_tasks():
    """Задачи при запуске бота"""
    print("=" * 60)
    print("🚀 ЗАПУСК СИМУЛЯТОРА МАГНАТА НА RAILWAY")
    print("=" * 60)
    
    # Проверяем конфигурацию
    print(f"🤖 Бот: @{(await bot.get_me()).username}")
    print(f"📁 База данных: {config.DB_FILE}")
    
    if config.CHANNEL_ID:
        print(f"📢 Канал статистики: {config.CHANNEL_ID}")
        try:
            chat = await bot.get_chat(config.CHANNEL_ID)
            print(f"   Название: {chat.title}")
        except Exception as e:
            print(f"   ⚠️ Канал не доступен: {e}")
    else:
        print("ℹ️ Канал статистики не настроен")
    
    # Проверяем базу данных
    db_status = db.check_database()
    print(f"🗄️ Состояние БД: {db_status.get('status', 'unknown')}")
    
    print("=" * 60)
    
    # Запускаем периодические задачи
    try:
        # Восстановление энергии каждые 5 минут
        scheduler.add_job(
            energy_recovery,
            'interval',
            minutes=config.ENERGY_RECOVERY_TIME,
            id='energy_recovery'
        )
        
        # Обновление биржи каждые 5 минут
        scheduler.add_job(
            stock_prices_update,
            'interval',
            minutes=5,
            id='stock_prices_update'
        )
        
        # Ежедневная статистика в 12:00 и 20:00
        for publish_time in config.STATS_PUBLISH_TIMES:
            scheduler.add_job(
                publish_daily_stats,
                CronTrigger(hour=publish_time.hour, minute=publish_time.minute),
                id=f'daily_stats_{publish_time.hour}'
            )
        
        # Случайные события каждые 2-4 часа
        scheduler.add_job(
            trigger_global_event,
            'interval',
            hours=random.randint(*config.RANDOM_EVENTS_INTERVAL),
            id='global_events'
        )
        
        scheduler.start()
        logger.info("✅ Периодические задачи запущены")
        
        # Приветственное сообщение в канал
        if config.CHANNEL_ID:
            try:
                await send_to_channel(
                    "🎮 <b>ИГРА 'СИМУЛЯТОР МАГНАТА' ЗАПУЩЕНА НА RAILWAY!</b>\n\n"
                    "📊 Статистика будет публиковаться 2 раза в день:\n"
                    "• 12:00 - дневная статистика\n"
                    "• 20:00 - вечерняя статистика\n\n"
                    "💰 Крупные события игроков тоже будут здесь!\n\n"
                    "🎯 Присоединяйтесь к игре: /start"
                )
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение в канал: {e}")
        
        print("✅ Бот успешно запущен и готов к работе!")
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"Ошибка запуска периодических задач: {e}")
        print(f"❌ Ошибка запуска задач: {e}")

# ========== ЗАПУСК БОТА ==========

async def on_startup():
    """Действия при запуске приложения"""
    try:
        await startup_tasks()
        return True
    except Exception as e:
        logger.error(f"Ошибка при запуске: {e}")
        return False

async def on_shutdown():
    """Действия при выключении"""
    logger.info("Выключение бота...")
    await bot.session.close()
    if scheduler.running:
        scheduler.shutdown()

async def main():
    """Основная функция запуска бота"""
    try:
        # Запускаем задачи при старте
        if not await on_startup():
            logger.error("Не удалось запустить бота")
            return
        
        # Запускаем бота
        logger.info("Запуск polling...")
        await dp.start_polling(
            bot,
            skip_updates=True,
            on_startup=on_startup,
            on_shutdown=on_shutdown
        )
        
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        print(f"\n❌ Критическая ошибка: {e}")
    finally:
        await on_shutdown()

if __name__ == "__main__":
    asyncio.run(main())