from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models import UserManager
from app import active_bots

verification_bp = Blueprint('verification', __name__)

@verification_bp.route('/api/verification_needed')
def api_verification_needed():
    """بررسی آیا حساب‌ها نیاز به تأیید دو مرحله‌ای دارند"""
    if 'user_id' not in session:
        return jsonify({'error': 'لطفاً ابتدا وارد شوید'}), 401
    
    verification_needed = {}
    for account_id, bot_info in active_bots.items():
        status = bot_info['bot'].get_verification_status()
        verification_needed[account_id] = {
            'needs_verification': status['needs_verification'],
            'account_id': account_id,
            'username': status['username'],
            'method': status['method']
        }
    
    return jsonify(verification_needed)

@verification_bp.route('/api/request_verification/<int:account_id>', methods=['POST'])
def api_request_verification(account_id):
    """درخواست کد تأیید دو مرحله‌ای"""
    if 'user_id' not in session:
        return jsonify({'error': 'لطفاً ابتدا وارد شوید'}), 401
    
    if account_id not in active_bots:
        return jsonify({'error': 'ربات پیدا نشد'}), 404
    
    data = request.get_json()
    method = data.get('method', 'sms')
    
    bot = active_bots[account_id]['bot']
    success = bot.request_verification_code(method)
    
    return jsonify({'success': success})

@verification_bp.route('/api/submit_verification/<int:account_id>', methods=['POST'])
def api_submit_verification(account_id):
    """ارسال کد تأیید دو مرحله‌ای"""
    if 'user_id' not in session:
        return jsonify({'error': 'لطفاً ابتدا وارد شوید'}), 401
    
    if account_id not in active_bots:
        return jsonify({'error': 'ربات پیدا نشد'}), 404
    
    data = request.get_json()
    code = data.get('code', '')
    
    if not code:
        return jsonify({'error': 'کد تأیید الزامی است'}), 400
    
    bot = active_bots[account_id]['bot']
    success = bot.submit_verification_code(code)
    
    return jsonify({'success': success})

@verification_bp.route('/api/verification_status/<int:account_id>')
def api_verification_status(account_id):
    """دریافت وضعیت تأیید دو مرحله‌ای"""
    if 'user_id' not in session:
        return jsonify({'error': 'لطفاً ابتدا وارد شوید'}), 401
    
    if account_id not in active_bots:
        return jsonify({'error': 'ربات پیدا نشد'}), 404
    
    bot = active_bots[account_id]['bot']
    status = bot.get_verification_status()
    
    return jsonify(status)

@verification_bp.route('/verification_modal/<int:account_id>')
def verification_modal(account_id):
    """صفحه مودال برای وارد کردن کد تأیید"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    # بررسی فعال بودن ربات و نیاز به تأیید
    if account_id not in active_bots:
        flash('❌ ربات پیدا نشد یا متوقف شده است!', 'error')
        return redirect(url_for('dashboard.dashboard'))
    
    user_manager = UserManager()
    account_data = user_manager.get_account_credentials(account_id, session['user_id'])
    
    if not account_data:
        flash('❌ حساب پیدا نشد!', 'error')
        return redirect(url_for('dashboard.dashboard'))
    
    verification_status = active_bots[account_id]['bot'].get_verification_status()
    
    # اگر نیازی به تأیید نیست، به dashboard برگرد
    if not verification_status['needs_verification']:
        flash('✅ این حساب نیازی به تأیید دو مرحله‌ای ندارد.', 'info')
        return redirect(url_for('dashboard.dashboard'))
    
    return render_template('verification_modal.html', 
                         account=account_data,
                         verification_status=verification_status)

@verification_bp.route('/submit_verification_code/<int:account_id>', methods=['POST'])
def submit_verification_code(account_id):
    """ارسال کد تأیید از طریق فرم"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    if account_id not in active_bots:
        flash('❌ ربات پیدا نشد!', 'error')
        return redirect(url_for('dashboard.dashboard'))
    
    try:
        code = request.form.get('verification_code', '').strip()
        
        if not code:
            flash('❌ لطفاً کد تأیید را وارد کنید!', 'error')
            return redirect(url_for('verification.verification_modal', account_id=account_id))
        
        bot = active_bots[account_id]['bot']
        success = bot.submit_verification_code(code)
        
        if success:
            flash('✅ کد تأیید با موفقیت پذیرفته شد! ربات ادامه خواهد داد.', 'success')
            return redirect(url_for('dashboard.dashboard'))
        else:
            flash('❌ کد تأیید نامعتبر است. لطفاً دوباره تلاش کنید.', 'error')
            return redirect(url_for('verification.verification_modal', account_id=account_id))
            
    except Exception as e:
        from app import app
        app.logger.error(f"خطا در ارسال کد تأیید: {e}")
        flash('❌ خطا در پردازش درخواست!', 'error')
        return redirect(url_for('verification.verification_modal', account_id=account_id))

@verification_bp.route('/request_new_code/<int:account_id>')
def request_new_code(account_id):
    """درخواست کد تأیید جدید"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    if account_id not in active_bots:
        flash('❌ ربات پیدا نشد!', 'error')
        return redirect(url_for('dashboard.dashboard'))
    
    try:
        bot = active_bots[account_id]['bot']
        status = bot.get_verification_status()
        method = status.get('method', 'sms')
        
        success = bot.request_verification_code(method)
        
        if success:
            flash('✅ کد جدید ارسال شد!', 'success')
        else:
            flash('❌ خطا در ارسال کد جدید!', 'error')
            
    except Exception as e:
        from app import app
        app.logger.error(f"خطا در درخواست کد جدید: {e}")
        flash('❌ خطا در پردازش درخواست!', 'error')
    
    return redirect(url_for('verification.verification_modal', account_id=account_id))