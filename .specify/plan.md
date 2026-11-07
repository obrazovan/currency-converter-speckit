# Технический план реализации (Technical Architecture Plan)

## 1. Компонентная структура приложения

```text
src/
└── currency_converter/
    ├── __init__.py                  # Экспорт публичных интерфейсов
    ├── models.py                    # Currency, Rate, ConversionResult
    ├── exceptions.py                # RateFetchError, ValidationError, OfflineError
    ├── cache_manager.py             # RateCacheManager (JSON оффлайн-кэш)
    ├── providers/
    │   ├── __init__.py
    │   ├── base.py                  # RateProvider (Protocol)
    │   ├── bnm_provider.py          # BnmRateProvider (XML парсинг + выходные)
    │   └── crypto_provider.py       # CryptoRateProvider (Binance Public API)
    ├── service.py                   # CurrencyConverterService (оркестрация и кросс-курсы)
    └── gui/
        ├── __init__.py
        ├── main_window.py           # Tkinter MainWindow
        └── styles.py                # Цветовая палитра, стили кнопок и шрифты
```

## 2. Математическая модель кросс-курсов
Все котировки приводятся к базовой фиатной валюте — Молдавскому лею (`MDL`):
1. **Фиатная валюта $F$**:
   $$\text{RateInMDL}(F) = \frac{\text{Value}_{\text{BNM}}}{\text{Nominal}_{\text{BNM}}}$$
   Для `MDL`: $\text{RateInMDL}(MDL) = 1.0$.
2. **Криптовалюта $C$**:
   $$\text{RateInMDL}(C) = \text{PriceInUSD}(C) \times \text{RateInMDL}(USD)$$
3. **Общая формула конвертации суммы $A$ из валюты $X$ в валюту $Y$**:
   $$\text{Result} = A \times \frac{\text{RateInMDL}(X)}{\text{RateInMDL}(Y)}$$

## 3. Механизм кэширования и работы в оффлайне
- Структура кэша в `cache/rates_cache.json`:
  ```json
  {
    "updated_at": "2026-11-07 15:30:00",
    "rates_date": "07.11.2026",
    "base_currency": "MDL",
    "rates": {
      "EUR": {"rate_to_base": 20.1089, "nominal": 1, "name": "Euro", "type": "fiat"},
      "USD": {"rate_to_base": 17.9200, "nominal": 1, "name": "US Dollar", "type": "fiat"},
      "BTC": {"rate_to_base": 1360757.17, "nominal": 1, "name": "Bitcoin", "type": "crypto"}
    }
  }
  ```
- При успешном сетевом запросе кэш обновляется автоматически.
- При ошибке сети данные загружаются из кэша с установкой флага `is_offline = True`.

## 4. Графический интерфейс
- На базе `tkinter` и `ttk` с темой `'clam'` и гармоничной палитрой (глубокий индиго, мягкий серый фон карточек).
- Отзывчивое поведение: кнопка блокируется при некорректном вводе в реальном времени (`<<KeyRelease>>` / валидация).
