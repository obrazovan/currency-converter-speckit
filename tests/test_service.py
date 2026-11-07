"""
Unit-тесты для CurrencyConverterService (бизнес-логика, математика кросс-курсов, оффлайн).
"""

from unittest.mock import patch
import pytest

from currency_converter.service import CurrencyConverterService
from currency_converter.exceptions import ValidationError, RateFetchError, OfflineCacheError
from currency_converter.models import CurrencyType, ExchangeRate


class TestCurrencyConverterService:
    def test_fiat_to_fiat_conversion(self, sample_service: CurrencyConverterService):
        # 100 EUR (курс 20.0 MDL) -> MDL
        res = sample_service.convert(100.0, "EUR", "MDL")
        assert res.result_amount == 2000.0
        assert res.rate == 20.0
        assert pytest.approx(res.reverse_rate, rel=1e-5) == 0.05

        # 180 MDL -> USD (курс 18.0 MDL)
        res_usd = sample_service.convert(180.0, "MDL", "USD")
        assert res_usd.result_amount == 10.0
        assert pytest.approx(res_usd.rate, rel=1e-5) == 1.0 / 18.0

        # 100 EUR -> USD (100 * 20.0 / 18.0 = 111.1111)
        res_cross = sample_service.convert(100.0, "EUR", "USD")
        assert pytest.approx(res_cross.result_amount, rel=1e-5) == 100.0 * 20.0 / 18.0

    def test_nominal_currency_conversion(self, sample_service: CurrencyConverterService):
        # RUB: номинал 100, стоимость 20.0 MDL (1 RUB = 0.2 MDL)
        # 500 RUB -> 100 MDL
        res = sample_service.convert(500.0, "RUB", "MDL")
        assert pytest.approx(res.result_amount, rel=1e-5) == 100.0

        # 100 MDL -> 500 RUB
        res_rev = sample_service.convert(100.0, "MDL", "RUB")
        assert pytest.approx(res_rev.result_amount, rel=1e-5) == 500.0

    def test_crypto_to_fiat_and_fiat_to_crypto(self, sample_service: CurrencyConverterService):
        # BTC (900,000 MDL) -> MDL
        res_btc = sample_service.convert(1.5, "BTC", "MDL")
        assert res_btc.result_amount == 1.5 * 900000.0

        # BTC -> USD (1 BTC = 900,000 MDL / 18 MDL = 50,000 USD)
        res_btc_usd = sample_service.convert(2.0, "BTC", "USD")
        assert pytest.approx(res_btc_usd.result_amount, rel=1e-5) == 100000.0

        # USD -> BTC (50,000 USD = 1.0 BTC)
        res_usd_btc = sample_service.convert(50000.0, "USD", "BTC")
        assert pytest.approx(res_usd_btc.result_amount, rel=1e-5) == 1.0

        # MDL -> BTC (900,000 MDL = 1.0 BTC)
        res_mdl_btc = sample_service.convert(900000.0, "MDL", "BTC")
        assert pytest.approx(res_mdl_btc.result_amount, rel=1e-5) == 1.0

    def test_crypto_to_crypto_conversion(self, sample_service: CurrencyConverterService):
        # BTC (900,000 MDL) -> ETH (36,000 MDL): 1 BTC = 25 ETH
        res = sample_service.convert(1.0, "BTC", "ETH")
        assert pytest.approx(res.result_amount, rel=1e-5) == 25.0
        assert pytest.approx(res.rate, rel=1e-5) == 25.0
        assert pytest.approx(res.reverse_rate, rel=1e-5) == 0.04

    def test_same_currency_conversion_rate_is_one(self, sample_service: CurrencyConverterService):
        """
        Проверка требования ТЗ:
        Одинаковые валюты. Выбор одной и той же валюты в обоих списках
        обрабатывается без ошибки (курс 1.0).
        """
        res_fiat = sample_service.convert(250.0, "USD", "USD")
        assert res_fiat.result_amount == 250.0
        assert res_fiat.rate == 1.0
        assert res_fiat.reverse_rate == 1.0

        res_crypto = sample_service.convert(3.14, "BTC", "BTC")
        assert res_crypto.result_amount == 3.14
        assert res_crypto.rate == 1.0

    def test_invalid_input_validation(self, sample_service: CurrencyConverterService):
        """
        Проверка требования ТЗ:
        Некорректный ввод. Отрицательная сумма, ноль, пустое поле —
        приложение сообщает об ошибке и не выполняет конвертацию.
        """
        with pytest.raises(ValidationError, match="больше нуля"):
            sample_service.convert(0.0, "EUR", "MDL")

        with pytest.raises(ValidationError, match="больше нуля"):
            sample_service.convert(-50.0, "EUR", "MDL")

        with pytest.raises(ValidationError, match="не найдена"):
            sample_service.convert(100.0, "UNKNOWN", "MDL")

        with pytest.raises(ValidationError, match="не найдена"):
            sample_service.convert(100.0, "USD", "UNKNOWN")

    def test_offline_fallback_on_network_failure(self, tmp_cache_path):
        """
        Проверка требования ТЗ:
        Нет сети. Приложение не падает, при наличии сохраненных данных
        предлагает работать с последним успешно полученным курсом.
        """
        from currency_converter.cache_manager import RateCacheManager
        cache_mgr = RateCacheManager(tmp_cache_path)

        cached_rates = {
            "MDL": ExchangeRate("MDL", 1, 1.0, "06.11.2026", "Кэш", CurrencyType.FIAT),
            "EUR": ExchangeRate("EUR", 1, 19.5, "06.11.2026", "Кэш", CurrencyType.FIAT),
        }
        cache_mgr.save_cache(cached_rates, "06.11.2026", "Сохраненный НБМ")

        service = CurrencyConverterService(cache_manager=cache_mgr)

        # Имитируем сбой сети при запросе к НБМ
        with patch.object(service.bnm_provider, "fetch_rates", side_effect=RateFetchError("No internet")):
            rates, date_str, source, is_offline = service.update_rates(force_network=True)

        assert is_offline is True
        assert date_str == "06.11.2026"
        assert "EUR" in rates
        assert rates["EUR"].rate_to_base == 19.5

        # Конвертация в оффлайн-режиме проходит успешно
        res = service.convert(100.0, "EUR", "MDL")
        assert res.result_amount == 1950.0
        assert res.is_offline is True
