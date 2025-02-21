from aiogram.fsm.state import StatesGroup, State


class WorkerPanel(StatesGroup):
    mamont_id = State()
    referal_ms_text = State()


class WorkerReferal(StatesGroup):
    referal_id = State()
    balance_amount = State()
    min_deposit = State()
    min_withdraw = State()
    mamont_message = State()