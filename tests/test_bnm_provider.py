"""
Unit-тесты для парсера курсов валют НБМ (BnmRateProvider).
"""

from unittest.mock import patch, MagicMock
import pytest
import requests

from currency_converter.providers.bnm_provider import BnmRateProvider
from currency_converter.exceptions import RateFetchError
from conftest import SAMPLE_BNM_XML, EMPTY_BNM_XML


class TestBnmRateProvider:
    def test_parse_valid_bnm_xml(self):
        provider = BnmRateProvider()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = SAMPLE_BNM_XML.encode("utf-8")

        with patch("requests.get", return_value=mock_resp):
            rates = provider._fetch_single_day("07.11.2026")

        # Проверяем наличие базовой валюты MDL
        assert "MDL" in rates
        assert rates["MDL"].rate_to_base == 1.0
        assert rates["MDL"].nominal == 1

        # Проверяем EUR и USD
        assert "EUR" in rates
        assert rates["EUR"].rate_to_base == 20.1089
        assert rates["EUR"].nominal == 1

        assert "USD" in rates
        assert rates["USD"].rate_to_base == 17.9200
        assert rates["USD"].nominal == 1

        # Проверяем валюту с номиналом (RUB номинал 100)
        assert "RUB" in rates
        assert rates["RUB"].nominal == 100
        assert rates["RUB"].rate_to_base == 21.9700

    def test_weekend_holiday_fallback_to_previous_day(self):
        """
        Проверка требования ТЗ:
        Если источник не публикует курс в выбранную дату (выходной/праздник),
        приложение корректно обрабатывает пустой ответ и берет последний доступный курс.
        """
        provider = BnmRateProvider()

        # Первый вызов (сегодня) возвращает пустой XML (выходной)
        # Второй вызов (вчера) возвращает валидный XML
        resp_empty = MagicMock(status_code=200, content=EMPTY_BNM_XML.encode("utf-8"))
        resp_valid = MagicMock(status_code=200, content=SAMPLE_BNM_XML.encode("utf-8"))

        with patch("requests.get", side_effect=[resp_empty, resp_valid]):
            rates, actual_date = provider.fetch_rates("08.11.2026")

        # Курсы успешно получены за предыдущий день
        assert len(rates) > 0
        assert actual_date == "07.11.2026"
        assert "EUR" in rates

    def test_network_connection_error_raises_rate_fetch_error(self):
        provider = BnmRateProvider()

        with patch("requests.get", side_effect=requests.ConnectionError("Network down")):
            with pytest.raises(RateFetchError, match="Сетевая ошибка"):
                provider._fetch_single_day("07.11.2026")

    def test_corrupted_xml_raises_rate_fetch_error(self):
        provider = BnmRateProvider()
        mock_resp = MagicMock(status_code=200, content=b"<broken xml")

        with patch("requests.get", return_value=mock_resp):
            with pytest.raises(RateFetchError, match="Ошибка парсинга XML"):
                provider._fetch_single_day("07.11.2026")
