"""
Расчёт цифровой печати.
Цены загружаются через tools.prices — единственный источник данных.
"""
import math
from .prices import load_prices, resolve_paper_price


def printdigi(
    tirazh: int,
    cenalista_a3: float,
    listov_na_a3: int,
    material: int,
    color_count: str,
    grammage: int = 80,
    material_name: str = None,
) -> dict:
    """
    Расчёт цифровой печати.

    Параметры:
    - tirazh: тираж изделий
    - cenalista_a3: цена листа А3 (используется если material_name не указан)
    - listov_na_a3: изделий на листе А3
    - material: 1=бумага, иное=другой материал
    - color_count: "10","11","40","44","41"
    - grammage: плотность бумаги г/м² (по умолчанию 80)
    - material_name: тип бумаги словом ("мелованная","офсетная","картон") —
                     если указан, цена берётся из paperDigiPrice.json,
                     а cenalista_a3 игнорируется

    Возвращает:
    dict: стоимость_печати, стоимость_бумаги, количество_листов_а3,
          реальный_граммаж, примечание (если граммаж был скорректирован)
    """
    prices = load_prices()

    note = None
    actual_grammage = grammage

    # Если указан тип материала — берём цену из paperDigiPrice.json
    if material_name:
        try:
            cenalista_a3, actual_grammage, note = resolve_paper_price(
                material_name, grammage
            )
        except (ValueError, KeyError) as e:
            return {"ошибка": str(e)}

    # Опорные данные из MyPrices.json
    rep     = prices["digitalBaseTirazh"]["value"]
    col_pr  = prices["priceDigitalPage"]["value"]
    wb_pr   = prices["priceWbPage"]["value"]

    listov_a3 = math.ceil(tirazh / listov_na_a3)

    # Находим ценовой диапазон для тиража
    i = len(rep)  # по умолчанию — последний диапазон
    for idx, threshold in enumerate(rep):
        if listov_a3 <= threshold:
            i = idx
            break

    # Цена цветной страницы
    pr_col_stranicy = col_pr[min(i, len(col_pr) - 1)]

    # Цена ч/б страницы: Nuvera (до 150 г/м², бумага) или Rico (всё остальное)
    pr_wb_stranicy = wb_pr[0] if (actual_grammage <= 150 and material == 1) else wb_pr[1]

    paper_sum = listov_a3 * cenalista_a3
    margin = 1.5

    if color_count == "10":
        final_sum = margin * listov_a3 * pr_wb_stranicy
    elif color_count == "11":
        final_sum = margin * listov_a3 * pr_wb_stranicy * 2
    elif color_count == "40":
        final_sum = margin * listov_a3 * pr_col_stranicy
    elif color_count == "44":
        final_sum = margin * listov_a3 * pr_col_stranicy * 2
    elif color_count == "41":
        final_sum = margin * listov_a3 * (wb_pr[1] + pr_col_stranicy)
    else:
        return {"ошибка": f"Неподдерживаемый тип цветности: {color_count}"}

    return {
        "стоимость_печати":   final_sum,
        "стоимость_бумаги":   paper_sum,
        "количество_листов_а3": listov_a3,
        "реальный_граммаж":   actual_grammage,
        "примечание":         note,
    }
