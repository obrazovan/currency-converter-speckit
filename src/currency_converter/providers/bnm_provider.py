"""
Провайдер официальных курсов валют Национального банка Молдовы (НБМ / BNM).
"""

from __future__ import annotations
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Dict, Optional
import requests

from ..models import ExchangeRate, CurrencyType
from ..exceptions import RateFetchError

logger = logging.getLogger(__name__)

BNM_URL = "https://www.bnm.md/en/official_exchange_rates"


class BnmRateProvider:
    """
    Парсер официального XML-шлюза Национального банка Молдовы.

    Реализует требования:
    - Парсинг XML с получением курсов к MDL.
    - Добавление базовой валюты MDL с курсом 1.0.
    - Автоматический откат на предыдущие рабочие дни в случае выходных или праздников.
    """

    def __init__(self, timeout: int = 10) -> None:
        self.timeout = timeout

    def fetch_rates(self, target_date: str | None = None) -> tuple[dict[str, ExchangeRate], str]:
        """
        Получает курсы валют на указанную дату (или на сегодня).
        При отсутствии курсов на выходные/праздники автоматически находит
        последний доступный рабочий курс.

        Returns:
            Кортеж ({код_валюты: ExchangeRate}, фактическая_дата).
        """
        current_dt = (
            datetime.strptime(target_date, "%d.%m.%Y")
            if target_date
            else datetime.now()
        )

        # Пытаемся получить курс, откатываясь назад до 7 дней (выходные/праздники)
        for attempt in range(7):
            date_str = current_dt.strftime("%d.%m.%Y")
            try:
                rates = self._fetch_single_day(date_str)
                if rates:
                    if attempt > 0:
                        logger.info(
                            "На дату %s курсы отсутствовали (выходной/праздник). Загружен курс за %s",
                            target_date,
                            date_str,
                        )
                    return rates, date_str
            except RateFetchError:
                if attempt == 6:
                    raise
            current_dt -= timedelta(days=1)

        raise RateFetchError("Не удалось получить курсы НБМ ни за один из последних 7 дней.")

    def _fetch_single_day(self, date_str: str) -> dict[str, ExchangeRate]:
        """Запрашивает и парсит XML НБМ за конкретную дату."""
        params = {"get_xml": "1", "date": date_str}
        try:
            response = requests.get(BNM_URL, params=params, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as e:
            raise RateFetchError(f"Сетевая ошибка при запросе к НБМ ({BNM_URL}): {e}") from e

        try:
            root = ET.fromstring(response.content)
        except ET.ParseError as e:
            raise RateFetchError(f"Ошибка парсинга XML ответа от НБМ: {e}") from e

        valutes = root.findall("Valute")
        if not valutes:
            # На эту дату курсы не публиковались (выходной или нерабочий день)
            return {}

        rates: dict[str, ExchangeRate] = {}

        # Добавляем базовую валюту Молдовы
        rates["MDL"] = ExchangeRate(
            code="MDL",
            nominal=1,
            rate_to_base=1.0,
            date=date_str,
            source="НБМ",
            currency_type=CurrencyType.FIAT,
        )

        for v in valutes:
            char_code_elem = v.find("CharCode")
            nominal_elem = v.find("Nominal")
            value_elem = v.find("Value")

            if char_code_elem is None or nominal_elem is None or value_elem is None:
                continue

            char_code = (char_code_elem.text or "").strip().upper()
            try:
                nominal = int(nominal_elem.text or "1")
                # В XML НБМ разделителем может быть точка или запятая
                val_str = (value_elem.text or "0").replace(",", ".").strip()
                rate_value = float(val_str)
            except (ValueError, TypeError):
                continue

            if char_code and rate_value > 0 and nominal > 0:
                rates[char_code] = ExchangeRate(
                    code=char_code,
                    nominal=nominal,
                    rate_to_base=rate_value,
                    date=date_str,
                    source="НБМ",
                    currency_type=CurrencyType.FIAT,
                )

        return rates
