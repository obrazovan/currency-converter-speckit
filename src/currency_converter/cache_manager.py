"""
Менеджер локального кэша курсов валют (Offline-first кэширование).
"""

from __future__ import annotations
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from .models import ExchangeRate, CurrencyType
from .exceptions import OfflineCacheError

logger = logging.getLogger(__name__)


class RateCacheManager:
    """
    Управляет локальным сохранением и чтением котировок в JSON-файле.
    Позволяет приложению переживать перезапуски и работать без подключения к сети.
    """

    def __init__(self, cache_file: str | Path = "cache/rates_cache.json") -> None:
        self.cache_file = Path(cache_file)

    def save_cache(
        self,
        rates: dict[str, ExchangeRate],
        rates_date: str,
        source: str,
    ) -> None:
        """Сохраняет актуальные курсы в локальный JSON-кэш."""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "cached_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "rates_date": rates_date,
                "source": source,
                "rates": {
                    code: {
                        "nominal": rate.nominal,
                        "rate_to_base": rate.rate_to_base,
                        "date": rate.date,
                        "source": rate.source,
                        "type": rate.currency_type.value,
                    }
                    for code, rate in rates.items()
                },
            }
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info("Кэш курсов успешно сохранен в %s", self.cache_file)
        except Exception as e:
            logger.error("Ошибка при сохранении кэша: %s", e)

    def load_cache(self) -> tuple[dict[str, ExchangeRate], str, str]:
        """
        Загружает кэшированные курсы валют.

        Returns:
            Кортеж (rates_dict, rates_date, source).
        Raises:
            OfflineCacheError: Если файл кэша отсутствует или поврежден.
        """
        if not self.cache_file.exists():
            raise OfflineCacheError(
                f"Локальный кэш отсутствует ({self.cache_file}). Требуется первичное подключение к сети."
            )

        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            rates_date = data.get("rates_date", "")
            cached_at = data.get("cached_at", "")
            source = f"{data.get('source', 'Кэш')} (оффлайн от {cached_at})"

            rates_raw = data.get("rates", {})
            if not rates_raw:
                raise OfflineCacheError("Файл кэша пуст.")

            rates: dict[str, ExchangeRate] = {}
            for code, item in rates_raw.items():
                curr_type = (
                    CurrencyType.CRYPTO
                    if item.get("type") == CurrencyType.CRYPTO.value
                    else CurrencyType.FIAT
                )
                rates[code] = ExchangeRate(
                    code=code,
                    nominal=int(item["nominal"]),
                    rate_to_base=float(item["rate_to_base"]),
                    date=item.get("date", rates_date),
                    source=source,
                    currency_type=curr_type,
                )

            logger.info("Успешно загружено %d курсов из оффлайн-кэша", len(rates))
            return rates, rates_date, source

        except Exception as e:
            if isinstance(e, OfflineCacheError):
                raise
            raise OfflineCacheError(f"Ошибка при чтении кэша: {e}") from e
