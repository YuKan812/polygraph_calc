"""
Расчёт стоимости ламинации.
Цены загружаются через tools.prices — единственный источник данных.
"""
from ..prices import load_prices

# Единственное место определения маппинга качества ламинации.
# Импортируется в blocknote.py и других модулях — не дублировать.
LAM_QUALITY_MAP: dict[str, str] = {
    "1": None,        # нет ламинации
    "2": "standard",    # глянцевая или матовая (одинаковая цена)
    "3": "softtouch",   # софттач
    "4": "75",        # плёнка 75 мкм
    "5": "125",       # плёнка 125 мкм
}


def calculate_lamination_price(
    lamination_type: str,
    sides: str,
    sheets_quantity: int,
) -> dict:
    """
    Рассчитывает стоимость ламинации тиражных листов А3+.

    Параметры:
    - lamination_type: "standard", "softtouch", "75", "125"
    - sides: "1+0" или "1+1"
    - sheets_quantity: количество тиражных листов А3+ (из результата печати)

    Оба стандартных формата SRA3 и А3+ попадают в тарифную зону "small",
    поэтому проверка размера не требуется.

    Возвращает:
    dict: unit_price, sides_multiplier, sheets_quantity,
          raw_cost, min_price, total_cost
    """
    prices = load_prices()
    lam = prices["lamination"][lamination_type]

    if lamination_type in ("75", "125"):
        # Плёночная: фиксированная цена за лист, всегда двусторонняя
        unit_price = lam["price"]
        min_price = lam["min"]
        sides_multiplier = 1  # цена включает обе стороны
    else:
        # Стандартная / softtouch: зона "small" для SRA3 и А3+
        unit_price = lam["small"]["price"]
        min_price = lam["small"]["min"]
        sides_multiplier = 1 if sides == "1+0" else 2

    raw_cost = unit_price * sides_multiplier * sheets_quantity
    total_cost = max(raw_cost, min_price)

    return {
        "unit_price":       unit_price,
        "sides_multiplier": sides_multiplier,
        "sheets_quantity":  sheets_quantity,
        "raw_cost":         raw_cost,
        "min_price":        min_price,
        "total_cost":       total_cost,
    }
