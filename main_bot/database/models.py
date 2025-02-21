from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, Table, Column
from .connect import Base
from datetime import datetime


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tg_id: Mapped[str] = mapped_column(unique=True)
    fname: Mapped[str | None]
    lname: Mapped[str | None]
    username: Mapped[str | None]
    last_login: Mapped[datetime] = mapped_column(default=datetime.now)
    is_verified: Mapped[bool] = mapped_column(default=False)
    ordinary_users: Mapped[list['OrdinaryUser']] = relationship(
        'OrdinaryUser', back_populates='regulatory_user') # аккаунты обычных пользователей
    # которые может регулировать данный пользователь
    is_blocked: Mapped[bool] = mapped_column(default=False)
    promocodes: Mapped[list['Promocode']] = relationship('Promocode', 
                                                         back_populates='creator')
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)

user_promo_association_table = Table( # Many-to-Many between ordinary users and promocodes
    "user_promocode_association_table",
    Base.metadata,
    Column("user_id", ForeignKey("ordinary_users.id"), primary_key=True),
    Column("promocode_id", ForeignKey("promocodes.id"), primary_key=True),
)


class OrdinaryUser(Base):
    '''Класс описывает модель пользователя, который не является админом
    и не является пользователем main бота, но который воспльзовался nft или trade ботом'''
    __tablename__ = "ordinary_users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tg_id: Mapped[str] = mapped_column(unique=True)
    fname: Mapped[str | None]
    lname: Mapped[str | None]
    username: Mapped[str | None]
    last_login: Mapped[datetime] = mapped_column(default=datetime.now)
    regulatory_user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'))
    regulatory_user: Mapped[User | None] = relationship('User', back_populates='ordinary_users')
    promocodes: Mapped[list['Promocode']] = relationship(
        secondary=user_promo_association_table,
        back_populates="users",
    )



class Promocode(Base):
    __tablename__ = "promocodes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str]
    amount: Mapped[int]
    number_of_activations: Mapped[int] = mapped_column(default=1)

    creator_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    creator: Mapped[User] = relationship('User', back_populates='promocodes')

    users: Mapped[list[OrdinaryUser]] = relationship(
        secondary=user_promo_association_table, back_populates="promocodes"
    )