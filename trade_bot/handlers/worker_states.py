from aiogram.fsm.state import StatesGroup, State


class CreatePromocode(StatesGroup):
    wait_code = State()
    wait_amount = State()
    wait_type = State()  # одноразовый или многоразовый


class SearchReferal(StatesGroup):
    wait_tg_id = State()


class ManageReferal(StatesGroup):
    wait_balance_amount = State()
    wait_deposit_amount = State()
    wait_min_withdraw_amount = State()
    wait_min_deposit_amount = State()
    wait_max_balance_amount = State()
    wait_message = State()


class ManageAllReferals(StatesGroup):
    wait_message = State()
    wait_min_deposit = State()
    wait_min_withdraw = State()
    wait_binding_id = State()
