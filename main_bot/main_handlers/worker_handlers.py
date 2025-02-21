from aiogram import Router, Bot, F
from aiogram.types import Message, FSInputFile
from middlewares import IsVerifiedMiddleware, AuthorizeMiddleware
from database.models import User
import datetime as dt

router = Router()
router.message.middleware(AuthorizeMiddleware())
router.message.middleware(IsVerifiedMiddleware())
router.callback_query.middleware(AuthorizeMiddleware())
router.callback_query.middleware(IsVerifiedMiddleware())


@router.message(F.text == '💎 Профиль')
async def profile(message: Message, user: User):
    days_number = (dt.datetime.now() - user.created_at).days
    text = f'<b>🔮 Профиль воркера</b>\n\nTelegram ID: {user.tg_id}\n\
Вы зарегистрировались в боте {days_number} дней назад'
    await message.answer(text, parse_mode='HTML')


@router.message(F.text == '💼 Трейд бот')
async def trade_bot(message: Message, user: User):
    link = ''  # EDIT BEFORE DEPLOY
    text = ('💼 <b>Трейд бот</b>\n\n'
            f'{link}\n'
            f'Чтобы войти в ворк-панель, перейдите по ссылке и напишите <code>Воркер</code>\n'
            f'<b>Ваша реферальная ссылка</b>(Нажми и скопируй)\n'
            f"<code>{link}?start=w{user.tg_id}</code>")
    await message.answer(text, parse_mode='HTML')


@router.message(F.text == '🎆 NFT бот')
async def nft_bot(message: Message, user: User):
    link = ''  # EDIT BEFORE DEPLOY
    text = ('🎆 <b>NFT бот</b>\n\n'
            f'{link}\n'
            f'Чтобы войти в ворк-панель, перейдите по ссылке и напишите <code>Воркер</code>\n'
            f'<b>Ваша реферальная ссылка(Нажми и скопируй)</b>\n'
            f"<code>{link}?start={user.tg_id}</code>")
    await message.answer(text, parse_mode='HTML')


@router.message(F.text == '🗽 О проекте')
async def about_project(message: Message, user: User):
    text = ('<b>🗽О проекте</b>\n\n')
    await message.answer(text, parse_mode='HTML')
