"""
Доменные модели данных для конвертера валют и криптовалют.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class CurrencyType(str, Enum):
    """Тип валюты: фиатная или криптовалюта."""
    FIAT = "fiat"
    CRYPTO = "crypto"


@dataclass(frozen=True)
class Currency:
    """
    Информация о валюте.

    Attributes:
        code: 3-буквенный или символьный код (USD, EUR, MDL, BTC, etc.).
        name: Название валюты (US Dollar, Euro, Bitcoin, etc.).
        currency_type: Тип валюты (FIAT или CRYPTO).
        symbol: Символ валюты ($, €, L, ₿, etc.).
    """
    code: str
    name: str
    currency_type: CurrencyType = CurrencyType.FIAT
    symbol: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", self.code.strip().upper())
        object.__setattr__(self, "name", self.name.strip())

    @property
    def display_name(self) -> str:
        """Отображаемое имя в выпадающих списках."""
        return f"{self.code} — {self.name}"


@dataclass(frozen=True)
class ExchangeRate:
    """
    Курс обмена по отношению к базовой валюте (MDL).

    Attributes:
        code: Код котируемой валюты (например, EUR).
        nominal: Номинал (например, 1 или 100).
        rate_to_base: Стоимость номинала в базовой валюте (MDL).
        date: Дата актуальности курса.
        source: Название источника (НБМ / Binance / Кэш).
        currency_type: Тип валюты.
    """
    code: str
    nominal: int
    rate_to_base: float
    date: str
    source: str
    currency_type: CurrencyType = CurrencyType.FIAT

    def __post_init__(self) -> None:
        if self.nominal <= 0:
            raise ValueError("Номинал должен быть положительным числом")
        if self.rate_to_base <= 0:
            raise ValueError("Курс валюты должен быть положительным числом")


@dataclass
class ConversionResult:
    """
    Результат операции конвертации.

    Attributes:
        amount: Исходная сумма.
        from_code: Код исходной валюты.
        to_code: Код целевой валюты.
        result_amount: Рассчитанная итоговая сумма.
        rate: Примененный кросс-курс (1 единица from = rate единиц to).
        reverse_rate: Обратный курс (1 единица to = reverse_rate единиц from).
        rate_date: Дата курса.
        source: Источник данных.
        is_offline: Флаг использования локального кэша при отсутствии сети.
    """
    amount: float
    from_code: str
    to_code: str
    result_amount: float
    rate: float
    reverse_rate: float
    rate_date: str
    source: str
    is_offline: bool = False
