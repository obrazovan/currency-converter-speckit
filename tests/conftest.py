"""
Pytest fixtures для тестирования конвертера валют и криптовалют.
"""

from __future__ import annotations
import tempfile
from pathlib import Path
from typing import Iterator
import pytest

from currency_converter.models import CurrencyType, ExchangeRate
from currency_converter.service import CurrencyConverterService
from currency_converter.cache_manager import RateCacheManager
from currency_converter.providers.bnm_provider import BnmRateProvider
from currency_converter.providers.crypto_provider import CryptoRateProvider

SAMPLE_BNM_XML = """<?xml version="1.0" encoding="utf-8"?>
<ValCurs Date="07.11.2026" name="Official exchange rate">
    <Valute ID="47">
        <NumCode>978</NumCode>
        <CharCode>EUR</CharCode>
        <Nominal>1</Nominal>
        <Name>Euro</Name>
        <Value>20.1089</Value>
    </Valute>
    <Valute ID="44">
        <NumCode>840</NumCode>
        <CharCode>USD</CharCode>
        <Nominal>1</Nominal>
        <Name>US Dollar</Name>
        <Value>17.9200</Value>
    </Valute>
    <Valute ID="36">
        <NumCode>946</NumCode>
        <CharCode>RON</CharCode>
        <Nominal>1</Nominal>
        <Name>Romanian Leu</Name>
        <Value>3.7663</Value>
    </Valute>
    <Valute ID="43">
        <NumCode>643</NumCode>
        <CharCode>RUB</CharCode>
        <Nominal>100</Nominal>
        <Name>Russian Ruble</Name>
        <Value>21.9700</Value>
    </Valute>
</ValCurs>"""

EMPTY_BNM_XML = """<?xml version="1.0" encoding="utf-8"?>
<ValCurs Date="07.11.2026" name="Official exchange rate">
</ValCurs>"""


@pytest.fixture
def tmp_cache_path() -> Iterator[Path]:
    """Временный файл кэша котировок."""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td) / "test_rates_cache.json"


@pytest.fixture(scope="session")
def mock_rates() -> dict[str, ExchangeRate]:
    """Словарь эталонных котировок для детерминированного тестирования расчетов."""
    date_str = "07.11.2026"
    source = "Тестовый источник"
    return {
        "MDL": ExchangeRate("MDL", 1, 1.0, date_str, source, CurrencyType.FIAT),
        "EUR": ExchangeRate("EUR", 1, 20.0, date_str, source, CurrencyType.FIAT),
        "USD": ExchangeRate("USD", 1, 18.0, date_str, source, CurrencyType.FIAT),
        "RON": ExchangeRate("RON", 1, 4.0, date_str, source, CurrencyType.FIAT),
        "RUB": ExchangeRate("RUB", 100, 20.0, date_str, source, CurrencyType.FIAT),  # 1 RUB = 0.2 MDL
        "BTC": ExchangeRate("BTC", 1, 900000.0, date_str, source, CurrencyType.CRYPTO),  # 50,000 USD * 18 MDL
        "ETH": ExchangeRate("ETH", 1, 36000.0, date_str, source, CurrencyType.CRYPTO),  # 2,000 USD * 18 MDL
        "USDT": ExchangeRate("USDT", 1, 18.0, date_str, source, CurrencyType.CRYPTO),
    }


@pytest.fixture
def sample_service(mock_rates: dict[str, ExchangeRate], tmp_cache_path: Path) -> CurrencyConverterService:
    """Сервис конвертации с предустановленными котировками и временным кэшем."""
    cache_mgr = RateCacheManager(cache_file=tmp_cache_path)
    service = CurrencyConverterService(cache_manager=cache_mgr)
    service._rates = dict(mock_rates)
    service._rates_date = "07.11.2026"
    service._source_name = "Тестовые котировки"
    service._is_offline = False
    return service
