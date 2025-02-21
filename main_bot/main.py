from api.routers import router as fastapi_router
import logging
from main_handlers import main_handlers, worker_handlers
from contextlib import asynccontextmanager
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Bot, Dispatcher, types
from aiogram.exceptions import TelegramBadRequest
import config
from admin_handlers import admin_handlers
from fastapi import FastAPI
import uvicorn
from database.connect import init_models, dispose_engine
from utils.bot_methods import bot
from utils.trade_bot_api_client import trade_bot_api_client


storage = MemoryStorage()
logging.basicConfig(level=logging.INFO)

dp = Dispatcher()
dp.include_routers(main_handlers.router, worker_handlers.router, admin_handlers.router)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await bot.set_webhook(url=(config.WEBHOOK_URL
                               + config.TELEGRAM_WEBHOOK_PATH))
    bot_info = await bot.get_me()
    print(f'Бот успешно запущен: {bot_info.username}')
    await init_models()
    await trade_bot_api_client.async_init()
    yield
    await trade_bot_api_client.close()
    await dispose_engine()
    await bot.session.close()


app = FastAPI(lifespan=lifespan)
app.include_router(fastapi_router)


@app.post(config.TELEGRAM_WEBHOOK_PATH)
async def bot_webhook(update: dict):
    telegram_update = types.Update(**update)
    try:
        await dp.feed_update(bot=bot, update=telegram_update)
    except TelegramBadRequest as e:
        logging.getLogger(__name__).error(e, stack_info=True)


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=config.WEBHOOK_PORT)
