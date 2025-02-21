from aiogram import BaseMiddleware
from aiogram.types import Message
import logging
from databases.models import User
from databases.connect import async_session
from sqlalchemy import select, update
from datetime import datetime
from databases.crud import get_user_by_tg_id, register_referal
from utils.main_bot_api_client import LogRequest, main_bot_api_client, ReferalModel
import asyncio


class AuthorizeMiddleware(BaseMiddleware):
    '''Inject AsyncSession and User objects'''
    async def __call__(self, handler, event: Message, data) -> bool:
        async with async_session() as session:
            uid = event.from_user.id if hasattr(event, 'from_user') else event.message.from_user.id
            query = select(User).where(User.tg_id == uid)
            user: User = (await session.execute(query)).scalar()
            if not user:
                user = User(tg_id=str(event.from_user.id),
                            fname=event.from_user.first_name,
                            lname=event.from_user.last_name,
                            username=event.from_user.username,
                            language='en'
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
