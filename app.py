# Entrypoint
from bot.telegram_bot import TelegramBot

bot = TelegramBot()

def main():
    bot.start_bot()


if __name__ == '__main__': 
    main()