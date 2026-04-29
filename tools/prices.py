"""
Единая точка загрузки ценовых данных для всех модулей калькулятора.

Два источника данных:
- MyPrices.json       — тарифы на печать, сборку, расходники
- paperDigiPrice.json — цены на бумагу для цифровой печати по типу и граммажу

Оба файла загружаются один раз и кэшируются на весь срок работы приложения.
Все модули в tools/ импортируют отсюда — не открывают файлы самостоятельно.
"""

import json
import os
from pathlib import Path

# Корень пакета tools/ — папка, где лежит этот файл
_TOOLS_DIR = Path(__file__).parent

# data/ лежит рядом с tools/ на одном уровне
_DATA_DIR = _TOOLS_DIR.parent / "data"

_PRICES_PATH      = _DATA_DIR / "MyPrices.json"
_DIGI_PAPER_PATH  = _DATA_DIR / "paperDigiPrice.json"

# ── Кэш ──────────────────────────────────────────────────────
_prices_cache: dict | None = None
_digi_paper_cache: dict | None = None


def load_prices() -> dict:
    """
    Возвращает содержимое MyPrices.json.
    Файл читается один раз; повторные вызовы возвращают кэш.
    """
    global _prices_cache
    if _prices_cache is None:
        if not _PRICES_PATH.exists():
            raise FileNotFoundError(
                f"Файл цен не найден: {_PRICES_PATH}\n"
                f"Убедитесь что data/MyPrices.json существует в корне проекта."
            )
        with open(_PRICES_PATH, encoding="utf-8") as f:
            _prices_cache = json.load(f)
    return _prices_cache


def load_digi_paper_prices() -> dict:
    """
    Возвращает содержимое paperDigiPrice.json.
    Файл читается один раз; повторные вызовы возвращают кэш.
    """
    global _digi_paper_cache
    if _digi_paper_cache is None:
        if not _DIGI_PAPER_PATH.exists():
            raise FileNotFoundError(
                f"Файл цен на бумагу не найден: {_DIGI_PAPER_PATH}\n"
                f"Убедитесь что data/paperDigiPrice.json существует в корне проекта."
            )
        with open(_DIGI_PAPER_PATH, encoding="utf-8") as f:
            _digi_paper_cache = json.load(f)
    return _digi_paper_cache


# ── Справочник: material_name + grammage → ключ в paperDigiPrice.json ────────

# Нормализованные алиасы для типов бумаги
_MATERIAL_ALIASES: dict[str, str] = {
    # мелованная
    "мелованная": "melovannaya",
    "мелов":      "melovannaya",
    "coated":     "melovannaya",
    "мел":        "melovannaya",
    # офсетная (бумага, не печать!)
    "офсетная":   "ofsetnaya",
    "офсет":      "ofsetnaya",
    "offset":     "ofsetnaya",
    # картон
    "картон":     "karton",
    "karton":     "karton",
    "cardboard":  "karton",
}

# Доступные граммажи для каждого типа (из paperDigiPrice.json)
_AVAILABLE_GRAMMAGES: dict[str, list[int]] = {
    "melovannaya": [90, 105, 115, 130, 150, 170, 200, 230, 250, 270, 300],
    "ofsetnaya":   [80, 100, 120, 160],
    "karton":      [250, 300],
}


def _normalize_material(material_name: str) -> str | None:
    """Нормализует название материала к внутреннему ключу."""
    key = material_name.strip().lower()
    return _MATERIAL_ALIASES.get(key)


def _nearest_grammage(material_key: str, grammage: int) -> int:
    """
    Возвращает ближайший доступный граммаж для данного типа материала.
    Например: melovannaya + 110 г/м² → 105 г/м²  (ближайший снизу)
    """
    available = _AVAILABLE_GRAMMAGES[material_key]
    # ближайший снизу или равный
    below = [g for g in available if g <= grammage]
    if below:
        return max(below)
    # если граммаж меньше минимального — берём минимальный
    return min(available)


def resolve_paper_price(
    material_name: str,
    grammage: int,
) -> tuple[float, int, str]:
    """
    Определяет цену листа А3 для цифровой печати по типу и граммажу бумаги.

    Используется в calculate_digital_printing когда пользователь указывает
    тип бумаги словом ("мелованная", "офсетная", "картон") вместо цены.

    Параметры:
        material_name: Название типа бумаги (регистр не важен)
        grammage: Желаемый граммаж г/м²

    Возвращает:
        (price, actual_grammage, note)
        price          — цена листа А3 в рублях
        actual_grammage — реальный граммаж из прайса (может отличаться от запрошенного)
        note           — примечание если граммаж был скорректирован

    Исключения:
        ValueError если тип материала не распознан
    """
    material_key = _normalize_material(material_name)
    if material_key is None:
        available = sorted(set(_MATERIAL_ALIASES.keys()))
        raise ValueError(
            f"Неизвестный тип материала: '{material_name}'.\n"
            f"Доступные варианты: {available}"
        )

    actual_grammage = _nearest_grammage(material_key, grammage)
    json_key = f"price_{material_key}_{actual_grammage}"

    digi_prices = load_digi_paper_prices()
    if json_key not in digi_prices:
        raise KeyError(
            f"Ключ '{json_key}' не найден в paperDigiPrice.json. "
            f"Проверьте файл цен."
        )

    price = digi_prices[json_key]["value"]

    note = ""
    if actual_grammage != grammage:
        note = (
            f"Граммаж {grammage} г/м² не найден в прайсе — "
            f"использован ближайший {actual_grammage} г/м²."
        )

    return price, actual_grammage, note


def invalidate_cache() -> None:
    """
    Сбрасывает кэш обоих файлов.
    Вызывать если файлы цен были изменены в процессе работы приложения.
    """
    global _prices_cache, _digi_paper_cache
    _prices_cache = None
    _digi_paper_cache = None
