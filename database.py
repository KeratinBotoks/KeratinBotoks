import sqlite3
import json
from datetime import datetime, timedelta
import config

class Database:
    def __init__(self, db_file: str = None):
        self.db_file = db_file or config.DB_FILE
        self.init_db()
    
    def init_db(self):
        """Инициализация всех таблиц"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
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
                FOREIGN KEY (player_id) REFERENCES players (id) ON DELETE CASCADE
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
                effects TEXT,  # JSON
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        conn.commit()
        conn.close()
    
    # ========== ИГРОКИ ==========
    
    def get_player(self, telegram_id: int):
        """Получить игрока"""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM players WHERE telegram_id = ?", (telegram_id,))
        row = cursor.fetchone()
        
        conn.close()
        return dict(row) if row else None
    
    def create_player(self, telegram_id: int, username: str):
        """Создать нового игрока"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO players (telegram_id, username, balance, energy, health) VALUES (?, ?, ?, ?, ?)",
            (telegram_id, username, 0, 100, 100)
        )
        conn.commit()
        conn.close()
        return True
    
    def get_player_id(self, telegram_id: int):
        """Получить ID игрока в базе"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM players WHERE telegram_id = ?", (telegram_id,))
        result = cursor.fetchone()
        
        conn.close()
        return result[0] if result else None
    
    def update_player(self, telegram_id: int, **kwargs):
        """Обновить данные игрока"""
        if not kwargs:
            return False
        
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = tuple(kwargs.values()) + (telegram_id,)
        
        cursor.execute(
            f"UPDATE players SET {set_clause} WHERE telegram_id = ?",
            values
        )
        conn.commit()
        conn.close()
        return True
    
    def update_player_by_id(self, player_id: int, **kwargs):
        """Обновить данные игрока по ID"""
        if not kwargs:
            return False
        
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = tuple(kwargs.values()) + (player_id,)
        
        cursor.execute(
            f"UPDATE players SET {set_clause} WHERE id = ?",
            values
        )
        conn.commit()
        conn.close()
        return True
    
    def add_transaction(self, player_id: int, amount: int, trans_type: str, description: str = ""):
        """Добавить транзакцию"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute(
            """INSERT INTO transactions (player_id, amount, type, description)
               VALUES (?, ?, ?, ?)""",
            (player_id, amount, trans_type, description)
        )
        conn.commit()
        conn.close()
    
    # ========== БИЗНЕСЫ ==========
    
    def get_player_businesses(self, player_id: int):
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
    
    def add_business(self, player_id: int, business_type: str):
        """Добавить бизнес игроку"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute(
            """INSERT INTO player_businesses (player_id, business_type, level)
               VALUES (?, ?, 1)""",
            (player_id, business_type)
        )
        conn.commit()
        conn.close()
        return True
    
    def upgrade_business(self, business_id: int, new_level: int):
        """Улучшить бизнес"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE player_businesses SET level = ? WHERE id = ?",
            (new_level, business_id)
        )
        conn.commit()
        conn.close()
        return True
    
    # ========== АКЦИИ/БИРЖА ==========
    
    def get_player_stocks(self, player_id: int):
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
    
    def buy_stock(self, player_id: int, symbol: str, quantity: int, price: int):
        """Купить акции"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Проверяем есть ли уже такие акции
        cursor.execute(
            "SELECT * FROM player_stocks WHERE player_id = ? AND stock_symbol = ?",
            (player_id, symbol)
        )
        existing = cursor.fetchone()
        
        if existing:
            # Обновляем существующие
            total_quantity = existing[3] + quantity
            total_invested = existing[5] + (quantity * price)
            new_avg_price = total_invested // total_quantity
            
            cursor.execute(
                """UPDATE player_stocks 
                   SET quantity = ?, average_price = ?, total_invested = ?
                   WHERE player_id = ? AND stock_symbol = ?""",
                (total_quantity, new_avg_price, total_invested, player_id, symbol)
            )
        else:
            # Добавляем новые
            cursor.execute(
                """INSERT INTO player_stocks (player_id, stock_symbol, quantity, average_price, total_invested)
                   VALUES (?, ?, ?, ?, ?)""",
                (player_id, symbol, quantity, price, quantity * price)
            )
        
        conn.commit()
        conn.close()
    
    def sell_stock(self, player_id: int, symbol: str, quantity: int, price: int):
        """Продать акции"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT quantity FROM player_stocks WHERE player_id = ? AND stock_symbol = ?",
            (player_id, symbol)
        )
        result = cursor.fetchone()
        
        if not result or result[0] < quantity:
            conn.close()
            return False
        
        new_quantity = result[0] - quantity
        
        if new_quantity == 0:
            cursor.execute(
                "DELETE FROM player_stocks WHERE player_id = ? AND stock_symbol = ?",
                (player_id, symbol)
            )
        else:
            cursor.execute(
                "UPDATE player_stocks SET quantity = ? WHERE player_id = ? AND stock_symbol = ?",
                (new_quantity, player_id, symbol)
            )
        
        conn.commit()
        conn.close()
        return True
    
    # ========== СТАТИСТИКА ==========
    
    def get_top_players(self, limit: int = 10):
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
    
    def get_game_stats(self):
        """Общая статистика игры"""
        conn = sqlite3.connect(self.db_file)
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
        
        conn.close()
        return stats

# Глобальный экземпляр базы данных
db = Database()