import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv

from db import init_db, add_user, set_currency


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


@dp.message(Command("start"))
async def cmd_start(message: Message) -> None:
    if message.from_user is not None:
        add_user(message.from_user.id)
    await message.answer(
        "👋 Welcome to Spending Tracker Bot!\n"
        "Set your default currency with /setcurrency (e.g. /setcurrency USD).\n"
        "Add expenses with /add."
    )


@dp.message(Command("setcurrency"))
async def cmd_setcurrency(message: Message) -> None:
    if not message.from_user or not message.text:
        return
    args = message.text.split()
    if len(args) != 2:
        await message.answer("Usage: /setcurrency USD")
        return
    currency = args[1].upper()
    if not (len(currency) == 3 and currency.isalpha()):
        await message.answer(
            "Please provide a valid 3-letter currency code (e.g. USD, EUR)."
        )
        return
    set_currency(message.from_user.id, currency)
    await message.answer(f"✅ Default currency set to {currency}.")


if __name__ == "__main__":
    dp.run_polling(bot)
