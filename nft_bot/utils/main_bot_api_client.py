import aiohttp
from pydantic import BaseModel
import config


class LogRequest(BaseModel):
    user_tg_id: str
    log_text: str


class ReferalModel(BaseModel):
    referal_tg_id: str
    referal_link_id: str
    fname: str | None = None
    lname: str | None = None
    username: str | None = None


class Promocode(BaseModel):
    creator_tg_id: int
    code: str
    amount: int
    number_of_activations: int = 1

    class Config:
        from_attributes = True


class PromocodeActivate(BaseModel):
    code: str
    tg_id: int


class PromocodeOut(BaseModel):
    available: bool
    promocode: Promocode | None = None


class TradeBotPaymentProps(BaseModel):
    card: str
    usdt_trc20_wallet: str
    btc_wallet: str
    eth_wallet: str


class MainBotApiClient:
    async def async_init(self, session: aiohttp.ClientSession = None):
        self.session = session or aiohttp.ClientSession()

    async def get_payment_props(self) -> TradeBotPaymentProps | None:
        '''Return payment props or None if props not set'''
        url = f"{config.MAIN_BOT_API_URL}/nft_bot/payment_props/"
        async with self.session.get(url) as response:
            if response.status != 200:
                raise Exception('Main bot api not found')
            data = await response.json()
            if data:
                return TradeBotPaymentProps(**data)

    async def close(self):
        await self.session.close()


main_bot_api_client = MainBotApiClient()
