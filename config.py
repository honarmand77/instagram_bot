from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import urlparse
import logging
import os

# تنظیمات لاگینگ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("instagram_bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# ایجاد نمونه دیتابیس
db = SQLAlchemy()

# متغیر global برای ربات‌های فعال
active_bots = {}

def create_app():
    app = Flask(__name__)
    
    # تنظیمات secret key
    app.secret_key = os.environ.get('SECRET_KEY') or 'your_secret_key_here_change_this_in_production'
    
    # تنظیمات پایگاه داده - استفاده از PostgreSQL اگر موجود باشد
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        # تبدیل postgres:// به postgresql:// برای سازگاری با SQLAlchemy
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgresql://instagram_bot_db_rjwl_user:J3V4Xv4nkU0V2cXm8RC6i0wfqxCoEv7t@dpg-d2s9i4e3jp1c739qa5n0-a/instagram_bot_db_rjwl', 'postgresql://instagram_bot_db_rjwl_user:J3V4Xv4nkU0V2cXm8RC6i0wfqxCoEv7t@dpg-d2s9i4e3jp1c739qa5n0-a.oregon-postgres.render.com/instagram_bot_db_rjwl', 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
    
    # تنظیمات اضافی برای دیتابیس
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 10,
        'pool_recycle': 300,
        'pool_pre_ping': True
    }
    
    # مقداردهی اولیه دیتابیس با اپلیکیشن
    db.init_app(app)
    
    # ثبت blueprint‌ها
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.accounts import accounts_bp
    from app.routes.messages import messages_bp
    from app.routes.bot_management import bot_management_bp
    from app.routes.verification import verification_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(accounts_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(bot_management_bp)
    app.register_blueprint(verification_bp)
    
    # ایجاد جداول دیتابیس در context اپلیکیشن
    with app.app_context():
        try:
            db.create_all()
            logging.info("Database tables created successfully")
        except Exception as e:
            logging.error(f"Error creating database tables: {e}")
    
    return app
