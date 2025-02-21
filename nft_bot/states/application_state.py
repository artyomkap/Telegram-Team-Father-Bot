from aiogram.fsm.state import StatesGroup, State


class Application(StatesGroup):
    user_name = State()
    user_id = State()
    first_question = State()
    second_question = State()
    third_question = State()
