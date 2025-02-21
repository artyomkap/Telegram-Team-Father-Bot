from pydantic import BaseModel, field_validator
from datetime import datetime, timedelta
from database.models import User


class OrderView(BaseModel):
    cryptocurrency: str
    amount: float
    amount_usd: float
    time: int
    is_long: bool
    is_active: bool  # False - inactive, True - active
    bets_result_win: bool  # False - lose, True - win
    profit: float
    profit_usd: float
    created_at: datetime = datetime.now

    class Config:
        from_attributes = True


class UserProfile(BaseModel):
    tg_id: int
    fname: str
    balance: float
    currency: str
    registration_date: datetime
    min_deposit: float
    min_withdraw: float
    is_verified: bool
    # purchase_enabled: bool
    # output_enabled: bool
    # bidding_blocked: bool
    is_blocked: bool
    bets_result_win: bool | None  # False - always must lose, True - win, None - random

    orders: list[OrderView]

    @field_validator('orders', mode='before')
    @classmethod
    def convert_int_serial(cls, val):
        return list(map(lambda v: OrderView.model_validate(v), val))
    
    class Config:
        from_attributes = True

