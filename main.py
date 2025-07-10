from src.app_init import setup_bot
from src.bot_setup import bot, dp


if __name__ == "__main__":
    setup_bot()
    dp.run_polling(bot)
