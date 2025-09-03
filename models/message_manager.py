import sqlite3
import logging
from datetime import date, datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class MessageManager:
    """مدیریت پیام‌های پاسخ"""
    
    def __init__(self, db_path="messages.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """ایجاد پایگاه داده برای ذخیره پیام‌ها"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # ایجاد جدول messages اگر وجود ندارد
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                content TEXT NOT NULL,
                key_type TEXT DEFAULT 'number',  -- اضافه کردن فیلد نوع کلید
                start_date DATE,
                end_date DATE,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, key)  -- اطمینان از یکتایی کلید برای هر کاربر
            )
        ''')
        
        # ایجاد جدول message_history اگر وجود ندارد
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS message_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message_key TEXT NOT NULL,
                thread_id TEXT NOT NULL,
                user_instagram_id TEXT NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # اضافه کردن فیلد key_type اگر وجود ندارد
        try:
            cursor.execute("ALTER TABLE messages ADD COLUMN key_type TEXT DEFAULT 'number'")
        except sqlite3.OperationalError:
            # فیلد قبلاً اضافه شده است
            pass
        
        conn.commit()
        conn.close()
    
    def add_default_messages(self, user_id: int):
        """افزودن پیام‌های پیش‌فرض برای کاربر"""
        default_messages = {
            "1": {
                "content": "🙏 سلام و وقت بخیر!\n\nبه پیج خوش آمدید. 👇\n\n✅ خدمات ما:\n• طراحی سایت\n• طراحی اپلیکیشن\n• سئو و بهینه‌سازی\n\nبرای اطلاعات بیشتر عدد 2 را ارسال کنید.",
                "type": "number"
            },
            "2": {
                "content": "💰 لیست قیمت خدمات:\n\n• طراحی سایت: 5-15 میلیون تومان\n• طراحی اپلیکیشن: 10-25 میلیون تومان\n• سئو: ماهانه 2-5 میلیون تومان\n\nبرای تماس با پشتیبانی عدد 3 را ارسال کنید.",
                "type": "number"
            },
            "3": {
                "content": "📞 اطلاعات تماس:\n\n• تلفن: 021-12345678\n• موبایل: 09123456789\n• ایمیل: info@example.com\n\nساعات کاری: 9 صبح تا 6 عصر\n\nبرای بازگشت به منوی اصلی عدد 1 را ارسال کنید.",
                "type": "number"
            },
            "default": {
                "content": "⚠️ لطفاً یک عدد بین 1 تا 3 ارسال کنید:\n\n1️⃣ اطلاعات کلی\n2️⃣ لیست قیمت\n3️⃣ تماس با ما",
                "type": "number"
            },
            "سلام": {
                "content": "🙏 سلام عزیز! خوش آمدید.\n\nچگونه می‌توانم به شما کمک کنم؟\n\n1️⃣ اطلاعات خدمات\n2️⃣ قیمت‌ها\n3️⃣ تماس با ما",
                "type": "text"
            },
            "خداحافظ": {
                "content": "👋 خداحافظ عزیز! امیدوارم再次 شما را ببینم.\n\nاگر سوالی دارید، خوشحال می‌شوم کمک کنم.",
                "type": "text"
            },
            "سپاس": {
                "content": "🤗 خواهش می‌کنم! خوشحالم که توانستم کمک کنم.\n\nاگر نیاز به اطلاعات بیشتری دارید، در خدمت شما هستم.",
                "type": "text"
            }
        }
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for key, data in default_messages.items():
            cursor.execute(
                "SELECT id FROM messages WHERE user_id = ? AND key = ?", 
                (user_id, key)
            )
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO messages (user_id, key, content, key_type) VALUES (?, ?, ?, ?)",
                    (user_id, key, data["content"], data["type"])
                )
        
        conn.commit()
        conn.close()
    
    def get_message(self, user_id: int, key: str) -> str:
        """دریافت پیام بر اساس کلید و تاریخ - فقط کلیدهای دقیق"""
        today = date.today()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # فقط کلیدهای دقیق را جستجو کنیم
        cursor.execute('''
            SELECT content FROM messages 
            WHERE user_id = ? AND key = ? AND is_active = TRUE
            AND (start_date IS NULL OR start_date <= ?)
            AND (end_date IS NULL OR end_date >= ?)
            ORDER BY created_at DESC
            LIMIT 1
        ''', (user_id, key, today, today))

        result = cursor.fetchone()
        conn.close()

        if result:
            return result[0]
    
    def get_all_messages(self, user_id: int) -> List[Dict]:
        """دریافت تمام پیام‌های کاربر"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, key, content, key_type, start_date, end_date, is_active, created_at 
            FROM messages 
            WHERE user_id = ?
            ORDER BY key_type, key
        ''', (user_id,))
        
        messages = []
        for row in cursor.fetchall():
            messages.append({
                "id": row[0],
                "key": row[1],
                "content": row[2],
                "key_type": row[3],
                "start_date": row[4],
                "end_date": row[5],
                "is_active": bool(row[6]),
                "created_at": row[7]
            })
        
        conn.close()
        return messages
    
    def update_message(self, message_id: int, user_id: int, key: str, content: str, 
                      key_type: str = "number",
                      start_date: Optional[str] = None, 
                      end_date: Optional[str] = None,
                      is_active: bool = True) -> bool:
        """به‌روزرسانی پیام"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE messages 
                SET key = ?, content = ?, key_type = ?, start_date = ?, end_date = ?, is_active = ?
                WHERE id = ? AND user_id = ?
            ''', (key, content, key_type, start_date, end_date, is_active, message_id, user_id))
            
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except sqlite3.IntegrityError:
            logger.error(f"کلید '{key}' از قبل برای این کاربر وجود دارد")
            return False
        except Exception as e:
            logger.error(f"خطا در به‌روزرسانی پیام: {e}")
            return False
    
    def add_message(self, user_id: int, key: str, content: str, 
                   key_type: str = "number",
                   start_date: Optional[str] = None, 
                   end_date: Optional[str] = None) -> bool:
        """افزودن پیام جدید"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO messages (user_id, key, content, key_type, start_date, end_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, key, content, key_type, start_date, end_date))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            logger.error(f"کلید '{key}' از قبل برای این کاربر وجود دارد")
            return False
        except Exception as e:
            logger.error(f"خطا در افزودن پیام: {e}")
            return False
    
    def delete_message(self, message_id: int, user_id: int) -> bool:
        """حذف پیام"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "DELETE FROM messages WHERE id = ? AND user_id = ?",
                (message_id, user_id)
            )
            
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"خطا در حذف پیام: {e}")
            return False
    
    def log_message_sent(self, user_id: int, message_key: str, thread_id: str, user_instagram_id: str):
        """ثبت تاریخچه ارسال پیام"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO message_history (user_id, message_key, thread_id, user_instagram_id)
                VALUES (?, ?, ?, ?)
            ''', (user_id, message_key, thread_id, user_instagram_id))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"خطا در ثبت تاریخچه پیام: {e}")
    
    def get_message_history(self, user_id: int, limit: int = 50) -> List[Dict]:
        """دریافت تاریخچه پیام‌های ارسال شده"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT mh.id, mh.message_key, mh.thread_id, mh.user_instagram_id, mh.sent_at, m.content, m.key_type
                FROM message_history mh
                LEFT JOIN messages m ON mh.message_key = m.key AND mh.user_id = m.user_id
                WHERE mh.user_id = ?
                ORDER BY mh.sent_at DESC
                LIMIT ?
            ''', (user_id, limit))
            
            history = []
            for row in cursor.fetchall():
                history.append({
                    "id": row[0],
                    "message_key": row[1],
                    "thread_id": row[2],
                    "user_instagram_id": row[3],
                    "sent_at": row[4],
                    "content_preview": row[5][:100] + "..." if row[5] and len(row[5]) > 100 else row[5] if row[5] else "",
                    "key_type": row[6] or "unknown"
                })
            
            conn.close()
            return history
        except Exception as e:
            logger.error(f"خطا در دریافت تاریخچه پیام: {e}")
            return []
    
    def search_messages(self, user_id: int, search_term: str, key_type: Optional[str] = None) -> List[Dict]:
        """جستجو در پیام‌های کاربر"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if key_type:
                cursor.execute('''
                    SELECT id, key, content, key_type, is_active 
                    FROM messages 
                    WHERE user_id = ? AND key_type = ? 
                    AND (key LIKE ? OR content LIKE ?)
                    ORDER BY key
                ''', (user_id, key_type, f'%{search_term}%', f'%{search_term}%'))
            else:
                cursor.execute('''
                    SELECT id, key, content, key_type, is_active 
                    FROM messages 
                    WHERE user_id = ? 
                    AND (key LIKE ? OR content LIKE ?)
                    ORDER BY key_type, key
                ''', (user_id, f'%{search_term}%', f'%{search_term}%'))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "id": row[0],
                    "key": row[1],
                    "content": row[2],
                    "key_type": row[3],
                    "is_active": bool(row[4])
                })
            
            conn.close()
            return results
        except Exception as e:
            logger.error(f"خطا در جستجوی پیام‌ها: {e}")
            return []
    
    def get_message_by_id(self, message_id: int, user_id: int) -> Optional[Dict]:
        """دریافت پیام بر اساس ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, key, content, key_type, start_date, end_date, is_active, created_at 
                FROM messages 
                WHERE id = ? AND user_id = ?
            ''', (message_id, user_id))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    "id": row[0],
                    "key": row[1],
                    "content": row[2],
                    "key_type": row[3],
                    "start_date": row[4],
                    "end_date": row[5],
                    "is_active": bool(row[6]),
                    "created_at": row[7]
                }
            return None
        except Exception as e:
            logger.error(f"خطا در دریافت پیام: {e}")
            return None