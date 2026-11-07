#!/usr/bin/env python3
"""
Точка входа для запуска GUI приложения конвертера валют.

Использование:
    python run.py
"""

import sys
from pathlib import Path

# Обеспечиваем корректную кодировку консоли Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Добавляем каталог src в sys.path
base_dir = Path(__file__).resolve().parent
src_dir = base_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from currency_converter.service import CurrencyConverterService
from currency_converter.cache_manager import RateCacheManager
from currency_converter.providers.bnm_provider import BnmRateProvider
from currency_converter.providers.crypto_provider import CryptoRateProvider
from currency_converter.gui.main_window import MainWindow


def main() -> int:
    cache_path = base_dir / "cache" / "rates_cache.json"
    cache_mgr = RateCacheManager(cache_file=cache_path)
    bnm_prov = BnmRateProvider()
    crypto_prov = CryptoRateProvider()

    service = CurrencyConverterService(
        bnm_provider=bnm_prov,
        crypto_provider=crypto_prov,
        cache_manager=cache_mgr,
    )

    app = MainWindow(service=service)
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
