"""
Базовый интерфейс поставщика курсов валют (LSP / ISP).
"""

from __future__ import annotations
from typing import Dict, Protocol
from ..models import ExchangeRate


class RateProvider(Protocol):
    """Интерфейс провайдера котировок валют."""

    def fetch_rates(self, date: str | None = None) -> dict[str, ExchangeRate]:
        """
        Получает словарь котировок {код_валюты: ExchangeRate}.

        Args:
            date: Дата в формате DD.MM.YYYY (опционально).
        """
        ...
