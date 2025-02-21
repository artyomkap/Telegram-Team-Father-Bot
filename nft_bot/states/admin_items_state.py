from aiogram.fsm.state import StatesGroup, State


class AdminCategoriesItems(StatesGroup):
    category = State()
    item = State()


class AdminItems(StatesGroup):
    item_name = State()
    item_description = State()
    item_price = State()
    item_author = State()
    item_photo = State()