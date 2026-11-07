"""
Unit-тесты для менеджера кэша RateCacheManager (оффлайн-режим).
"""

from pathlib import Path
import pytest

from currency_converter.cache_manager import RateCacheManager
from currency_converter.exceptions import OfflineCacheError
from currency_converter.models import ExchangeRate, CurrencyType


class TestRateCacheManager:
    def test_save_and_load_cache_survives_restart(self, tmp_cache_path: Path):
        """
        Проверка требования ТЗ:
        Последний успешный ответ источника сохраняется локально
        и переживает перезапуск приложения.
        """
        manager1 = RateCacheManager(tmp_cache_path)
        rates_to_save = {
            "MDL": ExchangeRate("MDL", 1, 1.0, "07.11.2026", "НБМ", CurrencyType.FIAT),
            "EUR": ExchangeRate("EUR", 1, 20.1089, "07.11.2026", "НБМ", CurrencyType.FIAT),
            "BTC": ExchangeRate("BTC", 1, 1360000.0, "07.11.2026", "Binance", CurrencyType.CRYPTO),
        }

        manager1.save_cache(rates_to_save, rates_date="07.11.2026", source="НБМ + Binance")
        assert tmp_cache_path.exists()

        # Имитируем перезапуск приложения: создаем новый менеджер с тем же путем
        manager2 = RateCacheManager(tmp_cache_path)
        loaded_rates, loaded_date, loaded_source = manager2.load_cache()

        assert loaded_date == "07.11.2026"
        assert "НБМ + Binance" in loaded_source
        assert "EUR" in loaded_rates
        assert loaded_rates["EUR"].rate_to_base == 20.1089
        assert loaded_rates["EUR"].currency_type == CurrencyType.FIAT

        assert "BTC" in loaded_rates
        assert loaded_rates["BTC"].rate_to_base == 1360000.0
        assert loaded_rates["BTC"].currency_type == CurrencyType.CRYPTO

    def test_missing_cache_raises_offline_cache_error(self, tmp_cache_path: Path):
        manager = RateCacheManager(tmp_cache_path)
        assert not tmp_cache_path.exists()

        with pytest.raises(OfflineCacheError, match="кэш отсутствует"):
            manager.load_cache()

    def test_corrupted_json_raises_offline_cache_error(self, tmp_cache_path: Path):
        tmp_cache_path.write_text("{ corrupt json ...", encoding="utf-8")
        manager = RateCacheManager(tmp_cache_path)

        with pytest.raises(OfflineCacheError, match="Ошибка при чтении кэша"):
            manager.load_cache()
