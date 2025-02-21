from config import SQLALCHEMY_URL
from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from utils.get_exchange_rate import currency_exchange
from .enums import CurrencyEnum
from datetime import datetime
from typing import Optional
from .connect import Base
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
import config
from aiogram import types, Bot

engine = create_async_engine(SQLALCHEMY_URL, echo=True)

async_session = async_sessionmaker(engine)


class UserPromocodeAssotiation(Base):  # Many-to-Many between ordinary users and promocodes
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
    language: Mapped[str]
    balance: Mapped[int] = mapped_column(default=0)
    currency: Mapped[CurrencyEnum] = mapped_column(default=CurrencyEnum.usd)
    is_blocked: Mapped[bool] = mapped_column(default=False)
    is_verified: Mapped[bool] = mapped_column(default=False)
    last_login: Mapped[datetime] = mapped_column(default=datetime.now)
    min_deposit: Mapped[int] = mapped_column(default=0)
    min_withdraw: Mapped[int] = mapped_column(default=0)
    is_withdraw: Mapped[bool] = mapped_column(default=True)
    is_buying: Mapped[bool] = mapped_column(default=True)
    is_worker: Mapped[bool] = mapped_column(default=False)

    referer_id: Mapped[Optional['User']] = mapped_column(ForeignKey('users.id'))
    referals: Mapped[list['User']] = relationship('User', back_populates='referer')
    referer: Mapped[Optional['User']] = relationship('User', back_populates='referals', remote_side=[id])

    favourites: Mapped[list['Favourites']] = relationship('Favourites', back_populates='user')
    purchased: Mapped[list['Purchased']] = relationship('Purchased', back_populates='user')

    promocodes: Mapped[list[UserPromocodeAssotiation]] = relationship(
        back_populates="user")

    currency_for_referals: Mapped[CurrencyEnum] = mapped_column(default=CurrencyEnum.usd)

    async def get_balance(self) -> float:
        '''Return user balance converted to user currency'''
        return await currency_exchange.get_exchange_rate(self.currency, self.balance)

    async def top_up_balance(self, session: AsyncSession, amount: int):
        """Asynchronously tops up the balance of the user by the specified amount."""
        await session.execute(
            update(User).where(User.tg_id == self.tg_id)
            .values(balance=User.balance + amount)
        )
        if (referer := await self.awaitable_attrs.referer) is not None:
            await session.execute(
                update(User).where(User.tg_id == referer.tg_id)
                .values(balance=User.balance + amount * config.REFERAL_BONUS_PERCENT)
            )

    async def send_log(self, bot: Bot, text: str,
                       kb: types.InlineKeyboardMarkup | None = None) -> None:
        '''Send log about user actions to his referer'''
        referer = await self.awaitable_attrs.referer
        if self.username:
            name = '@' + self.username
        else:
            name = self.fname or self.lname or None
        ident = f'{name}(<code>{self.tg_id}</code>)' if name else self.tg_id
        if referer:
            await bot.send_message(
                referer.tg_id,
                f'''Пользователем {ident} было совершено действие:
{text}''', reply_markup=kb, parse_mode='HTML')

    def __str__(self):
        if self.username is not None:
            return f"@{self.username}"
        elif self.fname is None and self.lname is None:
            return self.tg_id
        else:
            return f"{self.fname or ''} {self.lname or ''}({self.tg_id})"


class Category(Base):
    __tablename__ = 'categories'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column()

    products = relationship('Product', back_populates='category')  # Pluralized 'products'


class Product(Base):
    __tablename__ = 'products'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column()
    description: Mapped[str] = mapped_column()
    price: Mapped[str] = mapped_column()
    author: Mapped[str] = mapped_column()
    photo: Mapped[str] = mapped_column()
    category_id: Mapped[int] = mapped_column(ForeignKey('categories.id'))

    category = relationship('Category', back_populates='products')  # Pluralized 'products'
    favourites = relationship("Favourites", back_populates="product")
    purchased = relationship('Purchased', back_populates='product')

    async def get_product_price(self) -> float:
        '''Return product price converted to user currency'''
        return await currency_exchange.get_exchange_rate(User.currency, self.price)


class Favourites(Base):
    __tablename__ = 'favourites'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'))

    user = relationship('User', back_populates='favourites')
    product = relationship('Product', back_populates='favourites')


class Purchased(Base):
    __tablename__ = 'purchased'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'))

    user = relationship('User', back_populates='purchased')
    product = relationship('Product', back_populates='purchased')


class Promocode(Base):
    __tablename__ = "promocodes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str]
    currency: Mapped[CurrencyEnum] = mapped_column(default=CurrencyEnum.usd)
    amount: Mapped[int]
    reusable: Mapped[bool]


    users: Mapped[list[UserPromocodeAssotiation]] = relationship(
        back_populates="promocode", cascade='all, delete-orphan')