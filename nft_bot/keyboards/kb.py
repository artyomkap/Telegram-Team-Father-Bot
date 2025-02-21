import json
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

import config
from databases import requests
from sqlalchemy.ext.asyncio import AsyncSession

from databases.models import User, Promocode, UserPromocodeAssotiation, Favourites, Product, Purchased

languages = ["en", "ru", "pl", "uk"]
translations = {}

for lang in languages:
    with open(f"locales/{lang}.json", "r", encoding="utf-8") as file:
        translations[lang] = json.load(file)


# Функция для получения перевода
def get_translation(lang, key, **kwargs):
    translation = translations[lang].get(key, key)
    if isinstance(translation, dict):
        translation = translation.get(kwargs['status'], kwargs['status'])
    return translation.format(**kwargs)


def create_main_kb(lang, user):
    buttons = translations[lang]["buttons"].get('main_kb', {})
    main_kb = [
        [KeyboardButton(text='🎆 NFT')],
        [KeyboardButton(text=buttons['profile_main'])],
        [KeyboardButton(text=buttons['information_main']),
         KeyboardButton(text=buttons['support_main'])]
    ]
    if user.is_worker:
        main_kb.append([KeyboardButton(text='Воркер')])
    main = ReplyKeyboardMarkup(keyboard=main_kb, resize_keyboard=True)

    return main


def create_admin_main_kb(lang, user):
    buttons = translations[lang]["buttons"].get('main_kb', {})
    admin_main_kb = [
        [KeyboardButton(text='🎆 NFT')],
        [KeyboardButton(text=buttons['profile_main'])],
        [KeyboardButton(text=buttons['information_main']),
         KeyboardButton(text=buttons['support_main'])],
        [KeyboardButton(text='Админ-панель')]
    ]
    if user.is_worker:
        admin_main_kb.append([KeyboardButton(text='Воркер')])
    admin_main = ReplyKeyboardMarkup(keyboard=admin_main_kb, resize_keyboard=True)

    return admin_main


admin_panel_kb = [
    [InlineKeyboardButton(text='Ворк-панель', callback_data='work_panel')],
    [InlineKeyboardButton(text='Добавить категорию', callback_data='add_category'),
     InlineKeyboardButton(text='Добавить товар', callback_data='add_item')],
    [InlineKeyboardButton(text='Удалить категорию', callback_data='delete_category'),
     InlineKeyboardButton(text='Удалить товар', callback_data='delete_item')],
]

admin_panel = InlineKeyboardMarkup(inline_keyboard=admin_panel_kb)

work_panel_kb = [
    [InlineKeyboardButton(text='Управление промокодами', callback_data='worker_promocode')],
    [InlineKeyboardButton(text='Сообщение рефералам', callback_data='referral_message')],
    [InlineKeyboardButton(text='Привязать по ID', callback_data='connect_mamont')],
    [InlineKeyboardButton(text='Управление 🦣', callback_data='control_mamonts')],
    [InlineKeyboardButton(text='⬅️', callback_data='back_to_admin')]
]

work_panel = InlineKeyboardMarkup(inline_keyboard=work_panel_kb)

back_to_admin_button = InlineKeyboardButton(text='⬅️', callback_data='back_to_admin2')
back_to_admin = InlineKeyboardMarkup(inline_keyboard=[[back_to_admin_button]])

language_kb = [
    [InlineKeyboardButton(text='🇷🇺 Русский', callback_data='ru'),
     InlineKeyboardButton(text='🇬🇧 English', callback_data='en')],
    [InlineKeyboardButton(text='🇵🇱 Polski', callback_data='pl'),
     InlineKeyboardButton(text='🇺🇦 Український', callback_data='uk')]
]

language = InlineKeyboardMarkup(inline_keyboard=language_kb)


def create_profile_kb(lang):
    buttons = translations[lang]["buttons"].get('profile_kb', {})
    profile_kb = [
        [InlineKeyboardButton(text=buttons['wallet'], callback_data='wallet')],
        [InlineKeyboardButton(text=buttons['verification'], callback_data='verification'),
         InlineKeyboardButton(text=buttons['favorites'], callback_data='favorites')],
        [InlineKeyboardButton(text=buttons['statistics'], callback_data='statistics'),
         InlineKeyboardButton(text=buttons['settings'], callback_data='settings')],
        [InlineKeyboardButton(text=buttons['my_nft'], callback_data='my_nft'),
         InlineKeyboardButton(text=buttons['agreement'], url=config.AGREEMENT_URL)],
        [InlineKeyboardButton(text=buttons['how_to_create_nft'], callback_data='how_to_create_nft')]
    ]

    profile = InlineKeyboardMarkup(row_width=2, inline_keyboard=profile_kb)
    return profile


def create_wallet_kb(lang):
    buttons = translations[lang]["buttons"].get('wallet_kb', {})
    wallet_kb = [
        [InlineKeyboardButton(text=buttons['top_up'], callback_data='top_up'),
         InlineKeyboardButton(text=buttons['withdraw'], callback_data='withdraw')],
        [InlineKeyboardButton(text=buttons['promocode'], callback_data='promocode')],
        [InlineKeyboardButton(text='⬅️', callback_data='back')]
    ]

    wallet = InlineKeyboardMarkup(inline_keyboard=wallet_kb)
    return wallet


def create_verification_kb(lang):
    buttons = translations[lang]["buttons"].get('verification_kb', {})
    verification_kb = [
        [InlineKeyboardButton(text=buttons['verify'], url=config.SUPPORT_URL)],
        [InlineKeyboardButton(text='⬅️', callback_data='back')]
    ]

    verification = InlineKeyboardMarkup(inline_keyboard=verification_kb)
    return verification


async def create_buy_keyboard(lang, item_id, user_id, session):
    buttons = translations[lang]["buttons"].get('catalog_kb', {})

    # Query to check if the item is in the user's favorites
    result = await session.execute(
        select(Favourites).where(Favourites.user_id == user_id and Favourites.product_id == item_id)
    )
    favourite_item = result.scalars().first()

    # Determine the correct label and callback data for the favourites button
    if favourite_item:
        favourites_button_text = '💔'  # Fallback text if translation is missing
        favourites_callback_data = f'delete_from_favourites_{item_id}'
    else:
        favourites_button_text = '🤍️'  # Fallback text if translation is missing
        favourites_callback_data = f'add_to_favourites_{item_id}'

    buy_kb = [
        [InlineKeyboardButton(text=buttons['buy'], callback_data=f'buy_{item_id}')],
        [InlineKeyboardButton(text=favourites_button_text, callback_data=favourites_callback_data)],
        [InlineKeyboardButton(text='⬅️', callback_data='back_to_catalog')]
    ]

    buy = InlineKeyboardMarkup(inline_keyboard=buy_kb)
    return buy


def create_statistics_kb():
    statistics_kb = [
        [InlineKeyboardButton(text='⬅️', callback_data='back')]
    ]
    statistics = InlineKeyboardMarkup(inline_keyboard=statistics_kb)
    return statistics


def create_settings_kb(lang):
    buttons = translations[lang]["buttons"].get('settings_kb', {})
    settings_kb = [
        [InlineKeyboardButton(text=buttons['language'], callback_data='language')],
        [InlineKeyboardButton(text=buttons['currency'], callback_data='currency')],
        [InlineKeyboardButton(text='⬅️️', callback_data='back')]
    ]

    settings = InlineKeyboardMarkup(inline_keyboard=settings_kb)
    return settings


def create_nft_kb():
    nft_kb = [
        [InlineKeyboardButton(text='⬅️️', callback_data='back')]
    ]
    nft = InlineKeyboardMarkup(inline_keyboard=nft_kb)
    return nft


def create_deposit_kb(lang):
    buttons = translations[lang]["buttons"].get('deposit_kb', {})
    deposit_kb = [
        [InlineKeyboardButton(text=buttons['card'], callback_data='card'),
         InlineKeyboardButton(text=buttons['crypto'], callback_data='crypto')],
        [InlineKeyboardButton(text='⬅️️', callback_data='back_wallet')]
    ]

    deposit = InlineKeyboardMarkup(inline_keyboard=deposit_kb)
    return deposit


withdraw_kb = [
    [InlineKeyboardButton(text='⬅️️', callback_data='back_wallet')]
]

withdraw = InlineKeyboardMarkup(inline_keyboard=withdraw_kb)

deposit_card_back_kb = [
    [InlineKeyboardButton(text='⬅️️️️', callback_data='back_wallet2')]
]

deposit_card_back = InlineKeyboardMarkup(inline_keyboard=deposit_card_back_kb)

deposit_crypto_kb = [
    [InlineKeyboardButton(text='USDT [TRC-20]', callback_data='usdt')],
    [InlineKeyboardButton(text='BTC', callback_data='btc')],
    [InlineKeyboardButton(text='ETH', callback_data='eth')],
    [InlineKeyboardButton(text='⬅️️️️', callback_data='back_wallet2')]
]

deposit_crypto = InlineKeyboardMarkup(inline_keyboard=deposit_crypto_kb)

profile_back_kb = [
    [InlineKeyboardButton(text='⬅️️', callback_data='back')]
]

profile_back = InlineKeyboardMarkup(inline_keyboard=profile_back_kb)


def create_card_crypto_kb(lang):
    buttons = translations[lang]["buttons"].get('deposit_top_up_kb', {})
    deposit_kb = [
        [InlineKeyboardButton(text=buttons['check'], callback_data='check_payment')],
        [InlineKeyboardButton(text=buttons['support'], url=config.SUPPORT_URL)],
    ]

    deposit = InlineKeyboardMarkup(inline_keyboard=deposit_kb)
    return deposit


settings_language_kb = [
    [InlineKeyboardButton(text='🇷🇺 Русский', callback_data='set_ru'),
     InlineKeyboardButton(text='🇬🇧 English', callback_data='set_en')],
    [InlineKeyboardButton(text='🇵🇱 Polski', callback_data='set_pl'),
     InlineKeyboardButton(text='🇺🇦 Український', callback_data='set_uk')],
    [InlineKeyboardButton(text='⬅️️', callback_data='back')]
]

settings_language = InlineKeyboardMarkup(inline_keyboard=settings_language_kb)

settings_currency_kb = [
    [InlineKeyboardButton(text='🇺🇦 UAH', callback_data='uah'),
     InlineKeyboardButton(text='🇪🇺 EUR', callback_data='eur')],
    [InlineKeyboardButton(text='🇵🇱 PLN', callback_data='pln'),
     InlineKeyboardButton(text='🇷🇺 RUB', callback_data='rub')],
    [InlineKeyboardButton(text='🇧🇾 BYN', callback_data='byn')],
    [InlineKeyboardButton(text='⬅️️', callback_data='back')]
]

settings_currency = InlineKeyboardMarkup(inline_keyboard=settings_currency_kb)


async def get_categories_kb(session: AsyncSession):
    categories = await requests.get_categories(session)
    categories_kb = [
        [InlineKeyboardButton(text=category.name, callback_data=f'category_{category.id}')] for category in categories
    ]

    categories = InlineKeyboardMarkup(inline_keyboard=categories_kb)
    return categories


async def get_categories_kb2(session: AsyncSession):
    categories = await requests.get_categories(session)
    categories_kb = [
        [InlineKeyboardButton(text=category.name, callback_data=f'delete_category_{category.id}')] for category in
        categories
    ]

    categories = InlineKeyboardMarkup(inline_keyboard=categories_kb)
    return categories


async def get_delete_items_kb(session: AsyncSession):
    items = await requests.get_items(session)
    items_kb = [
        [InlineKeyboardButton(text=item.name, callback_data=f'delete_item_{item.id}')] for item in items
    ]

    items = InlineKeyboardMarkup(inline_keyboard=items_kb)
    return items


async def create_collections_keyboard(session: AsyncSession):
    categories_with_count = await requests.get_categories_with_item_count(session)
    categories_kb = [
        [InlineKeyboardButton(text=f"{category.name} ({category.item_count})",
                              callback_data=f'collection_{category.id}')]
        for category in categories_with_count
    ]
    navigation_buttons = [
        InlineKeyboardButton(text="⬅️", callback_data='left'),
        InlineKeyboardButton(text="1/1", callback_data='zero'),
        InlineKeyboardButton(text='➡️️', callback_data='right')
    ]
    categories_kb.append(navigation_buttons)

    categories_markup = InlineKeyboardMarkup(inline_keyboard=categories_kb)
    return categories_markup


async def create_items_keyboard(category_id, session: AsyncSession):
    items = await requests.get_items_by_category_id(session, category_id)
    items_kb = [
        [InlineKeyboardButton(text=f'{item.name} (${round(float(item.price), 2)})', callback_data=f'token_{item.id}')] for item in items
    ]
    navigation_buttons = [
        InlineKeyboardButton(text="⬅️", callback_data='left'),
        InlineKeyboardButton(text="1/1", callback_data='zero'),
        InlineKeyboardButton(text='➡️️', callback_data='right')
    ]
    items_kb.append(navigation_buttons)

    items_markup = InlineKeyboardMarkup(inline_keyboard=items_kb)
    return items_markup


async def create_mamont_control_kb(mamont_id, session):
    result = await session.execute(select(User).where(User.tg_id == int(mamont_id)))
    user = result.scalars().first()

    if user.is_buying:
        user_is_buying = 'Покупка включена'
    else:
        user_is_buying = 'Покупка выключена'

    if user.is_withdraw:
        user_is_withdraw = 'Вывод включен'
    else:
        user_is_withdraw = 'Вывод выключен'

    if user.is_verified:
        user_is_verified = 'Не вериф'
        call_is_verified = 'unverify'
    else:
        user_is_verified = 'Вериф'
        call_is_verified = 'verify'

    if user.is_blocked:
        user_is_blocked = '🔓 Разблокировать'
        call_is_blocked = 'unblock'
    else:
        user_is_blocked = '🔒 Заблокировать'
        call_is_blocked = 'block'

    keyboard = [
        [InlineKeyboardButton(text='✉️ Отправить сообщение ', callback_data='mamont|send_message')],
        [InlineKeyboardButton(text='💵 Изм. баланса', callback_data='mamont|change_balance')],
        [InlineKeyboardButton(text='📥 Мин. депозит', callback_data='mamont|min_deposit'),
         InlineKeyboardButton(text='📤 Мин. вывод', callback_data='mamont|min_withdraw')],
        [InlineKeyboardButton(text=f'🔺 {user_is_verified}', callback_data=f'mamont|{call_is_verified}'),
         InlineKeyboardButton(text='🔰 Вывод', callback_data='mamont|withdraw'),
         InlineKeyboardButton(text='🔰 Покупка', callback_data='mamont|buying')],
        [InlineKeyboardButton(text=f'{user_is_blocked}', callback_data=f'mamont|{call_is_blocked}')],
        [InlineKeyboardButton(text='🗑 Удалить лохматого', callback_data='mamont|delete')],
        [InlineKeyboardButton(text='♻️ Обновить сообщение', callback_data='mamont|update')]
    ]

    keyboard_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    return keyboard_markup


def get_worker_menu_back_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text='Назад', callback_data='worker_back')
    return kb.as_markup()


def get_promocode_currency_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text='🇺🇦 UAH', callback_data='promo_uah')
    kb.button(text='🇪🇺 EUR', callback_data='promo_eur')
    kb.button(text='🇵🇱 PLN', callback_data='promo_pln')
    kb.button(text='🇷🇺 RUB', callback_data='promo_rub')
    kb.button(text='🇧🇾 BYN', callback_data='promo_byn')
    kb.button(text='🇺🇸 USD', callback_data='promo_usd')
    kb.button(text='Назад', callback_data='worker_back')
    kb.adjust(3, 3, 1)
    return kb.as_markup()


def get_promocode_menu_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text='Создать промокод', callback_data='create_promocode')
    builder.button(text='Список промокодов', callback_data='get_promocode_list')
    builder.button(text='Назад', callback_data='worker_back')
    builder.adjust(2, 1)
    return builder.as_markup()


def get_promocode_list_kb(promocodes: list[Promocode]):
    builder = InlineKeyboardBuilder()
    for promocode in promocodes:
        builder.button(text=promocode.code, callback_data=f'manage_promocode_{promocode.id}')

    builder.button(text='Назад', callback_data='worker_back')
    builder.adjust(1)
    return builder.as_markup()


def get_promocode_managment_kb(promocode: Promocode):
    builder = InlineKeyboardBuilder()
    builder.button(text='Удалить', callback_data=f'delete_promocode_{promocode.id}')
    builder.button(text='Назад', callback_data='worker_back')
    builder.adjust(1)
    return builder.as_markup()


def get_worker_select_current_user_kb(user: User):
    builder = InlineKeyboardBuilder()
    builder.button(text=f"Управление аккаунтом пользователя {str(user)}",
                   callback_data=f'worker_user|{user.tg_id}')
    builder.button(text='Назад', callback_data='worker_back')
    builder.adjust(1)
    return builder.as_markup()


async def create_favourites_kb(session: AsyncSession, user_id: int):
    # Fetch the list of user's favourite items
    result = await session.execute(
        select(Favourites).where(Favourites.user_id == user_id)
    )
    favourite_items = result.scalars().all()

    favourites_kb = []

    # Dynamically add product buttons to the keyboard
    for fav in favourite_items:
        # Load the associated product for the favourite item
        product_result = await session.execute(
            select(Product).where(Product.id == fav.product_id)
        )
        product = product_result.scalar_one_or_none()

        if product:
            # Create button text and callback data
            button_text = f"{product.name} - {product.price}"
            callback_data = f"token_{product.id}"
            favourites_kb.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])

    # You can add navigation buttons or any additional buttons as needed
    navigation_kb = [
        InlineKeyboardButton(text="⬅️", callback_data='left'),
        InlineKeyboardButton(text=f"{len(favourite_items)}", callback_data='page_count'),
        InlineKeyboardButton(text='➡️️', callback_data='right')
    ]

    back_button = [InlineKeyboardButton(text='⬅️', callback_data='back')]

    # Combine the favourites, navigation, and back buttons into one keyboard
    favourites_kb.append(navigation_kb)
    favourites_kb.append(back_button)

    return InlineKeyboardMarkup(inline_keyboard=favourites_kb)


async def create_my_nft_kb(session: AsyncSession, user_id: int):
    result = await session.execute(
        select(Purchased).where(Purchased.user_id == user_id)
    )
    purchased_items = result.scalars().all()

    purchased_kb = []

    for item in purchased_items:
        product_result = await session.execute(
            select(Product).where(Product.id == item.product_id)
        )
        product = product_result.scalar_one_or_none()

        if product:
            # Create button text and callback data
            button_text = f"{product.name}"
            callback_data = f"my_token_{product.id}"
            purchased_kb.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])

        back_button = [InlineKeyboardButton(text='⬅️', callback_data='back')]
        purchased_kb.append(back_button)

        return InlineKeyboardMarkup(inline_keyboard=purchased_kb)


async def sell_my_nft_kb(lang, item_id):
    buttons = translations[lang]["buttons"].get('sell_nft_kb', {})
    kb = [
        [InlineKeyboardButton(text=buttons['sell1'], callback_data=f'sell_{item_id}')],
        [InlineKeyboardButton(text='⬅️', callback_data='my_nft')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


async def admin_sell_nft(item_id, referal_id, sell_amount):
    kb = [
        [InlineKeyboardButton(text='✅ Подтвердить продажу',
                              callback_data=f'admin_sell|{item_id}|{referal_id}|{sell_amount}')],
        [InlineKeyboardButton(text='❌ Отклонить продажу', callback_data=f'admin_cancel|{referal_id}')]
    ]

    return InlineKeyboardMarkup(inline_keyboard=kb)
