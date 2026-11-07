"""
Сервисный слой бизнес-логики конвертера валют и криптовалют.
"""

from __future__ import annotations
import logging
from typing import Dict, List, Optional, Tuple

from .models import Currency, CurrencyType, ExchangeRate, ConversionResult
from .exceptions import ValidationError, RateFetchError, OfflineCacheError
from .cache_manager import RateCacheManager
from .providers.bnm_provider import BnmRateProvider
from .providers.crypto_provider import CryptoRateProvider

logger = logging.getLogger(__name__)

# Метаданные и описания валют для отображения в UI
CURRENCY_METADATA = {
    # Фиатные валюты (НБМ)
    "MDL": Currency("MDL", "Молдавский лей", CurrencyType.FIAT, "L"),
    "EUR": Currency("EUR", "Евро", CurrencyType.FIAT, "€"),
    "USD": Currency("USD", "Доллар США", CurrencyType.FIAT, "$"),
    "RON": Currency("RON", "Румынский лей", CurrencyType.FIAT, "L"),
    "RUB": Currency("RUB", "Российский рубль", CurrencyType.FIAT, "₽"),
    "UAH": Currency("UAH", "Украинская гривна", CurrencyType.FIAT, "₴"),
    "GBP": Currency("GBP", "Британский фунт", CurrencyType.FIAT, "£"),
    "CHF": Currency("CHF", "Швейцарский франк", CurrencyType.FIAT, "Fr"),
    "PLN": Currency("PLN", "Польский злотый", CurrencyType.FIAT, "zł"),
    "TRY": Currency("TRY", "Турецкая лира", CurrencyType.FIAT, "₺"),
    "CAD": Currency("CAD", "Канадский доллар", CurrencyType.FIAT, "$"),
    "JPY": Currency("JPY", "Японская иена", CurrencyType.FIAT, "¥"),
    # Криптовалюты (Binance / CoinGecko)
    "BTC": Currency("BTC", "Bitcoin", CurrencyType.CRYPTO, "₿"),
    "ETH": Currency("ETH", "Ethereum", CurrencyType.CRYPTO, "Ξ"),
    "SOL": Currency("SOL", "Solana", CurrencyType.CRYPTO, "◎"),
    "TON": Currency("TON", "Toncoin", CurrencyType.CRYPTO, "💎"),
    "USDT": Currency("USDT", "Tether (USD)", CurrencyType.CRYPTO, "$"),
    "BNB": Currency("BNB", "Binance Coin", CurrencyType.CRYPTO, "BNB"),
}


class CurrencyConverterService:
    """
    Координатор логики конвертации валют и криптовалют.

    Обеспечивает:
    - Интеграцию с официальным курсом НБМ и рыночным курсом криптовалют.
    - Математически точный расчет кросс-курсов между любыми парами (фиат <-> крипта).
    - Автоматический откат на оффлайн-кэш при сбоях сети (Offline-First).
    - Валидацию пользовательского ввода и обработку краевых случаев.
    """

    def __init__(
        self,
        bnm_provider: BnmRateProvider | None = None,
        crypto_provider: CryptoRateProvider | None = None,
        cache_manager: RateCacheManager | None = None,
    ) -> None:
        self.bnm_provider = bnm_provider or BnmRateProvider()
        self.crypto_provider = crypto_provider or CryptoRateProvider()
        self.cache_manager = cache_manager or RateCacheManager()

        self._rates: dict[str, ExchangeRate] = {}
        self._rates_date: str = ""
        self._source_name: str = ""
        self._is_offline: bool = False

    @property
    def rates(self) -> dict[str, ExchangeRate]:
        return self._rates

    @property
    def rates_date(self) -> str:
        return self._rates_date

    @property
    def source_name(self) -> str:
        return self._source_name

    @property
    def is_offline(self) -> bool:
        return self._is_offline

    def update_rates(self, force_network: bool = True) -> tuple[dict[str, ExchangeRate], str, str, bool]:
        """
        Запрашивает актуальные котировки из сети или загружает из оффлайн-кэша.

        Returns:
            Кортеж (rates_dict, rates_date, source_name, is_offline).
        """
        if force_network:
            try:
                # 1. Получаем фиатные курсы НБМ
                bnm_rates, bnm_date = self.bnm_provider.fetch_rates()
                self._rates = dict(bnm_rates)
                self._rates_date = bnm_date
                self._source_name = f"Официальный курс НБМ ({bnm_date})"
                self._is_offline = False

                # 2. Получаем криптовалюты на основе USD/MDL
                usd_rate = bnm_rates.get("USD")
                if usd_rate and usd_rate.rate_to_base > 0:
                    try:
                        crypto_rates = self.crypto_provider.fetch_crypto_rates(usd_rate.rate_to_base)
                        self._rates.update(crypto_rates)
                        self._source_name += " + Binance Crypto"
                    except Exception as e:
                        logger.warning("Не удалось обновить криптовалюты: %s", e)

                # 3. Сохраняем успешный снимок в локальный кэш
                self.cache_manager.save_cache(self._rates, self._rates_date, self._source_name)
                return self._rates, self._rates_date, self._source_name, self._is_offline

            except RateFetchError as e:
                logger.warning("Сбой сети при запросе курсов (%s). Переход в режим оффлайн-кэша...", e)

        # 4. Если сеть недоступна — загружаем оффлайн-кэш
        try:
            cached_rates, cached_date, cached_source = self.cache_manager.load_cache()
            self._rates = cached_rates
            self._rates_date = cached_date
            self._source_name = cached_source
            self._is_offline = True
            return self._rates, self._rates_date, self._source_name, self._is_offline
        except OfflineCacheError as e:
            raise OfflineCacheError(
                "Не удалось загрузить курсы валют из сети, и локальный кэш отсутствует.\n"
                "Пожалуйста, подключитесь к интернету для первичной загрузки курсов."
            ) from e

    def get_available_currencies(self) -> list[Currency]:
        """Возвращает упорядоченный список доступных для конвертации валют."""
        available: list[Currency] = []

        # Сначала основные фиатные
        priority_fiats = ["MDL", "EUR", "USD", "RON", "RUB", "UAH", "GBP", "CHF", "PLN", "TRY"]
        for code in priority_fiats:
            if code in self._rates:
                meta = CURRENCY_METADATA.get(code, Currency(code, code, CurrencyType.FIAT))
                available.append(meta)

        # Затем остальные фиатные
        for code, rate in self._rates.items():
            if rate.currency_type == CurrencyType.FIAT and code not in priority_fiats:
                meta = CURRENCY_METADATA.get(code, Currency(code, code, CurrencyType.FIAT))
                available.append(meta)

        # Затем криптовалюты
        for code, rate in self._rates.items():
            if rate.currency_type == CurrencyType.CRYPTO:
                meta = CURRENCY_METADATA.get(code, Currency(code, code, CurrencyType.CRYPTO))
                available.append(meta)

        return available

    def convert(self, amount: float, from_code: str, to_code: str) -> ConversionResult:
        """
        Выполняет конвертацию суммы из from_code в to_code.

        Raises:
            ValidationError: При некорректной сумме или валюте.
        """
        if amount <= 0:
            raise ValidationError("Сумма для конвертации должна быть строго больше нуля.")

        from_code = from_code.strip().upper()
        to_code = to_code.strip().upper()

        if from_code not in self._rates:
            raise ValidationError(f"Исходная валюта '{from_code}' не найдена в таблице курсов.")
        if to_code not in self._rates:
            raise ValidationError(f"Целевая валюта '{to_code}' не найдена в таблице курсов.")

        # Одинаковые валюты -> курс 1.0 без погрешностей
        if from_code == to_code:
            return ConversionResult(
                amount=amount,
                from_code=from_code,
                to_code=to_code,
                result_amount=amount,
                rate=1.0,
                reverse_rate=1.0,
                rate_date=self._rates_date,
                source=self._source_name,
                is_offline=self._is_offline,
            )

        from_rate = self._rates[from_code]
        to_rate = self._rates[to_code]

        # Стоимость 1 единицы каждой валюты в MDL
        unit_val_from = from_rate.rate_to_base / from_rate.nominal
        unit_val_to = to_rate.rate_to_base / to_rate.nominal

        # Кросс-курс: 1 from_code = rate * to_code
        rate = unit_val_from / unit_val_to
        reverse_rate = 1.0 / rate if rate > 0 else 0.0

        result_amount = amount * rate

        return ConversionResult(
            amount=amount,
            from_code=from_code,
            to_code=to_code,
            result_amount=result_amount,
            rate=rate,
            reverse_rate=reverse_rate,
            rate_date=self._rates_date,
            source=self._source_name,
            is_offline=self._is_offline,
        )
