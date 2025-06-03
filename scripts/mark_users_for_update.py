from database.user import UserRepository
from bot.telegram_bot import TelegramBot
import sys 


# To Execute, run docker-compose exec app bash
# Then run python3 scripts/mark_users_for_update.py

UserRepository.mark_users_for_update()