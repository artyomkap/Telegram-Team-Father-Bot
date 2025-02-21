from database.enums import LangEnum
from .pl import data as pl_data
from .ru import data as ru_data
from .en import data as en_data
from .ua import data as ua_data

data = {
    LangEnum.en: en_data,
    LangEnum.ru: ru_data,
    LangEnum.ua: ua_data,
    LangEnum.pl: pl_data
}