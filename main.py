import logging
import os

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from src.db import init_db
from src.handlers import register_handlers


# ENV
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set.")

# Logging
logging.basicConfig(level=logging.INFO)

# Bot and Dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
dp.startup.register(init_db)

# Register handlers
register_handlers(dp)


if __name__ == "__main__":
    dp.run_polling(bot)
