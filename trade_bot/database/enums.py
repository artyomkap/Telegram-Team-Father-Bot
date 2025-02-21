from enum import Enum, unique

@unique
class LangEnum(Enum):
    ru = "RU"
    en = "EN"
    ua = "UA"
    pl = "PL"

@unique
class CurrencyEnum(Enum):
    usd = "USD"
    eur = "EUR"
    rub = "RUB"
    uah = "UAH"
    byn = "BYN"
    ils = "ILS"
    pln = "PLN"