import sqlite3
import os

class Database:
    def __init__(self, db_file="tycoon.db"):
        self.db_file = db_file
        self.init_db()
    
    def init_db(self):
        """Создание таблиц"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Игроки
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                username TEXT,
                balance INTEGER DEFAULT 1000,
                level INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        print("✅ База данных инициализирована")
    
    def get_player(self, telegram_id):
        """Получить игрока"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM players WHERE telegram_id = ?", (telegram_id,))
        player = cursor.fetchone()
        conn.close()
        return player
    
    def create_player(self, telegram_id, username):
        """Создать нового игрока"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO players (telegram_id, username) VALUES (?, ?)",
                (telegram_id, username)
            )
            conn.commit()
            return True
        except:
            return False
        finally:
            conn.close()

# Глобальная база данных
db = Database()