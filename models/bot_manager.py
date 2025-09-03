import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class BotManager:
    """مدیریت وضعیت ربات‌ها"""
    
    def __init__(self, db_path="bot_status.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """ایجاد پایگاه داده وضعیت ربات‌ها"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'stopped',
                last_activity TIMESTAMP,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def update_bot_status(self, account_id: int, user_id: int, status: str, error_message: str = None):
        """به‌روزرسانی وضعیت ربات"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # بررسی وجود رکورد
            cursor.execute(
                "SELECT id FROM bot_status WHERE account_id = ? AND user_id = ?",
                (account_id, user_id)
            )
            
            if cursor.fetchone():
                # به‌روزرسانی رکورد موجود
                cursor.execute('''
                    UPDATE bot_status 
                    SET status = ?, error_message = ?, updated_at = ?, last_activity = ?
                    WHERE account_id = ? AND user_id = ?
                ''', (status, error_message, datetime.now(), datetime.now(), account_id, user_id))
            else:
                # ایجاد رکورد جدید
                cursor.execute('''
                    INSERT INTO bot_status (account_id, user_id, status, error_message, last_activity)
                    VALUES (?, ?, ?, ?, ?)
                ''', (account_id, user_id, status, error_message, datetime.now()))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"خطا در به‌روزرسانی وضعیت ربات: {e}")
    
    def get_bot_status(self, account_id: int, user_id: int) -> Dict:
        """دریافت وضعیت ربات"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT status, error_message, last_activity, updated_at 
                FROM bot_status 
                WHERE account_id = ? AND user_id = ?
            ''', (account_id, user_id))
            
            status = cursor.fetchone()
            conn.close()
            
            if status:
                return {
                    "status": status[0],
                    "error_message": status[1],
                    "last_activity": status[2],
                    "updated_at": status[3]
                }
            return {
                "status": "stopped",
                "error_message": None,
                "last_activity": None,
                "updated_at": None
            }
        except Exception as e:
            logger.error(f"خطا در دریافت وضعیت ربات: {e}")
            return {
                "status": "error",
                "error_message": str(e),
                "last_activity": None,
                "updated_at": None
            }
    
    def get_all_bot_statuses(self, user_id: int) -> List[Dict]:
        """دریافت وضعیت تمام ربات‌های کاربر"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT bs.account_id, ia.instagram_username, bs.status, bs.error_message, bs.last_activity
                FROM bot_status bs
                JOIN instagram_accounts ia ON bs.account_id = ia.id
                WHERE bs.user_id = ?
                ORDER BY bs.updated_at DESC
            ''', (user_id,))
            
            statuses = []
            for row in cursor.fetchall():
                statuses.append({
                    "account_id": row[0],
                    "instagram_username": row[1],
                    "status": row[2],
                    "error_message": row[3],
                    "last_activity": row[4]
                })
            
            conn.close()
            return statuses
        except Exception as e:
            logger.error(f"خطا در دریافت وضعیت ربات‌ها: {e}")
            return []