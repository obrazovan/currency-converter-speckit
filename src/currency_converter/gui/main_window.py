"""
Главное окно графического интерфейса конвертера валют и криптовалют.
"""

from __future__ import annotations
import logging
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Optional

from ..models import Currency, CurrencyType, ConversionResult
from ..exceptions import ValidationError, OfflineCacheError
from ..service import CurrencyConverterService

logger = logging.getLogger(__name__)


class MainWindow(tk.Tk):
    """
    Графический интерфейс конвертера валют.

    Реализует все требования ТЗ:
    - Поле ввода суммы с валидацией.
    - Выбор исходной и целевой валюты.
    - Кнопка конвертации (неактивна при невалидном вводе).
    - Кнопка Swap (⇄) для быстрой смены направления.
    - Отображение результата, даты котировки и источника.
    - Индикация оффлайн-режима при отсутствии сети.
    - Переключение фильтра валют: Все / Фиатные (НБМ) / Криптовалюты.
    """

    def __init__(self, service: CurrencyConverterService) -> None:
        super().__init__()
        self.service = service

        self.title("Конвертер валют и криптовалют — Лабораторная работа №3")
        self.geometry("620x560")
        self.minsize(560, 520)

        # Выбранный режим фильтрации (all, fiat, crypto)
        self.filter_var = tk.StringVar(value="all")

        self._setup_styles()
        self._build_ui()
        self._center_window()

        # Первичная загрузка курсов валют
        self._load_rates()

    def _setup_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground="#FFFFFF")
        style.configure("SubHeader.TLabel", font=("Segoe UI", 9), foreground="#E2E8F0")
        style.configure("FieldLabel.TLabel", font=("Segoe UI", 10, "bold"), foreground="#1E293B")
        style.configure("Accent.TButton", font=("Segoe UI", 11, "bold"), padding=8)
        style.configure("Swap.TButton", font=("Segoe UI", 12, "bold"), padding=4)
        style.configure("Preset.TButton", font=("Segoe UI", 9), padding=3)

    def _center_window(self) -> None:
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w = 620
        h = 560
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self) -> None:
        # Верхний баннер
        header_banner = tk.Frame(self, bg="#1E3A8A", height=75)
        header_banner.pack(fill=tk.X, side=tk.TOP)
        header_banner.pack_propagate(False)

        title_lbl = tk.Label(
            header_banner,
            text="💱 Конвертер валют и криптовалют",
            font=("Segoe UI", 16, "bold"),
            bg="#1E3A8A",
            fg="#FFFFFF",
        )
        title_lbl.pack(pady=(12, 2))

        subtitle_lbl = tk.Label(
            header_banner,
            text="Официальные курсы НБМ • Котировки криптовалют Binance",
            font=("Segoe UI", 9),
            bg="#1E3A8A",
            fg="#CBD5E1",
        )
        subtitle_lbl.pack()

        # Основной контейнер
        main_frame = ttk.Frame(self, padding="20 16 20 16")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. Переключатель категорий валют (Все / Фиат / Крипта)
        filter_frame = ttk.Frame(main_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 12))

        ttk.Label(filter_frame, text="Категории:").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Radiobutton(
            filter_frame, text="Все валюты", value="all", variable=self.filter_var, command=self._apply_currency_filter
        ).pack(side=tk.LEFT, padx=6)
        ttk.Radiobutton(
            filter_frame, text="Фиат (НБМ)", value="fiat", variable=self.filter_var, command=self._apply_currency_filter
        ).pack(side=tk.LEFT, padx=6)
        ttk.Radiobutton(
            filter_frame, text="Криптовалюты", value="crypto", variable=self.filter_var, command=self._apply_currency_filter
        ).pack(side=tk.LEFT, padx=6)

        # Кнопка обновления курсов справа
        self.refresh_btn = ttk.Button(
            filter_frame,
            text="🔄 Обновить",
            command=self._on_refresh_clicked,
        )
        self.refresh_btn.pack(side=tk.RIGHT)

        # 2. Карточка конвертации
        card = ttk.LabelFrame(main_frame, text="Параметры конвертации", padding="16 14")
        card.pack(fill=tk.X, pady=(0, 12))

        # Поле ввода суммы
        ttk.Label(card, text="Сумма для конвертации:", style="FieldLabel.TLabel").pack(anchor="w", pady=(0, 4))
        self.amount_var = tk.StringVar(value="100")
        self.amount_var.trace_add("write", self._on_amount_changed)

        entry_frame = ttk.Frame(card)
        entry_frame.pack(fill=tk.X, pady=(0, 6))

        self.amount_entry = ttk.Entry(
            entry_frame,
            textvariable=self.amount_var,
            font=("Segoe UI", 12),
        )
        self.amount_entry.pack(fill=tk.X, side=tk.LEFT, expand=True)

        # Быстрые пресеты сумм
        presets_frame = ttk.Frame(card)
        presets_frame.pack(fill=tk.X, pady=(0, 10))
        for p_val in [10, 100, 1000, 5000]:
            btn = ttk.Button(
                presets_frame,
                text=str(p_val),
                style="Preset.TButton",
                command=lambda v=p_val: self.amount_var.set(str(v)),
            )
            btn.pack(side=tk.LEFT, padx=(0, 4))

        # Сообщение об ошибке валидации суммы
        self.validation_err_lbl = ttk.Label(
            card,
            text="",
            font=("Segoe UI", 9),
            foreground="#DC2626",
        )
        self.validation_err_lbl.pack(anchor="w", pady=(0, 6))

        # Выбор валют (Из валюты <-> В валюту)
        selectors_frame = ttk.Frame(card)
        selectors_frame.pack(fill=tk.X, pady=(0, 8))

        # Колонка "Из валюты"
        from_col = ttk.Frame(selectors_frame)
        from_col.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(from_col, text="Из валюты:", style="FieldLabel.TLabel").pack(anchor="w", pady=(0, 3))
        self.from_combo = ttk.Combobox(from_col, state="readonly", font=("Segoe UI", 10))
        self.from_combo.pack(fill=tk.X)
        self.from_combo.bind("<<ComboboxSelected>>", lambda e: self._on_currency_selected())

        # Кнопка Swap (⇄)
        swap_col = ttk.Frame(selectors_frame, padding="8 18 8 0")
        swap_col.pack(side=tk.LEFT)
        self.swap_btn = ttk.Button(
            swap_col,
            text="⇄",
            style="Swap.TButton",
            width=3,
            command=self._on_swap_clicked,
        )
        self.swap_btn.pack()

        # Колонка "В валюту"
        to_col = ttk.Frame(selectors_frame)
        to_col.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(to_col, text="В валюту:", style="FieldLabel.TLabel").pack(anchor="w", pady=(0, 3))
        self.to_combo = ttk.Combobox(to_col, state="readonly", font=("Segoe UI", 10))
        self.to_combo.pack(fill=tk.X)
        self.to_combo.bind("<<ComboboxSelected>>", lambda e: self._on_currency_selected())

        # Кнопка Конвертировать
        self.convert_btn = ttk.Button(
            card,
            text="Конвертировать",
            style="Accent.TButton",
            command=self._on_convert_clicked,
        )
        self.convert_btn.pack(fill=tk.X, pady=(10, 2), ipady=2)

        # 3. Карточка отображения результата
        self.result_card = tk.Frame(main_frame, bg="#F8FAFC", bd=1, relief=tk.GROOVE, padx=16, pady=12)
        self.result_card.pack(fill=tk.X, pady=(0, 10))

        self.result_amount_lbl = tk.Label(
            self.result_card,
            text="—",
            font=("Segoe UI", 18, "bold"),
            bg="#F8FAFC",
            fg="#1E3A8A",
        )
        self.result_amount_lbl.pack(anchor="center")

        self.rate_info_lbl = tk.Label(
            self.result_card,
            text="Введите сумму и нажмите 'Конвертировать'",
            font=("Segoe UI", 9),
            bg="#F8FAFC",
            fg="#64748B",
        )
        self.rate_info_lbl.pack(anchor="center", pady=(4, 0))

        # 4. Подвал и строка состояния
        footer = ttk.Frame(main_frame)
        footer.pack(fill=tk.X, side=tk.BOTTOM, pady=(6, 0))

        self.status_icon_lbl = ttk.Label(footer, text="●", font=("Segoe UI", 12))
        self.status_icon_lbl.pack(side=tk.LEFT, padx=(0, 4))

        self.status_text_lbl = ttk.Label(footer, text="Инициализация...", font=("Segoe UI", 9))
        self.status_text_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _load_rates(self) -> None:
        """Загружает котировки валют (из сети или кэша)."""
        try:
            rates, rates_date, source_name, is_offline = self.service.update_rates(force_network=True)
            self._update_status_bar(is_offline, rates_date, source_name)
            self._populate_currency_combos()
            self._validate_and_update_button_state()
            # Автоматическая конвертация для начального значения 100
            self._do_conversion()
        except OfflineCacheError as e:
            self.status_icon_lbl.config(foreground="#DC2626")
            self.status_text_lbl.config(text="Ошибка: нет сети и отсутствует локальный кэш.")
            messagebox.showerror("Ошибка получения курсов", str(e), parent=self)
        except Exception as e:
            logger.exception("Непредвиденная ошибка при загрузке курсов: %s", e)
            self.status_icon_lbl.config(foreground="#DC2626")
            self.status_text_lbl.config(text=f"Ошибка: {e}")

    def _update_status_bar(self, is_offline: bool, rates_date: str, source: str) -> None:
        if is_offline:
            self.status_icon_lbl.config(foreground="#D97706")
            self.status_text_lbl.config(
                text=f"Оффлайн-режим: используются сохраненные курсы ({rates_date}) | {source}"
            )
        else:
            self.status_icon_lbl.config(foreground="#16A34A")
            self.status_text_lbl.config(
                text=f"Онлайн: курсы актуальны на {rates_date} | Источник: {source}"
            )

    def _populate_currency_combos(self) -> None:
        """Заполняет выпадающие списки валют с учетом фильтра."""
        currencies = self.service.get_available_currencies()
        mode = self.filter_var.get()

        filtered: list[Currency] = []
        for c in currencies:
            if mode == "fiat" and c.currency_type != CurrencyType.FIAT:
                continue
            if mode == "crypto" and c.currency_type != CurrencyType.CRYPTO:
                continue
            filtered.append(c)

        values = [c.display_name for c in filtered]
        self.from_combo["values"] = values
        self.to_combo["values"] = values

        # Выбор по умолчанию: USD -> MDL или первые два элемента
        codes = [c.code for c in filtered]
        if "USD" in codes and "MDL" in codes:
            idx_from = codes.index("USD")
            idx_to = codes.index("MDL")
        elif len(values) >= 2:
            idx_from = 0
            idx_to = 1
        else:
            idx_from = 0
            idx_to = 0

        if values:
            self.from_combo.current(idx_from)
            self.to_combo.current(idx_to)

    def _apply_currency_filter(self) -> None:
        """Обработка переключения фильтра (Все / Фиат / Крипта)."""
        self._populate_currency_combos()
        self._validate_and_update_button_state()
        self._do_conversion()

    def _get_selected_code(self, combo: ttk.Combobox) -> str:
        val = combo.get()
        if not val:
            return ""
        return val.split("—")[0].strip().upper()

    def _on_amount_changed(self, *args) -> None:
        self._validate_and_update_button_state()

    def _on_currency_selected(self) -> None:
        self._validate_and_update_button_state()
        self._do_conversion()

    def _validate_and_update_button_state(self) -> bool:
        raw_amount = self.amount_var.get().replace(",", ".").strip()

        if not raw_amount:
            self.validation_err_lbl.config(text="Поле суммы не может быть пустым.")
            self.convert_btn.config(state="disabled")
            return False

        try:
            val = float(raw_amount)
            if val <= 0:
                self.validation_err_lbl.config(text="Сумма должна быть строго больше нуля.")
                self.convert_btn.config(state="disabled")
                return False
        except ValueError:
            self.validation_err_lbl.config(text="Некорректное число: используйте цифры и точку/запятую.")
            self.convert_btn.config(state="disabled")
            return False

        from_code = self._get_selected_code(self.from_combo)
        to_code = self._get_selected_code(self.to_combo)

        if not from_code or not to_code:
            self.convert_btn.config(state="disabled")
            return False

        self.validation_err_lbl.config(text="")
        self.convert_btn.config(state="normal")
        return True

    def _on_swap_clicked(self) -> None:
        """Меняет местами исходную и целевую валюты."""
        from_idx = self.from_combo.current()
        to_idx = self.to_combo.current()

        if from_idx >= 0 and to_idx >= 0:
            self.from_combo.current(to_idx)
            self.to_combo.current(from_idx)
            self._do_conversion()

    def _on_convert_clicked(self) -> None:
        self._do_conversion()

    def _do_conversion(self) -> None:
        if not self._validate_and_update_button_state():
            return

        raw_amount = self.amount_var.get().replace(",", ".").strip()
        amount = float(raw_amount)
        from_code = self._get_selected_code(self.from_combo)
        to_code = self._get_selected_code(self.to_combo)

        try:
            res = self.service.convert(amount, from_code, to_code)
            self._display_result(res)
        except ValidationError as e:
            self.result_amount_lbl.config(text="Ошибка валидации")
            self.rate_info_lbl.config(text=str(e))
        except Exception as e:
            logger.exception("Ошибка при расчете: %s", e)
            self.result_amount_lbl.config(text="Ошибка расчета")
            self.rate_info_lbl.config(text=str(e))

    def _display_result(self, res: ConversionResult) -> None:
        # Форматирование итогового числа
        if res.to_code in ("BTC", "ETH", "SOL", "TON") or res.result_amount < 0.01:
            res_str = f"{res.result_amount:.6f}".rstrip("0").rstrip(".")
        elif res.result_amount > 1000:
            res_str = f"{res.result_amount:,.2f}".replace(",", " ")
        else:
            res_str = f"{res.result_amount:.4f}".rstrip("0").rstrip(".")

        # Отображение суммы
        self.result_amount_lbl.config(
            text=f"{res.amount:g} {res.from_code} = {res_str} {res.to_code}"
        )

        # Отображение кросс-курса
        if res.rate == 1.0:
            rate_text = "Конвертация валюты самой в себя (курс 1.0)"
        else:
            rate_text = (
                f"1 {res.from_code} = {res.rate:.6g} {res.to_code}   •   "
                f"1 {res.to_code} = {res.reverse_rate:.6g} {res.from_code}\n"
                f"Дата котировки: {res.rate_date} ({res.source})"
            )

        self.rate_info_lbl.config(text=rate_text)

    def _on_refresh_clicked(self) -> None:
        """Принудительное обновление курсов."""
        self._load_rates()
