from aiogram import Router, Bot, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select, update
from database.methods import get_active_users_count
from sqlalchemy.ext.asyncio import AsyncSession
import config
from database.models import User
from keyboards import kb
from middlewares import IsVerifiedMiddleware, AuthorizeMiddleware
from admin_handlers.states import (ControlUsers, CreatePaymentProps, Mailing,
                                   UpdateCurrentPaymentProps)
from utils.payment_props import PAYMENT_PROPS, NftBotPaymentProps, TradeBotPaymentProps
import asyncio


router = Router()
router.message.middleware(AuthorizeMiddleware())
router.message.middleware(IsVerifiedMiddleware())
router.callback_query.middleware(AuthorizeMiddleware())
router.callback_query.middleware(IsVerifiedMiddleware())


@router.message(F.text == '🧐 Админ панель')
async def admin_panel(message: Message, user: User):
    if user.tg_id in config.ADMIN_IDS:
        await message.answer('Открыта админ-панель!', reply_markup=kb.admin_panel)


@router.message(F.text == 'Пользователи')
async def users(message: Message, user: User, bot: Bot, session: AsyncSession):
    if user.tg_id in config.ADMIN_IDS:
        # Получаем список всех пользователей
        result = await session.execute(select(User))
        users = result.scalars().all()

        # Форматируем данные в удобный табличный вид
        if users:
            text = "Список пользователей:\n\n"
            for user in users:
                text += f'ID: {user.id}\nTG ID: {user.tg_id}\nИмя: {user.fname or ""}\nФамилия: {user.lname or ""}\nUsername: {user.username or ""}\nБаланс: {user.balance}\nПроверен: {"Да" if user.is_verified else "Нет"}\nЗаблокирован: {"Да" if user.is_blocked else "Нет"}\n\n'
        else:
            text = "Пользователей не найдено."

        # Отправляем сообщение с пользователями
        await message.answer(text=text, reply_markup=kb.control_users)


@router.callback_query(F.data == 'control_users')
async def control_users(call: CallbackQuery, session: AsyncSession, state: FSMContext):
    await call.message.answer('Введите ID пользователя ниже: ')
    await state.set_state(ControlUsers.user_id)


@router.message(StateFilter(ControlUsers.user_id))
async def get_user(message: Message, session: AsyncSession, state: FSMContext):
    user_id = message.text
    result = await session.execute(select(User).where(User.id == int(user_id)))
    user = result.scalars().first()
    if user:
        if user.is_blocked:
            button_text = 'Разблокировать'
            callback_data = 'unblock'
        else:
            button_text = 'Заблокировать'
            callback_data = 'block'
        user_action_kb = [
            [InlineKeyboardButton(text=button_text, callback_data=f'user|{callback_data}'),
             InlineKeyboardButton(text='Написать сообщение', callback_data=f'user|writemessage')],
            [InlineKeyboardButton(text='Вернуться', callback_data='user|back')]
        ]
        user_action = InlineKeyboardMarkup(inline_keyboard=user_action_kb)
        await message.answer(text=f"ID: {user.id}\nTG ID: {user.tg_id}\nИмя: {user.fname or ''}\n"
                                  f"Фамилия: {user.lname or ''}\nUsername: {user.username or ''}\n"
                                  f"Баланс: {user.balance}\nПроверен: {'Да' if user.is_verified else 'Нет'}\n"
                                  f"Заблокирован: {'Да' if user.is_blocked else 'Нет'}", reply_markup=user_action)
        await state.update_data(user_id=user_id)
    else:
        await message.answer(text='Пользователь не найден.')
        await state.clear()


@router.callback_query(F.data.startswith('user|'))
async def action_user(call: CallbackQuery, session: AsyncSession, state: FSMContext):
    action = call.data.split('|')[1]
    data = await state.get_data()
    user_id = data['user_id']
    if action == 'block':
        await session.execute(update(User).where(User.id == user_id).values(is_blocked=True))
        await session.commit()
        await call.message.answer(text='Пользователь заблокирован.')
    elif action == 'unblock':
        await session.execute(update(User).where(User.id == user_id).values(is_blocked=False))
        await session.commit()
        await call.message.answer(text='Пользователь разблокирован.')
    elif action == 'writemessage':
        await call.message.answer(text='Введите сообщение ниже:')
        await state.set_state(ControlUsers.write_message)
    elif action == 'back':
        await call.answer('Открыта админ-панель!', reply_markup=kb.admin_panel)
        await state.clear()


@router.message(StateFilter(ControlUsers.write_message))
async def write_message(message: Message, session: AsyncSession, state: FSMContext):
    data = await state.get_data()
    user_id = data['user_id']
    user = await session.execute(select(User).where(User.id == user_id))
    user = user.scalars().first()
    if user:
        await message.bot.send_message(user.tg_id, text=message.text)
        await message.delete()
        await message.answer(text='Сообщение отправлено.')

    else:
        await message.answer(text='Пользователь не найден.')
    await state.clear()


@router.message(F.text == 'Реквизиты')
async def details(message: Message, user: User):
    if user.tg_id in config.ADMIN_IDS:
        await message.answer('Выберите сервис для добавления реквизитов: ', reply_markup=kb.services_details)


@router.callback_query(F.data.startswith('details_service|'))
async def choose_service(call: CallbackQuery,  state: FSMContext):
    await call.message.delete()
    global service_name
    service_id = call.data.split('|')[1]
    if service_id == '1':
        service_name = '💼 Трейд бот'
        service_id = 'trade'
    elif service_id == '2':
        service_name = '🎆 NFT бот'
        service_id = 'nft'

    payment_details = (PAYMENT_PROPS.nft_bot_payment_props if service_id == 'nft'
        else PAYMENT_PROPS.trade_bot_payment_props)

    if payment_details:
        text = f'''Детали оплаты для {service_name}:
Карта: {payment_details.card}
USDT[TRC-20]: {payment_details.usdt_trc20_wallet}
BTC: {payment_details.btc_wallet}
ETH: {payment_details.eth_wallet}'''
        await call.message.answer(text=text, 
                                  reply_markup=kb.get_set_props_kb(service_id))
    else:
        text = f"Детали оплаты для {service_name} ещё не установлены."
        await call.message.answer(text=text, reply_markup=kb.get_create_props_kb())

    # Отправка сообщения пользователю
    await state.update_data(service_id=service_id)
    

@router.callback_query(F.data == 'create_payment_props')
async def create_payment_props(call: CallbackQuery, state: FSMContext):
    await state.set_state(CreatePaymentProps.wait_card)
    await call.message.edit_text("Введите реквизиты для оплаты[Карта]:")

@router.message(StateFilter(CreatePaymentProps.wait_card))
async def set_card(message: Message, state: FSMContext):
    await state.update_data(card=message.text)
    await state.set_state(CreatePaymentProps.wait_usdt)
    await message.answer(text="Введите реквизиты для оплаты[USDT(TRC-20)]:")

@router.message(StateFilter(CreatePaymentProps.wait_usdt))
async def set_usdt_trc20(message: Message, state: FSMContext):
    await state.update_data(usdt_trc20_wallet=message.text)
    await state.set_state(CreatePaymentProps.wait_btc)
    await message.answer(text="Введите реквизиты для оплаты[BTC]:")

@router.message(StateFilter(CreatePaymentProps.wait_btc))
async def set_btc(message: Message, state: FSMContext):
    await state.update_data(btc_wallet=message.text)
    await state.set_state(CreatePaymentProps.wait_eth)
    await message.answer(text="Введите реквизиты для оплаты[ETH]:")

@router.message(StateFilter(CreatePaymentProps.wait_eth))
async def set_eth(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    service_id = data['service_id']
    PaymentsProps = (NftBotPaymentProps if service_id == 'nft'
        else TradeBotPaymentProps)
    props = PaymentsProps(card=data['card'], btc_wallet=data['btc_wallet'],
                            usdt_trc20_wallet=data['usdt_trc20_wallet'],
                            eth_wallet=message.text)
    if PaymentsProps == NftBotPaymentProps:
        PAYMENT_PROPS.nft_bot_payment_props = props
    else:
        PAYMENT_PROPS.trade_bot_payment_props = props
    PAYMENT_PROPS.save_on_disk()

    await message.answer(text="Реквизиты для оплаты обновлены")


@router.callback_query(F.data.startswith('set_payment_props_'))
async def cmd_set_props(call: CallbackQuery, state: FSMContext):
    service, props_type = call.data.split('_')[-2], call.data.split('_')[-1]
    await state.update_data(service=service, props_type=props_type)
    await state.set_state(UpdateCurrentPaymentProps.waiting)
    await call.message.edit_text("Выберите новые реквизиты для оплаты: ")

@router.message(F.text, UpdateCurrentPaymentProps.waiting)
async def update_current_props(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    payments_props = (PAYMENT_PROPS.nft_bot_payment_props if data['service'] == 'nft'
        else PAYMENT_PROPS.trade_bot_payment_props)
    attrs_names = {'card': 'card', 
                   'usdt': 'usdt_trc20_wallet', 'btc': 'btc_wallet', 
                   'eth': 'eth_wallet'}
    setattr(payments_props, attrs_names[data['props_type']], message.text)
    PAYMENT_PROPS.save_on_disk()
    await message.answer("Реквизиты для оплаты обновлены",
                         reply_markup=kb.back_to_admin)


@router.callback_query(F.data == 'back_to_admin')
async def back_to_admin(call: CallbackQuery):
    await call.message.delete()
    await call.message.answer('Открыта админ-панель!', reply_markup=kb.admin_panel)


@router.message(F.text == 'Статистика')
async def statistics(message: Message, user: User, session: AsyncSession):
    if user.tg_id in config.ADMIN_IDS:
        active_users_count = await get_active_users_count(session)
        await message.answer(f'Сегодня ботом воспользовалось {active_users_count} пользователей')


@router.message(F.text == 'Рассылка')
async def mailing(message: Message, user: User, state: FSMContext):
    if user.tg_id in config.ADMIN_IDS:
        await message.answer('Напишите сообщение для рассылки ниже:')
        await state.set_state(Mailing.text)


@router.message(StateFilter(Mailing.text))
async def send_message(message: Message, session: AsyncSession, state: FSMContext):
    await state.clear()
    users = await session.execute(select(User))
    users = users.scalars().all()
    asyncio.gather(message.copy_to(user.tg_id) for user in users if user.tg_id != message.from_user.id)
    await message.answer('Сообщение отправлено всем пользователям')

@router.message(F.text == 'Назад')
async def back(message: Message, user: User):
    if user.tg_id in config.ADMIN_IDS:
        await message.answer(text=f'<b>👋 Добро пожаловать, администратор {user.fname}!\n выберите сервис ниже:</b>',
                             parse_mode="HTML", reply_markup=kb.main_admin)
