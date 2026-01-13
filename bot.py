import asyncio
import logging
import random
import sqlite3
from datetime import datetime, time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import config
from database import db
from game_logic import game
from economy import stock_market, investment_fund
from keyboards import *

# ========== НАСТРОЙКА ==========
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

scheduler = AsyncIOScheduler()

# ========== FSM СОСТОЯНИЯ ==========
class GameStates(StatesGroup):
    waiting_business_choice = State()
    waiting_stock_choice = State()
    waiting_stock_quantity = State()
    waiting_invest_amount = State()

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
async def send_to_channel(message: str):
    """Отправить сообщение в канал"""
    if config.CHANNEL_ID:
        try:
            await bot.send_message(config.CHANNEL_ID, message, parse_mode="Markdown")
            logger.info(f"Отправлено в канал: {message[:100]}...")
        except Exception as e:
            logger.error(f"Ошибка отправки в канал: {e}")

async def check_and_publish_big_event(player_data: dict, event_type: str, amount: int, details: str = ""):
    """Проверить и опубликовать крупное событие"""
    thresholds = config.CHANNEL_THRESHOLDS
    
    if event_type == "big_income" and amount >= thresholds["big_income"]:
        await send_to_channel(
            f"💰 **КРУПНЫЙ ЗАРАБОТОК!**\n\n"
            f"👤 {player_data['username']} заработал {amount:,}₽!\n"
            f"{details}\n\n"
            f"💼 Баланс: {player_data['balance'] + amount:,}₽"
        )
    
    elif event_type == "big_loss" and abs(amount) >= thresholds["big_loss"]:
        await send_to_channel(
            f"💥 **КРУПНАЯ ПОТЕРЯ!**\n\n"
            f"👤 {player_data['username']} потерял {abs(amount):,}₽!\n"
            f"{details}\n\n"
            f"💼 Баланс: {player_data['balance'] + amount:,}₽"
        )
    
    elif event_type == "level_up" and amount >= thresholds["level_up"]:
        await send_to_channel(
            f"⭐ **НОВЫЙ УРОВЕНЬ!**\n\n"
            f"👤 {player_data['username']} достиг {amount} уровня!\n"
            f"🎯 Опыт: {player_data['experience']:,}\n\n"
            f"Поздравляем с прогрессом! 🎉"
        )

async def publish_daily_stats():
    """Публикация ежедневной статистики"""
    stats = db.get_game_stats()
    top_players = db.get_top_players(5)
    
    text = f"📊 **ЕЖЕДНЕВНАЯ СТАТИСТИКА**\n\n"
    text += f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
    
    text += f"📈 **Общая статистика:**\n"
    text += f"👥 Игроков: {stats['total_players']}\n"
    text += f"💰 Всего денег: {stats['total_money']:,}₽\n"
    text += f"🏪 Бизнесов: {stats['total_businesses']}\n"
    text += f"🏠 Недвижимости: {stats['total_properties']}\n"
    text += f"📊 Акций: {stats['total_stocks']:,}\n\n"
    
    text += f"🏆 **Топ-5 игроков:**\n"
    for i, (username, balance, level, earned) in enumerate(top_players, 1):
        medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i-1]
        username_display = username or 'Аноним'
        text += f"{medal} {username_display} - {balance:,}₽ (ур. {level})\n"
    
    text += f"\n🎮 Присоединяйтесь к игре! /start"
    
    await send_to_channel(text)

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
        },
        {
            "title": "🌧️ ПЛОХАЯ ПОГОДА",
            "message": "Ужасная погода! Сбор бутылок дает на 50% меньше.",
            "effect": "bottles_income_minus_50percent"
        }
    ]
    
    event = random.choice(events)
    
    await send_to_channel(
        f"🌍 **ГЛОБАЛЬНОЕ СОБЫТИЕ**\n\n"
        f"📢 {event['title']}\n"
        f"📝 {event['message']}\n\n"
        f"⏱️ Длительность: 2 часа"
    )
    
    logger.info(f"Глобальное событие: {event['title']}")

# ========== КОМАНДЫ ==========
@router.message(CommandStart())
async def cmd_start(message: Message):
    """Начало игры"""
    player = db.get_player(message.from_user.id)
    
    if not player:
        db.create_player(message.from_user.id, message.from_user.username or message.from_user.first_name)
        text = (
            "🎮 **Добро пожаловать в СИМУЛЯТОР МАГНАТА!**\n\n"
            "💰 **Вы начинаете свой путь с нуля:**\n"
            "• Баланс: 0₽\n"
            "• Энергия: 100⚡\n"
            "• Уровень: 1\n\n"
            "📈 **Особенности игры:**\n"
            "• Долгий и интересный путь к богатству\n"
            "• Реальная биржа с акциями\n"
            "• Инвестиционные фонды\n"
            "• Ежедневные бонусы\n"
            "• Соревнование с другими игроков\n\n"
            "🚀 **Первые шаги:**\n"
            "1. Нажмите '💰 Заработать'\n"
            "2. Собирайте бутылки\n"
            "3. Получайте ежедневный бонус\n"
            "4. Покупайте свой первый бизнес!\n\n"
            "📢 **Крупные события и статистика публикуются в канале!**"
        )
    else:
        text = (
            f"👋 **С возвращением, {player['username'] or 'игрок'}!**\n\n"
            f"💰 Баланс: {player['balance']:,}₽\n"
            f"⚡ Энергия: {player['energy']}/100\n"
            f"⭐ Уровень: {player['level']}\n"
            f"📈 Опыт: {player['experience']:,}\n\n"
            "Что будем делать сегодня?"
        )
    
    await message.answer(text, reply_markup=main_menu()) # type: ignore

@router.message(F.text == "💰 Заработать")
async def earn_menu_handler(message: Message):
    """Меню заработка"""
    await message.answer(
        "💼 **Выберите способ заработка:**\n\n"
        "• 🔍 Сбор бутылок - медленно, но стабильно\n"
        "• 🥫 Поиск еды - восстановление здоровья\n"
        "• 💤 Сон - восстановление энергии (риск ограбления)\n"
        "• 💼 Работа - разные варианты с разной оплатой",
        reply_markup=earn_menu() # type: ignore
    )

@router.message(F.text == "💼 Бизнес")
async def business_menu_handler(message: Message):
    """Меню бизнеса"""
    await message.answer(
        "🏪 **Управление бизнесом:**\n\n"
        "Бизнесы приносят пассивный доход каждый час!\n"
        "Чем дороже бизнес - тем больше доход.",
        reply_markup=business_menu() # type: ignore
    )

@router.message(F.text == "📈 Биржа")
async def stock_menu_handler(message: Message):
    """Меню биржи"""
    await message.answer(
        "📊 **Фондовая биржа:**\n\n"
        "Покупайте и продавайте акции компаний.\n"
        "Цены меняются каждые 5 минут.\n"
        "⚠️ Высокий риск, высокая доходность!",
        reply_markup=stock_menu() # type: ignore
    )

@router.message(F.text == "🏦 Инвестиции")
async def investment_menu_handler(message: Message):
    """Меню инвестиций"""
    await message.answer(
        "💰 **Инвестиционные фонды:**\n\n"
        "Вкладывайте деньги в фонды с разным уровнем риска.\n"
        "Доходность начисляется ежедневно.",
        reply_markup=investment_menu() # type: ignore
    )

@router.message(F.text == "🎁 Ежедневный бонус")
async def daily_bonus_handler(message: Message):
    """Ежедневный бонус"""
    player = db.get_player(message.from_user.id)
    if not player:
        await message.answer("❌ Сначала зарегистрируйтесь! /start")
        return
    
    result = await game.claim_daily_bonus(player)
    await message.answer(result["message"])

@router.message(F.text == "📊 Моя статистика")
async def my_stats_handler(message: Message):
    """Моя статистика"""
    player = db.get_player(message.from_user.id)
    if not player:
        await message.answer("❌ Сначала зарегистрируйтесь! /start")
        return
    
    player_id = db.get_player_id(message.from_user.id)
    businesses = db.get_player_businesses(player_id)
    stocks = db.get_player_stocks(player_id)
    
    # Рассчитываем прогресс до следующего уровня
    level = player['level']
    current_exp = player['experience']
    
    if level < 100:
        next_level_exp = game.LEVEL_EXPERIENCE[level]
        exp_needed = next_level_exp - current_exp
        progress_percent = int((current_exp - game.LEVEL_EXPERIENCE[level-1]) / 
                              (next_level_exp - game.LEVEL_EXPERIENCE[level-1]) * 100)
    else:
        exp_needed = 0
        progress_percent = 100
    
    text = f"📊 **Статистика {player['username']}**\n\n"
    text += f"💰 Баланс: {player['balance']:,}₽\n"
    text += f"⚡ Энергия: {player['energy']}/100\n"
    text += f"❤️ Здоровье: {player['health']}/100\n\n"
    
    text += f"⭐ Уровень: {level}\n"
    text += f"📈 Опыт: {current_exp:,}/{next_level_exp:,}\n"
    text += f"📊 Прогресс: {progress_percent}%\n\n"
    
    text += f"🏪 Бизнесов: {len(businesses)}\n"
    text += f"📊 Акций: {len(stocks)}\n"
    text += f"🔥 Серия бонусов: {player['daily_streak']} дней\n\n"
    
    text += f"💵 Всего заработано: {player['total_earned']:,}₽\n"
    text += f"💸 Всего потрачено: {player['total_spent'] or 0:,}₽"
    
    await message.answer(text)

@router.message(F.text == "🏆 Топ игроков")
async def top_players_handler(message: Message):
    """Топ игроков"""
    top_players = db.get_top_players(10)
    
    text = "🏆 **Топ-10 игроков по балансу:**\n\n"
    
    for i, (username, balance, level, earned) in enumerate(top_players, 1):
        medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"][i-1]
        username_display = username or 'Аноним'
        text += f"{medal} **{username_display}**\n"
        text += f"   💰 {balance:,}₽ | ⭐ Ур. {level}\n"
    
    stats = db.get_game_stats()
    text += f"\n📊 **Статистика игры:**\n"
    text += f"👥 Игроков: {stats['total_players']}\n"
    text += f"💰 Всего денег: {stats['total_money']:,}₽\n"
    text += f"🏪 Бизнесов: {stats['total_businesses']}"
    
    await message.answer(text)

@router.message(F.text == "ℹ️ Помощь")
async def help_handler(message: Message):
    """Помощь"""
    text = (
        "🆘 **Помощь по игре 'Симулятор Магната'**\n\n"
        
        "🎮 **Основные принципы:**\n"
        "• Деньги зарабатываются медленно\n"
        "• Бизнесы - основной источник дохода\n"
        "• Биржа - высокорисковый заработок\n"
        "• Инвестиции - пассивный доход\n\n"
        
        "💰 **Доступные действия:**\n"
        "• Сбор бутылок - первые медленные деньги\n"
        "• Покупка бизнесов - пассивный доход\n"
        "• Торговля на бирже - спекуляции\n"
        "• Инвестиции - долгосрочные вложения\n"
        "• Ежедневный бонус - за вход каждый день\n\n"
        
        "📈 **Прогресс:**\n"
        "• Уровни растут медленно\n"
        "• Чем больше денег, тем сложнее зарабатывать\n"
        "• Требуется стратегия и терпение\n\n"
        
        "📢 **Канал с событиями:**\n"
        "• Крупные заработки/потери игроков\n"
        "• Ежедневная статистика (12:00 и 20:00)\n"
        "• Глобальные события\n\n"
        
        "🚀 **Советы:**\n"
        "1. Не пропускайте ежедневный бонус\n"
        "2. Покупайте бизнесы как можно раньше\n"
        "3. Диверсифицируйте инвестиции\n"
        "4. Не вкладывайте все в биржу\n"
        "5. Следите за энергией и здоровьем"
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
    
    result = await game.collect_bottles(player)
    await callback.message.edit_text(result["message"])
    
    # Проверяем на крупный заработок
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
    
    # Проверяем на крупную потерю
    if result.get("robbed") and result.get("stolen", 0) >= config.CHANNEL_THRESHOLDS["big_loss"]:
        await check_and_publish_big_event(
            player, "big_loss", -result["stolen"], "Ограблен на вокзале!"
        )
    
    await callback.answer()

@router.callback_query(F.data == "business_buy")
async def business_buy_handler(callback: CallbackQuery, state: FSMContext):
    """Покупка бизнеса"""
    player = db.get_player(callback.from_user.id)
    if not player:
        await callback.answer("❌ Сначала зарегистрируйтесь!")
        return
    
    await state.set_state(GameStates.waiting_business_choice)
    await callback.message.edit_text(
        "🏪 **Выберите бизнес для покупки:**\n\n"
        "💡 Совет: Начинайте с дешевых бизнесов и постепенно улучшайте их.",
        reply_markup=buy_business_keyboard() # type: ignore
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
            f"❌ **Недостаточно средств!**\n\n"
            f"🏪 {business['name']}\n"
            f"💰 Цена: {business['price']:,}₽\n"
            f"💵 Ваш баланс: {player['balance']:,}₽\n\n"
            f"Нужно еще {business['price'] - player['balance']:,}₽",
            reply_markup=back_keyboard() # type: ignore
        )
        await callback.answer()
        return
    
    # Покупаем бизнес
    player_id = db.get_player_id(callback.from_user.id)
    db.add_business(player_id, business_type)
    
    # Списываем деньги
    db.update_player(
        callback.from_user.id,
        balance=player['balance'] - business['price'],
        total_spent=(player.get('total_spent') or 0) + business['price']
    )
    
    # Транзакция
    db.add_transaction(
        player_id,
        -business['price'],
        "business_purchase",
        f"Покупка {business['name']}"
    )
    
    await callback.message.edit_text(
        f"✅ **Бизнес куплен!**\n\n"
        f"🏪 {business['name']}\n"
        f"💰 Стоимость: {business['price']:,}₽\n"
        f"💵 Доход в час: {business['income_per_hour']}₽\n"
        f"⭐ Уровень: 1/{business['max_level']}\n\n"
        f"💡 Прибыль можно собирать каждый час!",
        reply_markup=back_keyboard() # type: ignore
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
    
    # Проверяем на крупный заработок
    if result.get("success") and result.get("profit", 0) >= config.CHANNEL_THRESHOLDS["big_income"]:
        await check_and_publish_big_event(
            player, "big_income", result["profit"], "Собрал прибыль с бизнесов!"
        )
    
    await callback.answer()

@router.callback_query(F.data == "stock_prices")
async def stock_prices_handler(callback: CallbackQuery):
    """Котировки акций"""
    text = "📊 **Текущие котировки акций:**\n\n"
    
    for symbol, data in config.STOCKS.items():
        stock_info = stock_market.get_stock_info(symbol)
        change_icon = "📈" if stock_info['change'] >= 0 else "📉"
        
        text += f"{data['name']} ({symbol})\n"
        text += f"💰 Цена: {stock_info['price']:,}₽ {change_icon} {abs(stock_info['change'])}%\n"
        text += f"📊 Волатильность: {stock_info['volatility']*100}%\n\n"
    
    text += "💡 Цены обновляются каждые 5 минут"
    
    await callback.message.edit_text(text, reply_markup=back_keyboard()) # type: ignore
    await callback.answer()

@router.callback_query(F.data == "stock_buy")
async def stock_buy_handler(callback: CallbackQuery, state: FSMContext):
    """Покупка акций"""
    await state.set_state(GameStates.waiting_stock_choice)
    await callback.message.edit_text(
        "💰 **Выберите акции для покупки:**",
        reply_markup=stock_list_keyboard() # type: ignore
    )

@router.callback_query(F.data.startswith("stock_info_"))
async def stock_info_handler(callback: CallbackQuery, state: FSMContext):
    """Информация об акции"""
    symbol = callback.data.replace("stock_info_", "")
    
    if symbol not in config.STOCKS:
        await callback.answer("❌ Акция не найдена")
        return
    
    stock_info = stock_market.get_stock_info(symbol)
    change_icon = "📈" if stock_info['change'] >= 0 else "📉"
    
    text = (
        f"📊 **{stock_info['name']} ({symbol})**\n\n"
        f"💰 Текущая цена: {stock_info['price']:,}₽\n"
        f"{change_icon} Изменение за день: {stock_info['change']}%\n"
        f"📊 Волатильность: {stock_info['volatility']*100}%\n\n"
        f"💡 Введите количество акций для покупки:"
    )
    
    await state.update_data(stock_symbol=symbol)
    await state.set_state(GameStates.waiting_stock_quantity)
    await callback.message.edit_text(text)
    await callback.answer()

@router.message(GameStates.waiting_stock_quantity)
async def process_stock_quantity(message: Message, state: FSMContext):
    """Обработка количества акций"""
    try:
        quantity = int(message.text)
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
        
        player_id = db.get_player_id(message.from_user.id)
        success, result_message = stock_market.buy_stocks(player_id, symbol, quantity)
        
        await message.answer(result_message, reply_markup=main_menu()) # type: ignore
        
        # Проверяем на крупную покупку
        stock_info = stock_market.get_stock_info(symbol)
        total_cost = stock_info['price'] * quantity
        
        if success and total_cost >= config.CHANNEL_THRESHOLDS["business_purchase"]:
            await check_and_publish_big_event(
                player, "business_purchase", total_cost, f"Купил акции {symbol}!"
            )
        
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Введите число!")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
        await state.clear()

@router.callback_query(F.data == "back_to_main")
async def back_to_main_handler(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    await callback.message.edit_text(
        "Главное меню:",
        reply_markup=main_menu() # type: ignore
    )
    await callback.answer()

@router.callback_query(F.data == "cancel_action")
async def cancel_action_handler(callback: CallbackQuery, state: FSMContext):
    """Отмена действия"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Действие отменено.",
        reply_markup=main_menu() # type: ignore
    )
    await callback.answer()

# ========== ПЕРИОДИЧЕСКИЕ ЗАДАЧИ ==========
async def energy_recovery():
    """Восстановление энергии у всех игроков"""
    try:
        conn = sqlite3.connect(config.DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE players SET energy = MIN(100, energy + 1) WHERE energy < 100"
        )
        conn.commit()
        conn.close()
        
        logger.info("Энергия восстановлена у всех игроков")
    except Exception as e:
        logger.error(f"Ошибка восстановления энергии: {e}")

async def stock_prices_update():
    """Обновление цен на бирже"""
    try:
        for symbol in config.STOCKS:
            stock_market.get_current_price(symbol)
        
        logger.info("Цены на бирже обновлены")
    except Exception as e:
        logger.error(f"Ошибка обновления цен: {e}")

async def startup_tasks():
    """Задачи при запуске"""
    logger.info("Запуск периодических задач...")
    
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
            CronTrigger(hour=publish_time.hour, minute=publish_time.minute, timezone='Europe/Moscow'),
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
    logger.info("Периодические задачи запущены")

# ========== ЗАПУСК БОТА ==========
async def on_startup():
    """Действия при запуске"""
    print("=" * 50)
    print("🚀 ЗАПУСК СИМУЛЯТОРА МАГНАТА")
    print("=" * 50)
    
    if config.BOT_TOKEN == "ВАШ_ТОКЕН_ЗДЕСЬ":
        print("❌ ОШИБКА: Замените BOT_TOKEN в config.py или настройте .env!")
        return False
    
    print(f"🤖 Бот: @{(await bot.get_me()).username}")
    
    if config.CHANNEL_ID:
        print(f"📢 Канал статистики: {config.CHANNEL_ID}")
        try:
            chat = await bot.get_chat(config.CHANNEL_ID)
            print(f"   Название: {chat.title}")
        except:
            print("   ⚠️ Канал не доступен, проверьте настройки")
    else:
        print("ℹ️ Канал статистики не настроен")
    
    print(f"📁 База данных: {config.DB_FILE}")
    print("=" * 50)
    
    # Запускаем периодические задачи
    await startup_tasks()
    
    # Приветственное сообщение в канал
    if config.CHANNEL_ID:
        try:
            await send_to_channel(
                "🎮 **ИГРА 'СИМУЛЯТОР МАГНАТА' ЗАПУЩЕНА!**\n\n"
                "📊 Статистика будет публиковаться 2 раза в день:\n"
                "• 12:00 - дневная статистика\n"
                "• 20:00 - вечерняя статистика\n\n"
                "💰 Крупные события игроков тоже будут здесь!\n\n"
                "🎯 Присоединяйтесь к игре: /start"
            )
        except Exception as e:
            print(f"⚠️ Не удалось отправить сообщение в канал: {e}")
    
    return True

async def main():
    """Основная функция"""
    if not await on_startup():
        return
    
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())