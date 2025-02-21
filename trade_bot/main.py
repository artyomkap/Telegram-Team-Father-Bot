from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
import config
from aiogram.exceptions import TelegramBadRequest
from handlers import (main_handlers, wallet_handlers, worker_handlers,
                       worker_control_handlers)
from database.connect import init_models, dispose_engine
import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from api import routers as api_router
import uvicorn
from utils import currency_exchange
from utils.main_bot_api_client import main_bot_api_client


logging.basicConfig(filename='trade_bot.log', level=logging.INFO)

dp = Dispatcher()
bot = Bot(token=config.TOKEN, default=DefaultBotProperties(parse_mode='HTML'))

@asynccontextmanager
async def lifespan(app: FastAPI):
    await bot.set_webhook(url = (config.WEBHOOK_URL
                           + config.TELEGRAM_WEBHOOK_PATH),
                           allowed_updates=['*'])
    bot_info = await bot.get_me()
    logging.getLogger(__name__).info(f'Бот успешно запущен: {bot_info.username}')
    await init_models()
    await currency_exchange.async_init()
    await main_bot_api_client.async_init()
    yield
    #await bot.delete_webhook()
    await bot.close()
    await currency_exchange.close()
    await main_bot_api_client.close()
    await dispose_engine()

app = FastAPI(lifespan=lifespan)

@app.post(config.TELEGRAM_WEBHOOK_PATH)
async def bot_webhook(update: dict):
    telegram_update = types.Update(**update)
    try:
        await dp.feed_update(bot=bot, update=telegram_update)
    except TelegramBadRequest as e:
        logging.error(e, stack_info=True)

if __name__ == '__main__':
    app.include_router(api_router.router)
    app.mount("/exchange", StaticFiles(directory="okx/ru/exchange"), name="static")
    dp.include_routers(main_handlers.router, 
                   wallet_handlers.router,
                   worker_handlers.router,
                   worker_control_handlers.router
                   )
    uvicorn.run(app, host="0.0.0.0", port=config.WEBHOOK_PORT)