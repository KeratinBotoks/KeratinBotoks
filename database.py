import sqlite3
import json
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import config

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_file: str = None):
        if db_file is None:
            db_file = config.DB_FILE
        
        self.db_file = db_file
        
        # Создаем директорию для базы данных если её нет
        os.makedirs(os.path.dirname(db_file), exist_ok=True)
        
        logger.info(f"📁 Инициализация базы данных: {db_file}")
        self.init_db()
    
    def get_connection(self):
        """Создать соединение с базой данных"""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")  # Для лучшей производительности
        return conn
    
    def init_db(self):
        """Инициализация всех таблиц"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                    is_active BOOLEAN DEFAULT TRUE,
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
            
            # Создаем индексы для ускорения запросов
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_players_telegram_id ON players(telegram_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_player_businesses_player_id ON player_businesses(player_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_player_stocks_player_id ON player_stocks(player_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_history_symbol_time ON stock_history(stock_symbol, timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_player_time ON transactions(player_id, timestamp)")
            
            conn.commit()
            logger.info("✅ Таблицы базы данных созданы/проверены")
            
            # Создаем триггер для обновления updated_at
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS update_players_timestamp 
                AFTER UPDATE ON players
                FOR EACH ROW
                BEGIN
                    UPDATE players SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
                END
            """)
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации базы данных: {e}")
            raise
        finally:
            conn.close()
    
    # ========== ИГРОКИ ==========
    
    def get_player(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Получить игрока"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM players WHERE telegram_id = ?", (telegram_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    
    def create_player(self, telegram_id: int, username: str = None) -> bool:
        """Создать нового игрока"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO players (telegram_id, username) VALUES (?, ?)",
                (telegram_id, username or f"Игрок_{telegram_id}")
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"❌ Ошибка создания игрока {telegram_id}: {e}")
            return False
        finally:
            conn.close()
    
    def update_player(self, telegram_id: int, **kwargs) -> bool:
        """Обновить данные игрока"""
        if not kwargs:
            return False
        
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
            values = tuple(kwargs.values()) + (telegram_id,)
            
            cursor.execute(
                f"UPDATE players SET {set_clause} WHERE telegram_id = ?",
                values
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"❌ Ошибка обновления игрока {telegram_id}: {e}")
            return False
        finally:
            conn.close()
    
    # ========== БИЗНЕСЫ ==========
    
    def get_player_businesses(self, player_id: int) -> List[Dict[str, Any]]:
        """Получить бизнесы игрока"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM player_businesses WHERE player_id = ? AND is_active = TRUE",
                (player_id,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
    
    def add_business(self, player_id: int, business_type: str) -> bool:
        """Добавить бизнес игроку"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO player_businesses (player_id, business_type, level)
                   VALUES (?, ?, 1)""",
                (player_id, business_type)
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка добавления бизнеса {business_type} игроку {player_id}: {e}")
            return False
        finally:
            conn.close()
    
    # ========== СТАТИСТИКА ==========
    
    def get_game_stats(self) -> Dict[str, Any]:
        """Общая статистика игры"""
        stats = {}
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) as count FROM players")
            stats['total_players'] = cursor.fetchone()['count'] or 0
            
            cursor.execute("SELECT SUM(balance) as total FROM players")
            stats['total_money'] = cursor.fetchone()['total'] or 0
            
            cursor.execute("SELECT COUNT(*) as count FROM player_businesses WHERE is_active = TRUE")
            stats['total_businesses'] = cursor.fetchone()['count'] or 0
            
            cursor.execute("SELECT SUM(quantity) as total FROM player_stocks WHERE quantity > 0")
            stats['total_stocks'] = cursor.fetchone()['total'] or 0
            
            cursor.execute("SELECT COUNT(*) as count FROM transactions")
            stats['total_transactions'] = cursor.fetchone()['count'] or 0
            
            # Самый богатый игрок
            cursor.execute("""
                SELECT username, balance 
                FROM players 
                ORDER BY balance DESC 
                LIMIT 1
            """)
            richest = cursor.fetchone()
            if richest and richest['username']:
                stats['richest_player'] = richest['username']
                stats['richest_balance'] = richest['balance']
            else:
                stats['richest_player'] = "Нет данных"
                stats['richest_balance'] = 0
            
            # Последний активный игрок
            cursor.execute("""
                SELECT username, updated_at 
                FROM players 
                ORDER BY updated_at DESC 
                LIMIT 1
            """)
            last_active = cursor.fetchone()
            if last_active:
                stats['last_active'] = last_active['updated_at']
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
        finally:
            conn.close()
        
        return stats
    
    def get_top_players(self, limit: int = 10) -> List[tuple]:
        """Топ игроков по балансу"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT username, balance, level, total_earned 
                FROM players 
                ORDER BY balance DESC 
                LIMIT ?
            """, (limit,))
            return cursor.fetchall()
        finally:
            conn.close()
    
    # ========== УТИЛИТЫ ==========
    
    def backup_database(self, backup_path: str = None):
        """Создать резервную копию базы данных"""
        if backup_path is None:
            backup_path = f"{self.db_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            import shutil
            shutil.copy2(self.db_file, backup_path)
            logger.info(f"✅ Резервная копия создана: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка создания резервной копии: {e}")
            return False
    
    def cleanup_old_data(self, days: int = 30):
        """Очистка старых данных"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Удаляем старые транзакции
            cursor.execute(
                "DELETE FROM transactions WHERE timestamp < ?",
                (cutoff_date,)
            )
            
            # Удаляем старую историю биржи (оставляем последние 1000 записей на символ)
            for symbol in config.STOCKS.keys():
                cursor.execute("""
                    DELETE FROM stock_history 
                    WHERE stock_symbol = ? AND id NOT IN (
                        SELECT id FROM stock_history 
                        WHERE stock_symbol = ? 
                        ORDER BY timestamp DESC 
                        LIMIT 1000
                    )
                """, (symbol, symbol))
            
            conn.commit()
            logger.info(f"✅ Очистка данных старше {days} дней выполнена")
        except Exception as e:
            logger.error(f"❌ Ошибка очистки данных: {e}")
        finally:
            conn.close()
    
    def get_database_size(self) -> str:
        """Получить размер базы данных"""
        try:
            size_bytes = os.path.getsize(self.db_file)
            if size_bytes < 1024:
                return f"{size_bytes} Б"
            elif size_bytes < 1024 * 1024:
                return f"{size_bytes / 1024:.2f} КБ"
            elif size_bytes < 1024 * 1024 * 1024:
                return f"{size_bytes / (1024 * 1024):.2f} МБ"
            else:
                return f"{size_bytes / (1024 * 1024 * 1024):.2f} ГБ"
        except:
            return "Неизвестно"

# Глобальный экземпляр базы данных
db = Database()