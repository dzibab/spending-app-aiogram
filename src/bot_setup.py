import os

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from dotenv import load_dotenv


load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set.")


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def get_bot_commands() -> list[BotCommand]:
    """Get the list of bot commands to be set in Telegram."""
    return [
        BotCommand(command="setcurrency", description="Set your default currency"),
        BotCommand(command="add", description="Add a new expense"),
    ]
