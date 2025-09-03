import os
from urllib.parse import urlparse

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_secret_key_here_change_this_in_production'
    
    # استفاده از PostgreSQL به جای SQLite
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    # اگر DATABASE_URL وجود دارد از آن استفاده کن، در غیر این صورت از SQLite محلی
    if DATABASE_URL:
        # تبدیل postgres:// به postgresql:// برای سازگاری با SQLAlchemy
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgresql://instagram_bot_db_rjwl_user:J3V4Xv4nkU0V2cXm8RC6i0wfqxCoEv7t@dpg-d2s9i4e3jp1c739qa5n0-a/instagram_bot_db_rjwl', 'postgresql://instagram_bot_db_rjwl_user:J3V4Xv4nkU0V2cXm8RC6i0wfqxCoEv7t@dpg-d2s9i4e3jp1c739qa5n0-a.oregon-postgres.render.com/instagram_bot_db_rjwl', 1)
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///users.db'
    
    DEBUG = os.environ.get('DEBUG') or True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
