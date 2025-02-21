from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo,
                           ReplyKeyboardMarkup, KeyboardButton)
import config
from database.models import User, Promocode


def get_main_kb(kb_lang_data: dict, is_worker: bool) -> InlineKeyboardMarkup:
    lang_data = kb_lang_data['buttons']['main_kb']
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=lang_data['trade'], callback_data='trade'))
    kb.row(InlineKeyboardButton(text=lang_data['wallet'], callback_data='wallet'))
    kb.row(InlineKeyboardButton(text=lang_data['change_lang'], callback_data='change_lang'),
           InlineKeyboardButton(text=lang_data['change_currency'], 
                                callback_data='change_currency'))
    kb.row(InlineKeyboardButton(text=lang_data['verif'], 
                                callback_data='get_verif'),
        InlineKeyboardButton(text=lang_data['support'], callback_data='support'))
    kb.row(InlineKeyboardButton(text=lang_data['license'], 
                                url='https://www.okx.com/'))
    if is_worker:
        kb.row(InlineKeyboardButton(
            text='Управление рефералами', callback_data='manage_worker_referals'))
    return kb.as_markup()

def get_main_reply_markup(kb_lang_data: dict) -> ReplyKeyboardMarkup:
    lang_data = kb_lang_data['buttons']['main_reply_kb']
    kb = ReplyKeyboardBuilder()
    kb.row(KeyboardButton(text=lang_data['main']))
    return kb.as_markup(resize_keyboard=True)

def get_trade_kb(kb_lang_data: dict, user_tg_id: str) -> InlineKeyboardMarkup:
    lang_data = kb_lang_data['buttons']['trade_kb']
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text='FAQ', callback_data='trade_faq'))
    kb.row(InlineKeyboardButton(text=lang_data['crypto'], 
           web_app=WebAppInfo(
url=f'{config.WEBSITE_URL}/?trade=BINANCE:BTCUSDT&id={user_tg_id}'
)))
    kb.row(InlineKeyboardButton(text=lang_data['back'], callback_data='back'))
    return kb.as_markup()

def get_wallet_kb(kb_lang_data: dict) -> InlineKeyboardMarkup:
    lang_data = kb_lang_data['buttons']['wallet_kb']
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=lang_data['top_up'], callback_data='top_up'),
        InlineKeyboardButton(text=lang_data['withdraw'], callback_data='withdraw'))
    kb.row(InlineKeyboardButton(text=lang_data['promocode'], callback_data='promocode'))
    kb.row(InlineKeyboardButton(text=lang_data['back'], callback_data='back'))
    return kb.as_markup()

def get_top_up_kb(kb_lang_data: dict) -> InlineKeyboardMarkup:
    lang_data = kb_lang_data['buttons']['top_up_kb']
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=lang_data['card'], callback_data='card'))
    kb.row(InlineKeyboardButton(text=lang_data['crypto'], callback_data='crypto'))
    kb.row(InlineKeyboardButton(text=lang_data['back'], callback_data='back'))
    return kb.as_markup()

def get_select_crypto_currency_kb(kb_lang_data: dict = None) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text='BTC', callback_data='crypto_currency_btc'))
    kb.row(InlineKeyboardButton(text='ETH', callback_data='crypto_currency_eth'))
    kb.row(InlineKeyboardButton(text='USDT[TRC-20]', callback_data='crypto_currency_usdt'))
    return kb.as_markup()

def get_support_kb(kb_lang_data: dict) -> InlineKeyboardMarkup:
    lang_data = kb_lang_data['buttons']['support_kb']

    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=lang_data['check_payment'],
                                 callback_data='check_payment'))
    kb.row(InlineKeyboardButton(text=lang_data['support'], callback_data='support'))
    return kb.as_markup()

def get_back_kb(kb_lang_data: dict) -> InlineKeyboardMarkup:
    lang_data = kb_lang_data['buttons']['back_kb']
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=lang_data['back'], callback_data='back'))
    return kb.as_markup()


def get_select_lang_kb(kb_lang_data: dict = None) -> InlineKeyboardMarkup:
    kb_lang_data = kb_lang_data['buttons']['select_lang_kb']
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=kb_lang_data['set_lang_ru'], callback_data='set_lang_ru'),
           InlineKeyboardButton(text=kb_lang_data['set_lang_en'], callback_data='set_lang_en'))
    kb.row(InlineKeyboardButton(text=kb_lang_data['set_lang_pl'], callback_data='set_lang_pl'),
           InlineKeyboardButton(text=kb_lang_data['set_lang_ua'], callback_data='set_lang_ua'))
    kb.row(InlineKeyboardButton(text=kb_lang_data['back'], callback_data='back'))
    return kb.as_markup()


def get_select_currency_kb(kb_lang_data: dict, for_worker: bool = False) -> InlineKeyboardMarkup:
    lang_data = kb_lang_data['buttons']['select_currency_kb']
    kb = InlineKeyboardBuilder()
    prefix = '' if not for_worker else 'worker_'
    kb.row(InlineKeyboardButton(text=lang_data['set_currency_pln'],
                callback_data=f'{prefix}set_currency_pln'),
           InlineKeyboardButton(text=lang_data['set_currency_eur'],
                callback_data=f'{prefix}set_currency_eur'))
    kb.row(InlineKeyboardButton(text=lang_data['set_currency_rub'],
                callback_data=f'{prefix}set_currency_rub'),
           InlineKeyboardButton(text=lang_data['set_currency_uah'],
                callback_data=f'{prefix}set_currency_uah'))
    kb.row(InlineKeyboardButton(text=lang_data['set_currency_byn'],
                callback_data=f'{prefix}set_currency_byn'),
            InlineKeyboardButton(text=lang_data['set_currency_ils'],
                callback_data=f'{prefix}set_currency_ils'))
    if for_worker:
        kb.row(InlineKeyboardButton(text='Назад', callback_data='worker_back'))
    else:
        kb.row(InlineKeyboardButton(text=lang_data['back'], callback_data='back'))
    return kb.as_markup()


def get_support_page_kb(kb_lang_data: dict) -> InlineKeyboardMarkup:
    lang_data = kb_lang_data['buttons']['support_page_kb']
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=lang_data['support'], url='https://google.com/'))
    kb.row(InlineKeyboardButton(text=lang_data['back'], callback_data='back'))
    return kb.as_markup()


def get_verif_kb(kb_lang_data: dict) -> InlineKeyboardMarkup:
    lang_data = kb_lang_data['buttons']['verif_kb']
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=lang_data['get_verif'],
                                url=config.OKX_SUPPORT_LINK))
    kb.row(InlineKeyboardButton(text=kb_lang_data['buttons']['back_kb']['back'],
                                 callback_data='back'))
    return kb.as_markup()

###
# Worker keyboards
###

def get_main_worker_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text='🗂 Список пользователей', callback_data='worker_list')
    kb.button(text='✉ Рассылка', callback_data='worker_mailing')
    kb.button(text='Привязать реферала', callback_data='worker_bind')
    kb.button(text='💸 Мин.пополнение всем', callback_data='worker_min_deposit')
    kb.button(text='💸 Промокод', callback_data='worker_promocode')
    kb.button(text='💲 Задать валюту', callback_data='worker_set_currency')
    kb.button(text='💲 Мин.вывод', callback_data='worker_min_withdraw')
    kb.button(text='🗑 Удалить всех', callback_data='worker_delete_all')
    kb.adjust(1)
    return kb.as_markup()

def get_worker_select_user_kb(users: list[User]):
    kb = InlineKeyboardBuilder()
    for user in users:
        kb.button(text=user.fname or user.username or user.tg_id,
                   callback_data=f'worker_user_{user.id}')
    kb.button(text='🔍 Поиск', callback_data='worker_search')
    kb.button(text='🔙 Назад', callback_data='worker_back')
    kb.adjust(1)
    return kb.as_markup()

def get_worker_user_managment_kb(user: User):
    user_id = user.id
    is_win_enabled = '✅' if user.bets_result_win == True else ''
    is_random_ebabled = '✅' if user.bets_result_win is None else ''
    is_lose_enabled = '✅' if user.bets_result_win == False else ''

    builder = InlineKeyboardBuilder()
    builder.button(text='🔄 Обновить', callback_data=f'worker_user_{user_id}')
    builder.button(text=f'👑 Выигрыш{is_win_enabled}', callback_data=f'worker_win_{user_id}')
    builder.button(text=f'🏁 Прогрыш{is_lose_enabled}', callback_data=f'worker_lose_{user_id}')
    builder.button(text=f'🎲 Рандом{is_random_ebabled}',
                    callback_data=f'worker_random_{user_id}')
    if not user.is_verified:
        builder.button(text='❌ Выдать верификацию', callback_data=f'worker_verif_{user_id}')
    else:
        builder.button(text='✅ Снять верификацию', callback_data=f'worker_verif_{user_id}')
    if not user.bidding_blocked:
        builder.button(text='✅ Блокировать торги',
            callback_data=f'worker_blockbidding_{user_id}')
    else:
        builder.button(text='❌ Разблокировать торги',
            callback_data=f'worker_blockbidding_{user_id}')
    if not user.withdraw_blocked:
        builder.button(text='✅ Блокировать вывод',
                        callback_data=f'worker_block_withdraw_{user_id}')
    else:
        builder.button(text='❌ Разблокировать вывод',
                        callback_data=f'worker_block_withdraw_{user_id}')
    builder.button(text='💰 Изменить баланс', callback_data=f'worker_change_balance_{user_id}')
    builder.button(text='💰 Добавить к балансу', callback_data=f'worker_add_balance_{user_id}')
    builder.button(text='🔝 Максимальный баланс', callback_data=f'worker_max_balance_{user_id}')
    builder.button(text='💸 Минимальное пополнение', callback_data=f'worker_min_deposit_{user_id}')
    builder.button(text='✉ Написать', callback_data=f'worker_send_message_{user_id}')
    builder.button(text='💳 Мин.вывод', callback_data=f'worker_min_withdraw_{user_id}')
    builder.button(text='🗑 Удалить реферала', callback_data=f'worker_unbind_{user_id}')
    if not user.is_blocked:
        builder.button(text='🔒 Заблокировать', callback_data=f'worker_block_{user_id}')
    else:
        builder.button(text='🔒 Разблокировать', callback_data=f'worker_block_{user_id}')
    builder.button(text='🔙 Назад', callback_data='worker_back')
    builder.adjust(1, 3, 1, 2, 2, 2, 1)
    return builder.as_markup()

def get_worker_back_to_managment_kb(user: User) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text='🔙 Назад', callback_data=f'worker_user_{user.id}')
    return kb.as_markup()


def get_worker_menu_back_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text='🔙 Назад', callback_data='worker_back')
    return kb.as_markup()

def get_promocode_menu_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text='Создать промокод', callback_data='create_promocode')
    builder.button(text='Список промокодов', callback_data='get_promocode_list')
    builder.button(text='🔙 Назад', callback_data='worker_back')
    builder.adjust(2,1)
    return builder.as_markup()

def get_promocode_list_kb(promocodes: list[Promocode]):
    builder = InlineKeyboardBuilder()
    for promocode in promocodes:
        builder.button(text=promocode.code,callback_data=f'manage_promocode_{promocode.id}')

    builder.button(text='🔙 Назад', callback_data='worker_back')
    builder.adjust(1)
    return builder.as_markup()

def get_promocode_managment_kb(promocode: Promocode):
    builder = InlineKeyboardBuilder()
    builder.button(text='🗑 Удалить', callback_data=f'delete_promocode_{promocode.id}')
    builder.button(text='🔙 Назад', callback_data='worker_back')
    builder.adjust(1)
    return builder.as_markup()

def get_confirm_all_referals_deletion_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text='✅ Подтвердить', callback_data='confirm_all_referals_deletion')
    builder.button(text='🔙 Назад', callback_data='worker_back')
    builder.adjust(1)
    return builder.as_markup()

def get_worker_select_current_user_kb(user: User):
    builder = InlineKeyboardBuilder()
    builder.button(text=f"Управление аккаунтом пользователя {str(user)}",
                   callback_data=f'worker_user_{user.id}')
    builder.button(text='🔙 Назад', callback_data='worker_back')
    builder.adjust(1)
    return builder.as_markup()


def get_confirm_referal_deposit_kb(referal_id: str, amount: int):
    builder = InlineKeyboardBuilder()
    builder.button(text='✅ Подтвердить', 
                   callback_data=f'confirm_referal_deposit_{amount}_{referal_id}')

    builder.adjust(1)
    return builder.as_markup()

def get_confirm_referal_withdraw_kb(referal_id: str):
    builder = InlineKeyboardBuilder()
    builder.button(text='✅', 
                   callback_data=f'referal_withdraw_confirm_{referal_id}')

    builder.button(text='❌',
                   callback_data=f'referal_withdraw_decline_{referal_id}')
    builder.button(text='⚙️ В тех.поддержку',
                   callback_data=f'referal_withdraw_support_{referal_id}')
    builder.adjust(2,1)
    return builder.as_markup()

def get_referal_withdraw_support_kb(referal_id: str):
    builder = InlineKeyboardBuilder()
    builder.button(text='✅', 
                   callback_data=f'referal_withdraw_confirm_{referal_id}')

    builder.button(text='❌',
                   callback_data=f'referal_withdraw_decline_{referal_id}')
    builder.adjust(2)
    return builder.as_markup()