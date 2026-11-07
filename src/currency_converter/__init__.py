"""
Currency Converter Application Package.
"""

from .models import Currency, CurrencyType, ExchangeRate, ConversionResult
from .exceptions import CurrencyConverterError, RateFetchError, ValidationError, OfflineCacheError
from .cache_manager import RateCacheManager
from .providers.bnm_provider import BnmRateProvider
from .providers.crypto_provider import CryptoRateProvider
from .service import CurrencyConverterService
from .gui.main_window import MainWindow

__all__ = [
    "Currency",
    "CurrencyType",
    "ExchangeRate",
    "ConversionResult",
    "CurrencyConverterError",
    "RateFetchError",
    "ValidationError",
    "OfflineCacheError",
    "RateCacheManager",
    "BnmRateProvider",
    "CryptoRateProvider",
    "CurrencyConverterService",
    "MainWindow",
]
