import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import config

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_file: str = None):
        """Инициализация базы данных"""
        self.db_file = db_file or config.DB_FILE
        logger.info(f"📁 Используется база данных: {self.db_file}")
        self.init_db()
    
    def get_connection(self) -> sqlite3.Connection:
        """Получить соединение с базой данных"""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """Инициализация всех таблиц"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Таблица игроков
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    balance BIGINT DEFAULT 0,
                    energy INTEGER DEFAULT 100,
                    health INTEGER DEFAULT 100,
                    level INTEGER DEFAULT 1,
                    experience BIGINT DEFAULT 0,
                    reputation INTEGER DEFAULT 0,
                    daily_streak INTEGER DEFAULT 0,
                    last_daily_bonus DATE,
                    last_energy_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_earned BIGINT DEFAULT 0,
                    total_spent BIGINT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Индексы для игроков
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_players_telegram_id ON players(telegram_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_players_balance ON players(balance DESC)")
            
            # Таблица бизнесов игроков
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS player_businesses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_id INTEGER NOT NULL,
                    business_type TEXT NOT NULL,
                    level INTEGER DEFAULT 1,
                    last_profit TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_profit BIGINT DEFAULT 0,
                    FOREIGN KEY (player_id) REFERENCES players (id) ON DELETE CASCADE,
                    UNIQUE(player_id, business_type)
                )
            """)
            
            # Таблица недвижимости игроков
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS player_properties (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_id INTEGER NOT NULL,
                    property_type TEXT NOT NULL,
                    purchase_price BIGINT NOT NULL,
                    purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (player_id) REFERENCES players (id) ON DELETE CASCADE
                )
            """)
            
            # Таблица акций игроков
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS player_stocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_id INTEGER NOT NULL,
                    stock_symbol TEXT NOT NULL,
                    quantity INTEGER DEFAULT 0,
                    average_price INTEGER,
                    total_invested BIGINT DEFAULT 0,
                    FOREIGN KEY (player_id) REFERENCES players (id) ON DELETE CASCADE,
                    UNIQUE(player_id, stock_symbol)
                )
            """)
            
            # История цен акций
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_symbol TEXT NOT NULL,
                    price INTEGER NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Транзакции игроков
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_id INTEGER NOT NULL,
                    amount BIGINT NOT NULL,
                    type TEXT NOT NULL,
                    description TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (player_id) REFERENCES players (id) ON DELETE CASCADE
                )
            """)
            
            # Глобальные события
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS global_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    effects TEXT,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            
            conn.commit()
            logger.info("✅ База данных успешно инициализирована")
            
            # Добавляем начальные данные если нужно
            self._add_initial_data(cursor)
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации базы данных: {e}")
            raise
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _add_initial_data(self, cursor):
        """Добавление начальных данных"""
        # Добавляем начальные записи в историю акций если таблица пуста
        cursor.execute("SELECT COUNT(*) FROM stock_history")
        if cursor.fetchone()[0] == 0:
            for symbol, data in config.STOCKS.items():
                cursor.execute(
                    "INSERT INTO stock_history (stock_symbol, price) VALUES (?, ?)",
                    (symbol, data["base_price"])
                )
    
    # ========== МЕТОДЫ ДЛЯ ИГРОКОВ ==========
    
    def get_player(self, telegram_id: int) -> Optional[Dict]:
        """Получить данные игрока"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM players WHERE telegram_id = ?",
                (telegram_id,)
            )
            row = cursor.fetchone()
            
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка получения игрока {telegram_id}: {e}")
            return None
        finally:
            conn.close()
    
    def get_player_by_id(self, player_id: int) -> Optional[Dict]:
        """Получить игрока по ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM players WHERE id = ?",
                (player_id,)
            )
            row = cursor.fetchone()
            
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка получения игрока ID {player_id}: {e}")
            return None
        finally:
            conn.close()
    
    def create_player(self, telegram_id: int, username: str, first_name: str = "", last_name: str = "") -> bool:
        """Создать нового игрока"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                """INSERT INTO players (telegram_id, username, first_name, last_name, 
                   balance, energy, health) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (telegram_id, username, first_name, last_name, 
                 config.START_BALANCE, config.START_ENERGY, config.MAX_HEALTH)
            )
            conn.commit()
            
            logger.info(f"✅ Создан новый игрок: {username} ({telegram_id})")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"Игрок {telegram_id} уже существует")
            return False
        except Exception as e:
            logger.error(f"Ошибка создания игрока: {e}")
            return False
        finally:
            conn.close()
    
    def update_player(self, telegram_id: int, **kwargs) -> bool:
        """Обновить данные игрока"""
        if not kwargs:
            return False
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
            values = list(kwargs.values())
            values.append(telegram_id)
            
            cursor.execute(
                f"UPDATE players SET {set_clause} WHERE telegram_id = ?",
                values
            )
            conn.commit()
            
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка обновления игрока {telegram_id}: {e}")
            return False
        finally:
            conn.close()
    
    def add_player_balance(self, telegram_id: int, amount: int, transaction_type: str, description: str = "") -> bool:
        """Добавить/убрать баланс игрока"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Получаем текущий баланс
            cursor.execute(
                "SELECT balance, id FROM players WHERE telegram_id = ?",
                (telegram_id,)
            )
            result = cursor.fetchone()
            
            if not result:
                return False
            
            current_balance, player_id = result
            new_balance = current_balance + amount
            
            # Обновляем баланс
            cursor.execute(
                "UPDATE players SET balance = ? WHERE telegram_id = ?",
                (new_balance, telegram_id)
            )
            
            # Добавляем запись о транзакции
            if amount != 0:
                cursor.execute(
                    """INSERT INTO transactions (player_id, amount, type, description)
                       VALUES (?, ?, ?, ?)""",
                    (player_id, amount, transaction_type, description)
                )
                
                # Обновляем общие суммы
                if amount > 0:
                    cursor.execute(
                        "UPDATE players SET total_earned = total_earned + ? WHERE telegram_id = ?",
                        (amount, telegram_id)
                    )
                else:
                    cursor.execute(
                        "UPDATE players SET total_spent = total_spent + ? WHERE telegram_id = ?",
                        (abs(amount), telegram_id)
                    )
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка изменения баланса {telegram_id}: {e}")
            return False
        finally:
            conn.close()
    
    # ========== МЕТОДЫ ДЛЯ БИЗНЕСОВ ==========
    
    def get_player_businesses(self, telegram_id: int) -> List[Dict]:
        """Получить бизнесы игрока"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT pb.* 
                FROM player_businesses pb
                JOIN players p ON pb.player_id = p.id
                WHERE p.telegram_id = ?
            """, (telegram_id,))
            
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка получения бизнесов {telegram_id}: {e}")
            return []
        finally:
            conn.close()
    
    def add_business(self, telegram_id: int, business_type: str) -> bool:
        """Добавить бизнес игроку"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Получаем ID игрока
            cursor.execute("SELECT id FROM players WHERE telegram_id = ?", (telegram_id,))
            result = cursor.fetchone()
            
            if not result:
                return False
            
            player_id = result[0]
            
            # Добавляем бизнес
            cursor.execute("""
                INSERT INTO player_businesses (player_id, business_type, level)
                VALUES (?, ?, 1)
            """, (player_id, business_type))
            
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"Бизнес {business_type} уже есть у игрока {telegram_id}")
            return False
        except Exception as e:
            logger.error(f"Ошибка добавления бизнеса: {e}")
            return False
        finally:
            conn.close()
    
    def upgrade_business(self, business_id: int, new_level: int) -> bool:
        """Улучшить бизнес"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "UPDATE player_businesses SET level = ? WHERE id = ?",
                (new_level, business_id)
            )
            conn.commit()
            
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка улучшения бизнеса {business_id}: {e}")
            return False
        finally:
            conn.close()
    
    def update_business_profit_time(self, business_id: int) -> bool:
        """Обновить время последней прибыли бизнеса"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "UPDATE player_businesses SET last_profit = CURRENT_TIMESTAMP WHERE id = ?",
                (business_id,)
            )
            conn.commit()
            
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка обновления времени бизнеса {business_id}: {e}")
            return False
        finally:
            conn.close()
    
    # ========== МЕТОДЫ ДЛЯ АКЦИЙ ==========
    
    def get_player_stocks(self, telegram_id: int) -> List[Dict]:
        """Получить акции игрока"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT ps.* 
                FROM player_stocks ps
                JOIN players p ON ps.player_id = p.id
                WHERE p.telegram_id = ? AND ps.quantity > 0
            """, (telegram_id,))
            
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка получения акций {telegram_id}: {e}")
            return []
        finally:
            conn.close()
    
    def get_player_stock(self, telegram_id: int, symbol: str) -> Optional[Dict]:
        """Получить конкретную акцию игрока"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT ps.* 
                FROM player_stocks ps
                JOIN players p ON ps.player_id = p.id
                WHERE p.telegram_id = ? AND ps.stock_symbol = ?
            """, (telegram_id, symbol))
            
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка получения акции {symbol}: {e}")
            return None
        finally:
            conn.close()
    
    def buy_stock(self, telegram_id: int, symbol: str, quantity: int, price: int) -> bool:
        """Купить акции для игрока"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Получаем ID игрока и текущие акции
            cursor.execute("""
                SELECT p.id, ps.quantity, ps.average_price, ps.total_invested
                FROM players p
                LEFT JOIN player_stocks ps ON p.id = ps.player_id AND ps.stock_symbol = ?
                WHERE p.telegram_id = ?
            """, (symbol, telegram_id))
            
            result = cursor.fetchone()
            if not result:
                return False
            
            player_id, current_qty, current_avg, current_invested = result
            
            total_cost = quantity * price
            
            # Проверяем баланс
            cursor.execute("SELECT balance FROM players WHERE id = ?", (player_id,))
            balance = cursor.fetchone()[0]
            
            if balance < total_cost:
                return False
            
            # Обновляем баланс
            cursor.execute(
                "UPDATE players SET balance = balance - ? WHERE id = ?",
                (total_cost, player_id)
            )
            
            # Обновляем или добавляем акции
            if current_qty is None:
                # Новые акции
                cursor.execute("""
                    INSERT INTO player_stocks (player_id, stock_symbol, quantity, average_price, total_invested)
                    VALUES (?, ?, ?, ?, ?)
                """, (player_id, symbol, quantity, price, total_cost))
            else:
                # Обновляем существующие
                new_qty = current_qty + quantity
                new_invested = current_invested + total_cost
                new_avg = new_invested // new_qty
                
                cursor.execute("""
                    UPDATE player_stocks 
                    SET quantity = ?, average_price = ?, total_invested = ?
                    WHERE player_id = ? AND stock_symbol = ?
                """, (new_qty, new_avg, new_invested, player_id, symbol))
            
            # Добавляем транзакцию
            cursor.execute("""
                INSERT INTO transactions (player_id, amount, type, description)
                VALUES (?, ?, ?, ?)
            """, (player_id, -total_cost, "stock_buy", f"Покупка {quantity} {symbol} по {price}₽"))
            
            # Обновляем общие расходы
            cursor.execute(
                "UPDATE players SET total_spent = total_spent + ? WHERE id = ?",
                (total_cost, player_id)
            )
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка покупки акций: {e}")
            return False
        finally:
            conn.close()
    
    def sell_stock(self, telegram_id: int, symbol: str, quantity: int, price: int) -> tuple[bool, int, int]:
        """Продать акции игрока. Возвращает (успех, прибыль, общая сумма)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Получаем акции игрока
            cursor.execute("""
                SELECT ps.id, ps.quantity, ps.average_price, p.id as player_id
                FROM player_stocks ps
                JOIN players p ON ps.player_id = p.id
                WHERE p.telegram_id = ? AND ps.stock_symbol = ?
            """, (telegram_id, symbol))
            
            result = cursor.fetchone()
            if not result:
                return False, 0, 0
            
            stock_id, current_qty, avg_price, player_id = result
            
            if current_qty < quantity:
                return False, 0, 0
            
            # Рассчитываем суммы
            total_income = quantity * price
            total_cost = quantity * avg_price
            profit = total_income - total_cost
            
            # Обновляем баланс
            cursor.execute(
                "UPDATE players SET balance = balance + ? WHERE id = ?",
                (total_income, player_id)
            )
            
            # Обновляем акции
            new_qty = current_qty - quantity
            if new_qty == 0:
                cursor.execute(
                    "DELETE FROM player_stocks WHERE id = ?",
                    (stock_id,)
                )
            else:
                cursor.execute(
                    "UPDATE player_stocks SET quantity = ? WHERE id = ?",
                    (new_qty, stock_id)
                )
            
            # Добавляем транзакцию
            cursor.execute("""
                INSERT INTO transactions (player_id, amount, type, description)
                VALUES (?, ?, ?, ?)
            """, (player_id, total_income, "stock_sell", f"Продажа {quantity} {symbol} по {price}₽"))
            
            # Обновляем общие доходы
            cursor.execute(
                "UPDATE players SET total_earned = total_earned + ? WHERE id = ?",
                (total_income, player_id)
            )
            
            conn.commit()
            return True, profit, total_income
        except Exception as e:
            logger.error(f"Ошибка продажи акций: {e}")
            return False, 0, 0
        finally:
            conn.close()
    
    # ========== МЕТОДЫ ДЛЯ НЕДВИЖИМОСТИ ==========
    
    def get_player_properties(self, telegram_id: int) -> List[Dict]:
        """Получить недвижимость игрока"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT pp.* 
                FROM player_properties pp
                JOIN players p ON pp.player_id = p.id
                WHERE p.telegram_id = ?
            """, (telegram_id,))
            
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка получения недвижимости {telegram_id}: {e}")
            return []
        finally:
            conn.close()
    
    def add_property(self, telegram_id: int, property_type: str, price: int) -> bool:
        """Добавить недвижимость игроку"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Получаем ID игрока
            cursor.execute("SELECT id FROM players WHERE telegram_id = ?", (telegram_id,))
            result = cursor.fetchone()
            
            if not result:
                return False
            
            player_id = result[0]
            
            # Добавляем недвижимость
            cursor.execute("""
                INSERT INTO player_properties (player_id, property_type, purchase_price)
                VALUES (?, ?, ?)
            """, (player_id, property_type, price))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления недвижимости: {e}")
            return False
        finally:
            conn.close()
    
    # ========== МЕТОДЫ СТАТИСТИКИ ==========
    
    def get_top_players(self, limit: int = 10) -> List[Dict]:
        """Топ игроков по балансу"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT username, first_name, last_name, balance, level, total_earned
                FROM players 
                ORDER BY balance DESC 
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка получения топа игроков: {e}")
            return []
        finally:
            conn.close()
    
    def get_game_stats(self) -> Dict[str, Any]:
        """Общая статистика игры"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            stats = {}
            
            cursor.execute("SELECT COUNT(*) FROM players")
            stats['total_players'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(balance) FROM players")
            stats['total_money'] = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COUNT(*) FROM player_businesses")
            stats['total_businesses'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM player_properties")
            stats['total_properties'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(quantity) FROM player_stocks")
            stats['total_stocks'] = cursor.fetchone()[0] or 0
            
            return stats
        except Exception as e:
            logger.error(f"Ошибка получения статистики игры: {e}")
            return {}
        finally:
            conn.close()
    
    def get_player_stats(self, telegram_id: int) -> Dict[str, Any]:
        """Подробная статистика игрока"""
        try:
            player = self.get_player(telegram_id)
            if not player:
                return {}
            
            businesses = self.get_player_businesses(telegram_id)
            stocks = self.get_player_stocks(telegram_id)
            properties = self.get_player_properties(telegram_id)
            
            return {
                'player': player,
                'businesses': businesses,
                'stocks': stocks,
                'properties': properties,
                'business_count': len(businesses),
                'stock_count': len(stocks),
                'property_count': len(properties)
            }
        except Exception as e:
            logger.error(f"Ошибка получения статистики игрока {telegram_id}: {e}")
            return {}
    
    # ========== МЕТОДЫ ДЛЯ БИРЖИ ==========
    
    def add_stock_price(self, symbol: str, price: int) -> bool:
        """Добавить запись о цене акции"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO stock_history (stock_symbol, price) VALUES (?, ?)",
                (symbol, price)
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления цены акции {symbol}: {e}")
            return False
        finally:
            conn.close()
    
    def get_latest_stock_price(self, symbol: str) -> Optional[int]:
        """Получить последнюю цену акции"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT price FROM stock_history 
                WHERE stock_symbol = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
            """, (symbol,))
            
            result = cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Ошибка получения цены акции {symbol}: {e}")
            return None
        finally:
            conn.close()
    
    def get_stock_price_history(self, symbol: str, hours: int = 24) -> List[Dict]:
        """Получить историю цен акции"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT price, timestamp 
                FROM stock_history 
                WHERE stock_symbol = ? 
                AND timestamp > datetime('now', ?)
                ORDER BY timestamp ASC
            """, (symbol, f'-{hours} hours'))
            
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка получения истории цен {symbol}: {e}")
            return []
        finally:
            conn.close()
    
    # ========== СЛУЖЕБНЫЕ МЕТОДЫ ==========
    
    def get_player_id(self, telegram_id: int) -> Optional[int]:
        """Получить ID игрока в базе"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id FROM players WHERE telegram_id = ?",
                (telegram_id,)
            )
            result = cursor.fetchone()
            
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Ошибка получения ID игрока {telegram_id}: {e}")
            return None
        finally:
            conn.close()
    
    def add_transaction(self, telegram_id: int, amount: int, trans_type: str, description: str = "") -> bool:
        """Добавить транзакцию для игрока"""
        try:
            player_id = self.get_player_id(telegram_id)
            if not player_id:
                return False
            
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO transactions (player_id, amount, type, description)
                VALUES (?, ?, ?, ?)
            """, (player_id, amount, trans_type, description))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления транзакции: {e}")
            return False
        finally:
            conn.close()
    
    def get_player_transactions(self, telegram_id: int, limit: int = 10) -> List[Dict]:
        """Получить последние транзакции игрока"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT t.* 
                FROM transactions t
                JOIN players p ON t.player_id = p.id
                WHERE p.telegram_id = ?
                ORDER BY t.timestamp DESC
                LIMIT ?
            """, (telegram_id, limit))
            
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка получения транзакций {telegram_id}: {e}")
            return []
        finally:
            conn.close()
    
    def check_database(self) -> Dict[str, Any]:
        """Проверить состояние базы данных"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            result = {
                'status': 'ok',
                'tables': {},
                'size': 0
            }
            
            # Проверяем существование таблиц
            tables = ['players', 'player_businesses', 'player_stocks', 
                     'player_properties', 'transactions', 'stock_history']
            
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                result['tables'][table] = cursor.fetchone()[0]
            
            # Получаем размер файла
            import os
            if os.path.exists(self.db_file):
                result['size'] = os.path.getsize(self.db_file)
            
            return result
        except Exception as e:
            logger.error(f"Ошибка проверки БД: {e}")
            return {'status': 'error', 'error': str(e)}
        finally:
            conn.close()


# Создаем глобальный экземпляр базы данных
db = Database()