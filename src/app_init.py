from src.db import init_db
from src.handlers import register_handlers
from .bot_setup import bot, dp, get_bot_commands


async def on_startup() -> None:
    """Handle bot startup tasks such as initializing the database and setting commands."""
    # Initialize DB
    init_db()
    # Set bot commands
    await bot.set_my_commands(get_bot_commands())
    # Register handlers
    register_handlers(dp)


def setup_bot() -> None:
    """Setup the bot and dispatcher."""
    dp.startup.register(on_startup)
