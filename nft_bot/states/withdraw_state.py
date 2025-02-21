from aiogram.fsm.state import StatesGroup, State


class Withdraw(StatesGroup):
    amount = State()
    currency = State
