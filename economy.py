import random
import json
import sqlite3
from datetime import datetime, timedelta
from database import db
import config

class StockMarket:
    """Класс для работы с биржей"""
    
    def __init__(self):
        self.stocks = config.STOCKS
        self.price_history = {}
        self.last_update = {}
        self.load_prices()
    
    def load_prices(self):
        """Загрузить текущие цены из истории"""
        for symbol in self.stocks:
            conn = sqlite3.connect(config.DB_FILE)
            cursor = conn.cursor()
            
            cursor.execute(
                """SELECT price FROM stock_history 
                   WHERE stock_symbol = ? 
                   ORDER BY timestamp DESC LIMIT 1""",
                (symbol,)
            )
            result = cursor.fetchone()
            
            if result:
                self.price_history[symbol] = result[0]
            else:
                # Начальная цена
                self.price_history[symbol] = self.stocks[symbol]["base_price"]
                
                # Сохраняем начальную цену в историю
                cursor.execute(
                    """INSERT INTO stock_history (stock_symbol, price)
                       VALUES (?, ?)""",
                    (symbol, self.stocks[symbol]["base_price"])
                )
                conn.commit()
            
            conn.close()
    
    def get_current_price(self, symbol: str):
        """Получить текущую цену акции"""
        if symbol not in self.price_history:
            self.price_history[symbol] = self.stocks[symbol]["base_price"]
            return self.price_history[symbol]
        
        # Обновляем цену если прошло больше 5 минут
        current_time = datetime.now()
        if symbol in self.last_update:
            if (current_time - self.last_update[symbol]).seconds < 300:
                return self.price_history[symbol]
        
        # Генерируем новую цену
        old_price = self.price_history[symbol]
        volatility = self.stocks[symbol]["volatility"]
        
        # Рандомное изменение цены (± volatility%)
        change = random.uniform(-volatility, volatility)
        new_price = int(old_price * (1 + change))
        
        # Минимальная цена 10% от базовой
        min_price = int(self.stocks[symbol]["base_price"] * 0.1)
        new_price = max(min_price, new_price)
        
        # Максимальная цена 500% от базовой
        max_price = int(self.stocks[symbol]["base_price"] * 5)
        new_price = min(max_price, new_price)
        
        self.price_history[symbol] = new_price
        self.last_update[symbol] = current_time
        
        # Сохраняем в историю
        self.save_price_to_history(symbol, new_price)
        
        return new_price
    
    def save_price_to_history(self, symbol: str, price: int):
        """Сохранить цену в историю"""
        conn = sqlite3.connect(config.DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute(
            """INSERT INTO stock_history (stock_symbol, price)
               VALUES (?, ?)""",
            (symbol, price)
        )
        conn.commit()
        conn.close()
    
    def get_stock_info(self, symbol: str):
        """Получить информацию об акции"""
        current_price = self.get_current_price(symbol)
        stock_data = self.stocks[symbol]
        
        # Рассчитываем изменение за день
        conn = sqlite3.connect(config.DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute(
            """SELECT price FROM stock_history 
               WHERE stock_symbol = ? 
               AND timestamp > datetime('now', '-1 day')
               ORDER BY timestamp ASC LIMIT 1""",
            (symbol,)
        )
        day_start = cursor.fetchone()
        
        change = 0
        if day_start:
            change = ((current_price - day_start[0]) / day_start[0]) * 100
        
        conn.close()
        
        return {
            "symbol": symbol,
            "name": stock_data["name"],
            "price": current_price,
            "change": round(change, 2),
            "volatility": stock_data["volatility"]
        }
    
    def buy_stocks(self, player_id: int, symbol: str, quantity: int):
        """Купить акции для игрока"""
        current_price = self.get_current_price(symbol)
        total_cost = current_price * quantity
        
        # Получаем баланс игрока
        conn = sqlite3.connect(config.DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT balance FROM players WHERE id = ?", (player_id,))
        result = cursor.fetchone()
        
        if not result or result[0] < total_cost:
            conn.close()
            return False, "Недостаточно средств"
        
        # Списываем деньги
        cursor.execute(
            "UPDATE players SET balance = balance - ? WHERE id = ?",
            (total_cost, player_id)
        )
        
        conn.commit()
        conn.close()
        
        # Добавляем акции
        db.buy_stock(player_id, symbol, quantity, current_price)
        
        # Записываем транзакцию
        db.add_transaction(
            player_id, 
            -total_cost, 
            "stock_purchase",
            f"Покупка {quantity} акций {symbol} по {current_price}₽"
        )
        
        return True, f"✅ Куплено {quantity} акций {symbol} по {current_price}₽ за акцию"
    
    def sell_stocks(self, player_id: int, symbol: str, quantity: int):
        """Продать акции"""
        current_price = self.get_current_price(symbol)
        total_income = current_price * quantity
        
        # Проверяем наличие акций
        player_stocks = db.get_player_stocks(player_id)
        player_qty = 0
        
        for stock in player_stocks:
            if stock["stock_symbol"] == symbol:
                player_qty = stock["quantity"]
                break
        
        if player_qty < quantity:
            return False, f"❌ У вас только {player_qty} акций {symbol}"
        
        # Продаем
        success = db.sell_stock(player_id, symbol, quantity, current_price)
        
        if not success:
            return False, "❌ Ошибка при продаже акций"
        
        # Зачисляем деньги
        db.update_player_by_id(player_id, balance=db.get_player_by_id(player_id)['balance'] + total_income)
        
        # Записываем транзакцию
        db.add_transaction(
            player_id,
            total_income,
            "stock_sale",
            f"Продажа {quantity} акций {symbol} по {current_price}₽"
        )
        
        # Рассчитываем прибыль/убыток
        conn = sqlite3.connect(config.DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute(
            """SELECT average_price FROM player_stocks 
               WHERE player_id = ? AND stock_symbol = ?""",
            (player_id, symbol)
        )
        result = cursor.fetchone()
        conn.close()
        
        profit_loss = 0
        if result:
            avg_price = result[0]
            profit_loss = (current_price - avg_price) * quantity
        
        profit_text = ""
        if profit_loss > 0:
            profit_text = f"📈 Прибыль: +{profit_loss}₽"
        elif profit_loss < 0:
            profit_text = f"📉 Убыток: {profit_loss}₽"
        
        return True, f"✅ Продано {quantity} акций {symbol} по {current_price}₽\n{profit_text}"
    
    def get_player_by_id(self, player_id: int):
        """Получить игрока по ID"""
        conn = sqlite3.connect(config.DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM players WHERE id = ?", (player_id,))
        row = cursor.fetchone()
        
        conn.close()
        return dict(row) if row else None

class InvestmentFund:
    """Инвестиционный фонд"""
    
    def __init__(self):
        self.funds = {
            "conservative": {
                "name": "⚖️ Консервативный",
                "min_invest": 10000,
                "return_rate": (0.05, 0.15),  # 5-15% в месяц
                "risk": "низкий"
            },
            "balanced": {
                "name": "📊 Сбалансированный",
                "min_invest": 50000,
                "return_rate": (0.1, 0.25),   # 10-25% в месяц
                "risk": "средний"
            },
            "aggressive": {
                "name": "🚀 Агрессивный",
                "min_invest": 200000,
                "return_rate": (0.2, 0.5),    # 20-50% в месяц
                "risk": "высокий"
            },
            "crypto": {
                "name": "₿ Крипто-фонд",
                "min_invest": 100000,
                "return_rate": (-0.3, 0.8),   # -30% до +80% в месяц
                "risk": "очень высокий"
            }
        }
    
    def get_fund_info(self, fund_type: str):
        """Получить информацию о фонде"""
        if fund_type not in self.funds:
            return None
        
        fund = self.funds[fund_type]
        return {
            "name": fund["name"],
            "min_invest": fund["min_invest"],
            "return_min": fund["return_rate"][0] * 100,
            "return_max": fund["return_rate"][1] * 100,
            "risk": fund["risk"]
        }
    
    def invest(self, player_id: int, fund_type: str, amount: int):
        """Инвестировать в фонд"""
        if fund_type not in self.funds:
            return False, "Неизвестный тип фонда"
        
        fund = self.funds[fund_type]
        
        if amount < fund["min_invest"]:
            return False, f"Минимальная сумма: {fund['min_invest']}₽"
        
        # Здесь будет логика инвестиций
        # Пока просто имитация
        
        # Рассчитываем потенциальную прибыль
        min_return = int(amount * fund["return_rate"][0])
        max_return = int(amount * fund["return_rate"][1])
        
        return True, (
            f"✅ Инвестировано {amount}₽ в {fund['name']}\n\n"
            f"📈 Ожидаемая доходность за месяц:\n"
            f"• Минимум: {min_return}₽ ({fund['return_rate'][0]*100}%)\n"
            f"• Максимум: {max_return}₽ ({fund['return_rate'][1]*100}%)\n\n"
            f"⚠️ Риск: {fund['risk'].upper()}"
        )

# Создаем экземпляры
stock_market = StockMarket()
investment_fund = InvestmentFund()