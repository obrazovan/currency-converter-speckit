"""
Провайдеры данных котировок валют.
"""

from .base import RateProvider
from .bnm_provider import BnmRateProvider
from .crypto_provider import CryptoRateProvider

__all__ = ["RateProvider", "BnmRateProvider", "CryptoRateProvider"]
