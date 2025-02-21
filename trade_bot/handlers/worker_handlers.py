from aiogram import types, F, Router, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
import keyboards as kb
from middlewares import AuthorizeMiddleware, get_string_user_representation
from database.models import User, Promocode, UserPromocodeAssotiation
from aiogram.fsm.context import FSMContext
from aiogram.utils.markdown import hlink
import asyncio
from database.enums import LangEnum, CurrencyEnum
from database.crud import (get_user_by_tg_id, set_min_deposit_for_referals,
                           set_min_withdraw_for_referals, set_currency_for_referals,
                           get_created_promocodes, get_promocode_by_code)
from sqlalchemy.ext.asyncio import AsyncSession
from .worker_states import ManageAllReferals, ManageReferal, CreatePromocode, SearchReferal
from utils.get_exchange_rate import currency_exchange
import string
import config


router = Router()
router.message.middleware(AuthorizeMiddleware())
router.callback_query.middleware(AuthorizeMiddleware())


@router.message(F.text == 'Воркер')
async def cmd_worker(message: Message, user: User, session: AsyncSession):
    await message.answer('Привет, воркер!',
                          reply_markup=kb.get_main_worker_kb())
    if not user.is_worker:
        user.is_worker = True
        session.add(user)

@router.callback_query(F.data == 'manage_worker_referals')
async def cmd_manage_worker_referals(callback: CallbackQuery):
    await callback.message.answer('Привет, воркер!',
                          reply_markup=kb.get_main_worker_kb())
    await callback.answer()

@router.callback_query(F.data == 'worker_back')
async def cmd_worker_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text('Привет, воркер!',
        reply_markup=kb.get_main_worker_kb())

@router.callback_query(F.data == 'worker_list')
async def cmd_worker_list(callback: CallbackQuery, user: User, session: AsyncSession):
    await callback.message.edit_reply_markup(
        reply_markup=kb.get_worker_select_user_kb(await user.awaitable_attrs.referals)
    )


@router.callback_query(F.data.startswith('worker_user_'))
async def select_target_user(callback: CallbackQuery, user: User, session: AsyncSession):
    target_uid = int(callback.data.split('_')[-1])
    target = await session.get(User, target_uid)
    try:
        await callback.message.edit_text(
            await get_string_user_representation(target, worker=user),
            reply_markup=kb.get_worker_user_managment_kb(target)
        )
    except TelegramBadRequest:
        await callback.answer() # msg not modified

@router.callback_query(F.data.startswith("worker_unbind_"))
async def unbind_user(callback: CallbackQuery, user: User, session: AsyncSession):
    target = await session.get(User, int(callback.data.split('_')[-1]))
    target.referer = None
    session.add_all([target, user])
    await callback.message.edit_text("Реферал удален", 
        reply_markup=kb.get_worker_back_to_managment_kb(target))


@router.callback_query(F.data == 'worker_bind')
async def cmd_bind(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text("Введите telegram ID пользователя, которого вы хотите добавить:",
                               reply_markup=kb.get_worker_menu_back_kb())
    await state.set_state(ManageAllReferals.wait_binding_id)

@router.message(F.text, ManageAllReferals.wait_binding_id)
async def set_binding_id(message: Message, user: User, state: FSMContext,
                          session: AsyncSession):
    target = await get_user_by_tg_id(session, message.text)
    if target is None:
        text = "Пользователь не найден"
    elif await target.awaitable_attrs.referer is not None:
        text = 'Этот пользователь уже является рефералом другого пользователя'
    else:
        (await user.awaitable_attrs.referals).append(target)
        text = 'Пользователь успешно добавлен'
    await message.answer(text, 
                         reply_markup=kb.get_worker_menu_back_kb())
    await state.clear()


@router.callback_query(F.data == 'worker_mailing')
async def cmd_mailing(cb: CallbackQuery, state: FSMContext):
    await state.set_state(ManageAllReferals.wait_message)
    await cb.message.edit_text(
        "Отправьте сообщение, которое будет отправлено всем вашим рефералам:",
        reply_markup=kb.get_worker_menu_back_kb())


    
@router.message(F.text, ManageAllReferals.wait_message)
async def cmd_mailing_set_msg(message: Message, user: User, state: FSMContext,
                              bot: Bot):
    await state.clear()
    await message.answer("Успешно!", reply_markup=kb.get_worker_menu_back_kb())
    asyncio.gather(
            *[bot.copy_message(r.tg_id, message.chat.id, message.message_id) 
              for r in await user.awaitable_attrs.referals]
    )
    

###
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
    await state.set_state(CreatePromocode.wait_amount)
    await message.answer("Введите сумму, которая будет получена при активации промокода(в USD):",
                         reply_markup=kb.get_worker_menu_back_kb())
    
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
    promocode = Promocode(code=data['code'],
                          amount=data['amount'],
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
Сумма: <b>{promocode.amount} USD</b>
Тип: {'Многоразовый' if promocode.reusable else 'Одноразовый'}''',
    reply_markup=kb.get_promocode_managment_kb(promocode))
    
@router.callback_query(F.data.startswith('delete_promocode_'))
async def cmd_delete_promocode(cb: CallbackQuery, session: AsyncSession):
    promocode = await session.get(Promocode, cb.data.split('_')[-1])
    await session.delete(promocode)
    await cb.message.edit_text(f"Промокод <code>{promocode.code}</code> удалён!",
                               reply_markup=kb.get_worker_menu_back_kb())
    

###
# </Promocodes>
###


@router.callback_query(F.data == 'worker_min_deposit')
async def cmd_set_min_deposit(cb: CallbackQuery, state: FSMContext):
    await state.set_state(ManageAllReferals.wait_min_deposit)
    await cb.message.edit_text("Укажите минимальную сумму для пополнения(в USD):",
                               reply_markup=kb.get_worker_menu_back_kb())
    
@router.message(F.text, ManageAllReferals.wait_min_deposit)
async def set_min_deposit(message: Message, state: FSMContext, session: AsyncSession,
                          user: User):
    try:
        amount = float(message.text)
        if amount < 0:
            raise ValueError
    except ValueError:
        await message.answer("Сумма должна быть положительным числом, введите ещё раз:",
                             reply_markup=kb.get_worker_menu_back_kb())
        return
    await set_min_deposit_for_referals(session, user, amount)
    await message.answer("Минимальная сумма депозита изменена для всех ваших рефералов",
                         reply_markup=kb.get_worker_menu_back_kb())
    await state.clear()


@router.callback_query(F.data == 'worker_min_withdraw')
async def cmd_set_min_withdraw(cb: CallbackQuery, state: FSMContext):
    await state.set_state(ManageAllReferals.wait_min_withdraw)
    await cb.message.edit_text("Укажите минимальную сумму для вывода(в USD):",
                               reply_markup=kb.get_worker_menu_back_kb())
    
@router.message(F.text, ManageAllReferals.wait_min_withdraw)
async def set_min_withdraw(message: Message, state: FSMContext, session: AsyncSession,
                           user: User):
    try:
        amount = float(message.text)
        if amount < 0:
            raise ValueError
    except ValueError:
        await message.answer("Сумма должна быть положительным числом, введите ещё раз:",
                             reply_markup=kb.get_worker_menu_back_kb())
        return
    await set_min_withdraw_for_referals(session, user, amount)
    await message.answer("Минимальная сумма вывода изменена для всех ваших рефералов",
                         reply_markup=kb.get_worker_menu_back_kb())
    await state.clear()



@router.callback_query(F.data == 'worker_delete_all')
async def cmd_delete_all_referals(cb: CallbackQuery):
    await cb.message.edit_text("Вы уверены, что хотите удалить всех рефералов?",
    reply_markup=kb.get_confirm_all_referals_deletion_kb())

@router.callback_query(F.data == 'confirm_all_referals_deletion')
async def delete_all_referals(cb: CallbackQuery, session: AsyncSession, user: User):
    await session.refresh(user, ['referals'])
    user.referals = []
    session.add(user)
    await cb.message.edit_text("Все рефералы удалены!",
        reply_markup=kb.get_worker_menu_back_kb())
    
@router.callback_query(F.data == 'worker_search')
async def cmd_search(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text("Введите telegram ID реферала",
                               reply_markup=kb.get_worker_menu_back_kb())
    await state.set_state(SearchReferal.wait_tg_id)

@router.message(F.text, SearchReferal.wait_tg_id)
async def search_referal(message: Message, state: FSMContext, session: AsyncSession):
    referal = await get_user_by_tg_id(session, message.text)
    if not referal:
        await message.answer('''Пользователь не найден!
Укажите user_id пользователя:''', reply_markup=kb.get_worker_menu_back_kb())
    else:
        await state.clear()
        await message.answer('Пользователь найден',
                             reply_markup=kb.get_worker_select_current_user_kb(referal))
        
@router.callback_query(F.data == 'worker_set_currency')
async def cmd_set_worker_currency(cb: CallbackQuery, user: User):
    await cb.message.edit_text(f'''Выберите валюту для приглашенных людей:
Текущая валюта: <code>{user.currency_for_referals.value.upper()}</code>''',
    reply_markup=kb.get_select_currency_kb(user.lang_data, for_worker=True))

@router.callback_query(F.data.startswith('worker_set_currency_'))
async def set_worker_currency(cb: CallbackQuery, session: AsyncSession, user: User):
    currency = CurrencyEnum[cb.data.split('_')[-1]]
    await set_currency_for_referals(session, user, currency)
    await cb.message.edit_text('Валюта для приглашенных людей изменена',
                               reply_markup=kb.get_worker_menu_back_kb())
    
#####
#
# Manage certain user
#
####

@router.callback_query(F.data.startswith('worker_change_balance_'))
async def change_balance(cb: CallbackQuery, session: AsyncSession, state: FSMContext):
    target = await session.get(User, cb.data.split('_')[-1])
    await state.update_data(target_id=target.id)
    await cb.message.edit_text(f'''✍️ Укажите новый баланс {
        target.currency.value.upper()} пользователя:''',
          reply_markup=kb.get_worker_back_to_managment_kb(target))
    await state.set_state(ManageReferal.wait_balance_amount)
    
@router.message(F.text, ManageReferal.wait_balance_amount)
async def set_balance_amount(message: Message, state: FSMContext, session: AsyncSession):
    target_id = (await state.get_data())['target_id']
    target = await session.get(User, target_id)
    try:
        amount = float(message.text)
        if amount < 0:
            raise ValueError
    except ValueError:
        await message.answer("Сумма должна быть положительным числом, введите ещё раз:",
                             reply_markup=kb.get_worker_back_to_managment_kb(target))
        return
    target.balance = await currency_exchange.convert_to_usd(target.currency, amount)
    session.add(target)
    await message.answer("Баланс пользователя изменен",
                         reply_markup=kb.get_worker_back_to_managment_kb(target))
    await state.clear()

@router.callback_query(F.data.startswith('worker_add_balance_'))
async def cmd_add_balance(cb: CallbackQuery, session: AsyncSession, state: FSMContext):
    target = await session.get(User, cb.data.split('_')[-1])
    await state.update_data(target_id=target.id)
    await cb.message.edit_text(
        f'''✍️ Укажите сколько хотите добавить к балансу {
            target.currency.value.upper()} пользователя:''',
              reply_markup=kb.get_worker_back_to_managment_kb(target))
    await state.set_state(ManageReferal.wait_deposit_amount)
    
@router.message(F.text, ManageReferal.wait_deposit_amount)
async def set_deposit_amount(message: Message, state: FSMContext, session: AsyncSession):
    target_id = (await state.get_data())['target_id']
    target = await session.get(User, target_id)
    try:
        amount = float(message.text)
        if amount < 0:
            raise ValueError
    except ValueError:
        await message.answer("Сумма должна быть положительным числом, введите ещё раз:",
                             reply_markup=kb.get_worker_back_to_managment_kb(target))
        return
    await target.top_up_balance(session, 
                                await currency_exchange.convert_to_usd(
                                    target.currency, amount)
                                    )
    await message.answer("Баланс пользователя пополнен",
                         reply_markup=kb.get_worker_back_to_managment_kb(target))
    await state.clear()

@router.callback_query(F.data.startswith('worker_max_balance_'))
async def cmd_max_balance(cb: CallbackQuery, session: AsyncSession, state: FSMContext):
    target = await session.get(User, cb.data.split('_')[-1])
    await state.update_data(target_id=target.id)
    await cb.message.edit_text(
        f'''✍️ Укажите новый максимальный баланс {
            target.currency.value.upper()} пользователя:''',
        reply_markup=kb.get_worker_back_to_managment_kb(target))
    
    await state.set_state(ManageReferal.wait_max_balance_amount)

@router.message(F.text, ManageReferal.wait_max_balance_amount)
async def set_max_balance_amount(message: Message, state: FSMContext, session: AsyncSession):
    target_id = (await state.get_data())['target_id']
    target = await session.get(User, target_id)
    try:
        amount = float(message.text)
        if amount < 0:
            raise ValueError
    except ValueError:
        await message.answer("Сумма должна быть положительным числом, введите ещё раз:",
                             reply_markup=kb.get_worker_back_to_managment_kb(target))
        return
    target.max_balance = await currency_exchange.convert_to_usd(target.currency, amount)
    session.add(target)
    await message.answer("Максимальный баланс пользователя изменен",
                         reply_markup=kb.get_worker_back_to_managment_kb(target))
    await state.clear()

@router.callback_query(F.data.startswith('worker_min_deposit_'))
async def cmd_min_deposit(cb: CallbackQuery, session: AsyncSession, state: FSMContext):
    target = await session.get(User, cb.data.split('_')[-1])
    await state.update_data(target_id=target.id)
    await cb.message.edit_text(
        f'''✍️ Укажите минимальную сумму пополнения {
            target.currency.value.upper()} пользователя:''',
        reply_markup=kb.get_worker_back_to_managment_kb(target))
    
    await state.set_state(ManageReferal.wait_min_deposit_amount)

@router.message(F.text, ManageReferal.wait_min_deposit_amount)
async def set_min_deposit_amount(message: Message, state: FSMContext, session: AsyncSession):
    target_id = (await state.get_data())['target_id']
    target = await session.get(User, target_id)
    try:
        amount = float(message.text)
        if amount < 0:
            raise ValueError
    except ValueError:
        await message.answer("Сумма должна быть положительным числом, введите ещё раз:",
                             reply_markup=kb.get_worker_back_to_managment_kb(target))
        return
    target.min_deposit = await currency_exchange.convert_to_usd(target.currency, amount)
    session.add(target)
    await message.answer("Минимальное пополнение пользователя изменено",
                         reply_markup=kb.get_worker_back_to_managment_kb(target))
    await state.clear()

@router.callback_query(F.data.startswith('worker_min_withdraw_'))
async def cmd_min_withdraw(cb: CallbackQuery, session: AsyncSession, state: FSMContext):
    target = await session.get(User, cb.data.split('_')[-1])
    await state.update_data(target_id=target.id)
    await cb.message.edit_text(
        f'''✍️ Укажите минимальную сумму вывода для пользователя {target.currency.value.upper()}
Текущий мин.вывод: {await currency_exchange.get_exchange_rate(target.currency, target.min_withdraw)} {target.currency.value.upper()}''',
        reply_markup=kb.get_worker_back_to_managment_kb(target))
    
    await state.set_state(ManageReferal.wait_min_withdraw_amount)

@router.message(F.text, ManageReferal.wait_min_withdraw_amount)
async def set_min_withdraw_amount(message: Message, state: FSMContext, session: AsyncSession):
    target_id = (await state.get_data())['target_id']
    target = await session.get(User, target_id)
    try:
        amount = float(message.text)
        if amount < 0:
            raise ValueError
    except ValueError:
        await message.answer("Сумма должна быть положительным числом, введите ещё раз:",
                             reply_markup=kb.get_worker_back_to_managment_kb(target))
        return

    target.min_withdraw = await currency_exchange.convert_to_usd(target.currency, amount)
    session.add(target)
    await message.answer("Минимальный вывод пользователя изменен",
                         reply_markup=kb.get_worker_back_to_managment_kb(target))

@router.callback_query(F.data.startswith('worker_send_message_'))
async def cmd_send_message_to_referal(cb: CallbackQuery, session: AsyncSession,
                                       state: FSMContext):
    await state.update_data(target_id=cb.data.split('_')[-1])
    target = await session.get(User, cb.data.split('_')[-1])
    await cb.message.edit_text(
        "Введите сообщение, которое вы хотите отправить этому пользователю",
        reply_markup=kb.get_worker_back_to_managment_kb(target))
    await state.set_state(ManageReferal.wait_message)
    
@router.message(F.text, ManageReferal.wait_message)
async def send_message_to_referal(message: Message, state: FSMContext, session: AsyncSession,
                                  bot: Bot):
    target_id = (await state.get_data())['target_id']
    target = await session.get(User, target_id)
    try:
        await bot.copy_message(target.tg_id, message.chat.id, message.message_id)
    except TelegramBadRequest:
        await message.answer(
            "Не удалось отправить сообщение. Вероятно, пользователь заблокировал бота",
                         reply_markup=kb.get_worker_back_to_managment_kb(target))
    else:
        await message.answer("Сообщение успешно отправлено пользователю",
                            reply_markup=kb.get_worker_back_to_managment_kb(target))
    await state.clear()

@router.callback_query(F.data.startswith('confirm_referal_deposit_'))
async def cmd_confirm_referal_deposit(cb: CallbackQuery, state: FSMContext,
                                       session: AsyncSession):
    data = cb.data.split('_')
    amount, referal_id = data[-2], data[-1]
    target = await session.get(User, referal_id)
    await target.top_up_balance(session, amount)
    await cb.message.edit_text(
        "Пополнение пользователя прошло успешно",
        reply_markup=None
    )

@router.callback_query(F.data.startswith('referal_withdraw_'))
async def cmd_confirm_referal_withdraw(cb: CallbackQuery, bot: Bot,
                                       session: AsyncSession):
    data = cb.data.split('_')
    status, target_id = data[-2], data[-1]
    target = await session.get(User, target_id)
    if status == 'confirm':
        log_status = '✅Успешно приняли вывод\n'
        text = target.lang_data['text']['withdraw_accept']
    elif status == 'decline':
        log_status = '❌Отклонили вывод\n'
        text = target.lang_data['text']['withdraw_decline'].format(config.OKX_SUPPORT_LINK)
    else: # Support
        log_status = 'Отправлен в Тех.поддержку\n'
        text = target.lang_data['text']['withdraw_support'].format(config.OKX_SUPPORT_LINK)
    msg_text = cb.message.text
    new_message_text = log_status + msg_text.partition('\n')[2]
    if status != 'support': 
        reply_markup = None
    else:
        reply_markup=kb.get_referal_withdraw_support_kb(target.id)
    await cb.message.edit_text(new_message_text, reply_markup=reply_markup)
    await bot.send_message(target.tg_id, text)
