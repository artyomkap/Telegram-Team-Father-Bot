from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.models import OrdinaryUser


main_kb = [
    [KeyboardButton(text="💎 Профиль"),
     KeyboardButton(text="💼 Трейд бот")],
    [KeyboardButton(text='🎆 NFT бот'),
     KeyboardButton(text='🗽 О проекте')]
]

admin_kb = [
    [KeyboardButton(text="💎 Профиль"),
     KeyboardButton(text="💼 Трейд бот")],
    [KeyboardButton(text='🎆 NFT бот'),
     KeyboardButton(text='🗽 О проекте')],
    [KeyboardButton(text='🧐 Админ панель')]
]

main = ReplyKeyboardMarkup(keyboard=main_kb, resize_keyboard=True)
main_admin = ReplyKeyboardMarkup(keyboard=admin_kb, resize_keyboard=True)

admin_panel_kb = [
    [KeyboardButton(text='Пользователи'),
     KeyboardButton(text='Реквизиты')],
    [KeyboardButton(text='Статистика'),
     KeyboardButton(text='Рассылка')],
    [KeyboardButton(text='Назад')]
]

admin_panel = ReplyKeyboardMarkup(keyboard=admin_panel_kb, resize_keyboard=True)

services_details_kb = [
    [InlineKeyboardButton(text='💼 Трейд бот', callback_data='details_service|1')],
    [InlineKeyboardButton(text='🎆 NFT бот', callback_data='details_service|2')]
]

services_details = InlineKeyboardMarkup(inline_keyboard=services_details_kb)

apply_kb = [
    [InlineKeyboardButton(text='Подать заявку', callback_data='apply')]
]

apply = InlineKeyboardMarkup(inline_keyboard=apply_kb)

application_send_kb = [
    [InlineKeyboardButton(text='Отправить', callback_data='send_application'),
     InlineKeyboardButton(text='Заново', callback_data='again')]
]

application_send = InlineKeyboardMarkup(inline_keyboard=application_send_kb)


def get_admin_accept_kb(user_id: int):
    admin_accept_kb = [
        [InlineKeyboardButton(text='✅ Принять', callback_data=f'request_accept_{user_id}'),
         InlineKeyboardButton(text='❌ Отклонить', callback_data=f'request_decline_{user_id}')]
    ]

    admin_accept = InlineKeyboardMarkup(inline_keyboard=admin_accept_kb)
    return admin_accept


сontrol_users_kb = [
    [InlineKeyboardButton(text='Действия с пользователями', callback_data='control_users')]
]

control_users = InlineKeyboardMarkup(inline_keyboard=сontrol_users_kb)

add_payment_details_kb = [
    [InlineKeyboardButton(text='Добавить', callback_data='add_payment_details')],
    [InlineKeyboardButton(text='Удалить', callback_data='delete_payment_details')],
    [InlineKeyboardButton(text='Назад', callback_data='back_to_admin')]
]

add_payment_details = InlineKeyboardMarkup(inline_keyboard=add_payment_details_kb)


add_payment_details_method_kb = [
    [InlineKeyboardButton(text='Карта', callback_data='add_payment_details_method|card')],
    [InlineKeyboardButton(text='BTC', callback_data='add_payment_details_method|btc')],
    [InlineKeyboardButton(text='Назад', callback_data='back_to_admin')]
]

add_payment_details_method = InlineKeyboardMarkup(inline_keyboard=add_payment_details_method_kb)

back_to_admin_kb = [
    [InlineKeyboardButton(text='Назад', callback_data='back_to_admin')]
]

back_to_admin = InlineKeyboardMarkup(inline_keyboard=back_to_admin_kb)


def get_set_props_kb(type: str):
    set_props_kb = [
        [InlineKeyboardButton(text='Карта', callback_data=f'set_payment_props_{type}_card')],
        [InlineKeyboardButton(text='USDT', callback_data=f'set_payment_props_{type}_usdt')],
        [InlineKeyboardButton(text='BTC', callback_data=f'set_payment_props_{type}_btc')],
        [InlineKeyboardButton(text='ETH', callback_data=f'set_payment_props_{type}_eth')],
        [InlineKeyboardButton(text='Назад', callback_data=f'back_to_admin')]
    ]

    set_props = InlineKeyboardMarkup(inline_keyboard=set_props_kb)
    return set_props

def get_create_props_kb():
    create_props_kb = [
        [InlineKeyboardButton(text='Создать', callback_data='create_payment_props')],
        [InlineKeyboardButton(text='Назад', callback_data='back_to_admin')]
    ]

    create_props = InlineKeyboardMarkup(inline_keyboard=create_props_kb)
    return create_props


def get_worker_panel_kb(ordinary_user_id: str):
    builder = InlineKeyboardBuilder()
    builder.button(text='Изменение баланса', callback_data=f'change_balance_{ordinary_user_id}')
    builder.button(text='Мин.Депозит', callback_data=f'min_deposit_{ordinary_user_id}')
    builder.button(text='Мин.Вывод', callback_data=f'min_withdraw_{ordinary_user_id}')
    builder.button(text='Вериф', callback_data=f'verif_{ordinary_user_id}')
    builder.button(text='Вывод', callback_data=f'withdraw_{ordinary_user_id}')
    builder.button(text='Покупка', callback_data=f'buy_{ordinary_user_id}')
    builder.button(text='Избранное', callback_data=f'favorite_{ordinary_user_id}')
    builder.button(text='Заблокировать', 
                   callback_data=f'block_{ordinary_user_id}')
    builder.button(text='Удалить', callback_data=f'delete_{ordinary_user_id}')
    builder.adjust(1,2,3,1)
    return builder.as_markup()

def get_worker_back_kb(ordinary_user_tg_id: str):
    builder = InlineKeyboardBuilder()
    builder.button(text='Назад', callback_data=f'management_{ordinary_user_tg_id}')
    return builder.as_markup()

def get_worker_select_kb(ordinary_users: list[OrdinaryUser]):
    builder = InlineKeyboardBuilder()
    for user in ordinary_users:
        builder.button(text=f'{user.tg_id}', callback_data=f'management_{user.tg_id}')
    return builder.as_markup()