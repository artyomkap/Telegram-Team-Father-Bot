from api.schemas import NftBotPaymentProps, TradeBotPaymentProps
from pydantic import BaseModel
import json


PROPS_STORAGE_PATH = 'payment_props.json'

class PropsManager(BaseModel):
    nft_bot_payment_props: NftBotPaymentProps | None = None
    trade_bot_payment_props: TradeBotPaymentProps | None = None

    def save_on_disk(self):
        with open(PROPS_STORAGE_PATH, 'w') as file:
            json.dump(self.model_dump(), file)

def load_props():
    try:
        with open(PROPS_STORAGE_PATH, 'r') as file:
            props = json.load(file)
            return PropsManager(**props)
    except FileNotFoundError:
        return PropsManager()

PAYMENT_PROPS = load_props() # Singleton