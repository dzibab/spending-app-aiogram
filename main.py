import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from dotenv import load_dotenv

from src.db import init_db, add_user, set_currency, add_expense
from src.constants import DEFAULT_CATEGORIES
from src.fsm import AddExpenseStates


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


@dp.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext) -> None:
    await message.answer("Enter the amount:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AddExpenseStates.amount)


@dp.message(AddExpenseStates.amount)
async def add_amount(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.strip():
        await message.answer("Amount cannot be empty. Please enter the amount:")
        return
    try:
        amount = float(message.text)
        await state.update_data(amount=amount)
    except ValueError:
        await message.answer("Amount must be a number. Please enter the amount:")
        return
    # Show categories as keyboard
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=cat)] for cat in DEFAULT_CATEGORIES],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await message.answer("Choose a category:", reply_markup=keyboard)
    await state.set_state(AddExpenseStates.category)


@dp.message(AddExpenseStates.category)
async def add_category(message: Message, state: FSMContext) -> None:
    category = message.text
    if category not in DEFAULT_CATEGORIES:
        await message.answer("Please choose a category from the list.")
        return
    await state.update_data(category=category)
    await message.answer(
        "Enter a description (or type '-' to skip):", reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(AddExpenseStates.description)


@dp.message(AddExpenseStates.description)
async def add_description(message: Message, state: FSMContext) -> None:
    description = message.text if message.text != "-" else ""
    data = await state.get_data()
    amount = data.get("amount")
    category = data.get("category")
    if not (amount and category):
        await message.answer("Something went wrong. Please try /add again.")
        await state.clear()
        return
    if not message.from_user or not message.from_user.id:
        await message.answer("User information is missing. Please try /add again.")
        await state.clear()
        return
    try:
        add_expense(message.from_user.id, amount, category, description)
    except ValueError as e:
        await message.answer(f"❌ Could not add expense: {e}")
        await state.clear()
        return
    await message.answer(
        f"✅ Added expense: {amount} {category} {description}",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.clear()


if __name__ == "__main__":
    dp.run_polling(bot)
