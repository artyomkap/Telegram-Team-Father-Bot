from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
import logging
from aiogram.exceptions import TelegramBadRequest
from database.models import User
from database.connect import async_session
from database.crud import register_referal, get_user_by_tg_id
from sqlalchemy import select, update
from datetime import datetime
from utils.get_exchange_rate import currency_exchange
import keyboards as kb


class AuthorizeMiddleware(BaseMiddleware):
    '''Inject AsyncSession and User objects'''
    async def __call__(self, handler, event: Message, data) -> bool:
        async with async_session() as session:
            uid = event.from_user.id if hasattr(event, 'from_user') else event.message.from_user.id
            query = select(User).where(User.tg_id == uid)
            user: User | None = (await session.execute(query)).scalar()

            if not user:
                user = User(tg_id=str(event.from_user.id),
                            fname=event.from_user.first_name,
                            lname=event.from_user.last_name,
                            username=event.from_user.username
                            )
                logger = logging.getLogger()
                logger.info(f'New user')
                session.add(user)
                if 'command' in data and (command := data['command']).args:
                    referer_tg_id = command.args
                    referer = await get_user_by_tg_id(session, referer_tg_id)

                    if referer and not referer.is_worker:  # Check if referer is not None
                        await referer.send_log(data['bot'],
                                               f"Добавление реферала\nID реферала:<code>{user.tg_id}</code>")

                    await session.refresh(user, ['referer'])

                    if referer and referer is not user and user.referer is None:
                        user.currency = referer.currency_for_referals
                        session.add(user)
                        await session.commit()
                        await register_referal(session, referer, user,
                                                bot=data['bot'])

            if user.is_blocked:
                await event.answer("Ваш аккаунт заблокирован")
                return False

            query = update(User).where(User.tg_id==user.tg_id).values(last_login=datetime.now())
            await session.execute(query)
            await session.commit()

            data['user'] = user
            data['session'] = session
            result = await handler(event, data)
            await session.commit()

        return result


class IsAdminMiddleware(BaseMiddleware):
    async def __call__(self, handler, message: Message, data) -> bool:
        user = data['user']
        if not user.is_admin:
            await message.answer('Вы не являетесь администратором. Войдите в админ панель, написав команду /a')
        else:
            return await handler(message, data)

async def get_string_user_representation(target: User, worker: User):
    states = {None: 'Рандом', False: 'Проигрыш', True: 'Выигрыш'}
    return f'''🆔 Id: {target.tg_id} 
{f'👦 Username: @{target.username}' if target.username else ''}
👨‍💻 Воркер: {worker.tg_id}
💰 Баланс: {await target.get_balance()} {target.currency.value.upper()}
 ∟Мин. вывод: {await currency_exchange.get_exchange_rate(target.currency,
  target.min_withdraw)} {target.currency.value.upper()}
🔝 Максимальный баланс: {await currency_exchange.get_exchange_rate(target.currency,
 target.max_balance)} {target.currency.value.upper()}
💸 Минимальная сумма пополнения: {await currency_exchange.get_exchange_rate(target.currency,
 target.min_deposit)} {target.currency.value.upper()}
📑 Верификация: {'✅' if target.is_verified else '❌'}
📊 Статус торгов: {'✅' if not target.bidding_blocked else '❌'}
💰 Статус вывода: {'✅' if not target.withdraw_blocked else '❌'}
🎰 Статус: {states[target.bets_result_win]}
'''


class WorkerInjectTargetUserMiddleware(BaseMiddleware):
    def __init__(self, *args, get_text: callable=get_string_user_representation, **kwargs):
        self.get_text = get_text
        super().__init__(*args, **kwargs)

    async def __call__(self, handler, callback: CallbackQuery, data) -> bool:
        if (not callback.data.startswith('worker_') 
                or not callback.data.split('_')[-1].isdigit()):
            return await handler(callback, data)
        session = data['session']
        target_uid = int(callback.data.split('_')[-1])
        target = await session.get(User, target_uid)
        data['target'] = target
        res = await handler(callback, data)
        session.add(target)
        try:
            await callback.message.edit_text(
                await self.get_text(worker=data['user'], target=target),
                reply_markup=kb.get_worker_user_managment_kb(target))
        except TelegramBadRequest:
            pass # msg not modified
        return res