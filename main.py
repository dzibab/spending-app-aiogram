from src.app_init import setup_bot
from src.bot_setup import bot, dp
from src.logger_config import setup_logging


if __name__ == "__main__":
    setup_logging()
    setup_bot()
    dp.run_polling(bot)
