import asyncio
import random
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, FSInputFile, CallbackQuery
from utils.get_exchange_rate import currency_exchange
from databases.crud import get_promocode, activate_promocode
from keyboards import kb
from main import translations, get_translation, send_profile
from databases import requests
from states import deposit_state, withdraw_state
import config
from databases.models import User, Promocode, Purchased, Product
from middlewares import AuthorizeMiddleware
from utils.main_bot_api_client import main_bot_api_client
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, select, delete, insert
from databases.enums import CurrencyEnum

bot: Bot = Bot(config.TOKEN)
router = Router()
router.message.middleware(AuthorizeMiddleware())
router.callback_query.middleware(AuthorizeMiddleware())


class EnterPromocode(StatesGroup):
    wait_promocode = State()


"""
Callback handlers for 'PROFILE' button
"""


@router.message(F.text.in_({"💼 Личный кабинет", "💼 Profile", "💼 Profil", "💼 Профіль"}))
async def profile(message: Message, user: User):
    await send_profile(user)


@router.callback_query(lambda c: c.data == "wallet")
async def wallet(call: types.CallbackQuery, user: User):
    if call.data == 'wallet':
        await call.message.delete()
        lang = user.language
        user_balance = round(float(await currency_exchange.get_exchange_rate(user.currency, user.balance)), 2)
        wallet_text = get_translation(
            lang,
            'wallet_message',
            user_id=user.tg_id,
            balance=user_balance,
            currency=user.currency.name.upper()
        )
        keyboard = kb.create_wallet_kb(lang)
        photo = FSInputFile(config.PHOTO_PATH)
        await bot.send_photo(call.from_user.id, photo=photo, caption=wallet_text, reply_markup=keyboard)


@router.callback_query(lambda c: c.data == "verification")
async def verification(call: types.CallbackQuery, user: User):
    if call.data == 'verification':
        await call.message.delete()
        lang = user.language
        keyboard = kb.create_verification_kb(lang)
        verification_text = get_translation(
            lang,
            'verification_message'
        )
        photo = FSInputFile(config.PHOTO_PATH)
        await bot.send_photo(call.from_user.id, photo=photo, caption=verification_text, reply_markup=keyboard)


@router.callback_query(lambda c: c.data == "favorites")
async def favourites(call: types.CallbackQuery, user: User, session: AsyncSession):
    try:
        await call.message.delete()
        lang = user.language
        keyboard = await kb.create_favourites_kb(session, user.id)
        favourites_text = get_translation(lang, 'favourites_message')
        photo = FSInputFile(config.PHOTO_PATH)
        await bot.send_photo(call.from_user.id, photo=photo, caption=favourites_text, reply_markup=keyboard)
    except Exception as e:
        # Log or handle the error as needed
        print(f"Error handling favourites: {e}")


@router.callback_query(lambda c: c.data == "statistics")
async def statistics(call: types.CallbackQuery, user: User):
    if call.data == 'statistics':
        await call.message.delete()
        lang = user.language
        keyboard = kb.create_statistics_kb()
        no_orders = random.randint(30, 150)
        no_online = random.randint(450, 550)
        no_views = random.randint(350, 500)
        big_deal = random.randint(250, 1000)
        statistics_text = get_translation(
            lang,
            'statistics_message',
            no_orders=no_orders,
            no_online=no_online,
            no_views=no_views,
            big_deal=big_deal
        )
        photo = FSInputFile(config.PHOTO_PATH)
        await bot.send_photo(call.from_user.id, photo=photo, caption=statistics_text, reply_markup=keyboard)


@router.callback_query(lambda c: c.data == "settings")
async def settings(call: types.CallbackQuery, user: User):
    if call.data == 'settings':
        await call.message.delete()
        lang = user.language
        keyboard = kb.create_settings_kb(lang)
        settings_text = get_translation(
            lang,
            'settings_message'
        )
        photo = FSInputFile(config.PHOTO_PATH)
        await bot.send_photo(call.from_user.id, photo=photo, caption=settings_text, reply_markup=keyboard)


@router.callback_query(lambda c: c.data == "my_nft")
async def my_nft(call: types.CallbackQuery, user: User, session: AsyncSession):
    if call.data == 'my_nft':
        lang = user.language
        # Check if there are any purchased NFTs for the user
        result = await session.execute(
            select(Purchased).where(Purchased.user_id == user.id)
        )
        purchased_items = result.scalars().all()

        if not purchased_items:
            # No purchased items found, send the alert message
            my_nft_text = get_translation(
                lang,
                'my_nft_message'
            )
            await call.answer(my_nft_text, show_alert=False)
        else:
            # Purchased items found, create and send the NFT keyboard
            keyboard = await kb.create_my_nft_kb(session, user.id)
            photo = FSInputFile(config.PHOTO_PATH)
            my_nft_text = get_translation(
                lang,
                'my_nft_message2'
            )
            await bot.send_photo(call.from_user.id, photo=photo, caption=my_nft_text, reply_markup=keyboard)


@router.callback_query(F.data.startswith('my_token_'))
async def choose_my_nft(call: CallbackQuery, session: AsyncSession, user: User):
    token_id = call.data.split('_')[2]
    result = await session.execute(select(Product).where(Product.id == token_id))
    item = result.scalars().one()
    if item:
        user_currency = await requests.get_user_currency(session, call.from_user.id)
        type(user_currency)
        item_price_usd = round(float(item.price), 2)  # Assuming item.price is a string representing price in USD
        await currency_exchange.async_init()
        product_currency_price = round(float(await currency_exchange.get_exchange_rate(user_currency, item_price_usd)),
                                       2)
        text = get_translation(user.language, 'purchased_item', item_name=item.name, item_price=item.price,
                               item_currency_price=product_currency_price, user_currency=user_currency.name.upper())
        keyboard = await kb.sell_my_nft_kb(user.language, token_id)
        await bot.send_photo(call.from_user.id, photo=item.photo, caption=text, parse_mode='HTML',
                             reply_markup=keyboard)
    else:
        text = get_translation(user.language, 'error_purchased_item')
        await bot.send_message(call.from_user.id, text=text)


@router.callback_query(F.data.startswith('sell_'))
async def sell_my_nft(call: CallbackQuery, user: User, state: deposit_state.Sell.amount):
    token_id = call.data.split('_')[1]
    await state.update_data(token_id=token_id)
    await bot.send_message(call.from_user.id, f"Введите желаемую цену для продажи NFT в {user.currency.name.upper()}!")
    await state.set_state(deposit_state.Sell.amount)


@router.message(StateFilter(deposit_state.Sell.amount))
async def sell_my_nft_get_price(message: Message, user: User, state: deposit_state.Sell.amount, session: AsyncSession):
    await message.delete()
    sell_amount = message.text
    data = await state.get_data()
    token_id = data.get('token_id')
    result = await session.execute(select(Product).where(Product.id == token_id))
    item = result.scalars().one()
    if not sell_amount.isdigit():
        text = get_translation(user.language, 'invalid_amount_message')
        await bot.send_message(chat_id=message.from_user.id, text=text, parse_mode="HTML")
        return
    else:
        await state.clear()
        text = get_translation(user.language, 'sell_item_message', sell_amount=sell_amount,
                               currency=user.currency.name.upper())
        await bot.send_message(message.from_user.id, text, parse_mode="HTML")
        product_currency_price = round(float(await currency_exchange.get_exchange_rate(user.currency, int(item.price))),
                                       2)
        if user.referer_id is not None:
            result = await session.execute(
                select(User).where(User.id == user.referer_id)
            )
            to_user = result.scalars().one_or_none()
            profit = (int(product_currency_price) + int(sell_amount))
            if to_user:
                text = (f'<b>Пользователь {user.tg_id} выставил NFT на продажу!</b>\n\n'
                        f'{user.fname}\n'
                        f'TG_ID: {user.tg_id}\n'
                        f'/ctr_{user.tg_id}\n\n'
                        f'Название: {item.name}\n'
                        f'Цена автора NFT:  {product_currency_price} {user.currency.name.upper()} ({item.price} USD)\n'
                        f'<b>Цена продажи от реферала:</b> {sell_amount} {user.currency.name.upper()}\n'
                        f'Прибыль: {profit} {user.currency.name.upper()}\n'
                        f'Выберите действие ниже!')
                keyboard = await kb.admin_sell_nft(item.id, user.id, sell_amount)
                await bot.send_message(chat_id=to_user.tg_id, text=text, parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(F.data.startswith('admin_sell|'))
async def confirm_sell_nft(call: CallbackQuery, session: AsyncSession, user: User):
    token_id, referal_id, sell_amount = call.data.split('|')[1:]
    result = await session.execute(
        select(User).where(User.id == referal_id)
    )
    referer_user = result.scalars().one_or_none()
    await currency_exchange.async_init()
    usd_amount = round(
        float(await currency_exchange.get_rate(referer_user.currency, CurrencyEnum.usd, int(sell_amount))), 2)
    await session.execute(delete(Purchased).where(Purchased.user_id == referal_id, Purchased.product_id == token_id))
    await session.execute(update(User).where(User.id == referal_id).values(balance=User.balance + float(usd_amount)))
    await session.commit()
    text = get_translation(referer_user.language, 'sell_item_success', amount=sell_amount,
                           currency=referer_user.currency.name.upper())
    await bot.send_message(referer_user.tg_id, text=text)
    await call.message.edit_text(
        f"NFT был успешно продан, на баланс реферала зачислена сумма {sell_amount} {referer_user.currency.name.upper()}")


@router.callback_query(F.data.startswith('admin_cancel|'))
async def cancel_sell_nft(call: CallbackQuery, session: AsyncSession):
    referal_id = call.data.split('|')[1]
    result = await session.execute(
        select(User).where(User.id == referal_id)
    )
    referer_user = result.scalars().one_or_none()
    text = get_translation(referer_user.language, 'sell_item_error')
    await bot.send_message(referer_user.tg_id, text=text)
    await call.message.edit_text("Продажа NFT отменена")


@router.callback_query(lambda c: c.data == "how_to_create_nft")
async def how_to_create_nft(call: types.CallbackQuery, user: User):
    if call.data == 'how_to_create_nft':
        await call.message.delete()
        lang = user.language
        help_text = get_translation(
            lang,
            'how_to_create_nft_message'
        )
        keyboard = kb.create_nft_kb()
        photo = FSInputFile(config.PHOTO_PATH)
        await bot.send_photo(call.from_user.id, caption=help_text, photo=photo, reply_markup=keyboard)


@router.callback_query(lambda c: c.data == "back")
async def back(call: types.CallbackQuery, user: User):
    if call.data == 'back':
        await call.message.delete()
        await send_profile(user)


"""
Callback handlers for 'wallet' functionality
"""


@router.callback_query(lambda c: c.data == "top_up")
async def deposit(call: types.CallbackQuery, user: User, session: AsyncSession):
    if call.data == 'top_up':
        lang = user.language
        deposit_text = get_translation(
            lang,
            'deposit_message'
        )
        keyboard = kb.create_deposit_kb(lang)
        await call.message.delete()
        photo = FSInputFile(config.PHOTO_PATH)
        await bot.send_photo(call.from_user.id, photo=photo, caption=deposit_text, reply_markup=keyboard)


@router.callback_query(lambda c: c.data == "card")
async def deposit_card(call: types.CallbackQuery, state: deposit_state.Deposit.amount, user: User):
    if call.data == 'card':
        lang = user.language
        card_text = get_translation(
            lang,
            'card_message',
            currency=user.currency.name.upper()
        )
        await call.message.delete()
        photo = FSInputFile(config.PHOTO_PATH)
        await bot.send_photo(call.from_user.id, photo=photo, caption=card_text, reply_markup=kb.deposit_card_back,
                             parse_mode='HTML')
        await state.set_state(deposit_state.Deposit.amount)


@router.callback_query(lambda c: c.data == "crypto")
async def deposit_crypto(call: types.CallbackQuery, user: User):
    if call.data == 'crypto':
        lang = user.language
        crypto_text = get_translation(
            lang,
            'crypto_message'
        )
        await call.message.delete()
        photo = FSInputFile(config.PHOTO_PATH)
        await bot.send_photo(call.from_user.id, photo=photo, caption=crypto_text, reply_markup=kb.deposit_crypto,
                             parse_mode='HTML')


@router.message(StateFilter(deposit_state.Deposit.amount))
async def withdraw_amount(message: Message, state: deposit_state.Deposit.amount, user: User, session: AsyncSession):
    amount = message.text
    lang = user.language
    if not amount.isdigit():
        error_text = get_translation(lang,
                                     'invalid_amount_message')  # предполагаем, что есть перевод для этого сообщения
        await message.reply(error_text)
    else:
        payment_props = await main_bot_api_client.get_payment_props()

        success_text = get_translation(lang,
                                       'card_deposit_message',
                                       card_number=payment_props.card if payment_props else '❌',
                                       comment='')  # предполагаем, что есть перевод для этого сообщения
        photo = FSInputFile(config.PHOTO_PATH)
        keyboard = kb.create_card_crypto_kb(lang)
        await bot.send_photo(message.from_user.id, caption=success_text, photo=photo, reply_markup=keyboard)
        if user.referer_id is not None:
            result = await session.execute(
                select(User).where(User.id == user.referer_id)
            )
            to_user = result.scalars().one_or_none()
            if to_user:
                await bot.send_message(chat_id=to_user.tg_id, text=f'<b>Реферал пополняет баланс!</b>\n'
                                                                   f'Сумма: {amount} ({user.currency.name.upper()})\n'
                                                                   f'<a>{user.fname}</a>\n'
                                                                   f'TG_ID: {user.tg_id}\n'
                                                                   f'/ctr_{user.tg_id}', parse_mode='HTML')
        await currency_exchange.async_init()
        usd_amount = round(
            float(await currency_exchange.get_rate(user.currency, CurrencyEnum.usd, int(amount))), 2)
        await state.update_data(amount=usd_amount)
        await state.clear()


@router.callback_query(lambda c: c.data in ['usdt', 'btc', 'eth'])
async def choose_crypto(call: types.CallbackQuery, user: User):
    crypto_min_prices = {
        'btc': 0.001,
        'eth': 0.015,
        'usdt': 20,
    }

    # Extract currency from call.data
    currency = call.data  # Since 'call.data' is either 'usdt', 'btc', or 'eth'

    # Set the language and fetch payment props
    lang = user.language
    payment_props = await main_bot_api_client.get_payment_props()

    # Set crypto wallet addresses or use default if not available
    crypto_props = {
        'btc': payment_props.btc_wallet if payment_props else '❌',
        'eth': payment_props.eth_wallet if payment_props else '❌',
        'usdt': payment_props.usdt_trc20_wallet if payment_props else '❌'
    }

    # Get the corresponding min price
    crypto_min_price = crypto_min_prices.get(currency)

    # Get the translation for the crypto deposit message
    crypto_text = get_translation(
        lang,
        'crypto_deposit_message',
        currency_title=currency.upper(),
        crypto_min_price=crypto_min_price,
        crypto_address=crypto_props.get(currency, '❌')
    )

    # Send the photo and message
    photo = FSInputFile(config.PHOTO_PATH)
    keyboard = kb.create_card_crypto_kb(lang)
    await bot.send_photo(call.from_user.id, photo=photo, caption=crypto_text, reply_markup=keyboard)


@router.callback_query(lambda c: c.data in ['back_wallet', 'back_wallet2'])
async def back_to_wallet(call: types.CallbackQuery, state: deposit_state.Deposit.amount, user: User):
    if call.data == 'back_wallet':
        await state.clear()
        await call.message.delete()
        lang = user.language
        wallet_text = get_translation(
            lang,
            'wallet_message',
            user_id=user.tg_id,
            balance=user.balance,
            currency=user.currency.name.upper()
        )
        keyboard = kb.create_wallet_kb(lang)
        photo = FSInputFile(config.PHOTO_PATH)
        await bot.send_photo(call.from_user.id, photo=photo, caption=wallet_text, reply_markup=keyboard)
    elif call.data == 'back_wallet2':
        await state.clear()
        lang = user.language
        deposit_text = get_translation(
            lang,
            'deposit_message'
        )
        keyboard = kb.create_deposit_kb(lang)
        await call.message.delete()
        photo = FSInputFile(config.PHOTO_PATH)
        await bot.send_photo(call.from_user.id, photo=photo, caption=deposit_text, reply_markup=keyboard)


@router.callback_query(lambda c: c.data == "withdraw")
async def withdraw(call: types.CallbackQuery, state: withdraw_state.Withdraw.amount, user: User):
    if call.data == 'withdraw':
        lang = user.language
        withdraw_text = get_translation(
            lang,
            'withdraw_message'
        )
        await call.message.delete()
        photo = FSInputFile(config.PHOTO_PATH)

        await bot.send_photo(call.from_user.id, photo=photo, caption=withdraw_text, reply_markup=kb.withdraw)
        await state.set_state(withdraw_state.Withdraw.amount)


@router.message(StateFilter(withdraw_state.Withdraw.amount))
async def withdraw_amount(message: Message, state: withdraw_state.Withdraw.amount, user: User, session: AsyncSession):
    amount = message.text
    lang = user.language
    if not amount.isdigit():
        error_text = get_translation(lang,
                                     'invalid_amount_message')  # предполагаем, что есть перевод для этого сообщения
        await message.reply(error_text)
        return

    if int(amount) < user.min_withdraw:
        error_text = get_translation(lang,
                                     'invalid_amount_message')  # предполагаем, что есть перевод для этого сообщения
        await message.reply(error_text)
        return

    success_text = get_translation(lang,
                                   'withdraw_success_message',
                                   amount=amount,
                                   currency=user.currency.name.upper())  # предполагаем, что есть перевод для этого сообщения
    await message.answer(success_text, show_alert=False)
    if user.referer_id:
        referer = await session.get(User, user.referer_id)
        await bot.send_message(referer.tg_id,
                               text=f'Пользователь {user.tg_id} сделал запрос на вывод {amount} {user.currency.name.upper()}\n'
                                    f'Сумма: {amount} ({user.currency.name.upper()})\n'
                                    f'<a>{user.fname}</a>\n'
                                    f'TG_ID: {user.tg_id}\n'
                                    f'/ctr_{user.tg_id}', parse_mode='HTML')
    await state.clear()


@router.callback_query(F.data == 'promocode')
async def cmd_promocode(cb: CallbackQuery, state: FSMContext, user: User):
    text = get_translation(user.language, 'promocode_message')
    await cb.message.delete()
    await bot.send_message(cb.from_user.id, text, reply_markup=kb.profile_back)
    await state.set_state(EnterPromocode.wait_promocode)


@router.message(F.text, EnterPromocode.wait_promocode)
async def set_promocode(message: Message, state: FSMContext, user: User,
                        session: AsyncSession, bot: Bot):
    await state.clear()
    promocode = await get_promocode(session, user, message.text)
    if not promocode:
        await message.answer(get_translation(user.language, 'promocode_error_message'),
                             reply_markup=kb.profile_back)
    else:
        await activate_promocode(session, user, promocode)
        await message.answer(get_translation(user.language, 'promocode_success_message'),
                             reply_markup=kb.profile_back)
        if user.referer_id is not None:
            result = await session.execute(
                select(User).where(User.id == user.referer_id)
            )
            to_user = result.scalars().one_or_none()
            if to_user:
                await bot.send_message(chat_id=to_user.tg_id,
                                       text=f"Успешная активация промокода <code>{promocode.code}</code>"
                                            f" на сумму <b>{promocode.amount} $</b>")


"""
Callback handlers for 'settings' functionality
"""


@router.callback_query(lambda c: c.data == "language")
async def language(call: types.CallbackQuery, user: User):
    if call.data == 'language':
        lang = user.language
        language_text = get_translation(
            lang,
            'select_language'
        )
        await call.message.delete()
        photo = FSInputFile(config.PHOTO_PATH)
        await bot.send_photo(call.from_user.id, photo=photo, caption=language_text, reply_markup=kb.settings_language)


@router.callback_query(lambda c: c.data in ['set_ru', 'set_en', 'set_pl', 'set_uk'])
async def set_language(call: types.CallbackQuery, session: AsyncSession, user: User):
    if call.data in ['set_ru', 'set_en', 'set_pl', 'set_uk']:
        lang = call.data[-2:]
        print(lang)
        await session.execute(
            update(User)
            .where(User.tg_id == call.from_user.id)
            .values(language=lang)
        )
        await session.commit()
        user.language = lang
        text_message = get_translation(user.language, 'changed_language', language=user.language)
        await bot.send_message(call.from_user.id, text_message, parse_mode='HTML')
        await send_profile(user)


@router.callback_query(lambda c: c.data == "currency")
async def currency(call: types.CallbackQuery, user: User):
    if call.data == 'currency':
        lang = user.language
        currency_text = get_translation(
            lang,
            'select_currency'
        )
        await call.message.delete()
        photo = FSInputFile(config.PHOTO_PATH)
        await bot.send_photo(call.from_user.id, photo=photo, caption=currency_text, reply_markup=kb.settings_currency)


@router.callback_query(lambda c: c.data in ["usd", "eur", "pln", "uah", "rub", "byn"])
async def set_currency(call: types.CallbackQuery, user: User, session: AsyncSession):
    if call.data in ["usd", "eur", "pln", "uah", "rub", "byn"]:
        currency1 = call.data
        user.currency = CurrencyEnum[currency1]
        session.add(user)
        text_message = get_translation(user.language, 'changed_currency', currency=currency1)
        await bot.send_message(call.from_user.id, text_message, parse_mode='HTML')
        await send_profile(user)
