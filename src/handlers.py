import logging

from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    BufferedInputFile,
)

from .db import (
    add_user,
    set_currency,
    add_expense,
    get_user_stats_for_period,
    export_user_data,
    get_recent_expenses,
    delete_expense,
)
from .constants import DEFAULT_CATEGORIES
from .fsm import AddExpenseStates, RemoveExpenseStates
from .utils import format_stats_message, format_expense_list


def register_handlers(dp: Dispatcher) -> None:
    """Register all handlers with the dispatcher"""
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_setcurrency, Command("setcurrency"))
    dp.message.register(cmd_add, Command("add"))
    dp.message.register(add_amount, AddExpenseStates.amount)
    dp.message.register(add_category, AddExpenseStates.category)
    dp.message.register(add_description, AddExpenseStates.description)
    dp.message.register(cmd_remove, Command("remove"))
    dp.message.register(select_expense_to_remove, RemoveExpenseStates.selecting_expense)
    dp.message.register(
        confirm_expense_deletion, RemoveExpenseStates.confirming_deletion
    )
    dp.message.register(cmd_stats, Command("stats"))
    dp.message.register(cmd_export, Command("export"))
    logging.info("Handlers registered.")


async def cmd_start(message: Message) -> None:
    if message.from_user is not None:
        add_user(message.from_user.id)
        logging.info(f"User {message.from_user.id} started the bot.")
    await message.answer(
        "Welcome to Spending Tracker Bot!\n\n"
        "Easily track your daily expenses, analyze your spending habits, and stay on top of your budget.\n\n"
        "✨ What you can do:\n"
        "• Add new expenses with /add\n"
        "• Remove recent expenses with /remove\n"
        "• Get detailed stats for week, month, or year with /stats <week|month|year>\n"
        "• Set your preferred currency with /setcurrency (e.g. /setcurrency USD)\n"
        "• Export your data with /export\n\n"
        "Start by setting your currency and adding your first expense!"
    )


async def cmd_setcurrency(message: Message) -> None:
    if not message.from_user or not message.text:
        logging.warning("/setcurrency called without user or text.")
        return
    args = message.text.split()
    if len(args) != 2:
        await message.answer("Usage: /setcurrency USD")
        logging.warning("/setcurrency called with wrong number of arguments.")
        return
    currency = args[1].upper()
    if not (len(currency) == 3 and currency.isalpha()):
        await message.answer(
            "Please provide a valid 3-letter currency code (e.g. USD, EUR)."
        )
        logging.warning(f"Invalid currency code: {currency}")
        return
    set_currency(message.from_user.id, currency)
    logging.info(f"User {message.from_user.id} set currency to {currency}.")
    await message.answer(f"✅ Default currency set to {currency}.")


async def cmd_add(message: Message, state: FSMContext) -> None:
    logging.info(
        f"User {message.from_user.id if message.from_user else 'unknown'} started adding an expense."
    )
    await message.answer("Enter the amount:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AddExpenseStates.amount)


async def add_amount(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.strip():
        await message.answer("Amount cannot be empty. Please enter the amount:")
        logging.warning("Amount not provided or empty.")
        return
    try:
        amount = float(message.text)
        await state.update_data(amount=amount)
        logging.info(f"Amount entered: {amount}")
    except ValueError:
        await message.answer("Amount must be a number. Please enter the amount:")
        logging.warning(f"Invalid amount entered: {message.text}")
        return
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=cat)] for cat in DEFAULT_CATEGORIES],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await message.answer("Choose a category:", reply_markup=keyboard)
    await state.set_state(AddExpenseStates.category)


async def add_category(message: Message, state: FSMContext) -> None:
    category = message.text
    if category not in DEFAULT_CATEGORIES:
        await message.answer("Please choose a category from the list.")
        logging.warning(f"Invalid category selected: {category}")
        return
    await state.update_data(category=category)
    logging.info(f"Category selected: {category}")
    await message.answer(
        "Enter a description (or type '-' to skip):", reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(AddExpenseStates.description)


async def add_description(message: Message, state: FSMContext) -> None:
    description = message.text if message.text != "-" else ""
    data = await state.get_data()
    amount = data.get("amount")
    category = data.get("category")
    if not (amount and category):
        await message.answer("Something went wrong. Please try /add again.")
        await state.clear()
        logging.error("Missing amount or category in FSM state data.")
        return
    if not message.from_user or not message.from_user.id:
        await message.answer("User information is missing. Please try /add again.")
        await state.clear()
        logging.error("User information missing in add_description handler.")
        return
    try:
        add_expense(message.from_user.id, amount, category, description)
        logging.info(
            f"Expense added for user {message.from_user.id}: {amount} {category} {description}"
        )
    except ValueError as e:
        await message.answer(f"❌ Could not add expense: {e}")
        await state.clear()
        logging.error(f"Failed to add expense: {e}")
        return
    await message.answer(
        f"✅ Added expense: {amount} {category} {description}",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.clear()


async def cmd_stats(message: Message) -> None:
    if not message.from_user or not message.text:
        await message.answer("/stats called without user or text.")
        return
    args = message.text.split()
    if len(args) != 2 or args[1] not in ("week", "month", "year"):
        await message.answer(
            "Usage: /stats <week|month|year>\n"
            "week — last 7 days, month — from 1st day of current month, year — from 1st January of current year."
        )
        return
    period = args[1]
    try:
        user_id = message.from_user.id
        user_currency, category_totals, total = get_user_stats_for_period(
            user_id, period
        )
        msg = format_stats_message(period, category_totals, total, user_currency)
        await message.answer(msg, parse_mode="HTML")
    except ValueError as e:
        await message.answer(str(e))
    except Exception as e:
        logging.error(f"/stats error: {e}")
        await message.answer("❌ Could not fetch stats. Please try again later.")


async def cmd_export(message: Message) -> None:
    """Export all data for the current user as a file."""
    if not message.from_user:
        return
    user_id = message.from_user.id

    file_bytes, filename = export_user_data(user_id)
    if not file_bytes:
        await message.answer("No data found to export.")
        return
    file_bytes.seek(0)
    safe_filename = filename or f"spending_export_{user_id}.csv"
    file = BufferedInputFile(file_bytes.read(), safe_filename)
    await message.answer_document(file, caption="Your data export.")


async def cmd_remove(message: Message, state: FSMContext) -> None:
    """Show recent expenses and allow user to select one for removal."""
    if not message.from_user:
        await message.answer("User information is missing.")
        return

    try:
        expenses = get_recent_expenses(message.from_user.id, limit=10)
        if not expenses:
            await message.answer("You don't have any expenses to remove.")
            return

        # Store expenses in FSM data for later reference
        await state.update_data(expenses=expenses)

        # Format and send the expense list
        expense_list = format_expense_list(expenses)
        await message.answer(
            expense_list, parse_mode="HTML", reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(RemoveExpenseStates.selecting_expense)

        logging.info(f"User {message.from_user.id} requested to remove an expense.")
    except ValueError as e:
        await message.answer(f"❌ {e}")
        logging.error(f"Error in cmd_remove: {e}")
    except Exception as e:
        await message.answer("❌ Could not fetch expenses. Please try again later.")
        logging.error(f"Unexpected error in cmd_remove: {e}")


async def select_expense_to_remove(message: Message, state: FSMContext) -> None:
    """Handle user selection of expense to remove."""
    if not message.text or not message.text.strip():
        await message.answer("Please enter a valid number (1-10).")
        return

    try:
        selection = int(message.text.strip())
        data = await state.get_data()
        expenses = data.get("expenses", [])

        if not expenses:
            await message.answer("No expenses found. Please try /remove again.")
            await state.clear()
            return

        if selection < 1 or selection > len(expenses):
            await message.answer(
                f"Please enter a number between 1 and {len(expenses)}."
            )
            return

        # Get the selected expense (convert to 0-based index)
        selected_expense = expenses[selection - 1]

        # Store the selected expense for confirmation
        await state.update_data(selected_expense=selected_expense)

        # Show confirmation message
        amount = selected_expense["amount"]
        category = selected_expense["category"]
        currency = selected_expense["currency"]
        description = selected_expense.get("description", "")
        created_at = selected_expense["created_at"]
        expense_id = selected_expense["id"]

        # Format date
        if hasattr(created_at, "strftime"):
            date_str = created_at.strftime("%B %d, %Y at %H:%M")
        else:
            date_str = str(created_at)

        desc_text = f"\nDescription: {description}" if description else ""

        confirmation_text = (
            f"🗑️ <b>Confirm Deletion</b>\n\n"
            f"You are about to delete:\n"
            f"<b>{amount} {currency}</b> • {category}{desc_text}\n"
            f"Date: {date_str}\n\n"
            f"Type 'yes' to confirm deletion or 'no' to cancel."
        )

        await message.answer(confirmation_text, parse_mode="HTML")
        await state.set_state(RemoveExpenseStates.confirming_deletion)

        if message.from_user:
            logging.info(
                f"User {message.from_user.id} selected expense {expense_id} for removal."
            )

    except ValueError:
        await message.answer("Please enter a valid number (1-10).")
        logging.warning(f"Invalid number entered for expense selection: {message.text}")
    except Exception as e:
        await message.answer("❌ Something went wrong. Please try /remove again.")
        await state.clear()
        logging.error(f"Error in select_expense_to_remove: {e}")


async def confirm_expense_deletion(message: Message, state: FSMContext) -> None:
    """Handle confirmation of expense deletion."""
    if not message.text or not message.from_user:
        await message.answer("Invalid input. Please try /remove again.")
        await state.clear()
        return

    user_response = message.text.strip().lower()

    if user_response not in ["yes", "no"]:
        await message.answer("Please type 'yes' to confirm deletion or 'no' to cancel.")
        return

    if user_response == "no":
        await message.answer("❌ Deletion cancelled.")
        await state.clear()
        logging.info(f"User {message.from_user.id} cancelled expense deletion.")
        return

    # User confirmed deletion
    try:
        data = await state.get_data()
        selected_expense = data.get("selected_expense")

        if not selected_expense:
            await message.answer("❌ No expense selected. Please try /remove again.")
            await state.clear()
            return

        expense_id = selected_expense["id"]
        success = delete_expense(message.from_user.id, expense_id)

        if success:
            amount = selected_expense["amount"]
            category = selected_expense["category"]
            currency = selected_expense["currency"]
            await message.answer(
                f"✅ Successfully deleted expense: <b>{amount} {currency}</b> • {category}",
                parse_mode="HTML",
            )
            logging.info(
                f"User {message.from_user.id} successfully deleted expense {expense_id}."
            )
        else:
            await message.answer(
                "❌ Could not delete expense. It may have already been removed."
            )
            logging.warning(
                f"Failed to delete expense {expense_id} for user {message.from_user.id}."
            )

    except Exception as e:
        await message.answer("❌ Something went wrong while deleting the expense.")
        logging.error(f"Error in confirm_expense_deletion: {e}")

    await state.clear()
