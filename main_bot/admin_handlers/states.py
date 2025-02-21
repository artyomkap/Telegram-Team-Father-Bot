from aiogram.fsm.state import StatesGroup, State


class ControlUsers(StatesGroup):
    user_id = State()
    write_message = State()


class CreatePaymentProps(StatesGroup):
    wait_card = State()
    wait_usdt = State()
    wait_btc = State()
    wait_eth = State()

class UpdateCurrentPaymentProps(StatesGroup):
    waiting = State()


class Mailing(StatesGroup):
    text = State()