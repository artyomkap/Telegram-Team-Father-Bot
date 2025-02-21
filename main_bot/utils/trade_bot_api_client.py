from pydantic import BaseModel
import aiohttp
import config


class UserProfile(BaseModel):
    tg_id: int
    balance: int
    min_deposit: int
    min_withdraw: int
    is_verified: bool
    purchase_enabled: bool
    output_enabled: bool
    is_blocked: bool


class UserNotFoundError(Exception):
    pass

class TradeBotApiClient:
    def __init__(self):
        self.session = None

    async def async_init(self):
        self.session = aiohttp.ClientSession()

    async def get_user_profile(self, user_tg_id: int) -> UserProfile:
        url = f"{config.TRADE_BOT_API_URL}/user/{user_tg_id}/"
        async with self.session.get(url) as response:
            if response.status == 404:
                raise UserNotFoundError
            data = await response.json()
            return UserProfile(**data)
        
    async def set_user_profile(self, profile: UserProfile):
        url = f"{config.TRADE_BOT_API_URL}/user/profiles/"
        async with self.session.post(url, json=profile.model_dump()) as response:
            return await response.json()
        
    async def close(self):
        if self.session:
            await self.session.close()

trade_bot_api_client = TradeBotApiClient()