import json
import random
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import StateFilter
from aiogram.types import Message, FSInputFile
from keyboards import kb
from databases import requests
from databases.enums import CurrencyEnum
from states import deposit_state, withdraw_state, admin_items_state
import config
from utils.get_exchange_rate import currency_exchange
from databases.models import User, Product, Favourites, Purchased
from middlewares import AuthorizeMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, insert, delete
from databases.enums import CurrencyEnum
from utils.main_bot_api_client import main_bot_api_client
from sqlalchemy import update, select

bot: Bot = Bot(config.TOKEN)
router = Router()
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


@router.message(F.text == '🎆 NFT')
async def nft_panel(message: types.Message, user: User, session: AsyncSession):
    lang = user.language
    if user.is_blocked:
        await message.answer(get_translation(lang, 'blocked'))
    else:
        collections_number = await requests.get_category_count(session)
        nft_text = get_translation(
            lang,
            'catalog_message',
            collections_number=collections_number
        )
        keyboard = await kb.create_collections_keyboard(session)
        photo = FSInputFile(config.PHOTO_PATH)
        await bot.send_photo(message.from_user.id, caption=nft_text, photo=photo, parse_mode="HTML",
                             reply_markup=keyboard)


@router.callback_query(lambda c: c.data.startswith('collection_'))
async def choose_collection(call: types.CallbackQuery, user: User, session: AsyncSession):
    collection_id = call.data.split('_')[1]
    categories_with_count = await requests.get_categories_with_item_count_by_id(session, int(collection_id))

    if categories_with_count:
        category = categories_with_count[0]  # Поскольку мы ожидаем только одну категорию, берем первый элемент списка
        lang = user.language
        nft_text = get_translation(
            lang,
            'collection_message',
            collection_name=category.name,
            number_of_tokens=category.item_count
        )
        keyboard = await kb.create_items_keyboard(collection_id, session)
        photo = FSInputFile(config.PHOTO_PATH)
        await bot.send_photo(call.from_user.id, caption=nft_text, photo=photo, parse_mode="HTML", reply_markup=keyboard)
    else:
        await call.answer("Category not found.", show_alert=True)


@router.callback_query(lambda c: c.data.startswith('token_'))
async def choose_item(call: types.CallbackQuery, user: User, session: AsyncSession):
    item_id = call.data.split('_')[1]
    lang = user.language
    item = await requests.get_item_info(session, int(item_id))

    if not item:
        await call.answer("Item not found")
        return

    type(user.currency)

    user_currency = await requests.get_user_currency(session, call.from_user.id)
    type(user_currency)
    random_price = random.randint(1, 100)
    item_price_usd = round(float(item.price), 2) + random_price  # Assuming item.price is a string representing price in USD
    await currency_exchange.async_init()
    product_currency_price = round(float(await currency_exchange.get_exchange_rate(user_currency, item_price_usd)), 2)

    item_id, item_name, item_description, item_price, item_author, item_photo, category_name = item

    token_text = get_translation(
        lang,
        'token_message',
        token_name=item_name,
        item_description=item_description,
        category_name=category_name,
        item_author=item_author,
        item_price=item_price_usd,
        item_currency_price=product_currency_price,
        user_currency=user_currency.value
    )

    keyboard = await kb.create_buy_keyboard(lang, item_id, user.id, session)
    await bot.send_photo(call.from_user.id, caption=token_text, photo=item_photo, parse_mode="HTML",
                         reply_markup=keyboard)


@router.callback_query(lambda c: c.data.startswith('buy_'))
async def buy_item(call: types.CallbackQuery, user: User, session: AsyncSession):
    item_id = call.data.split('_')[1]
    lang = user.language
    item = await requests.get_item_info(session, int(item_id))

    if not item:
        await call.answer("Item not found")
        return

    item_id, item_name, item_description, item_price, item_author, item_photo, category_name = item
    user_balance = user.balance
    if user_balance < float(item_price):
        token_text = get_translation(
            lang,
            'buy_no_balance',
            token_name=item_name,
            item_description=item_description,
            category_name=category_name,
            item_author=item_author,
            item_price=item.price
        )
    else:
        token_text = get_translation(
            lang,
            'buy_success',
            token_name=item_name,
            item_description=item_description,
            category_name=category_name,
            item_author=item_author,
            item_price=item.price
        )
        await user.top_up_balance(session, -float(item_price))
        # Add item to purchased list
        purchased_item = Purchased(user_id=user.id, product_id=item_id)
        session.add(purchased_item)
        await session.commit()
        product_currency_price = round(float(await currency_exchange.get_exchange_rate(user.currency, int(item.price))),
                                       2)
        if user.referer_id is not None:
            result = await session.execute(
                select(User).where(User.id == user.referer_id)
            )
            to_user = result.scalars().one_or_none()
            if to_user:
                await bot.send_message(chat_id=to_user.tg_id, text=f'<b>Реферал купил токен</b>\n'
                                                                   f'Сумма: {product_currency_price} {user.currency.value.upper()} ({item.price} USD)\n'
                                                                   f'Токен: {item_name}\n\n'
                                                                   f'<a>{user.fname}</a>\n'
                                                                   f'TG_ID: {user.tg_id}\n'
                                                                   f'/ctr_{user.tg_id}', parse_mode='HTML')

    await bot.send_message(call.from_user.id, text=token_text)


@router.callback_query(lambda c: c.data.startswith('add_to_favourites'))
async def add_to_favourites(call: types.CallbackQuery, user: User, session: AsyncSession):
    item_id = int(call.data.split('_')[3])
    await session.execute(
        insert(Favourites).values(user_id=user.id, product_id=item_id))
    await session.commit()
    fav_text = get_translation(user.language, "add_to_fav")
    await call.answer(fav_text)
    lang = user.language
    item = await requests.get_item_info(session, int(item_id))

    if not item:
        await call.answer("Item not found")
        return

    type(user.currency)

    user_currency = await requests.get_user_currency(session, call.from_user.id)
    type(user_currency)
    item_price_usd = round(float(item.price), 2)  # Assuming item.price is a string representing price in USD
    await currency_exchange.async_init()
    product_currency_price = await currency_exchange.get_exchange_rate(user_currency, item_price_usd)

    item_id, item_name, item_description, item_price, item_author, item_photo, category_name = item

    token_text = get_translation(
        lang,
        'token_message',
        token_name=item_name,
        item_description=item_description,
        category_name=category_name,
        item_author=item_author,
        item_price=item.price,
        item_currency_price=product_currency_price,
        user_currency=user_currency.value
    )
    keyboard = await kb.create_buy_keyboard(lang, item_id, user.id, session)
    await bot.send_photo(call.from_user.id, caption=token_text, photo=item_photo, parse_mode="HTML",
                         reply_markup=keyboard)


@router.callback_query(lambda c: c.data.startswith('delete_from_favourites'))
async def delete_from_favourites(call: types.CallbackQuery, user: User, session: AsyncSession):
    item_id = int(call.data.split('_')[3])  # Extract item_id from the callback data
    await session.execute(
        delete(Favourites).where(Favourites.user_id == user.id, Favourites.product_id == item_id)
    )
    await session.commit()
    fav_text = get_translation(user.language, "delete_from_fav")
    await call.answer(fav_text)
    lang = user.language
    item = await requests.get_item_info(session, int(item_id))

    if not item:
        await call.answer("Item not found")
        return

    type(user.currency)

    user_currency = await requests.get_user_currency(session, call.from_user.id)
    type(user_currency)
    item_price_usd = round(float(item.price), 2)  # Assuming item.price is a string representing price in USD
    await currency_exchange.async_init()
    product_currency_price = await currency_exchange.get_exchange_rate(user_currency, item_price_usd)

    item_id, item_name, item_description, item_price, item_author, item_photo, category_name = item

    token_text = get_translation(
        lang,
        'token_message',
        token_name=item_name,
        item_description=item_description,
        category_name=category_name,
        item_author=item_author,
        item_price=item.price,
        item_currency_price=product_currency_price,
        user_currency=user_currency.value
    )
    keyboard = await kb.create_buy_keyboard(lang, item_id, user.id, session)
    await bot.send_photo(call.from_user.id, caption=token_text, photo=item_photo, parse_mode="HTML",
                         reply_markup=keyboard)


@router.callback_query(lambda c: c.data.startswith('back_to_catalog'))
async def back_to_catalog(call: types.CallbackQuery, user: User, session: AsyncSession):
    if user:
        if user.is_blocked:
            await call.answer(get_translation(user.language, 'blocked'))
        else:
            collections_number = await requests.get_category_count(session)
            nft_text = get_translation(
                user.language,
                'catalog_message',
                collections_number=collections_number
            )
            keyboard = await kb.create_collections_keyboard(session)
            photo = FSInputFile(config.PHOTO_PATH)
            await bot.send_photo(call.from_user.id, caption=nft_text, photo=photo, parse_mode="HTML",
                                 reply_markup=keyboard)
    else:
        await bot.send_message(call.from_user.id, text=f'Выберите язык:\nSelect a language:', parse_mode="HTML",
                               reply_markup=kb.language)
