"""
Расчёт стоимости производства кубариков.
Цены загружаются через tools.prices — единственный источник данных.
"""
import math
from .control_offset import control_offset
from .prices import load_prices


def kubarik(tirazh, kubelist, listprice, cvetnost, pantony=0, tochnost="0"):
    """
    Расчёт стоимости производства кубарика (блок склеенных листов).

    На одном листе А3 размещается 12 листков кубарика.

    Параметры:
    - tirazh (int): тираж кубариков
    - kubelist (int): листов в одном кубарике
    - listprice (float): цена бумаги за А3
    - cvetnost (str): "10","11","20","22","21"
    - pantony (int): количество пантонов
    - tochnost (str): "0"=приблизительный, "1"=точный

    Возвращает:
    dict: общая_стоимость, цена_за_единицу, количество_листов_а3,
          стоимость_бумаги, стоимость_печати,
          стоимость_предварительной_резки, стоимость_промазки, стоимость_финальной_резки
    """
    prices = load_prices()
    price_rezka         = prices["priceRezka"]["value"]
    pr_kub_promaz_first = prices["prKubPromazFirst"]["value"]
    pr_kub_promaz_last  = prices["prKubPromazLast"]["value"]

    # Офсетный тираж (листы А3): 12 листков кубарика на лист А3
    of_tirazh = math.ceil(tirazh * kubelist / 12)

    offset_result = control_offset(of_tirazh, 1, "1", listprice, cvetnost, pantony, tochnost)
    final_sum   = offset_result["стоимость_печати"]
    paper_sum   = offset_result["стоимость_бумаги"]
    paper_sheets = offset_result["количество_листов_а3"]

    # Предварительная резка (пачки по 300 листов, 15 резов на пачку)
    col_pachek = math.ceil(of_tirazh / 300)
    pred_rezka = col_pachek * price_rezka * 15

    # Промазка клеем
    promazka = (
        pr_kub_promaz_first
        + pr_kub_promaz_last * (math.ceil(kubelist / 50) - 1)
    ) * tirazh

    # Финальная резка
    fin_rezka = math.ceil(tirazh / math.ceil(500 / kubelist)) * price_rezka * 3

    total_cost = final_sum + pred_rezka + promazka + fin_rezka + paper_sum
    price_per_unit = total_cost / tirazh if tirazh > 0 else 0

    return {
        "общая_стоимость":               total_cost,
        "цена_за_единицу":               price_per_unit,
        "количество_листов_а3":          paper_sheets,
        "стоимость_бумаги":              paper_sum,
        "стоимость_печати":              final_sum,
        "стоимость_предварительной_резки": pred_rezka,
        "стоимость_промазки":            promazka,
        "стоимость_финальной_резки":     fin_rezka,
    }


if __name__ == "__main__":
    result = kubarik(tirazh=500, kubelist=100, listprice=2.0, cvetnost="11")
    print(f"Итого: {result['общая_стоимость']:.2f} / {result['цена_за_единицу']:.2f} за шт.")
