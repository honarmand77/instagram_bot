from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import MessageManager

messages_bp = Blueprint('messages', __name__)

@messages_bp.route('/edit_message/<int:message_id>', methods=['GET', 'POST'])
def edit_message(message_id):
    """ویرایش پیام"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    message_manager = MessageManager()
    
    if request.method == 'POST':
        try:
            key = request.form.get('key', '').strip()
            content = request.form.get('content', '').strip()
            key_type = request.form.get('key_type', 'number')
            start_date = request.form.get('start_date', '').strip() or None
            end_date = request.form.get('end_date', '').strip() or None
            is_active = 'is_active' in request.form
            
            if not key or not content:
                flash('❌ لطفاً کلید و محتوا را وارد کنید!', 'error')
                return render_template('edit_message.html', message={
                    'id': message_id,
                    'key': key,
                    'content': content,
                    'key_type': key_type,
                    'start_date': start_date,
                    'end_date': end_date,
                    'is_active': is_active
                })
            
            # اعتبارسنجی نوع کلید
            if key_type == 'number' and not key.isdigit():
                flash('❌ برای کلیدهای عددی فقط می‌توانید از اعداد استفاده کنید!', 'error')
                return render_template('edit_message.html', message={
                    'id': message_id,
                    'key': key,
                    'content': content,
                    'key_type': key_type,
                    'start_date': start_date,
                    'end_date': end_date,
                    'is_active': is_active
                })
            
            if message_manager.update_message(message_id, session['user_id'], key, content, 
                                             key_type, start_date, end_date, is_active):
                flash('✅ پیام با موفقیت به‌روزرسانی شد!', 'success')
                return redirect(url_for('dashboard.dashboard'))
            else:
                flash('❌ خطا در به‌روزرسانی پیام! ممکن است کلید تکراری باشد.', 'error')
                
        except Exception as e:
            from app import app
            app.logger.error(f"خطا در ویرایش پیام: {e}")
            flash('❌ خطا در پردازش درخواست!', 'error')
    
    # پیدا کردن پیام برای نمایش در فرم
    message = message_manager.get_message_by_id(message_id, session['user_id'])
    
    if not message:
        flash('❌ پیام پیدا نشد!', 'error')
        return redirect(url_for('dashboard.dashboard'))
    
    return render_template('edit_message.html', message=message)

@messages_bp.route('/add_message', methods=['GET', 'POST'])
def add_message():
    """افزودن پیام جدید"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        try:
            key = request.form.get('key', '').strip()
            content = request.form.get('content', '').strip()
            key_type = request.form.get('key_type', 'number')
            start_date = request.form.get('start_date', '').strip() or None
            end_date = request.form.get('end_date', '').strip() or None
            
            if not key or not content:
                flash('❌ لطفاً کلید و محتوا را وارد کنید!', 'error')
                return render_template('add_message.html')
            
            # اعتبارسنجی نوع کلید
            if key_type == 'number' and not key.isdigit():
                flash('❌ برای کلیدهای عددی فقط می‌توانید از اعداد استفاده کنید!', 'error')
                return render_template('add_message.html')
            
            message_manager = MessageManager()
            if message_manager.add_message(session['user_id'], key, content, 
                                         key_type, start_date, end_date):
                flash('✅ پیام جدید با موفقیت افزوده شد!', 'success')
                return redirect(url_for('dashboard.dashboard'))
            else:
                flash('❌ خطا در افزودن پیام! ممکن است کلید تکراری باشد.', 'error')
                
        except Exception as e:
            from app import app
            app.logger.error(f"خطا در افزودن پیام: {e}")
            flash('❌ خطا در پردازش درخواست!', 'error')
    
    return render_template('add_message.html')

@messages_bp.route('/delete_message/<int:message_id>')
def delete_message(message_id):
    """حذف پیام"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    try:
        message_manager = MessageManager()
        if message_manager.delete_message(message_id, session['user_id']):
            flash('✅ پیام با موفقیت حذف شد!', 'success')
        else:
            flash('❌ خطا در حذف پیام!', 'error')
            
    except Exception as e:
        from app import app
        app.logger.error(f"خطا در حذف پیام: {e}")
        flash('❌ خطا در پردازش درخواست!', 'error')
    
    return redirect(url_for('dashboard.dashboard'))

@messages_bp.route('/search_messages')
def search_messages():
    """جستجوی پیام‌ها"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    try:
        search_term = request.args.get('q', '').strip()
        key_type = request.args.get('type', '')
        
        message_manager = MessageManager()
        
        if search_term:
            results = message_manager.search_messages(session['user_id'], search_term, 
                                                     key_type if key_type else None)
        else:
            results = []
        
        return render_template('search_messages.html', 
                             results=results, 
                             search_term=search_term,
                             key_type=key_type)
            
    except Exception as e:
        from app import app
        app.logger.error(f"خطا در جستجوی پیام‌ها: {e}")
        flash('❌ خطا در جستجوی پیام‌ها!', 'error')
        return redirect(url_for('dashboard.dashboard'))