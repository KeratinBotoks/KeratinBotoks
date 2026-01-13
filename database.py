import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

class Database:
    def __init__(self, db_file: str = None):
        if db_file is None:
            from config import DB_FILE
            db_file = DB_FILE
        
        # Создаем директорию для базы данных если её нет
        os.makedirs(os.path.dirname(db_file), exist_ok=True)
        
        self.db_file = db_file
        self.init_db()
    
    def init_db(self):
        """Инициализация всех таблиц"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Включаем поддержку внешних ключей
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Игроки
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
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
        
        # Бизнесы игроков
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_businesses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                business_type TEXT NOT NULL,
                level INTEGER DEFAULT 1,
                last_profit TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_profit BIGINT DEFAULT 0,
                FOREIGN KEY (player_id) REFERENCES players (id) ON DELETE CASCADE
            )
        """)
        
        # Недвижимость игроков
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
        
        # Акции игроков
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
        
        # История биржи
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_symbol TEXT NOT NULL,
                price INTEGER NOT NULL,
                volume INTEGER DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Транзакции
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                amount BIGINT NOT NULL,
                type TEXT NOT NULL,
                description TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (player_id) REFERENCES players (id)
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
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        # Индексы для ускорения запросов
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_players_telegram_id ON players(telegram_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_player_businesses_player_id ON player_businesses(player_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_player_stocks_player_id ON player_stocks(player_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_history_symbol ON stock_history(stock_symbol)")
        
        conn.commit()
        conn.close()
        print(f"✅ База данных инициализирована: {self.db_file}")
    
    # ========== ИГРОКИ ==========
    
    def get_player(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Получить игрока"""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM players WHERE telegram_id = ?", (telegram_id,))
        row = cursor.fetchone()
        
        conn.close()
        return dict(row) if row else None
    
    def create_player(self, telegram_id: int, username: str) -> bool:
        """Создать нового игрока"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO players (telegram_id, username) VALUES (?, ?)",
                (telegram_id, username or "Игрок")
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Игрок уже существует
            return True
        except Exception as e:
            print(f"❌ Ошибка создания игрока: {e}")
            return False
        finally:
            conn.close()
    
    def update_player(self, telegram_id: int, **kwargs) -> bool:
        """Обновить данные игрока"""
        if not kwargs:
            return False
        
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
            values = tuple(kwargs.values()) + (telegram_id,)
            
            cursor.execute(
                f"UPDATE players SET {set_clause} WHERE telegram_id = ?",
                values
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ Ошибка обновления игрока: {e}")
            return False
        finally:
            conn.close()
    
    def get_player_id(self, telegram_id: int) -> Optional[int]:
        """Получить ID игрока"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM players WHERE telegram_id = ?", (telegram_id,))
        row = cursor.fetchone()
        
        conn.close()
        return row[0] if row else None
    
    def add_transaction(self, player_id: int, amount: int, trans_type: str, description: str = "") -> bool:
        """Добавить транзакцию"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """INSERT INTO transactions (player_id, amount, type, description)
                   VALUES (?, ?, ?, ?)""",
                (player_id, amount, trans_type, description)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка добавления транзакции: {e}")
            return False
        finally:
            conn.close()
    
    # ========== БИЗНЕСЫ ==========
    
    def get_player_businesses(self, player_id: int) -> List[Dict[str, Any]]:
        """Получить бизнесы игрока"""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM player_businesses WHERE player_id = ?",
            (player_id,)
        )
        rows = cursor.fetchall()
        
        conn.close()
        return [dict(row) for row in rows]
    
    def add_business(self, player_id: int, business_type: str) -> bool:
        """Добавить бизнес игроку"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """INSERT INTO player_businesses (player_id, business_type, level)
                   VALUES (?, ?, 1)""",
                (player_id, business_type)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка добавления бизнеса: {e}")
            return False
        finally:
            conn.close()
    
    def update_business(self, business_id: int, **kwargs) -> bool:
        """Обновить бизнес"""
        if not kwargs:
            return False
        
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
            values = tuple(kwargs.values()) + (business_id,)
            
            cursor.execute(
                f"UPDATE player_businesses SET {set_clause} WHERE id = ?",
                values
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ Ошибка обновления бизнеса: {e}")
            return False
        finally:
            conn.close()
    
    def update_business_profit_time(self, business_id: int) -> bool:
        """Обновить время последней прибыли бизнеса"""
        return self.update_business(business_id, last_profit=datetime.now().isoformat())
    
    # ========== АКЦИИ/БИРЖА ==========
    
    def get_player_stocks(self, player_id: int) -> List[Dict[str, Any]]:
        """Получить акции игрока"""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM player_stocks WHERE player_id = ? AND quantity > 0",
            (player_id,)
        )
        rows = cursor.fetchall()
        
        conn.close()
        return [dict(row) for row in rows]
    
    def buy_stock(self, player_id: int, symbol: str, quantity: int, price: int) -> bool:
        """Купить акции"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            # Проверяем есть ли уже такие акции
            cursor.execute(
                "SELECT id, quantity, average_price, total_invested FROM player_stocks WHERE player_id = ? AND stock_symbol = ?",
                (player_id, symbol)
            )
            existing = cursor.fetchone()
            
            if existing:
                # Обновляем существующие
                stock_id, old_quantity, old_avg_price, old_invested = existing
                total_quantity = old_quantity + quantity
                total_invested = old_invested + (quantity * price)
                new_avg_price = total_invested // total_quantity
                
                cursor.execute(
                    """UPDATE player_stocks 
                       SET quantity = ?, average_price = ?, total_invested = ?
                       WHERE id = ?""",
                    (total_quantity, new_avg_price, total_invested, stock_id)
                )
            else:
                # Добавляем новые
                cursor.execute(
                    """INSERT INTO player_stocks (player_id, stock_symbol, quantity, average_price, total_invested)
                       VALUES (?, ?, ?, ?, ?)""",
                    (player_id, symbol, quantity, price, quantity * price)
                )
            
            # Добавляем в историю
            cursor.execute(
                "INSERT INTO stock_history (stock_symbol, price, volume) VALUES (?, ?, ?)",
                (symbol, price, quantity)
            )
            
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка покупки акций: {e}")
            return False
        finally:
            conn.close()
    
    def sell_stock(self, player_id: int, symbol: str, quantity: int, price: int) -> bool:
        """Продать акции"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT id, quantity FROM player_stocks WHERE player_id = ? AND stock_symbol = ?",
                (player_id, symbol)
            )
            result = cursor.fetchone()
            
            if not result or result[1] < quantity:
                return False
            
            stock_id, current_quantity = result
            new_quantity = current_quantity - quantity
            
            if new_quantity == 0:
                cursor.execute(
                    "DELETE FROM player_stocks WHERE id = ?",
                    (stock_id,)
                )
            else:
                cursor.execute(
                    "UPDATE player_stocks SET quantity = ? WHERE id = ?",
                    (new_quantity, stock_id)
                )
            
            # Добавляем в историю
            cursor.execute(
                "INSERT INTO stock_history (stock_symbol, price, volume) VALUES (?, ?, ?)",
                (symbol, price, -quantity)
            )
            
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка продажи акций: {e}")
            return False
        finally:
            conn.close()
    
    def get_stock_price(self, symbol: str) -> Optional[int]:
        """Получить текущую цену акции"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT price FROM stock_history WHERE stock_symbol = ? ORDER BY timestamp DESC LIMIT 1",
            (symbol,)
        )
        row = cursor.fetchone()
        
        conn.close()
        return row[0] if row else None
    
    def get_stock_history(self, symbol: str, limit: int = 10) -> List[tuple]:
        """Получить историю цен акции"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT price, timestamp FROM stock_history WHERE stock_symbol = ? ORDER BY timestamp DESC LIMIT ?",
            (symbol, limit)
        )
        rows = cursor.fetchall()
        
        conn.close()
        return rows
    
    # ========== СТАТИСТИКА ==========
    
    def get_top_players(self, limit: int = 10) -> List[tuple]:
        """Топ игроков по балансу"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute(
            """SELECT username, balance, level, total_earned 
               FROM players 
               ORDER BY balance DESC 
               LIMIT ?""",
            (limit,)
        )
        rows = cursor.fetchall()
        
        conn.close()
        return rows
    
    def get_game_stats(self) -> Dict[str, Any]:
        """Общая статистика игры"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        stats = {}
        
        try:
            cursor.execute("SELECT COUNT(*) FROM players")
            stats['total_players'] = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT SUM(balance) FROM players")
            stats['total_money'] = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COUNT(*) FROM player_businesses")
            stats['total_businesses'] = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COUNT(*) FROM player_properties")
            stats['total_properties'] = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT SUM(quantity) FROM player_stocks")
            stats['total_stocks'] = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COUNT(*) FROM transactions")
            stats['total_transactions'] = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT username, balance FROM players ORDER BY balance DESC LIMIT 1")
            richest = cursor.fetchone()
            if richest:
                stats['richest'] = richest[0] or "Нет игроков"
                stats['richest_balance'] = richest[1] or 0
            else:
                stats['richest'] = "Нет игроков"
                stats['richest_balance'] = 0
                
        except Exception as e:
            print(f"❌ Ошибка получения статистики: {e}")
            stats = {
                'total_players': 0,
                'total_money': 0,
                'total_businesses': 0,
                'total_properties': 0,
                'total_stocks': 0,
                'total_transactions': 0,
                'richest': "Нет данных",
                'richest_balance': 0
            }
        
        conn.close()
        return stats
    
    def close_all_connections(self):
        """Закрыть все соединения (для корректного завершения)"""
        pass  # SQLite автоматически закрывает соединения

# Создаем глобальный экземпляр базы данных
db = Database()