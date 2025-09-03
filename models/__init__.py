from .user_manager import UserManager
from .message_manager import MessageManager
from .bot_manager import BotManager

# ایجاد نمونه‌های جهانی
user_manager = UserManager()
message_manager = MessageManager()
bot_manager = BotManager()

__all__ = ['UserManager', 'MessageManager', 'BotManager', 'user_manager', 'message_manager', 'bot_manager']