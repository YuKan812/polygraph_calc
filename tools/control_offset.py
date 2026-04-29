"""
Расчёт офсетной печати.
Цены загружаются через tools.prices — единственный источник данных.
"""
import math
from .prices import load_prices


def control_offset(
    tirazh: int,
    listov_na_a3: int,
    material: str,
    cenalista_a3: float,
    cvetnost: str,
    kolvo_pantone: int,
    tochnost: str,
) -> dict:
    """
    Расчёт офсетной печати.

    Параметры:
    - tirazh: тираж изделий
    - listov_na_a3: изделий на листе А3
    - material: "1"=бумага, иное=картон
    - cenalista_a3: цена листа А3
    - cvetnost: "10","11","20","22","21"
    - kolvo_pantone: количество пантонов
    - tochnost: "1"=точный, иное=приблизительный подбор пантона

    Возвращает:
    dict: стоимость_печати, стоимость_бумаги, количество_листов_а3, количество_форм
    """
    prices = load_prices()

    # Цена прогона зависит от материала
    if material == "1":
        price_progon = prices["priceProgonPaper"]["value"]
    else:
        price_progon = prices["priceProgonKarton"]["value"]

    # Количество форм и прогонов по цветности
    CVETNOST_MAP = {
        "10": (1, 1),   # 1+0
        "11": (2, 2),   # 1+1
        "20": (2, 1),   # 2+0
        "22": (4, 2),   # 2+2
        "21": (3, 2),   # 2+1
    }
    if cvetnost not in CVETNOST_MAP:
        raise ValueError(f"Неподдерживаемый тип цветности: {cvetnost}")

    kolvo_form, kolvo_progon = CVETNOST_MAP[cvetnost]

    # Цена подбора пантона
    if tochnost == "1":
        cena_podbora = prices["pricePodborPantonToch"]["value"]
    else:
        cena_podbora = prices["pricePodborPantonPrib"]["value"]

    return _print_offset(
        tirazh=tirazh,
        cenalista_a3=cenalista_a3,
        listov_na_a3=listov_na_a3,
        price_progon=price_progon,
        kolvo_form=kolvo_form,
        kolvo_progon=kolvo_progon,
        kolvo_pantone=kolvo_pantone,
        cena_pod_pantona=cena_podbora,
        prices=prices,
    )


def _print_offset(
    tirazh: int,
    cenalista_a3: float,
    listov_na_a3: int,
    price_progon: float,
    kolvo_form: int,
    kolvo_progon: int,
    kolvo_pantone: int,
    cena_pod_pantona: float,
    prices: dict,
) -> dict:
    """Внутренняя функция расчёта офсетной печати."""
    listov_a3 = math.ceil(tirazh / listov_na_a3)

    # Приладка: +10% до 5000 листов, +5% свыше
    if listov_a3 < 5000:
        listov_a3_s_prilad = listov_a3 * 1.1
    else:
        listov_a3_s_prilad = listov_a3 * 1.05

    print_tirazh = (
        listov_a3 * price_progon * kolvo_progon
        + kolvo_form * prices["priceForma"]["value"]
        + prices["pricePriladkaOffs"]["value"]
        + kolvo_pantone * cena_pod_pantona
    )

    paper_sum = listov_a3_s_prilad * cenalista_a3

    return {
        "стоимость_печати":    print_tirazh,
        "стоимость_бумаги":    paper_sum,
        "количество_листов_а3": listov_a3_s_prilad,
        "количество_форм":     kolvo_form,
    }
