import json
import random
import string
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, FSInputFile, CallbackQuery
from keyboards import kb
from databases import requests
from main_handlers.promocode_handlers import CreatePromocode
from states import deposit_state, withdraw_state, admin_items_state, worker_state
import config
from sqlalchemy.ext.asyncio import AsyncSession
from databases.models import User, Promocode, UserPromocodeAssotiation
from sqlalchemy import update, select, delete
from databases.crud import (get_created_promocodes, get_promocode_by_code)
from utils.get_exchange_rate import currency_exchange
from databases.enums import CurrencyEnum

bot: Bot = Bot(config.TOKEN)
router = Router()
languages = ["en", "ru", "pl", "uk"]
translations = {}

for lang in languages:
    with open(f"locales/{lang}.json", "r", encoding="utf-8") as file:
        translations[lang] = json.load(file)


@router.message(F.text == 'Воркер')
async def open_work_panel(message: Message, user: User, session: AsyncSession):
    if user.is_worker:
        await bot.send_message(chat_id=message.from_user.id, text='Ворк-панель: ',
                               parse_mode="HTML", reply_markup=kb.work_panel)
    if not user.is_worker:
        user.is_worker = True
        session.add(user)
        await bot.send_message(chat_id=message.from_user.id, text='Ворк-панель: ',
                               parse_mode="HTML", reply_markup=kb.work_panel)


@router.callback_query(lambda c: c.data == 'work_panel')
async def work_panel(call: types.CallbackQuery):
    await bot.edit_message_text(chat_id=call.from_user.id, message_id=call.message.message_id, text='Ворк-панель: ',
                                parse_mode="HTML", reply_markup=kb.work_panel)


@router.callback_query(F.data == 'referral_message')
async def get_message_to_referals(call: CallbackQuery, state: worker_state.WorkerPanel.referal_ms_text, user: User,
                                  session: AsyncSession):
    await bot.edit_message_text(chat_id=call.from_user.id, message_id=call.message.message_id,
                                text='Введите сообщение для всех рефералов:', parse_mode="HTML")
    await state.set_state(worker_state.WorkerPanel.referal_ms_text)


@router.message(StateFilter(worker_state.WorkerPanel.referal_ms_text))
async def send_message_to_referals(message: types.Message, user: User, state: worker_state.WorkerPanel.referal_ms_text,
                                   session: AsyncSession):
    referal_ms_text = message.text
    digit_count = sum(char.isdigit() for char in referal_ms_text)

    # Check if there are more than 4 digits in the message
    if digit_count > 4:
        await bot.send_message(
            chat_id=message.from_user.id,
            text='Ваше сообщение содержит более 4-х цифр. Пожалуйста, уменьшите количество цифр и попробуйте снова.',
            parse_mode="HTML"
        )
        return

    result = await session.execute(select(User).where(User.referer_id == user.id))
    referals = result.scalars().all()
    for referal in referals:
        await bot.send_message(chat_id=referal.tg_id, text=referal_ms_text,
                               parse_mode="HTML")
    await state.clear()


@router.callback_query(lambda c: c.data == 'connect_mamont')
async def connect_mamont(call: types.CallbackQuery, state: worker_state.WorkerPanel.referal_id):
    await bot.edit_message_text(chat_id=call.from_user.id, message_id=call.message.message_id,
                                text='Введите <b>ID</b> реферала:', parse_mode="HTML")
    await state.set_state(worker_state.WorkerPanel.referal_id)


@router.message(StateFilter(worker_state.WorkerPanel.referal_id))
async def connect_referal_id(message: types.Message, user: User, state: worker_state.WorkerPanel.referal_id,
                            session: AsyncSession):
    referal_id = message.text
    await state.clear()

    if not referal_id.isdigit():
        await bot.send_message(chat_id=message.from_user.id, text='Введите корректный referal_id!', parse_mode="HTML")
        return

    result = await session.execute(select(User).where(User.tg_id == int(referal_id)))
    user1 = result.scalars().first()

    if not user1:
        await bot.send_message(chat_id=message.from_user.id, text='Такого referal_id не существует!', parse_mode="HTML")
        return

    elif user1.referer_id is not None:
        await bot.send_message(chat_id=message.from_user.id, text='Этот referal_id уже привязан!', parse_mode="HTML")
        pass

    else:
        await state.update_data(referal_id=referal_id)
        await session.execute(
            update(User)
            .where(User.tg_id == referal_id)
            .values(referer_id=user.id)
        )
        await state.clear()
        await bot.send_message(chat_id=message.from_user.id, text='Реферал привязан!', parse_mode="HTML")


@router.callback_query(lambda c: c.data == 'control_mamonts')
async def control_mamonts(call: types.CallbackQuery, user: User, session: AsyncSession,
                          state: worker_state.WorkerReferal.referal_id):
    result = await session.execute(select(User).where(User.referer_id == user.id))
    users = result.scalars().all()

    if users:
        text = 'Рефералы:\n\n'
        for user in users:
            user_balance = round(float(await user.get_balance()), 2)
            text += f'/r_{user.tg_id} | {user.username} | {user_balance} {user.currency.name.upper()}\n'
        text += f'\n<b>Всего рефералов:</b> {len(users)}'
        text += '\nНажмите на ID реферала для управления: '
    else:
        text = 'У вас нет рефералов.'

    await bot.edit_message_text(chat_id=call.from_user.id, message_id=call.message.message_id, text=text,
                                parse_mode="HTML", reply_markup=kb.back_to_admin)
    await state.set_state(worker_state.WorkerReferal.referal_id)


@router.message(F.text.startswith('/ctr_'))
async def mamont_control_panel2(message: Message, session: AsyncSession, user: User,
                                state: worker_state.WorkerReferal.referal_id):
    referal_id = message.text.strip()[5:]
    if not referal_id.isdigit():
        await bot.send_message(chat_id=message.from_user.id, text='Введите корректный referal_id!', parse_mode="HTML")
        return
    result = await session.execute(select(User).where(User.tg_id == int(referal_id)))
    referer = result.scalars().first()
    if not referer:
        await bot.send_message(chat_id=message.from_user.id, text='Такого referal_id не существует!', parse_mode="HTML")
        return

    if referer.id == referer.referer_id:
        if referer.is_buying:
            user_is_buying = 'Покупка включена'
        else:
            user_is_buying = 'Покупка выключена'

        if referer.is_withdraw:
            user_is_withdraw = 'Вывод включен'
        else:
            user_is_withdraw = 'Вывод выключен'

        if referer.is_verified:
            user_is_verified = 'Верифицирован'
        else:
            user_is_verified = 'Не верифицирован'

        if referer.is_blocked:
            user_is_blocked = 'Заблокирован'
        else:
            user_is_blocked = 'Активен'

        user_balance_in_currency = round(float(await referer.get_balance()), 2)
        keyboard = await kb.create_mamont_control_kb(referal_id, session)
        text = (f'🏙 <b>Профиль реферала</b> {referal_id}\n\n'
                f'<b>Информация</b>\n'
                f'┠ Баланс в валюте: <b>{user_balance_in_currency} {referer.currency.name.upper()}</b>\n'
                f'┠ Мин. депозит: <b>{referer.min_deposit}</b>\n'
                f'┠ Мин. вывод: <b>{referer.min_withdraw}</b>\n'
                f'┠ 🔰 <b>{user_is_buying}</b>\n'
                f'┠ 🔰 <b>{user_is_withdraw}</b>\n'
                f'┠ 🔐 <b>{user_is_blocked}</b>\n'
                f'┖ 🔺 <b>{user_is_verified}</b>\n\n'
                f'<b>Последний логин</b>\n'
                f'┖ {user.last_login}')
        await state.update_data(referal_id=referal_id)
        await bot.send_message(chat_id=message.from_user.id, text=text, parse_mode="HTML", reply_markup=keyboard)


@router.message(StateFilter(worker_state.WorkerReferal.referal_id))
async def mamont_control_panel(message: Message, session: AsyncSession, state: worker_state.WorkerReferal.referal_id):
    referal_id = message.text.strip()
    await state.clear()

    # Extract referal_id if the message is in the format "/r_{referal_id}"
    if referal_id.startswith("/r_"):
        referal_id = referal_id[3:]  # Remove "/r_"

    if not referal_id.isdigit():
        await bot.send_message(chat_id=message.from_user.id, text='Введите корректный referal_id!', parse_mode="HTML")
        return

    result = await session.execute(select(User).where(User.tg_id == int(referal_id)))
    user = result.scalars().first()

    if not user:
        await bot.send_message(chat_id=message.from_user.id, text='Такого referal_id не существует!', parse_mode="HTML")
        return

    # Rest of your code to handle user control panel
    if user.is_buying:
        user_is_buying = 'Покупка включена'
    else:
        user_is_buying = 'Покупка выключена'

    if user.is_withdraw:
        user_is_withdraw = 'Вывод включен'
    else:
        user_is_withdraw = 'Вывод выключен'

    if user.is_verified:
        user_is_verified = 'Верифицирован'
    else:
        user_is_verified = 'Не верифицирован'

    if user.is_blocked:
        user_is_blocked = 'Заблокирован'
    else:
        user_is_blocked = 'Активен'

    user_balance_in_currency = round(float(await user.get_balance()), 2)
    keyboard = await kb.create_mamont_control_kb(referal_id, session)
    text = (f'🏙 <b>Профиль реферала</b> {referal_id}\n\n'
            f'<b>Информация</b>\n'
            f'┠ Баланс в валюте: <b>{user_balance_in_currency} {user.currency.name.upper()}</b>\n'
            f'┠ Мин. депозит: <b>{user.min_deposit}</b>\n'
            f'┠ Мин. вывод: <b>{user.min_withdraw}</b>\n'
            f'┠ 🔰 <b>{user_is_buying}</b>\n'
            f'┠ 🔰 <b>{user_is_withdraw}</b>\n'
            f'┠ 🔐 <b>{user_is_blocked}</b>\n'
            f'┖ 🔺 <b>{user_is_verified}</b>\n\n'
            f'<b>Последний логин</b>\n'
            f'┖ {user.last_login}')
    await state.update_data(referal_id=referal_id)
    await bot.send_message(chat_id=message.from_user.id, text=text, parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(lambda c: c.data.startswith('mamont|'))
async def mamont_control_handler(call: types.CallbackQuery, state: worker_state.WorkerReferal.referal_id,
                                 session: AsyncSession):
    global new_mamont_deposit, new_mamont_withdraw
    callback = call.data.split('|')[1]
    state_info = await state.get_data()
    referal_id = state_info['referal_id']
    result = await session.execute(select(User).where(User.tg_id == int(referal_id)))
    user = result.scalars().first()
    if callback == 'change_balance':
        await bot.edit_message_text(message_id=call.message.message_id, chat_id=call.from_user.id,
                                    text=f'<b>Пополнение баланса пользователя <code>{user.tg_id}</code></b>\n'
                                         f'{user.fname}\n'
                                         f'/ctr_{user.tg_id}\n\n'
                                         f'Активная валюта пользователя: <b>{user.currency.name.upper()}</b>\n'
                                         f'Баланс пользователя на данный момент: <b>{user.balance} {user.currency.name.upper()}</b>\n\n'
                                         f'<i>Укажите сумму пополнения и валюту\n'
                                         f'Пример:\n'
                                         f'800 RUB</i>',
                                    parse_mode='HTML')
        await state.set_state(worker_state.WorkerReferal.balance_amount)
        return
    elif callback == 'send_message':
        await bot.edit_message_text(message_id=call.message.message_id, chat_id=call.from_user.id,
                                    text='Введите сообщение для реферала: ')
        await state.set_state(worker_state.WorkerReferal.mamont_message)
        return
    elif callback == 'min_deposit':
        await bot.edit_message_text(message_id=call.message.message_id, chat_id=call.from_user.id,
                                    text='Введите сумму для изменения минимального депозита: ')
        await state.set_state(worker_state.WorkerReferal.min_deposit)
        return
    elif callback == 'min_withdraw':
        await bot.edit_message_text(message_id=call.message.message_id, chat_id=call.from_user.id,
                                    text='Введите сумму для изменения минимального вывода: ')
        await state.set_state(worker_state.WorkerReferal.min_withdraw)
    elif callback == 'unverify':
        await session.execute(update(User).where(User.tg_id == int(referal_id)).values(is_verified=False))
        await session.commit()
    elif callback == 'verify':
        await session.execute(update(User).where(User.tg_id == int(referal_id)).values(is_verified=True))
        await session.commit()
    elif callback == 'withdraw':
        if user.is_withdraw:
            await session.execute(update(User).where(User.tg_id == int(referal_id)).values(is_withdraw=False))
            await session.commit()
        else:
            await session.execute(update(User).where(User.tg_id == int(referal_id)).values(is_withdraw=True))
            await session.commit()
    elif callback == 'buying':
        if user.is_buying:
            await session.execute(update(User).where(User.tg_id == int(referal_id)).values(is_buying=False))
            await session.commit()
        else:
            await session.execute(update(User).where(User.tg_id == int(referal_id)).values(is_buying=True))
            await session.commit()
    elif callback == 'block':
        await session.execute(update(User).where(User.tg_id == int(referal_id)).values(is_blocked=True))
        await session.commit()
    elif callback == 'unblock':
        await session.execute(update(User).where(User.tg_id == int(referal_id)).values(is_blocked=False))
        await session.commit()
    elif callback == 'delete':
        await session.execute(delete(User).where(User.tg_id == int(referal_id)))
        await session.commit()
    elif callback == 'update':
        result2 = await session.execute(select(User).where(User.tg_id == int(referal_id)))
        user = result2.scalars().first()

        if user.is_buying:
            user_is_buying = 'Покупка включена'
        else:
            user_is_buying = 'Покупка выключена'

        if user.is_withdraw:
            user_is_withdraw = 'Вывод включен'
        else:
            user_is_withdraw = 'Вывод выключен'

        if user.is_verified:
            user_is_verified = 'Верифицирован'
        else:
            user_is_verified = 'Не верифицирован'

        if user.is_blocked:
            user_is_blocked = 'Заблокирован'
        else:
            user_is_blocked = 'Активен'

        user_balance_in_currency = round(float(await user.get_balance()), 2)
        keyboard = await kb.create_mamont_control_kb(referal_id, session)
        text = (f'🏙 <b>Профиль реферала</b> {referal_id}\n\n'
                f'<b>Информация</b>\n'
                f'┠ Баланс в валюте: <b>{user_balance_in_currency} {user.currency.name.upper()}</b>\n'
                f'┠ Мин. депозит: <b>{user.min_deposit}</b>\n'
                f'┠ Мин. вывод: <b>{user.min_withdraw}</b>\n'
                f'┠ 🔰 <b>{user_is_buying}</b>\n'
                f'┠ 🔰 <b>{user_is_withdraw}</b>\n'
                f'┠ 🔐 <b>{user_is_blocked}</b>\n'
                f'┖ 🔺 <b>{user_is_verified}</b>\n\n'
                f'<b>Последний логин</b>\n'
                f'┖ {user.last_login}')
        await call.answer('Успешно обновлено')
        await bot.edit_message_text(chat_id=call.from_user.id, message_id=call.message.message_id, text=text,
                                    parse_mode="HTML", reply_markup=keyboard)
        return

    result2 = await session.execute(select(User).where(User.tg_id == int(referal_id)))
    user2 = result2.scalars().first()

    if user2.is_buying:
        user_is_buying = 'Покупка включена'
    else:
        user_is_buying = 'Покупка выключена'

    if user2.is_withdraw:
        user_is_withdraw = 'Вывод включен'
    else:
        user_is_withdraw = 'Вывод выключен'

    if user2.is_verified:
        user_is_verified = 'Верифицирован'
    else:
        user_is_verified = 'Не верифицирован'

    if user2.is_blocked:
        user_is_blocked = 'Заблокирован'
    else:
        user_is_blocked = 'Активен'

    user_balance_in_currency = round(float(await user2.get_balance()), 2)
    keyboard = await kb.create_mamont_control_kb(referal_id, session)
    text = (f'🏙 <b>Профиль реферала</b> {referal_id}\n\n'
            f'<b>Информация</b>\n'
            f'┠ Баланс в валюте: <b>{user_balance_in_currency} {user2.currency.name.upper()}</b>\n'
            f'┠ Мин. депозит: <b>{user2.min_deposit} RUB</b>\n'
            f'┠ Мин. вывод: <b>{user2.min_withdraw} RUB</b>\n'
            f'┠ 🔰 <b>{user_is_buying}</b>\n'
            f'┠ 🔰 <b>{user_is_withdraw}</b>\n'
            f'┠ 🔐 <b>{user_is_blocked}</b>\n'
            f'┖ 🔺 <b>{user_is_verified}</b>\n\n'
            f'<b>Последний логин</b>\n'
            f'┖ {user2.last_login}')
    await bot.edit_message_text(chat_id=call.from_user.id, message_id=call.message.message_id, text=text,
                                parse_mode="HTML", reply_markup=keyboard)


@router.message(StateFilter(worker_state.WorkerReferal.mamont_message))
async def send_message_to_mamont(message: Message, state: worker_state.WorkerReferal.mamont_message):
    await message.delete()
    message_text = message.text

    # Count the number of digits in the message
    digit_count = sum(char.isdigit() for char in message_text)

    # Check if there are more than 4 digits in the message
    if digit_count > 4:
        await bot.send_message(
            chat_id=message.from_user.id,
            text='Ваше сообщение содержит более 4-х цифр. Пожалуйста, уменьшите количество цифр и попробуйте снова.',
            parse_mode="HTML"
        )
        return

    # Retrieve referal_id from the state
    state_info = await state.get_data()
    referal_id = state_info['referal_id']

    # Send the message to the mamont
    await bot.send_message(chat_id=int(referal_id), text=message_text)
    await bot.send_message(chat_id=message.from_user.id, text='Сообщение успешно отправлено!')
    # Clear the state
    await state.clear()


@router.message(StateFilter(worker_state.WorkerReferal.min_deposit))
async def change_min_deposit(message: Message, session: AsyncSession, state: worker_state.WorkerReferal.min_deposit):
    await message.delete()
    min_deposit = message.text
    if not min_deposit.isdigit():
        await bot.send_message(chat_id=message.from_user.id, text='Введите корректную сумму!', parse_mode="HTML")
        return
    state_info = await state.get_data()
    referal_id = state_info['referal_id']
    await session.execute(update(User).where(User.tg_id == int(referal_id)).values(min_deposit=int(min_deposit)))
    await session.commit()
    await bot.send_message(chat_id=message.from_user.id, text=f'Минимальный депозит изменен на {min_deposit}!')
    await state.clear()


@router.message(StateFilter(worker_state.WorkerReferal.min_withdraw))
async def change_min_withdraw(message: Message, session: AsyncSession, state: worker_state.WorkerReferal.min_withdraw):
    await message.delete()
    min_withdraw = message.text
    if not min_withdraw.isdigit():
        await bot.send_message(chat_id=message.from_user.id, text='Введите корректную сумму!', parse_mode="HTML")
        return
    state_info = await state.get_data()
    referal_id = state_info['referal_id']
    await session.execute(update(User).where(User.tg_id == int(referal_id)).values(min_withdraw=int(min_withdraw)))
    await session.commit()
    await bot.send_message(chat_id=message.from_user.id, text=f'Минимальный вывод изменен на {min_withdraw}!')
    await state.clear()


@router.message(StateFilter(worker_state.WorkerReferal.balance_amount))
async def change_mamont_balance(message: Message, session: AsyncSession, state: FSMContext):
    # Extract and parse the balance amount and currency from the message
    parts = message.text.strip().split()

    if len(parts) != 2:
        await bot.send_message(
            chat_id=message.from_user.id,
            text='Введите корректную сумму и валюту в формате "800 RUB" или "-800 RUB"!',
            parse_mode="HTML"
        )
        return

    # Try to convert the first part into a float to handle both positive and negative amounts
    try:
        balance_amount = float(parts[0])
    except ValueError:
        await bot.send_message(
            chat_id=message.from_user.id,
            text='Введите корректное число для суммы!',
            parse_mode="HTML"
        )
        return

    currency_input = parts[1].upper()

    # Check if the provided currency is valid
    if currency_input not in CurrencyEnum._value2member_map_:
        await bot.send_message(
            chat_id=message.from_user.id,
            text='Введите корректную валюту! Например, "USD" или "RUB".',
            parse_mode="HTML"
        )
        return

    # Retrieve the referal_id from the state
    state_info = await state.get_data()
    referal_id = state_info['referal_id']

    # Retrieve the user associated with the referal_id
    result = await session.execute(select(User).where(User.tg_id == int(referal_id)))
    user = result.scalars().first()

    if not user:
        await bot.send_message(
            chat_id=message.from_user.id,
            text='Пользователь не найден!',
            parse_mode="HTML"
        )
        return

    # Convert the provided currency amount to USD
    new_balance_change = await currency_exchange.get_rate(CurrencyEnum[currency_input.lower()], CurrencyEnum.usd, balance_amount)

    # Update the user's balance
    updated_balance = user.balance + new_balance_change  # Adjust the balance by the new amount

    await session.execute(
        update(User).where(User.tg_id == int(referal_id)).values(balance=round(float(updated_balance), 2))
    )
    await session.commit()

    # Notify the worker of the successful update
    await bot.send_message(
        chat_id=message.from_user.id,
        text=f'Баланс изменен на {balance_amount} {currency_input} ({new_balance_change} USD). Новый баланс: {updated_balance} USD!',
        parse_mode="HTML"
    )
    await state.clear()
    await message.edit_text('Привет, воркер!', reply_markup=kb.work_panel)



@router.callback_query(F.data == 'worker_back')
async def cmd_worker_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text('Привет, воркер!',
                                     reply_markup=kb.work_panel)


@router.callback_query(F.data.startswith('worker_user|'))
async def open_worker(callback: CallbackQuery, user: User, session: AsyncSession,
                      state: worker_state.WorkerReferal.referal_id):
    referal_id = callback.data.split('|')[1]
    if not referal_id.isdigit():
        await bot.send_message(chat_id=callback.from_user.id, text='Введите корректный referal_id!', parse_mode="HTML")
        return

    result = await session.execute(select(User).where(User.tg_id == int(referal_id)))
    user = result.scalars().first()

    if not user:
        await bot.send_message(chat_id=callback.from_user.id, text='Такого referal_id не существует!', parse_mode="HTML")
        return

    if user.is_buying:
        user_is_buying = 'Покупка включена'
    else:
        user_is_buying = 'Покупка выключена'

    if user.is_withdraw:
        user_is_withdraw = 'Вывод включен'
    else:
        user_is_withdraw = 'Вывод выключен'

    if user.is_verified:
        user_is_verified = 'Верифицирован'
    else:
        user_is_verified = 'Не верифицирован'

    if user.is_blocked:
        user_is_blocked = 'Заблокирован'
    else:
        user_is_blocked = 'Активен'

    user_balance_in_currency = round(float(await user.get_balance()), 2)
    keyboard = await kb.create_mamont_control_kb(referal_id, session)
    text = (f'🏙 <b>Профиль реферала</b> {referal_id}\n\n'
            f'<b>Информация</b>\n'
            f'┠ Баланс в валюте: <b>{user_balance_in_currency} {user.currency.name.upper()}</b>\n'
            f'┠ Мин. депозит: <b>{user.min_deposit}</b>\n'
            f'┠ Мин. вывод: <b>{user.min_withdraw}</b>\n'
            f'┠ 🔰 <b>{user_is_buying}</b>\n'
            f'┠ 🔰 <b>{user_is_withdraw}</b>\n'
            f'┠ 🔐 <b>{user_is_blocked}</b>\n'
            f'┖ 🔺 <b>{user_is_verified}</b>\n\n'
            f'<b>Последний логин</b>\n'
            f'┖ {user.last_login}')
    await state.update_data(referal_id=referal_id)
    await bot.send_message(chat_id=callback.from_user.id, text=text, parse_mode="HTML", reply_markup=keyboard)


##
# <Promocodes>
###

@router.callback_query(F.data == 'worker_promocode')
async def get_promocode_menu(cb: CallbackQuery):
    await cb.message.edit_text("Выберите действие с промокодами:",
                               reply_markup=kb.get_promocode_menu_kb())


@router.callback_query(F.data == 'create_promocode')
async def cmd_create_promocode(cb: CallbackQuery, state: FSMContext):
    await state.set_state(CreatePromocode.wait_code)
    await cb.message.edit_text("✍️ Укажите новый промокод::",
                               reply_markup=kb.get_worker_menu_back_kb())


@router.message(F.text, CreatePromocode.wait_code)
async def set_promocode_code(message: Message, state: FSMContext, session: AsyncSession):
    allowed_char_range = string.ascii_uppercase + string.digits
    if (not all(char in allowed_char_range for char in message.text)
        or len(message.text)) <= 4:
        await message.answer('Используйте только большие англ. буквы и цифры, длина промокода больше 4 символов:',
                             reply_markup=kb.get_worker_menu_back_kb())
        return
    if await get_promocode_by_code(session, message.text) is not None:
        await message.answer('Промокод с таким кодом уже существует, введите другой код:',
                             reply_markup=kb.get_worker_menu_back_kb())
        return
    await state.update_data(code=message.text)
    await message.answer('Выберите валюту в которой будет пополняться баланс при активации промокода:',
                         reply_markup=kb.get_promocode_currency_kb())
    await state.set_state(CreatePromocode.wait_currency)


@router.callback_query(F.data.startswith('promo_'))
async def set_promocode_currency(cb: CallbackQuery, state: FSMContext):
    currency = cb.data.split('_')[1]
    await state.update_data(currency=currency)
    await cb.message.edit_text(f"Введите сумму, которая будет получена при активации промокода в {currency.upper()}:",
                               reply_markup=kb.get_worker_menu_back_kb())
    await state.set_state(CreatePromocode.wait_amount)


@router.message(F.text, CreatePromocode.wait_amount)
async def set_promocode_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text)
    except ValueError:
        await message.answer("Сумма должна быть числом, введите ещё раз:",
                             reply_markup=kb.get_worker_menu_back_kb())
        return
    await state.update_data(amount=amount)
    await state.set_state(CreatePromocode.wait_type)
    await message.answer("Выберите тип промокода - введите '0' для одноразового или '1' для многоразового:",
                         reply_markup=kb.get_worker_menu_back_kb())


@router.message(F.text, CreatePromocode.wait_type)
async def set_promocode_type(message: Message, state: FSMContext, user: User,
                             session: AsyncSession):
    if message.text not in ('1', '0'):
        await message.answer(
            "Выберите тип промокода - введите '0' для одноразового или '1' для многоразового:",
            reply_markup=kb.get_worker_menu_back_kb())
        return
    data = await state.get_data()
    await state.clear()
    currency = data['currency']
    promocode = Promocode(code=data['code'],
                          amount=data['amount'],
                          currency=CurrencyEnum[currency],
                          reusable=True if message.text == '1' else False)
    (await promocode.awaitable_attrs.users).append(
        UserPromocodeAssotiation(user=user, is_creator=True))
    session.add(promocode)
    await message.answer("Промокод успешно создан", reply_markup=kb.get_worker_menu_back_kb())


@router.callback_query(F.data == 'get_promocode_list')
async def cmd_get_promocode_list(cb: CallbackQuery, user: User, session: AsyncSession):
    await cb.message.edit_text("Выберите промокод",
                               reply_markup=kb.get_promocode_list_kb(
                                   await get_created_promocodes(session, user),
                               ))


@router.callback_query(F.data.startswith('manage_promocode_'))
async def cmd_manage_promocode(cb: CallbackQuery, user: User, session: AsyncSession):
    promocode = await session.get(Promocode, cb.data.split('_')[-1])
    await cb.message.edit_text(f'''Промокод <code>{promocode.code}</code>
Сумма: <b>{promocode.amount} {promocode.currency.name.upper()}</b>
Тип: {'Многоразовый' if promocode.reusable else 'Одноразовый'}''',
                               reply_markup=kb.get_promocode_managment_kb(promocode), parse_mode='HTML')


@router.callback_query(F.data.startswith('delete_promocode_'))
async def cmd_delete_promocode(cb: CallbackQuery, session: AsyncSession):
    promocode = await session.get(Promocode, cb.data.split('_')[-1])
    await session.delete(promocode)
    await cb.message.edit_text(f"Промокод <code>{promocode.code}</code> удалён!",
                               reply_markup=kb.get_worker_menu_back_kb())

###
# </Promocodes>
###
