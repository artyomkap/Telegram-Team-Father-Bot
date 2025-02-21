from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery
from middlewares import IsVerifiedMiddleware, AuthorizeMiddleware
from database.models import User
from aiogram.filters import Command
from keyboards import kb
from database.models import OrdinaryUser
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.fsm.context import FSMContext

router = Router()
router.message.middleware(AuthorizeMiddleware())
router.message.middleware(IsVerifiedMiddleware())
router.callback_query.middleware(AuthorizeMiddleware())
router.callback_query.middleware(IsVerifiedMiddleware())


@router.message(Command('worker'))
async def cmd_worker(message: Message, user: User):
    ordinary_users = await user.awaitable_attrs.ordinary_users
    text = 'Выберите пользователя' if ordinary_users else 'Пользователи отсутствуют'
    await message.answer(text,
                         reply_markup=kb.get_worker_select_kb(ordinary_users))


@router.callback_query(F.data.startswith('management_'))
async def cmd_management(cb: CallbackQuery, user: User, session: AsyncSession):
    ordinary_user_id = cb.data.split('_')[-1]
    ordinary_user = await session.get(OrdinaryUser, ordinary_user_id)
    await cb.message.edit_text(ordinary_user.get_management_text(),
                               reply_markup=kb.get_worker_panel_kb(ordinary_user.id))
