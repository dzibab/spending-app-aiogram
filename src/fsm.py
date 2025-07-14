from aiogram.fsm.state import State, StatesGroup


class AddExpenseStates(StatesGroup):
    amount = State()
    category = State()
    description = State()


class RemoveExpenseStates(StatesGroup):
    selecting_expense = State()
    confirming_deletion = State()
