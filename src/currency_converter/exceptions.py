"""
Иерархия исключений приложения конвертера валют.
"""


class CurrencyConverterError(Exception):
    """Базовое исключение для ошибок конвертера валют."""
    pass


class RateFetchError(CurrencyConverterError):
    """Ошибка при получении курсов валют из удаленного источника."""
    pass


class ValidationError(CurrencyConverterError):
    """Ошибка валидации пользовательского ввода (сумма, валюта)."""
    pass


class OfflineCacheError(CurrencyConverterError):
    """Ошибка при отсутствии локального кэша в оффлайн-режиме."""
    pass
