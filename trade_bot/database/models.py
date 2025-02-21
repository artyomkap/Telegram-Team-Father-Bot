from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, select, update, Table, Column
from .connect import Base
from datetime import datetime, timedelta
from .enums import LangEnum, CurrencyEnum
from utils import currency_exchange
from locales import data as lang_data
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import config
from aiogram import types, Bot


class UserPromocodeAssotiation(Base): # Many-to-Many between ordinary users and promocodes
    __tablename__ = "user_promocode_association_table"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    promocode_id: Mapped[int] = mapped_column(ForeignKey("promocodes.id"), primary_key=True)
    is_creator: Mapped[bool] = mapped_column(default=False)

    user = relationship("User", back_populates="promocodes", cascade='all, delete')
    promocode = relationship("Promocode", back_populates="users", cascade='all, delete')
    

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tg_id: Mapped[str] = mapped_column(unique=True)
    fname: Mapped[str | None]
    lname: Mapped[str | None]
    username: Mapped[str | None]
    language: Mapped[LangEnum] = mapped_column(default=LangEnum.ru)
    balance: Mapped[int] = mapped_column(default=0)
    currency: Mapped[CurrencyEnum] = mapped_column(default=CurrencyEnum.usd)
    is_blocked: Mapped[bool] = mapped_column(default=False)
    is_verified: Mapped[bool] = mapped_column(default=False)
    last_login: Mapped[datetime] = mapped_column(default=datetime.now)
    registration_date: Mapped[datetime] = mapped_column(default=datetime.now)

    # for referals, useless for workers
    min_deposit: Mapped[int] = mapped_column(default=0)
    min_withdraw: Mapped[int] = mapped_column(default=0)
    max_balance: Mapped[int] = mapped_column(default=1000000)
    withdraw_blocked: Mapped[bool] = mapped_column(default=False)
    bidding_blocked: Mapped[bool] = mapped_column(default=False)
    bets_result_win: Mapped[bool | None] = mapped_column(
        default=None)  # None - random, False - lose, True - win

    referer_id: Mapped[Optional['User']] = mapped_column(ForeignKey('users.id'))
    referals: Mapped[list['User']] = relationship('User', back_populates='referer')
    referer: Mapped[Optional['User']] = relationship('User', back_populates='referals',
                                                   remote_side=[id])
    is_worker: Mapped[bool] = mapped_column(default=False)

    orders: Mapped[list['Order']] = relationship('Order', back_populates='user')
    
    promocodes: Mapped[list[UserPromocodeAssotiation]] = relationship(
        back_populates="user")
    
    currency_for_referals: Mapped[CurrencyEnum] = mapped_column(default=CurrencyEnum.usd)
    
    async def top_up_balance(self, session: AsyncSession, amount: int):
        """
        Asynchronously tops up the balance of the user by the specified amount.
        """
        await session.execute(
            update(User).where(User.tg_id == self.tg_id)
            .values(balance=User.balance + amount)
        )

    async def get_balance(self) -> float:
        '''retun user balance converted to user currency'''
        return await currency_exchange.get_exchange_rate(self.currency, self.balance)


    @property
    def lang_data(self) -> dict:
        return lang_data[self.language]

    async def send_log(self, bot: Bot, text: str, 
                       kb: types.InlineKeyboardMarkup | None = None) -> None:
        '''Send log about user actions to his referer'''
        referer = await self.awaitable_attrs.referer
        if self.username:
            name = '@' + self.username
        else:
            name = self.fname or self.lname or None
        ident = f'{name}(<code>{self.tg_id}</code>)' if name else self.tg_id
        if self.referer:
            await bot.send_message(
                referer.tg_id, 
                f'''Пользователем {ident} было совершено действие:
{text}''', reply_markup=kb)

    def __str__(self):
        if self.username is not None:
            return f"@{self.username}"
        elif self.fname is None and self.lname is None:
            return self.tg_id
        else:
            return f"{self.fname or ''} {self.lname or ''}({self.tg_id})"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    cryptocurrency: Mapped[str | None]
    amount: Mapped[int] = mapped_column(default=0)
    amount_usd: Mapped[int] = mapped_column(default=0)
    is_long: Mapped[bool] = mapped_column(default=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    bets_result_win: Mapped[bool]
    # False - lose, True - win

    profit: Mapped[int] # Profit in User.Currency, may be less than 0 if bets_resut_win is False
    profit_usd: Mapped[int]  # profit in USD
    time: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)

    user: Mapped[User] = relationship('User', back_populates='orders')

class Promocode(Base):
    __tablename__ = "promocodes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str]
    amount: Mapped[int]
    reusable: Mapped[bool]

    users: Mapped[list[UserPromocodeAssotiation]] = relationship(
        back_populates="promocode", cascade='all, delete-orphan')
    
