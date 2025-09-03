import time
import logging
import threading
import random
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from datetime import datetime

logger = logging.getLogger(__name__)

class BaseBot(ABC):
    """کلاس پایه برای تمام ربات‌ها با الگوهای زمانی هوشمند"""
    
    def __init__(self):
        self.running = False
        self.stop_event = threading.Event()
        
        # تنظیمات هوشمند زمان‌بندی
        self.sleep_duration = 60  # زمان خواب اولیه
        self.max_sleep_duration = 600  # حداکثر زمان خواب (10 دقیقه)
        self.min_sleep_duration = 30  # حداقل زمان خواب (30 ثانیه)
        self.consecutive_inactive_cycles = 0
        self.max_consecutive_inactive = 8  # چرخه‌های غیرفعال قبل از بازنشانی
        self.last_reset_time = time.time()
        self.last_activity_check = 0
        
        # الگوهای زمانی انسانی
        self.activity_patterns = [
            # صبح (8-12): فعالیت بالا
            {"start_hour": 8, "end_hour": 12, "base_interval": 45, "variation": 30},
            # ظهر (12-14): فعالیت متوسط
            {"start_hour": 12, "end_hour": 14, "base_interval": 90, "variation": 45},
            # بعدازظهر (14-18): فعالیت بالا
            {"start_hour": 14, "end_hour": 18, "base_interval": 60, "variation": 40},
            # عصر (18-22): فعالیت بسیار بالا
            {"start_hour": 18, "end_hour": 22, "base_interval": 40, "variation": 25},
            # شب (22-8): فعالیت بسیار کم
            {"start_hour": 22, "end_hour": 8, "base_interval": 300, "variation": 120},
        ]
        
    @abstractmethod
    def is_logged_in(self) -> bool:
        """بررسی آیا کاربر وارد شده است"""
        pass
        
    @abstractmethod
    def check_new_messages(self) -> bool:
        """بررسی وجود پیام جدید و پردازش آن"""
        pass
        
    @abstractmethod
    def login(self) -> bool:
        """ورود به سیستم"""
        pass
        
    def get_current_activity_pattern(self) -> Dict[str, int]:
        """دریافت الگوی فعالیت متناسب با ساعت فعلی"""
        current_hour = datetime.now().hour
        
        for pattern in self.activity_patterns:
            if pattern["start_hour"] <= current_hour < pattern["end_hour"]:
                return pattern
        
        # پیش‌فرض برای موارد خارج از محدوده
        return {"base_interval": 120, "variation": 60}
    
    def calculate_smart_interval(self, has_activity: bool) -> int:
        """محاسبه هوشمند فاصله زمانی بر اساس فعالیت و الگو"""
        current_pattern = self.get_current_activity_pattern()
        
        if has_activity:
            # فعالیت وجود دارد - فاصله کوتاه‌تر
            base = current_pattern["base_interval"] * 0.6
            variation = current_pattern["variation"] * 0.6
        else:
            # فعالیت وجود ندارد - فاصله طولانی‌تر
            base = current_pattern["base_interval"] * 1.2
            variation = current_pattern["variation"] * 1.2
        
        # اضافه کردن تغییرات تصادفی
        interval = random.uniform(base - variation/2, base + variation/2)
        return max(self.min_sleep_duration, min(self.max_sleep_duration, int(interval)))
    
    def should_reset_sleep(self) -> bool:
        """بررسی是否需要 reset کردن زمان خواب"""
        if self.sleep_duration >= self.max_sleep_duration:
            return True
            
        if self.consecutive_inactive_cycles >= self.max_consecutive_inactive:
            return True
            
        if time.time() - self.last_reset_time > 7200:  # بازنشانی هر 2 ساعت
            return True
            
        return False
    
    def reset_sleep_cycle(self):
        """Reset کردن چرخه خواب به حالت اولیه"""
        old_sleep_duration = self.sleep_duration
        self.sleep_duration = self.min_sleep_duration
        self.consecutive_inactive_cycles = 0
        self.last_reset_time = time.time()
        logger.info(f"چرخه خواب reset شد: {old_sleep_duration} → {self.sleep_duration} ثانیه")
    
    def adaptive_sleep(self, has_activity: bool):
        """زمان خواب هوشمند بر اساس فعالیت و الگوهای زمانی"""
        if has_activity:
            # کاهش زمان خواب هنگام فعالیت
            self.sleep_duration = self.calculate_smart_interval(True)
            self.consecutive_inactive_cycles = 0
            logger.info(f"فعالیت تشخیص داده شد، زمان خواب: {self.sleep_duration} ثانیه")
        else:
            # افزایش زمان خواب هنگام عدم فعالیت
            self.sleep_duration = self.calculate_smart_interval(False)
            self.consecutive_inactive_cycles += 1
            logger.info(f"فعالیتی یافت نشد، زمان خواب: {self.sleep_duration} ثانیه (چرخه {self.consecutive_inactive_cycles}/{self.max_consecutive_inactive})")
        
        if self.should_reset_sleep():
            self.reset_sleep_cycle()
    
    def smart_sleep(self, duration: int):
        """خواب هوشمند با قابلیت interrupt و بررسی دوره‌ای"""
        logger.info(f"در حال خواب به مدت {duration} ثانیه...")
        
        # تعیین اندازه chunk بر اساس الگوی زمانی
        current_pattern = self.get_current_activity_pattern()
        chunk_size = max(15, min(60, current_pattern["base_interval"] // 4))
        
        remaining = duration
        
        while remaining > 0 and not self.stop_event.is_set():
            sleep_time = min(chunk_size, remaining)
            time.sleep(sleep_time)
            remaining -= sleep_time
            
            # بررسی پیام فقط در صورت لزوم
            if remaining > 30 and not self.stop_event.is_set():
                try:
                    if self.check_new_messages():
                        logger.info("پیام جدید در حین خواب یافت شد، بیدار شدن...")
                        break
                except Exception as e:
                    logger.error(f"خطا در بررسی پیام در حین خواب: {e}")
    
    def process_messages(self):
        """پردازش پیام‌های دریافتی به صورت کاملاً هوشمند"""
        logger.info("شروع پردازش پیام‌ها با الگوریتم هوشمند...")
        self.running = True
        self.last_activity_check = time.time()
        self.reset_sleep_cycle()
        
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while not self.stop_event.is_set():
            try:
                if not self.is_logged_in():
                    logger.warning("نیاز به لاگین مجدد")
                    if not self.login():
                        consecutive_errors += 1
                        if consecutive_errors >= max_consecutive_errors:
                            logger.error("خطاهای متوالی در لاگین، خواب طولانی...")
                            time.sleep(300)
                            consecutive_errors = 0
                        else:
                            time.sleep(60)
                        continue
                
                try:
                    consecutive_errors = 0  # reset خطاهای متوالی
                    has_activity = self.check_new_messages()
                    self.adaptive_sleep(has_activity)
                    self.smart_sleep(int(self.sleep_duration))
                    
                except Exception as e:
                    consecutive_errors += 1
                    logger.error(f"خطا در پردازش پیام: {e}")
                    
                    if consecutive_errors >= max_consecutive_errors:
                        logger.error("خطاهای متوالی، خواب طولانی...")
                        time.sleep(300)
                        consecutive_errors = 0
                    else:
                        time.sleep(120)
                
            except KeyboardInterrupt:
                logger.info("توقف توسط کاربر")
                break
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"خطای غیرمنتظره: {e}")
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("خطاهای متوالی، خواب طولانی...")
                    time.sleep(300)
                    consecutive_errors = 0
                else:
                    time.sleep(120)
        
        self.running = False
        logger.info("پردازش پیام‌ها متوقف شد")
    
    def run_bot(self):
        """اجرای ربات با مدیریت خطای پیشرفته"""
        try:
            if self.login():
                logger.info("ربات با موفقیت شروع به کار کرد")
                self.process_messages()
            else:
                logger.error("عدم توانایی در ورود به سیستم")
                time.sleep(300)
        except Exception as e:
            logger.error(f"خطا در اجرای ربات: {e}")
            time.sleep(300)
    
    def stop_bot(self):
        """توقف ایمن ربات"""
        try:
            logger.info("درخواست توقف ربات...")
            
            if not self.running:
                logger.info("ربات از قبل متوقف شده است")
                return True
                
            self.stop_event.set()
            
            timeout = 30
            start_time = time.time()
            
            while self.running and time.time() - start_time < timeout:
                time.sleep(2)
            
            if self.running:
                logger.warning("ربات به صورت عادی متوقف نشد")
                self.running = False
            
            logger.info("ربات با موفقیت متوقف شد")
            return True
            
        except Exception as e:
            logger.error(f"خطا در توقف ربات: {e}")
            return False