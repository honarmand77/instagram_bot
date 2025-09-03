from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import UserManager, MessageManager

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """صفحه لاگین"""
    if 'user_id' in session:
        return redirect(url_for('dashboard.dashboard'))
    
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            
            if not username or not password:
                flash('❌ لطفاً نام کاربری و رمز عبور را وارد کنید!', 'error')
                return render_template('login.html')
            
            user_manager = UserManager()
            user = user_manager.verify_user(username, password)
            
            if user:
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['is_admin'] = user['is_admin']
                
                # ایجاد پیام‌های پیش‌فرض برای کاربر جدید
                try:
                    message_manager = MessageManager()
                    message_manager.add_default_messages(user['id'])
                except Exception as e:
                    from app import app
                    app.logger.error(f"خطا در ایجاد پیام‌های پیش‌فرض: {e}")
                
                flash('✅ با موفقیت وارد شدید!', 'success')
                return redirect(url_for('dashboard.dashboard'))
            else:
                flash('❌ نام کاربری یا رمز عبور اشتباه است!', 'error')
                
        except Exception as e:
            from app import app
            app.logger.error(f"خطا در ورود: {e}")
            flash('❌ خطا در پردازش درخواست!', 'error')
    
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """صفحه ثبت نام"""
    if 'user_id' in session:
        return redirect(url_for('dashboard.dashboard'))
    
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            confirm_password = request.form.get('confirm_password', '').strip()
            
            if not username or not password or not confirm_password:
                flash('❌ لطفاً تمام فیلدها را پر کنید!', 'error')
                return render_template('register.html')
            
            if password != confirm_password:
                flash('❌ رمز عبور و تکرار آن مطابقت ندارند!', 'error')
                return render_template('register.html')
            
            user_manager = UserManager()
            if user_manager.create_user(username, password):
                flash('✅ حساب کاربری با موفقیت ایجاد شد! اکنون می‌توانید وارد شوید.', 'success')
                return redirect(url_for('auth.login'))
            else:
                flash('❌ نام کاربری قبلاً استفاده شده است!', 'error')
                
        except Exception as e:
            from app import app
            app.logger.error(f"خطا در ثبت نام: {e}")
            flash('❌ خطا در پردازش درخواست!', 'error')
    
    return render_template('register.html')

@auth_bp.route('/logout')
def logout():
    """خروج از سیستم"""
    from app import active_bots
    
    # توقف تمام ربات‌های در حال اجرا
    for account_id in list(active_bots.keys()):
        try:
            if account_id in active_bots:
                active_bots[account_id]['bot'].stop_bot()
                if active_bots[account_id]['thread'] and active_bots[account_id]['thread'].is_alive():
                    active_bots[account_id]['thread'].join(timeout=3.0)
                del active_bots[account_id]
        except Exception as e:
            from app import app
            app.logger.error(f"خطا در توقف ربات هنگام خروج: {e}")
    
    session.clear()
    flash('✅ با موفقیت خارج شدید!', 'success')
    return redirect(url_for('auth.login'))
