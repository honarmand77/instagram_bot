import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_secret_key_here_change_this_in_production'
    SQLITE_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///users.db'
    DEBUG = os.environ.get('DEBUG') or True