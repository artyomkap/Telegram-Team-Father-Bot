from aiogram.fsm.state import StatesGroup, State


class SendApplication(StatesGroup):
    first_question = State()
    second_question = State()
    third_question = State()


