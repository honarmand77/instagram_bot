from flask import Blueprint, render_template, session, redirect, url_for
from models import UserManager, MessageManager
from app import active_bots

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
def dashboard():
    """صفحه اصلی داشبورد"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_manager = UserManager()
    message_manager = MessageManager()
    
    accounts = user_manager.get_user_accounts(session['user_id'])
    messages = message_manager.get_all_messages(session['user_id'])
    
    # بررسی وضعیت ربات‌های فعال و وضعیت تأیید
    bot_statuses = {}
    verification_statuses = {}
    
    for account in accounts:
        account_id = account['id']
        bot_statuses[account_id] = account_id in active_bots
        
        # بررسی وضعیت تأیید دو مرحله‌ای
        if account_id in active_bots:
            verification_statuses[account_id] = active_bots[account_id]['bot'].get_verification_status()
        else:
            verification_statuses[account_id] = {
                'needs_verification': False, 
                'method': None, 
                'username': account['instagram_username'],
                'verification_info': None
            }
    
    # انتقال داده‌های session به template
    verification_required = session.get('verification_required', False)
    verification_account_id = session.get('verification_account_id')
    
    # حذف session flags پس از استفاده
    if verification_required:
        session.pop('verification_required', None)
        session.pop('verification_account_id', None)
    
    return render_template('dashboard.html', 
                         accounts=accounts, 
                         messages=messages,
                         username=session['username'],
                         bot_statuses=bot_statuses,
                         verification_statuses=verification_statuses,
                         verification_required=verification_required,
                         verification_account_id=verification_account_id)
