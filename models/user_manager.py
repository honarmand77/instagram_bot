from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class UserManager:
    """مدیریت کاربران سیستم"""
    
    def __init__(self, db_path="users.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """ایجاد پایگاه داده کاربران"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS instagram_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                instagram_username TEXT NOT NULL,
                instagram_password TEXT NOT NULL,
                session_data TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        
        # ایجاد کاربر ادمین پیش‌فرض اگر وجود ندارد
        cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            password_hash = generate_password_hash('admin123')
            cursor.execute(
                "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)",
                ('admin', password_hash, True)
            )
        
        conn.commit()
        conn.close()
    
    def create_user(self, username: str, password: str, is_admin: bool = False) -> bool:
        """ایجاد کاربر جدید"""
        try:
            password_hash = generate_password_hash(password)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)",
                (username, password_hash, is_admin)
            )
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False  # کاربر از قبل وجود دارد
        except Exception as e:
            logger.error(f"خطا در ایجاد کاربر: {e}")
            return False
    
    def verify_user(self, username: str, password: str) -> Optional[Dict]:
        """احراز هویت کاربر"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id, username, password_hash, is_admin FROM users WHERE username = ?",
                (username,)
            )
            
            user = cursor.fetchone()
            conn.close()
            
            if user and check_password_hash(user[2], password):
                return {
                    "id": user[0],
                    "username": user[1],
                    "is_admin": bool(user[3])
                }
            return None
        except Exception as e:
            logger.error(f"خطا در احراز هویت کاربر: {e}")
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """دریافت کاربر بر اساس ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id, username, is_admin FROM users WHERE id = ?",
                (user_id,)
            )
            
            user = cursor.fetchone()
            conn.close()
            
            if user:
                return {
                    "id": user[0],
                    "username": user[1],
                    "is_admin": bool(user[2])
                }
            return None
        except Exception as e:
            logger.error(f"خطا در دریافت کاربر: {e}")
            return None
    
    def get_all_users(self) -> List[Dict]:
        """دریافت تمام کاربران"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id, username, is_admin, created_at FROM users ORDER BY created_at DESC"
            )
            
            users = []
            for row in cursor.fetchall():
                users.append({
                    "id": row[0],
                    "username": row[1],
                    "is_admin": bool(row[2]),
                    "created_at": row[3]
                })
            
            conn.close()
            return users
        except Exception as e:
            logger.error(f"خطا در دریافت کاربران: {e}")
            return []
    
    def delete_user(self, user_id: int) -> bool:
        """حذف کاربر"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # ابتدا حساب‌های اینستاگرام کاربر را حذف می‌کنیم
            cursor.execute(
                "DELETE FROM instagram_accounts WHERE user_id = ?",
                (user_id,)
            )
            
            # سپس کاربر را حذف می‌کنیم
            cursor.execute(
                "DELETE FROM users WHERE id = ?",
                (user_id,)
            )
            
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"خطا در حذف کاربر: {e}")
            return False
    
    def add_instagram_account(self, user_id: int, instagram_username: str, instagram_password: str) -> bool:
        """افزودن حساب اینستاگرام"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO instagram_accounts (user_id, instagram_username, instagram_password) VALUES (?, ?, ?)",
                (user_id, instagram_username, instagram_password)
            )
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"خطا در افزودن حساب اینستاگرام: {e}")
            return False
    
    def get_user_accounts(self, user_id: int) -> List[Dict]:
        """دریافت حساب‌های اینستاگرام کاربر"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, instagram_username, is_active, last_login, created_at 
                FROM instagram_accounts 
                WHERE user_id = ?
                ORDER BY created_at DESC
            ''', (user_id,))
            
            accounts = []
            for row in cursor.fetchall():
                accounts.append({
                    "id": row[0],
                    "instagram_username": row[1],
                    "is_active": bool(row[2]),
                    "last_login": row[3],
                    "created_at": row[4]
                })
            
            conn.close()
            return accounts
        except Exception as e:
            logger.error(f"خطا در دریافت حساب‌های کاربر: {e}")
            return []
    
    def get_account_credentials(self, account_id: int, user_id: int) -> Optional[Dict]:
        """دریافت اطلاعات حساب اینستاگرام"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT instagram_username, instagram_password, session_data 
                FROM instagram_accounts 
                WHERE id = ? AND user_id = ?
            ''', (account_id, user_id))
            
            account = cursor.fetchone()
            conn.close()
            
            if account:
                return {
                    "instagram_username": account[0],
                    "instagram_password": account[1],
                    "session_data": account[2]
                }
            return None
        except Exception as e:
            logger.error(f"خطا در دریافت اطلاعات حساب: {e}")
            return None
    
    def update_account_session(self, account_id: int, session_data: str) -> bool:
        """به‌روزرسانی session حساب"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "UPDATE instagram_accounts SET session_data = ?, last_login = ? WHERE id = ?",
                (session_data, datetime.now(), account_id)
            )
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"خطا در به‌روزرسانی session: {e}")
            return False
    
    def update_account_status(self, account_id: int, is_active: bool) -> bool:
        """به‌روزرسانی وضعیت حساب"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "UPDATE instagram_accounts SET is_active = ? WHERE id = ?",
                (is_active, account_id)
            )
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"خطا در به‌روزرسانی وضعیت حساب: {e}")
            return False
    
    def delete_instagram_account(self, account_id: int, user_id: int) -> bool:
        """حذف حساب اینستاگرام"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "DELETE FROM instagram_accounts WHERE id = ? AND user_id = ?",
                (account_id, user_id)
            )
            
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"خطا در حذف حساب اینستاگرام: {e}")
            return False
    
    def get_account_id(self, user_id: int, instagram_username: str) -> int:
        """دریافت ID حساب از دیتابیس"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id FROM instagram_accounts WHERE user_id = ? AND instagram_username = ?",
                (user_id, instagram_username)
            )
            
            account = cursor.fetchone()
            conn.close()
            
            if account:
                return account[0]
            return -1
        except Exception as e:
            logger.error(f"خطا در دریافت ID حساب: {e}")
            return -1