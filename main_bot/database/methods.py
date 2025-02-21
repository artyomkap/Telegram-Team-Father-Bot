from api.schemas import ReferalModel, Promocode as PromocodeModel
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, OrdinaryUser, Promocode
import datetime as dt


async def get_user_by_tg_id(session: AsyncSession, tg_id: int):
    return await session.scalar(select(User).where(User.tg_id == tg_id))


async def add_referal(session: AsyncSession, referal: ReferalModel):
    new_referal = OrdinaryUser(tg_id = referal.referal_tg_id,
                               fname = referal.fname, lname = referal.lname,
                               username = referal.username)
    referer = await get_user_by_tg_id(session, referal.referal_link_id)
    (await referer.awaitable_attrs.ordinary_users).append(new_referal)
    session.add_all([new_referal, referer])
    await session.commit()

async def get_user_by_their_referal(session: AsyncSession, referal_tg_id: int) -> User | None:
    ordinary_user = await session.scalar(select(OrdinaryUser)
                             .where(OrdinaryUser.tg_id == referal_tg_id)
                             .options(selectinload(OrdinaryUser.regulatory_user)))
    return ordinary_user.regulatory_user

async def create_promocode(session: AsyncSession, promocode_model: PromocodeModel):
    worker = await get_user_by_tg_id(session, promocode_model.creator_tg_id)
    promocode = Promocode(**promocode_model.model_dump(), creator=worker)
    session.add(promocode)
    await session.commit()



async def activate_promocode(session: AsyncSession, code: str, 
                             tg_id: int) -> PromocodeModel | None:
    user = await session.scalar(select(OrdinaryUser).where(User.tg_id == tg_id))
    promocode = await session.scalar(select(Promocode).where(Promocode.code == code))
    if user and promocode:
        if user in promocode.awaitable_attrs.users:
            return None
        promocode.number_of_activations += 1
        (await user.awaitable_attrs.promocodes).append(promocode)
        creator = await promocode.awaitable_attrs.creator
        session.add_all([promocode, user])
        await session.commit()
        return PromocodeModel(promocode, creator_tg_id=creator.tg_id)
    return None

async def get_active_users_count(session: AsyncSession) -> list[User]:
    '''return count of users who usebot in last 24 hours'''
    separator = dt.datetime.now() - dt.timedelta(hours=24)
    return (await session.execute(
        select(func.count(User.id))
        .where(User.last_login >= separator))).scalars().all()