import random
import math
import sqlite3
from datetime import datetime, timedelta
from database import db
import config

class GameLogic:
    """Основная игровая логика"""
    
    # Опыт для уровней (геометрическая прогрессия)
    LEVEL_EXPERIENCE = [0]
    for i in range(1, 101):
        LEVEL_EXPERIENCE.append(LEVEL_EXPERIENCE[-1] + int(100 * (1.5 ** i)))
    
    @staticmethod
    def calculate_income_multiplier(balance: int) -> float:
        """Рассчитать множитель дохода в зависимости от баланса"""
        if balance < 1000:
            return config.INCOME_MULTIPLIERS["beginner"]
        elif balance < 10000:
            return config.INCOME_MULTIPLIERS["trader"]
        elif balance < 100000:
            return config.INCOME_MULTIPLIERS["businessman"]
        elif balance < 1000000:
            return config.INCOME_MULTIPLIERS["magnate"]
        else:
            return config.INCOME_MULTIPLIERS["oligarch"]
    
    @staticmethod
    async def collect_bottles(player_data: dict) -> dict:
        """Собрать бутылки - очень медленный заработок"""
        if player_data['energy'] < 15:
            return {"success": False, "message": "❌ Недостаточно энергии! Нужно 15⚡"}
        
        bottles = random.randint(1, 3)  # Очень мало!
        earnings = bottles * 10  # Всего 10₽ за бутылку
        
        # Умножаем на сложность
        multiplier = GameLogic.calculate_income_multiplier(player_data['balance'])
        earnings = int(earnings * multiplier)
        
        # Бонус за уровень
        level_bonus = 1 + (player_data['level'] * 0.01)
        earnings = int(earnings * level_bonus)
        
        # Обновляем игрока
        new_balance = player_data['balance'] + earnings
        new_energy = player_data['energy'] - 15
        new_exp = player_data['experience'] + 5
        
        db.update_player(
            player_data['telegram_id'],
            balance=new_balance,
            energy=new_energy,
            experience=new_exp,
            total_earned=player_data['total_earned'] + earnings
        )
        
        # Транзакция
        player_id = db.get_player_id(player_data['telegram_id'])
        if player_id:
            db.add_transaction(
                player_id,
                earnings,
                "bottle_collection",
                f"Собрано {bottles} бутылок"
            )
        
        return {
            "success": True,
            "message": f"✅ Собрано {bottles} бутылок\n💰 Заработано: {earnings}₽\n⚡ Энергии потрачено: 15",
            "earnings": earnings,
            "energy_cost": 15
        }
    
    @staticmethod
    async def search_food(player_data: dict) -> dict:
        """Поиск еды"""
        if player_data['energy'] < 8:
            return {"success": False, "message": "❌ Недостаточно энергии! Нужно 8⚡"}
        
        db.update_player(
            player_data['telegram_id'],
            energy=player_data['energy'] - 8
        )
        
        if random.random() < 0.6:  # 60% шанс
            foods = [
                ("хлеб", 10, 0.9),
                ("консервы", 15, 0.8),
                ("фрукты", 20, 0.7),
                ("колбаса", 25, 0.6),
                ("готовый обед", 30, 0.5)
            ]
            
            food, health_gain, good_condition_chance = random.choice(foods)
            
            if random.random() > good_condition_chance:
                # Испорченная еда
                health_loss = random.randint(5, 15)
                new_health = max(0, player_data['health'] - health_loss)
                
                db.update_player(
                    player_data['telegram_id'],
                    health=new_health
                )
                
                return {
                    "success": True,
                    "message": f"⚠️ Нашли {food}, но он испорчен!\n❤️ Здоровье: -{health_loss}",
                    "health_change": -health_loss
                }
            else:
                # Хорошая еда
                new_health = min(100, player_data['health'] + health_gain)
                
                db.update_player(
                    player_data['telegram_id'],
                    health=new_health
                )
                
                return {
                    "success": True,
                    "message": f"✅ Нашли {food}!\n❤️ Здоровье: +{health_gain}",
                    "health_change": health_gain
                }
        else:
            return {
                "success": False,
                "message": "❌ Ничего не нашли...",
                "energy_cost": 8
            }
    
    @staticmethod
    async def sleep_at_station(player_data: dict) -> dict:
        """Сон на вокзале"""
        energy_gain = random.randint(20, 40)
        health_gain = random.randint(10, 20)
        
        # Риск ограбления зависит от баланса
        robbery_chance = min(0.5, player_data['balance'] / 1000000 * 0.3 + 0.2)
        
        if random.random() < robbery_chance:
            stolen_percent = random.uniform(0.05, 0.15)  # 5-15%
            stolen = int(player_data['balance'] * stolen_percent)
            stolen = max(100, min(50000, stolen))  # От 100 до 50,000₽
            
            new_balance = player_data['balance'] - stolen
            new_energy = min(100, player_data['energy'] + energy_gain)
            new_health = min(100, player_data['health'] + health_gain)
            
            db.update_player(
                player_data['telegram_id'],
                balance=new_balance,
                energy=new_energy,
                health=new_health
            )
            
            # Транзакция
            player_id = db.get_player_id(player_data['telegram_id'])
            if player_id:
                db.add_transaction(
                    player_id,
                    -stolen,
                    "robbery",
                    "Ограблен на вокзале"
                )
            
            return {
                "success": True,
                "message": (
                    f"😴 Поспали на вокзале\n"
                    f"⚡ Энергия: +{energy_gain}\n"
                    f"❤️ Здоровье: +{health_gain}\n"
                    f"💸 Ограблены на: {stolen}₽"
                ),
                "energy_gain": energy_gain,
                "health_gain": health_gain,
                "stolen": stolen,
                "robbed": True
            }
        
        # Успешный сон
        new_energy = min(100, player_data['energy'] + energy_gain)
        new_health = min(100, player_data['health'] + health_gain)
        
        db.update_player(
            player_data['telegram_id'],
            energy=new_energy,
            health=new_health
        )
        
        return {
            "success": True,
            "message": (
                f"😴 Поспали на вокзале\n"
                f"⚡ Энергия: +{energy_gain}\n"
                f"❤️ Здоровье: +{health_gain}"
            ),
            "energy_gain": energy_gain,
            "health_gain": health_gain,
            "robbed": False
        }
    
    @staticmethod
    async def collect_profits(player_data: dict) -> dict:
        """Собрать прибыль с бизнесов"""
        player_id = db.get_player_id(player_data['telegram_id'])
        if not player_id:
            return {"success": False, "message": "❌ Ошибка получения данных"}
        
        businesses = db.get_player_businesses(player_id)
        
        if not businesses:
            return {"success": False, "message": "❌ У вас нет бизнесов!"}
        
        total_profit = 0
        updated_businesses = []
        
        for business in businesses:
            business_info = config.BUSINESSES.get(business['business_type'])
            if not business_info:
                continue
            
            # Проверяем время с последнего сбора
            last_profit = datetime.fromisoformat(business['last_profit'].replace('Z', '+00:00'))
            hours_passed = (datetime.now() - last_profit).total_seconds() / 3600
            
            if hours_passed >= 1:
                # Базовый доход
                base_income = business_info['income_per_hour']
                
                # Умножаем на уровень бизнеса
                level_income = base_income * business['level']
                
                # Умножаем на множитель сложности
                difficulty_mult = GameLogic.calculate_income_multiplier(player_data['balance'])
                income = int(level_income * difficulty_mult)
                
                total_profit += income
                updated_businesses.append(business_info['name'])
                
                # Обновляем время сбора
                conn = sqlite3.connect(config.DB_FILE)
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE player_businesses SET last_profit = ? WHERE id = ?",
                    (datetime.now().isoformat(), business['id'])
                )
                conn.commit()
                conn.close()
        
        if total_profit > 0:
            # Начисляем прибыль
            new_balance = player_data['balance'] + total_profit
            
            db.update_player(
                player_data['telegram_id'],
                balance=new_balance,
                total_earned=player_data['total_earned'] + total_profit
            )
            
            # Транзакция
            db.add_transaction(
                player_id,
                total_profit,
                "business_profit",
                f"Прибыль от {len(updated_businesses)} бизнесов"
            )
            
            return {
                "success": True,
                "message": (
                    f"💰 Собрана прибыль с бизнесов\n"
                    f"💵 Сумма: {total_profit}₽\n"
                    f"🏪 Бизнесов: {len(updated_businesses)}\n"
                    f"⏱️ Следующий сбор через 1 час"
                ),
                "profit": total_profit,
                "business_count": len(updated_businesses)
            }
        else:
            return {
                "success": False,
                "message": "⏳ Прибыль еще не накопилась. Подождите хотя бы час."
            }
    
    @staticmethod
    async def claim_daily_bonus(player_data: dict) -> dict:
        """Получить ежедневный бонус"""
        today = datetime.now().date()
        
        if player_data['last_daily_bonus']:
            last_bonus = datetime.fromisoformat(player_data['last_daily_bonus']).date()
            
            if last_bonus == today:
                return {"success": False, "message": "❌ Вы уже получали бонус сегодня!"}
            
            if (today - last_bonus).days == 1:
                # Подряд
                new_streak = player_data['daily_streak'] + 1
            else:
                # Сброс
                new_streak = 1
        else:
            new_streak = 1
        
        # Определяем бонус
        if new_streak > 7:
            bonus_day = 7
        else:
            bonus_day = new_streak
        
        bonus_amount = config.DAILY_BONUS[bonus_day]
        
        # Обновляем игрока
        db.update_player(
            player_data['telegram_id'],
            balance=player_data['balance'] + bonus_amount,
            daily_streak=new_streak,
            last_daily_bonus=today.isoformat(),
            total_earned=player_data['total_earned'] + bonus_amount
        )
        
        # Транзакция
        player_id = db.get_player_id(player_data['telegram_id'])
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
        
        return {
            "success": True,
            "message": (
                f"🎁 Ежедневный бонус!\n\n"
                f"💰 Получено: {bonus_amount}₽\n"
                f"📅 День: {new_streak}{streak_text}\n\n"
                f"🎯 Завтра: {next_bonus}₽"
            ),
            "bonus": bonus_amount,
            "streak": new_streak
        }

game = GameLogic()