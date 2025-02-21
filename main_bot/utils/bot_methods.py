import config
from aiogram import Bot

bot: Bot = Bot(config.TOKEN)


async def send_notification_of_referal(tg_id):
    '''Send notification about new referal that doesn't have referal link'''
    for admin_id in config.ADMIN_IDS:
        await bot.send_message(admin_id, f'Пользователь с ID {tg_id} пришел \
без реферальной ссылки!')  # TODO button for binding referal
