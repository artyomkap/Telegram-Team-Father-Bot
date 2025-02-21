from aiogram.fsm.state import StatesGroup, State


class TopUpBalanceWithCard(StatesGroup):
    wait_amount = State()

class WithdrawBalance(StatesGroup):
    wait_amount = State()


class EnterPromocode(StatesGroup):
    wait_promocode = State()