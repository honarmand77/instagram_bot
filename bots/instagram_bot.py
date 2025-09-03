from instagrapi import Client
from instagrapi.exceptions import TwoFactorRequired, ChallengeRequired, LoginRequired, ClientConnectionError, ClientError
from instagrapi.types import DirectThread
import os
import json
import logging
import time
import random
from typing import Dict, Any, Optional, Set, List, Tuple
from datetime import datetime, timedelta
from models import UserManager, MessageManager
from .base_bot import BaseBot
import hashlib

logger = logging.getLogger(__name__)

class InstagramBot(BaseBot):
    def __init__(self, instagram_username: str, instagram_password: str, user_id: int):
        super().__init__()
        self.instagram_username = instagram_username
        self.instagram_password = instagram_password
        self.user_id = user_id
        
        # تنظیمات پیشرفته client
        self.client = Client()
        self.setup_client_settings()
        
        self.session_file = f"session_{user_id}_{instagram_username}.json"
        self.user_manager = UserManager()
        self.message_manager = MessageManager()
        
        # متغیرهای مدیریت تأیید دو مرحله‌ای
        self.two_factor_required = False
        self.challenge_required = False
        self.verification_code = None
        self.verification_method = None
        self.challenge_context = None
        self.verification_info = None
        
        # مدیریت پیام‌های پردازش شده
        self.processed_message_ids: Set[str] = set()
        self.last_cleanup_time = time.time()
        
        # مدیریت هوشمند درخواست‌ها - بهینه‌شده برای سرعت
        self.request_timestamps = []
        self.request_count_5min = 0
        self.last_request_reset = time.time()
        self.rate_limit_detected = False
        self.rate_limit_cooldown = 0
        self.last_successful_request = time.time()
        
        # کش برای کاهش درخواست‌های تکراری - کاهش زمان کش
        self.thread_cache = {}
        self.cache_expiry = 120  # کاهش به 2 دقیقه
        
        logger.info(f"ربات سریع برای {instagram_username} راه‌اندازی شد")

    def setup_client_settings(self):
        """تنظیمات پیشرفته برای شبیه‌سازی مرورگر"""
        settings = {
            "user_agent": "Instagram 269.0.0.18.75 Android (28/9; 420dpi; 1080x2260; OnePlus; ONEPLUS A6013; OnePlus6T; qcom; en_US; 314665256)",
            "device_settings": {
                "app_version": "269.0.0.18.75",
                "android_version": 28,
                "android_release": "9",
                "dpi": "420dpi",
                "resolution": "1080x2260",
                "manufacturer": "OnePlus",
                "device": "ONEPLUS A6013",
                "model": "OnePlus6T",
                "cpu": "qcom",
                "locale": "en_US"
            },
            "headers": {
                'X-IG-App-ID': '567067343352427',
                'X-IG-Device-ID': self.generate_device_id(),
                'X-IG-Android-ID': self.generate_android_id(),
            },
            "proxy": None,
            "timeout": 20,  # کاهش timeout
            "connection_retries": 2,
            "request_timeout": (5, 20)  # کاهش timeout
        }
        self.client.set_settings(settings)
    
    def generate_device_id(self) -> str:
        """تولید device ID تصادفی"""
        import uuid
        return str(uuid.uuid4())
    
    def generate_android_id(self) -> str:
        """تولید Android ID تصادفی"""
        import random
        import string
        return 'android-' + ''.join(random.choices(string.hexdigits.lower(), k=16))
    
    def update_request_stats(self):
        """به‌روزرسانی آمار درخواست‌ها"""
        current_time = time.time()
        self.request_timestamps.append(current_time)
        
        # حذف درخواست‌های قدیمی‌تر از 5 دقیقه
        self.request_timestamps = [ts for ts in self.request_timestamps if current_time - ts < 300]
        self.request_count_5min = len(self.request_timestamps)
        
        # بازنشانی شمارنده هر 5 دقیقه
        if current_time - self.last_request_reset > 300:
            self.request_count_5min = 0
            self.last_request_reset = current_time
    
    def can_make_request(self) -> Tuple[bool, float]:
        """بررسی امکان انجام درخواست جدید - بهینه‌شده برای سرعت"""
        current_time = time.time()
        
        # اگر در حالت cooldown هستیم
        if self.rate_limit_detected and current_time - self.rate_limit_cooldown < 300:
            wait_time = self.rate_limit_cooldown + 300 - current_time
            return False, wait_time
        
        # محدودیت نرخ درخواست - افزایش برای سرعت بیشتر
        max_requests_per_5min = 60  # افزایش محدودیت
        
        if self.request_count_5min >= max_requests_per_5min:
            # محاسبه زمان انتظار تا آزاد شدن slot
            oldest_request = min(self.request_timestamps) if self.request_timestamps else current_time
            wait_time = oldest_request + 300 - current_time
            return False, wait_time
        
        # فاصله زمانی بین درخواست‌ها - کاهش شدید برای سرعت
        time_since_last_request = current_time - self.last_successful_request
        min_interval = 1.5  # کاهش به 1.5 ثانیه
        
        if time_since_last_request < min_interval:
            return False, min_interval - time_since_last_request
        
        return True, 0
    
    def safe_api_call(self, api_method, *args, **kwargs):
        """فراخوانی ایمن API با مدیریت خطا - بهینه‌شده برای سرعت"""
        retry_count = 0
        max_retries = 2
        
        while retry_count < max_retries:
            try:
                can_request, wait_time = self.can_make_request()
                if not can_request and wait_time > 0:
                    time.sleep(wait_time)
                
                # اضافه کردن تغییرات تصادفی انسانی - کاهش تأخیر
                human_delay = random.uniform(0.5, 1.5)  # کاهش تأخیر
                time.sleep(human_delay)
                
                result = api_method(*args, **kwargs)
                self.update_request_stats()
                self.last_successful_request = time.time()
                self.rate_limit_detected = False
                
                return result
                
            except (ClientError, ConnectionError) as e:
                if "rate limit" in str(e).lower() or "too many requests" in str(e).lower():
                    logger.warning("محدودیت نرخ درخواست شناسایی شد")
                    self.rate_limit_detected = True
                    self.rate_limit_cooldown = time.time()
                    
                    if retry_count < max_retries - 1:
                        wait_time = (2 ** retry_count) * 30  # کاهش زمان انتظار
                        logger.info(f"انتظار برای {wait_time} ثانیه قبل از تلاش مجدد")
                        time.sleep(wait_time)
                        retry_count += 1
                        continue
                
                logger.error(f"خطای API: {e}")
                break
                
            except Exception as e:
                logger.error(f"خطای غیرمنتظره در فراخوانی API: {e}")
                if retry_count < max_retries - 1:
                    time.sleep(2)  # کاهش زمان انتظار
                    retry_count += 1
                    continue
                break
        
        return None

    def load_session(self) -> bool:
        """بارگذاری session از دیتابیس"""
        try:
            account_data = self.user_manager.get_account_credentials(
                self.get_account_id(), self.user_id
            )
            
            if account_data and account_data['session_data']:
                session_data = json.loads(account_data['session_data'])
                self.client.set_settings(session_data)
                logger.info("Session از دیتابیس بارگذاری شد")
                return True
                
            # Fallback به فایل اگر در دیتابیس وجود نداشت
            if os.path.exists(self.session_file):
                with open(self.session_file, 'r') as f:
                    session_data = json.load(f)
                
                if session_data and 'authorization_data' in session_data:
                    self.client.set_settings(session_data)
                    # ذخیره در دیتابیس برای دفعات بعد
                    self.user_manager.update_account_session(
                        self.get_account_id(), json.dumps(session_data)
                    )
                    logger.info("Session از فایل بارگذاری و در دیتابیس ذخیره شد")
                    return True
                    
            return False
        except Exception as e:
            logger.error(f"خطا در بارگذاری session: {e}")
            return False
    
    def save_session(self) -> bool:
        """ذخیره session در دیتابیس"""
        try:
            session_data = self.client.get_settings()
            if session_data:
                # ذخیره در دیتابیس
                success = self.user_manager.update_account_session(
                    self.get_account_id(), json.dumps(session_data)
                )
                
                # همچنین در فایل هم ذخیره کنید (به عنوان پشتیبان)
                with open(self.session_file, 'w') as f:
                    json.dump(session_data, f)
                
                logger.info("Session در دیتابیس و فایل ذخیره شد")
                return success
            return False
        except Exception as e:
            logger.error(f"خطا در ذخیره session: {e}")
            return False
    
    def get_account_id(self) -> int:
        """دریافت ID حساب از دیتابیس"""
        accounts = self.user_manager.get_user_accounts(self.user_id)
        for account in accounts:
            if account['instagram_username'] == self.instagram_username:
                return account['id']
        return -1
    
    def is_logged_in(self) -> bool:
        """بررسی آیا کاربر وارد شده است"""
        try:
            if hasattr(self.client, 'user_id') and self.client.user_id:
                return True
            
            try:
                # تست اتصال با یک درخواست سبک
                self.client.get_timeline_feed(amount=1)
                return True
            except (LoginRequired, Exception) as e:
                logger.debug(f"نیاز به لاگین مجدد: {e}")
                return False
                
        except Exception as e:
            logger.error(f"خطا در بررسی وضعیت لاگین: {e}")
            return False
    
    def handle_two_factor(self, e: TwoFactorRequired) -> bool:
        """مدیریت تأیید دو مرحله‌ای"""
        logger.info("تأیید دو مرحله‌ای لازم است")
        self.two_factor_required = True
        
        try:
            if hasattr(e, 'json_data'):
                json_data = e.json_data
                if 'two_factor_info' in json_data:
                    two_factor_info = json_data['two_factor_info']
                    self.challenge_context = {
                        "user_id": two_factor_info.get('two_factor_identifier'),
                        "nonce_code": two_factor_info.get('sms_two_factor_on')
                    }
                else:
                    self.challenge_context = {
                        "user_id": getattr(e, 'user_id', None),
                        "nonce_code": getattr(e, 'nonce_code', None)
                    }
            else:
                self.challenge_context = {
                    "user_id": getattr(e, 'user_id', None),
                    "nonce_code": getattr(e, 'nonce_code', None)
                }
            
            self.verification_info = {
                "username": self.instagram_username,
                "method": "sms",
                "two_factor": True,
                "challenge": False
            }
            
            return True
            
        except Exception as e:
            logger.error(f"خطا در مدیریت تأیید دو مرحله‌ای: {e}")
            return False
    
    def handle_challenge(self, e: ChallengeRequired) -> bool:
        """مدیریت چالش امنیتی"""
        logger.info("چالش امنیتی لازم است")
        self.challenge_required = True
        
        try:
            self.challenge_context = getattr(e, 'context', None)
            
            self.verification_info = {
                "username": self.instagram_username,
                "method": "email",
                "two_factor": False,
                "challenge": True
            }
            
            return True
            
        except Exception as e:
            logger.error(f"خطا در مدیریت چالش امنیتی: {e}")
            return False
    
    def request_verification_code(self, method: str = "sms") -> bool:
        """درخواست کد تأیید"""
        try:
            if not self.challenge_context:
                logger.error("هیچ چالشی برای درخواست کد وجود ندارد")
                return False
                
            if self.two_factor_required:
                user_id = self.challenge_context.get("user_id")
                if user_id:
                    if method.lower() == "sms":
                        self.client.send_two_factor_login_sms(user_id)
                    else:
                        self.client.send_two_factor_login_email(user_id)
                    self.verification_method = method
                    self.verification_info["method"] = method
                    logger.info(f"کد تأیید از طریق {method} ارسال شد")
                    return True
                    
            elif self.challenge_required:
                choice = 0 if method.lower() == "sms" else 1
                self.client.challenge_resend(self.challenge_context, choice)
                self.verification_method = method
                self.verification_info["method"] = method
                logger.info(f"کد تأیید از طریق {method} ارسال شد")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"خطا در درخواست کد تأیید: {e}")
            return False
    
    def submit_verification_code(self, code: str) -> bool:
        """ارسال کد تأیید برای تکمیل فرآیند ورود"""
        try:
            if self.two_factor_required and self.challenge_context:
                user_id = self.challenge_context.get("user_id")
                if user_id:
                    result = self.client.two_factor_login(
                        user_id, code, verification_method=self.verification_method
                    )
                    if result:
                        self.two_factor_required = False
                        self.save_session()
                        logger.info("ورود با کد تأیید دو مرحله‌ای موفقیت‌آمیز بود")
                        return True
            
            elif self.challenge_required and self.challenge_context:
                self.client.challenge_code(self.challenge_context, code)
                if self.is_logged_in():
                    self.challenge_required = False
                    self.save_session()
                    logger.info("چالش امنیتی با موفقیت حل شد")
                    return True
            
            logger.error("کد تأیید نامعتبر است یا منقضی شده")
            return False
            
        except Exception as e:
            logger.error(f"خطا در ارسال کد تأیید: {e}")
            return False
    
    def get_verification_status(self) -> Dict[str, Any]:
        """دریافت وضعیت تأیید دو مرحله‌ای"""
        return {
            "needs_verification": self.two_factor_required or self.challenge_required,
            "method": self.verification_method,
            "username": self.instagram_username,
            "verification_info": self.verification_info
        }
    
    def login(self) -> bool:
        """ورود به اینستاگرام با پشتیبانی از تأیید دو مرحله‌ای"""
        max_retries = 2
        
        if self.is_logged_in():
            logger.info("قبلاً وارد شده‌اید")
            return True
            
        for attempt in range(max_retries):
            try:
                logger.info(f"تلاش برای ورود ({attempt + 1}/{max_retries})...")
                
                if self.load_session() and self.is_logged_in():
                    logger.info("با session موجود وارد شدید")
                    return True
                
                logger.info("انجام لاگین جدید...")
                
                try:
                    # کاهش تأخیر بین درخواست‌ها
                    time.sleep(random.uniform(2, 5))
                    
                    result = self.safe_api_call(
                        self.client.login, 
                        self.instagram_username, 
                        self.instagram_password
                    )
                    
                    if result and self.is_logged_in():
                        self.save_session()
                        logger.info("ورود موفقیت‌آمیز بود")
                        return True
                    
                except TwoFactorRequired as e:
                    if self.handle_two_factor(e):
                        logger.info("ربات آماده دریافت کد تأیید است")
                        return False
                    
                except ChallengeRequired as e:
                    if self.handle_challenge(e):
                        logger.info("ربات آماده دریافت کد تأیید است")
                        return False
                
                except ClientConnectionError:
                    logger.error("خطای اتصال. لطفاً VPN خود را بررسی کنید")
                    if attempt < max_retries - 1:
                        time.sleep(15)
                        continue
                
            except Exception as e:
                logger.error(f"خطا در ورود: {e}")
                if attempt < max_retries - 1:
                    time.sleep(15)
        
        return False
    
    def cleanup_old_processed_messages(self):
        """پاکسازی پیام‌های پردازش شده قدیمی"""
        current_time = time.time()
        # هر 30 دقیقه یکبار پاکسازی انجام شود
        if current_time - self.last_cleanup_time > 1800:
            logger.info("پاکسازی پیام‌های پردازش شده قدیمی")
            
            # فقط پیام‌های قدیمی‌تر از 12 ساعت را پاک کن
            twenty_four_hours_ago = current_time - (12 * 3600)
            self.processed_message_ids = set(
                msg_id for msg_id in self.processed_message_ids
            )
            
            self.last_cleanup_time = current_time
    
    def get_all_threads(self) -> List[DirectThread]:
        """دریافت تمام threads با مدیریت هوشمند - بهینه‌شده برای سرعت"""
        current_time = time.time()
        
        # بررسی کش اول
        if self.thread_cache.get('threads') and current_time - self.thread_cache.get('timestamp', 0) < self.cache_expiry:
            logger.debug("استفاده از threads کش شده")
            return self.thread_cache['threads']
        
        threads = []
        
        try:
            # دریافت threads اصلی - افزایش amount برای دریافت بیشتر
            main_threads = self.safe_api_call(self.client.direct_threads, amount=15)
            if main_threads:
                threads.extend(main_threads)
        except Exception as e:
            logger.warning(f"خطا در دریافت threads اصلی: {e}")
        
        # دریافت threads دیگر با احتمال بیشتر
        if random.random() < 0.5:  # افزایش به 50% مواقع
            try:
                pending_result = self.safe_api_call(self.client.direct_pending_inbox)
                if pending_result and hasattr(pending_result, 'threads'):
                    threads.extend(pending_result.threads)
            except Exception as e:
                logger.warning(f"خطا در دریافت threads pending: {e}")
        
        # ذخیره در کش
        self.thread_cache = {
            'threads': threads,
            'timestamp': current_time
        }
        
        return threads

    def check_new_messages(self) -> bool:
        """بررسی وجود پیام جدید با الگوریتم هوشمند - بهینه‌شده برای سرعت"""
        try:
            # پاکسازی پیام‌های قدیمی
            self.cleanup_old_processed_messages()
            
            # دریافت threads با مدیریت هوشمند
            threads = self.get_all_threads()
            
            if not threads:
                logger.debug("هیچ threadی یافت نشد")
                return False
            
            logger.info(f"تعداد threads یافت شده: {len(threads)}")
            
            has_activity = False
            current_user_id = self.client.user_id

            for thread in threads:
                if self.stop_event.is_set():
                    break
                
                try:
                    # دریافت کامل thread با cache کوتاه‌تر
                    thread_hash = hashlib.md5(thread.id.encode()).hexdigest()
                    cache_key = f"thread_{thread_hash}"
                    
                    if cache_key in self.thread_cache and time.time() - self.thread_cache[cache_key]['timestamp'] < 60:
                        full_thread = self.thread_cache[cache_key]['data']
                    else:
                        full_thread = self.safe_api_call(self.client.direct_thread, thread.id)
                        if full_thread:
                            self.thread_cache[cache_key] = {
                                'data': full_thread,
                                'timestamp': time.time()
                            }
                    
                    if not full_thread or not full_thread.messages:
                        continue
                            
                    last_message = full_thread.messages[0]
                    message_id = getattr(last_message, 'id', None)
                    
                    # بررسی اینکه پیام از کاربر فعلی نیست
                    if last_message.user_id == current_user_id:
                        continue
                    
                    if not message_id or message_id in self.processed_message_ids:
                        continue
                    
                    # بررسی زمان پیام - کاهش زمان بررسی
                    message_time = last_message.timestamp.timestamp() if hasattr(last_message.timestamp, 'timestamp') else last_message.timestamp
                    if message_time < (time.time() - 86400):  # فقط پیام‌های 24 ساعت اخیر
                        continue
                    
                    message_text = last_message.text.strip() if last_message.text else ""
                    if not message_text:
                        continue
                    
                    # علامتگذاری پیام به عنوان پردازش شده
                    self.processed_message_ids.add(message_id)

                    # پردازش پیام
                    response = self.process_message_content(message_text)
                    
                    if response:
                        # تأخیر کمتر قبل از ارسال پاسخ
                        can_request, wait_time = self.can_make_request()
                        if not can_request and wait_time > 0:
                            time.sleep(wait_time)
                        
                        self.send_response(response, thread.id, last_message.user_id, message_text)
                        has_activity = True
                        
                        # تأخیر کمتر بین ارسال پاسخ‌ها
                        time.sleep(random.uniform(1, 3))  # کاهش تأخیر
                        
                except Exception as e:
                    logger.error(f"خطا در پردازش مکالمه {thread.id}: {e}")
                    continue
                
            self.last_activity_check = time.time()
            return has_activity

        except LoginRequired:
            logger.warning("Session منقضی شده")
            raise
        except Exception as e:
            logger.error(f"خطا در بررسی پیام‌ها: {e}")
            return False

    def process_message_content(self, message_text: str) -> str:
        """پردازش محتوای پیام و تولید پاسخ"""
        try:
            if message_text.isdigit():
                response = self.message_manager.get_message(self.user_id, message_text)
            else:
                response = self.message_manager.get_message(self.user_id, message_text.lower())
            
            return response.strip() if response else ""
        except Exception as e:
            logger.error(f"خطا в پردازش محتوای پیام: {e}")
            return ""

    def send_response(self, response: str, thread_id: str, user_id: str, original_message: str):
        """ارسال پاسخ به پیام"""
        try:
            # ارسال پاسخ
            self.client.direct_send(response, thread_ids=[thread_id])
            
            # لاگ کردن ارسال
            self.message_manager.log_message_sent(
                self.user_id, original_message, thread_id, user_id
            )
            
            logger.info(f"پاسخ به پیام '{original_message}' ارسال شد")
            
            # علامتگذاری به عنوان خوانده شده
            try:
                self.client.direct_thread_mark_read(thread_id)
            except Exception as e:
                logger.warning(f"خطا در علامتگذاری به عنوان خوانده شده: {e}")
                
        except Exception as e:
            logger.error(f"خطا در ارسال پاسخ: {e}")

    def process_messages(self):
        """پردازش پیام‌های دریافتی به صورت هوشمند"""
        if self.two_factor_required or self.challenge_required:
            logger.info("منتظر تأیید دو مرحله‌ای/چالش امنیتی هستیم...")
            time.sleep(5)  # کاهش زمان انتظار
            return
        
        super().process_messages()

    def run_bot(self):
        """اجرای ربات"""
        try:
            login_result = self.login()
            
            if login_result:
                logger.info("ربات با موفقیت شروع به کار کرد")
                self.process_messages()
            else:
                status = self.get_verification_status()
                if status["needs_verification"]:
                    logger.info("ربات آماده دریافت کد تأیید است")
                    # انتظار برای دریافت کد تأیید
                    time.sleep(15)  # کاهش زمان انتظار
                else:
                    logger.error("عدم توانایی در ورود به سیستم")
                    # راه‌حل fallback یا اطلاع‌رسانی به کاربر
                    
        except Exception as e:
            logger.error(f"خطا در اجرای ربات: {e}")
            # راه‌حل بازیابی از خطا
            time.sleep(30)  # کاهش زمان انتظار

    def safe_shutdown(self):
        """خاموش کردن ایمن ربات"""
        try:
            self.save_session()
            logger.info("Session ذخیره شد و ربات خاموش می‌شود")
        except Exception as e:
            logger.error(f"خطا در خاموش کردن ربات: {e}")
        finally:
            self.stop_event.set()