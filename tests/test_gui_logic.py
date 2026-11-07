"""
Тесты логики графического интерфейса пользователя (MainWindow).
"""

import tkinter as tk
import pytest

from currency_converter.gui.main_window import MainWindow
from currency_converter.service import CurrencyConverterService
from currency_converter.cache_manager import RateCacheManager


@pytest.fixture(scope="module")
def shared_tk_window(mock_rates, tmp_path_factory):
    """Модульная фикстура для единого экземпляра Tkinter в тестах."""
    cache_file = tmp_path_factory.mktemp("cache") / "rates_cache.json"
    cache_mgr = RateCacheManager(cache_file=cache_file)
    service = CurrencyConverterService(cache_manager=cache_mgr)
    service._rates = dict(mock_rates)
    service._rates_date = "07.11.2026"
    service._source_name = "Тестовые котировки"
    service._is_offline = False

    win = MainWindow(service=service)
    win.withdraw()
    yield win
    try:
        win.destroy()
    except Exception:
        pass


class TestUILogic:
    def test_amount_validation_controls_button_state(self, shared_tk_window: MainWindow):
        """
        Проверка требования ТЗ:
        Кнопка конвертации неактивна до заполнения обязательных полей.
        При некорректном вводе (ноль, минус, буквы) кнопка неактивна.
        """
        win = shared_tk_window

        # 1. Корректное положительное число -> кнопка активна
        win.amount_var.set("150.50")
        assert win._validate_and_update_button_state() is True
        assert str(win.convert_btn["state"]) == "normal"
        assert win.validation_err_lbl.cget("text") == ""

        # 2. Пустое поле -> кнопка неактивна
        win.amount_var.set("")
        assert win._validate_and_update_button_state() is False
        assert str(win.convert_btn["state"]) == "disabled"
        assert "не может быть пустым" in win.validation_err_lbl.cget("text")

        # 3. Ноль -> кнопка неактивна
        win.amount_var.set("0")
        assert win._validate_and_update_button_state() is False
        assert str(win.convert_btn["state"]) == "disabled"
        assert "больше нуля" in win.validation_err_lbl.cget("text")

        # 4. Отрицательное число -> кнопка неактивна
        win.amount_var.set("-100")
        assert win._validate_and_update_button_state() is False
        assert str(win.convert_btn["state"]) == "disabled"
        assert "больше нуля" in win.validation_err_lbl.cget("text")

        # 5. Буквенный ввод -> кнопка неактивна
        win.amount_var.set("abc")
        assert win._validate_and_update_button_state() is False
        assert str(win.convert_btn["state"]) == "disabled"
        assert "Некорректное число" in win.validation_err_lbl.cget("text")

    def test_swap_button_swaps_currencies(self, shared_tk_window: MainWindow):
        """Кнопка Swap (⇄) меняет местами исходную и целевую валюты."""
        win = shared_tk_window
        win.amount_var.set("100")

        # Находим индексы USD и EUR
        values = list(win.from_combo["values"])
        usd_idx = next(i for i, v in enumerate(values) if v.startswith("USD"))
        eur_idx = next(i for i, v in enumerate(values) if v.startswith("EUR"))

        win.from_combo.current(usd_idx)
        win.to_combo.current(eur_idx)

        assert win._get_selected_code(win.from_combo) == "USD"
        assert win._get_selected_code(win.to_combo) == "EUR"

        # Нажимаем кнопку Swap
        win._on_swap_clicked()

        assert win._get_selected_code(win.from_combo) == "EUR"
        assert win._get_selected_code(win.to_combo) == "USD"

    def test_currency_filter_switching(self, shared_tk_window: MainWindow):
        """Переключение фильтров 'Все', 'Фиат', 'Крипта' обновляет списки."""
        win = shared_tk_window

        # 1. Фиатный фильтр
        win.filter_var.set("fiat")
        win._apply_currency_filter()
        fiat_values = list(win.from_combo["values"])
        assert any(v.startswith("USD") for v in fiat_values)
        assert any(v.startswith("EUR") for v in fiat_values)
        assert not any(v.startswith("BTC") for v in fiat_values)

        # 2. Крипто-фильтр
        win.filter_var.set("crypto")
        win._apply_currency_filter()
        crypto_values = list(win.from_combo["values"])
        assert any(v.startswith("BTC") for v in crypto_values)
        assert any(v.startswith("ETH") for v in crypto_values)
        assert not any(v.startswith("EUR") for v in crypto_values)

        # 3. Все валюты
        win.filter_var.set("all")
        win._apply_currency_filter()
        all_values = list(win.from_combo["values"])
        assert any(v.startswith("USD") for v in all_values)
        assert any(v.startswith("BTC") for v in all_values)
