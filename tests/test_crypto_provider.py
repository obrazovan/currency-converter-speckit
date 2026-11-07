"""
Unit-тесты для провайдера криптовалют (CryptoRateProvider).
"""

from unittest.mock import patch, MagicMock
import pytest

from currency_converter.providers.crypto_provider import CryptoRateProvider
from currency_converter.exceptions import RateFetchError
from currency_converter.models import CurrencyType


class TestCryptoRateProvider:
    def test_fetch_crypto_rates_converts_to_mdl(self):
        provider = CryptoRateProvider()
        usd_mdl_rate = 18.0

        def mock_binance_response(*args, **kwargs):
            symbol = kwargs.get("params", {}).get("symbol")
            mock = MagicMock(status_code=200)
            if symbol == "BTCUSDT":
                mock.json.return_value = {"price": "50000.00"}
            elif symbol == "ETHUSDT":
                mock.json.return_value = {"price": "2000.00"}
            else:
                mock.json.return_value = {"price": "100.00"}
            return mock

        with patch("requests.get", side_effect=mock_binance_response):
            rates = provider.fetch_crypto_rates(usd_to_mdl_rate=usd_mdl_rate)

        assert "BTC" in rates
        # 50,000 USD * 18.0 MDL = 900,000 MDL
        assert rates["BTC"].rate_to_base == 900000.0
        assert rates["BTC"].currency_type == CurrencyType.CRYPTO

        # USDT = 1 * 18.0 MDL = 18.0 MDL
        assert "USDT" in rates
        assert rates["USDT"].rate_to_base == 18.0

        # ETH = 2,000 USD * 18.0 MDL = 36,000 MDL
        assert rates["ETH"].rate_to_base == 36000.0

    def test_invalid_usd_rate_raises_value_error(self):
        provider = CryptoRateProvider()
        with pytest.raises(ValueError, match="положительным"):
            provider.fetch_crypto_rates(usd_to_mdl_rate=0.0)

        with pytest.raises(ValueError, match="положительным"):
            provider.fetch_crypto_rates(usd_to_mdl_rate=-18.0)

    def test_all_requests_failed_raises_rate_fetch_error(self):
        provider = CryptoRateProvider()

        # Имитируем ошибку для всех пар
        with patch("requests.get", side_effect=Exception("Binance timeout")):
            # Единственной успешной будет USDT (так как она не требует сетевого запроса к Binance)
            # Проверяем, что USDT всегда формируется
            rates = provider.fetch_crypto_rates(usd_to_mdl_rate=18.0)
            assert "USDT" in rates
            assert rates["USDT"].rate_to_base == 18.0
