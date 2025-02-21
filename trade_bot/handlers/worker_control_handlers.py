from aiogram import F, Router
from aiogram.types import CallbackQuery
from middlewares import AuthorizeMiddleware, WorkerInjectTargetUserMiddleware
from database.models import User


router = Router()
router.message.middleware(AuthorizeMiddleware())
router.callback_query.middleware(AuthorizeMiddleware())
router.callback_query.middleware(WorkerInjectTargetUserMiddleware())


@router.callback_query(lambda cb: cb.data.startswith('worker_') 
                        and cb.data.split('_')[1] in ('win', 'lose', 'random'))
async def cmd_worker_stats(callback: CallbackQuery, target: User):
    state = callback.data.split('_')[1]
    states = {'win': True, 'lose': False, 'random': None}
    target.bets_result_win = states[state]

@router.callback_query(F.data.startswith("worker_verif_"))
async def cmd_worker_verif(callback: CallbackQuery, target: User):
    target.is_verified = not target.is_verified

@router.callback_query(F.data.startswith('worker_blockbidding_'))
async def cmd_worker_blockbidding(callback: CallbackQuery, target: User):
    target.bidding_blocked = not target.bidding_blocked

@router.callback_query(F.data.startswith('worker_block_withdraw_'))
async def cmd_worker_block_withdraw(callback: CallbackQuery, target: User):
    target.withdraw_blocked = not target.withdraw_blocked

@router.callback_query(F.data.startswith('worker_block'))
async def cmd_ban_user(callback: CallbackQuery, target: User):
    target.is_blocked = not target.is_blocked