"""
Провайдер котировок криптовалют (Binance Public Ticker API).
"""

from __future__ import annotations
import logging
from datetime import datetime
from typing import Dict, List, Optional
import requests

from ..models import ExchangeRate, CurrencyType
from ..exceptions import RateFetchError

logger = logging.getLogger(__name__)

BINANCE_TICKER_URL = "https://api.binance.com/api/v3/ticker/price"

# Список поддерживаемых криптовалют
SUPPORTED_CRYPTO_SYMBOLS = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "TON": "TONUSDT",
    "BNB": "BNBUSDT",
}


class CryptoRateProvider:
    """
    Получение рыночных котировок криптовалют в реальном времени.

    Котировки криптовалют получаются к USD/USDT, после чего через
    официальный курс USD/MDL приводятся к единой базовой валюте MDL.
    """

    def __init__(self, timeout: int = 5) -> None:
        self.timeout = timeout

    def fetch_crypto_rates(self, usd_to_mdl_rate: float) -> dict[str, ExchangeRate]:
        """
        Запрашивает котировки криптовалют и пересчитывает их стоимость в MDL.

        Args:
            usd_to_mdl_rate: Текущий официальный курс USD к MDL от НБМ.
        """
        if usd_to_mdl_rate <= 0:
            raise ValueError("Курс USD к MDL должен быть положительным числом")

        now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
        rates: dict[str, ExchangeRate] = {}

        # 1. Добавляем стейблкоин USDT (1 USDT = 1 USD)
        rates["USDT"] = ExchangeRate(
            code="USDT",
            nominal=1,
            rate_to_base=usd_to_mdl_rate,
            date=now_str,
            source="Binance / Pegged USD",
            currency_type=CurrencyType.CRYPTO,
        )

        for code, pair in SUPPORTED_CRYPTO_SYMBOLS.items():
            try:
                response = requests.get(
                    BINANCE_TICKER_URL,
                    params={"symbol": pair},
                    timeout=self.timeout,
                )
                if response.status_code == 200:
                    data = response.json()
                    usd_price = float(data.get("price", 0))
                    if usd_price > 0:
                        # Стоимость 1 крипто-монеты в молдавских леях
                        mdl_rate = usd_price * usd_to_mdl_rate
                        rates[code] = ExchangeRate(
                            code=code,
                            nominal=1,
                            rate_to_base=mdl_rate,
                            date=now_str,
                            source="Binance Crypto API",
                            currency_type=CurrencyType.CRYPTO,
                        )
            except Exception as e:
                logger.warning("Не удалось получить котировку %s с Binance: %s", pair, e)

        if not rates:
            raise RateFetchError("Не удалось получить ни одной котировки криптовалют.")

        return rates
