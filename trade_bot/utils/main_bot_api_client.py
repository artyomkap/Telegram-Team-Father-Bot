import aiohttp
from pydantic import BaseModel
import config


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
        url = f"{config.MAIN_BOT_URL}/trade_bot/payment_props/"
        async with self.session.get(url) as response:
            if response.status != 200:
                raise Exception('Main bot api not found')
            data = await response.json()
            if data:
                return TradeBotPaymentProps(**data)

    async def close(self):
        await self.session.close()


main_bot_api_client = MainBotApiClient()
