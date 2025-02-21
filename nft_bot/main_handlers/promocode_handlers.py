from aiogram.filters.state import State, StatesGroup


class PromocodeMenu(StatesGroup):
    wait = State()

class CreatePromocode(StatesGroup):
    wait_code = State()
    wait_amount = State()
    wait_currency = State()
    wait_type = State() # одноразовый или многоразовый
    delete_menu = State()

class ManagePromocode(StatesGroup):
    select_promocode = State()
    manage_promocode = State()
    delete_promocode = State()


