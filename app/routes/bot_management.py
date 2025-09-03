from flask import Blueprint, redirect, url_for, session, flash, jsonify
from models import UserManager
from bots.instagram_bot import InstagramBot
from app import active_bots
import threading
import logging

logger = logging.getLogger(__name__)

bot_management_bp = Blueprint('bot_management', __name__)

@bot_management_bp.route('/start_bot/<int:account_id>')
def start_bot(account_id):
    """شروع ربات برای حساب مشخص"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    try:
        if account_id in active_bots:
            flash('⚠️ ربات در حال حاضر در حال اجرا است!', 'warning')
            return redirect(url_for('dashboard.dashboard'))
        
        user_manager = UserManager()
        account_data = user_manager.get_account_credentials(account_id, session['user_id'])
        
        if account_data:
            bot = InstagramBot(
                account_data['instagram_username'],
                account_data['instagram_password'],
                session['user_id']
            )
            
            # استفاده از Event برای هماهنگی
            verification_event = threading.Event()
            
            active_bots[account_id] = {
                'bot': bot,
                'thread': None,
                'running': False,
                'needs_verification': False,
                'verification_event': verification_event
            }
            
            def run_bot_wrapper():
                active_bots[account_id]['running'] = True
                try:
                    # ابتدا لاگین را امتحان می‌کنیم
                    login_success = bot.login()
                    
                    if not login_success:
                        # اگر نیاز به تأیید دو مرحله‌ای دارد
                        status = bot.get_verification_status()
                        if status['needs_verification']:
                            active_bots[account_id]['needs_verification'] = True
                            logger.info(f"حساب {account_data['instagram_username']} نیاز به تأیید دو مرحله‌ای دارد")
                            # سیگنال به thread اصلی که نیاز به تأیید داریم
                            verification_event.set()
                            return
                    
                    # اگر لاگین موفق بود یا تأیید انجام شد، پردازش پیام‌ها را شروع کن
                    if bot.is_logged_in():
                        bot.process_messages()
                    
                except Exception as e:
                    logger.error(f"خطا در اجرای ربات: {e}")
                finally:
                    active_bots[account_id]['running'] = False
                    active_bots[account_id]['needs_verification'] = False
                    if account_id in active_bots:
                        del active_bots[account_id]
            
            bot_thread = threading.Thread(target=run_bot_wrapper, daemon=True)
            active_bots[account_id]['thread'] = bot_thread
            bot_thread.start()
            
            flash(f'✅ ربات برای حساب {account_data["instagram_username"]} شروع شد!', 'success')
            
            # منتظر سیگنال تأیید دو مرحله‌ای با timeout
            if verification_event.wait(timeout=10):  # 10 ثانیه منتظر می‌مانیم
                # ذخیره اطلاعات در session برای استفاده در مودال
                session['verification_account_id'] = account_id
                session['verification_required'] = True
                logger.info(f"هدایت به صفحه تأیید برای حساب {account_id}")
                return redirect(url_for('verification.verification_modal', account_id=account_id))
                
        else:
            flash('❌ حساب پیدا نشد!', 'error')
            
    except Exception as e:
        logger.error(f"خطا در شروع ربات: {e}")
        flash('❌ خطا در شروع ربات!', 'error')
    
    return redirect(url_for('dashboard.dashboard'))

@bot_management_bp.route('/stop_bot/<int:account_id>')
def stop_bot(account_id):
    """توقف ربات برای حساب مشخص"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    try:
        if account_id in active_bots:
            # توقف ربات
            result = active_bots[account_id]['bot'].stop_bot()
            
            # صبر کردن تا thread تمام شود
            if active_bots[account_id]['thread'] and active_bots[account_id]['thread'].is_alive():
                active_bots[account_id]['thread'].join(timeout=5.0)
            
            # حذف از دیکشنری
            if account_id in active_bots:
                del active_bots[account_id]
            
            user_manager = UserManager()
            account_data = user_manager.get_account_credentials(account_id, session['user_id'])
            
            if result:
                flash(f'✅ ربات برای حساب {account_data["instagram_username"]} متوقف شد!', 'success')
            else:
                flash(f'⚠️ ربات برای حساب {account_data["instagram_username"]} متوقف شد، اما با برخی خطاها!', 'warning')
        else:
            flash('❌ ربات برای این حساب در حال اجرا نیست!', 'error')
            
    except KeyError:
        # اگر ربات در دیکشنری وجود ندارد
        flash('❌ ربات برای این حساب در حال اجرا نیست!', 'error')
    except Exception as e:
        logger.error(f"خطا در توقف ربات: {e}")
        flash('❌ خطا در توقف ربات!', 'error')
    
    return redirect(url_for('dashboard.dashboard'))

@bot_management_bp.route('/api/bot_status')
def api_bot_status():
    """وضعیت ربات‌ها را به صورت JSON برمی‌گرداند"""
    if 'user_id' not in session:
        return jsonify({'error': 'لطفاً ابتدا وارد شوید'}), 401
    
    statuses = {}
    for account_id, bot_info in active_bots.items():
        statuses[account_id] = {
            'running': bot_info['running'],
            'verification_status': bot_info['bot'].get_verification_status()
        }
    
    return jsonify(statuses)