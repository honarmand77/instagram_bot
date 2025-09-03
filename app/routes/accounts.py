from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import UserManager
from app import active_bots

accounts_bp = Blueprint('accounts', __name__)

@accounts_bp.route('/add_account', methods=['GET', 'POST'])
def add_account():
    """افزودن حساب اینستاگرام"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        try:
            instagram_username = request.form.get('instagram_username', '').strip()
            instagram_password = request.form.get('instagram_password', '').strip()
            
            if not instagram_username or not instagram_password:
                flash('❌ لطفاً تمام فیلدها را پر کنید!', 'error')
                return render_template('add_account.html')
            
            user_manager = UserManager()
            if user_manager.add_instagram_account(session['user_id'], instagram_username, instagram_password):
                flash('✅ حساب اینستاگرام با موفقیت افزوده شد!', 'success')
                return redirect(url_for('dashboard.dashboard'))
            else:
                flash('❌ خطا در افزودن حساب! ممکن است حساب تکراری باشد.', 'error')
                
        except Exception as e:
            from app import app
            app.logger.error(f"خطا در افزودن حساب: {e}")
            flash('❌ خطا در پردازش درخواست!', 'error')
    
    return render_template('add_account.html')

@accounts_bp.route('/delete_account/<int:account_id>')
def delete_account(account_id):
    """حذف حساب اینستاگرام"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    try:
        # توقف ربات اگر در حال اجرا است
        if account_id in active_bots:
            active_bots[account_id]['bot'].stop_bot()
            if active_bots[account_id]['thread'] and active_bots[account_id]['thread'].is_alive():
                active_bots[account_id]['thread'].join(timeout=3.0)
            del active_bots[account_id]
        
        user_manager = UserManager()
        if user_manager.delete_instagram_account(account_id, session['user_id']):
            flash('✅ حساب اینستاگرام با موفقیت حذف شد!', 'success')
        else:
            flash('❌ خطا در حذف حساب!', 'error')
            
    except Exception as e:
        from app import app
        app.logger.error(f"خطا در حذف حساب: {e}")
        flash('❌ خطا در پردازش درخواست!', 'error')
    
    return redirect(url_for('dashboard.dashboard'))
