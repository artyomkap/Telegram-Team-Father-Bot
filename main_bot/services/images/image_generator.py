from PIL import Image, ImageDraw, ImageFont
import io

from aiogram.types import InputFile


def generate_image(data):
    image_path = 'services/images/astronaut.png'
    image = Image.open(image_path)
    draw = ImageDraw.Draw(image)
    font_path = 'services/images/code_pro.otf'
    font = ImageFont.truetype(font_path, 45)

    worker_lvl, worker_days, worker_profits, sum_profits, next_lvl = data
    sum_profits = sum_profits + ' RUB'
    next_lvl = next_lvl + ' RUB'

    worker_lvl_position = (120, 314)
    worker_days_position = (120, 470)
    worker_profits_position = (120, 626)
    sum_profits_position = (580, 360)
    next_lvl_position = (580, 562)

    font1 = ImageFont.truetype(font_path, 45)
    draw.text(worker_lvl_position, worker_lvl, fill=(255, 255, 255), font=font1)
    draw.text(worker_days_position, worker_days, fill=(255, 255, 255), font=font1)
    draw.text(worker_profits_position, worker_profits, fill=(255, 255, 255), font=font1)
    font2 = ImageFont.truetype(font_path, 70)
    draw.text(sum_profits_position, sum_profits, fill=(255, 255, 255), font=font2)
    draw.text(next_lvl_position, next_lvl, fill=(255, 255, 255), font=font2)


    # Сохраняем изображение на диск
    output_image_path = 'profile.png'
    image.save(output_image_path, format='PNG')

    return output_image_path