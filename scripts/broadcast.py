from database.user import UserRepository
from bot.telegram_bot import TelegramBot
import sys 
from logger import logger


# To Execute, run docker-compose exec app bash
# Then run python3 scripts/broadcast.py "Put you message in here" 

telegram_bot = TelegramBot()
message_content = sys.argv[1]
users = UserRepository.get_users()
for user in users: 
    try:
        logger.info(f"chat_id: {user.chat_id}  is_updated: {user.is_updated}")
        telegram_bot.bot.send_message(user.chat_id, message_content)
        logger.info(f"Done {user.chat_id}")
    except:
        logger.error(f'Exception ->{user.chat_id}', exc_info=True)
        continue