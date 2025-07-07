import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv

from db import init_db, add_user


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


@dp.message(Command("start"))
async def cmd_start(message: Message) -> None:
    if message.from_user is not None:
        add_user(message.from_user.id)
    await message.answer(
        "👋 Welcome to Spending Tracker Bot!\n"
        "Set your default currency with /setcurrency (e.g. /setcurrency USD).\n"
        "Add expenses with /add."
    )


if __name__ == "__main__":
    init_db()
    dp.run_polling(bot)
