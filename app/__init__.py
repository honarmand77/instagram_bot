from flask import Flask
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

# متغیر global برای ربات‌های فعال
active_bots = {}

def create_app():
    app = Flask(__name__)
    app.secret_key = 'your_secret_key_here_change_this_in_production'
    
    # تنظیمات پایگاه داده
    app.config['SQLITE_DATABASE_URI'] = 'sqlite:///users.db'
    
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
    
    return app