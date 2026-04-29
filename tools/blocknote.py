"""
Расчёт стоимости изготовления блокнотов с пружиной.
Цены загружаются через tools.prices — единственный источник данных.
"""
import math
from .control_offset import control_offset
from .control_digital import printdigi
from .lamination.calculator import calculate_lamination_price
from .prices import load_prices


def blocknote(
    tirazh, list_block, format_val, storona, cvetnost, pantony=0, tochnost="0",
    list_price=2.0, rezka="1", pruzhina=1, cover_price=5.0,
    cover_color_count="40", lam_quality="1",
    lam_sides="1+0",
    backing_color_count="0", backing_lam_quality="1", backing_lam_sides="1+0",
):
    """
    Расчёт стоимости изготовления блокнотов.

    Параметры:
    - tirazh (int): тираж блокнотов
    - list_block (int): количество листов в блоке
    - format_val (int): формат (А6=8, А5=4, А4=2, А3=1)
    - storona (str): сторона пружины ("1"=короткая, "2"=длинная)
    - cvetnost (str): цветность блока ("10","11","20","22","21")
    - pantony (int): количество пантонов
    - tochnost (str): точность пантона ("0"=приблиз., "1"=точный)
    - list_price (float): цена бумаги блока за А3
    - rezka (str): "1"=один рез, "2"=два реза
    - pruzhina (int): размер пружины 0–5
    - cover_price (float): цена картона обложки за А3
    - cover_color_count (str): цветность обложки ("40","44","10","11")
    - lam_quality (str): ламинация обложки ("1"=нет,"2"=глянец,"3"=софттач,"4"=75мкм,"5"=125мкм)
    - lam_sides (str): стороны ламинации обложки ("1+0" или "1+1")
    - backing_color_count (str): цветность подложки ("0"=без печати,"40","44","10","11")
    - backing_lam_quality (str): ламинация подложки ("1"=нет,"2"=глянец,"3"=софттач,"4"=75мкм,"5"=125мкм)
    - backing_lam_sides (str): стороны ламинации подложки ("1+0" или "1+1")
    """
    valid_cvetnost = {"10", "11", "20", "22", "21"}
    valid_formats = {8, 4, 2, 1}

    cvetnost = str(cvetnost).replace("+", "")
    cover_color_count = str(cover_color_count).replace("+", "")
    backing_color_count = str(backing_color_count).replace("+", "")

    if cvetnost not in valid_cvetnost:
        return {"error": f"Неподдерживаемая цветность: {cvetnost}. Допустимые: {valid_cvetnost}"}
    if cover_color_count not in {"40", "44", "10", "11"}:
        return {"error": f"Неподдерживаемая цветность обложки: {cover_color_count}"}
    if format_val not in valid_formats:
        return {"error": f"Неподдерживаемый формат: {format_val}. Допустимые: {valid_formats}"}
    if tirazh < 1 or list_block < 1:
        return {"error": "Тираж и количество листов должны быть >= 1"}

    prices = load_prices()

    sum_rezka = 0
    schet_listov = 0
    sum_dyrki = 0
    sum_pruzhina = 0

    # ── Блок (офсетная печать) ────────────────────────────────
    of_tirazh = math.ceil(tirazh * list_block / format_val)

    try:
        offset_result = control_offset(of_tirazh, 1, "1", list_price, cvetnost, pantony, tochnost)
        if "error" in offset_result or "ошибка" in offset_result:
            return {"error": f"Ошибка расчёта блока: {offset_result}"}
        block_print_cost = offset_result["стоимость_печати"]
        block_paper_cost = offset_result["стоимость_бумаги"]
        block_sheets_a3 = offset_result["количество_листов_а3"]
    except Exception as e:
        return {"error": f"Ошибка расчёта блока: {str(e)}"}

    # ── Резка ─────────────────────────────────────────────────
    col_rez = prices["colRez"]["value"]
    price_rezka = prices["priceRezka"]["value"]
    for rez_data in col_rez:
        if int(rez_data["format"]) == format_val:
            if rezka == "1":
                sum_rezka = rez_data["rez1"] * math.ceil(of_tirazh / 300) * price_rezka
            else:
                sum_rezka = rez_data["rez2"] * math.ceil(of_tirazh / 300) * price_rezka
            break

    # ── Счёт листов ───────────────────────────────────────────
    schet_listov = of_tirazh * prices["zhSchListov"]["value"]

    # ── Пробивка дырок ────────────────────────────────────────
    pr_probiv_dyrok = prices["prProbivDyrok"]["value"]
    sum_dyrki = math.floor(list_block / 12) * tirazh * pr_probiv_dyrok
    if format_val == 1 and storona == "2":
        sum_dyrki *= 2.4

    # ── Пружина ───────────────────────────────────────────────
    col_petel_block = prices["colPetelBlock"]["value"]
    col_petli_bobina = prices["colPetliBobina"]["value"]
    pr_pruzhina = prices["prPruzhina"]["value"]

    col_petel = 0
    for petel_data in col_petel_block:
        if int(petel_data["format"]) == format_val:
            col_petel = petel_data["korotkaya" if storona == "1" else "dlinnaya"] * tirazh
            break

    cena_petli = pr_pruzhina / col_petli_bobina[pruzhina]
    sum_pruzhina = cena_petli * col_petel * 3

    spring_sizes = [
        "1/4 d 6,4 мм", "5/16 d 7,9 мм", "3/8 d 9,5 мм",
        "7/16 d 11.1 мм", "1/2 d 12,7 мм", "9/16 d 14,3 мм",
    ]
    spring_size = spring_sizes[pruzhina]
    col_petel_total = col_petel  # сохраняем для отчёта

    # ── Обложка ───────────────────────────────────────────────
    cover_tirazh = math.ceil(tirazh / format_val) + 2

    try:
        if cover_color_count in ("40", "44"):
            cover_result = printdigi(cover_tirazh, cover_price, 1, 2, cover_color_count, 300)
        else:
            cover_result = control_offset(cover_tirazh, 1, "1", cover_price, cover_color_count, 0, "0")
        if "error" in cover_result or "ошибка" in cover_result:
            return {"error": f"Ошибка расчёта обложки: {cover_result}"}
        cover_print_cost = cover_result["стоимость_печати"]
        cover_paper_cost = cover_result["стоимость_бумаги"]
        cover_sheets_a3 = cover_result["количество_листов_а3"]
    except Exception as e:
        return {"error": f"Ошибка расчёта обложки: {str(e)}"}

    # ── Ламинация обложки ─────────────────────────────────────
    LAM_TYPE_MAP = {"1": None, "2": "standard", "3": "softtouch", "4": "75", "5": "125"}
    lam_names = {"1": "нет", "2": "стандартная", "3": "софттач", "4": "плёнка 75мкм", "5": "плёнка 125мкм"}

    cover_lam_type = LAM_TYPE_MAP.get(str(lam_quality))
    cover_lam_sides = "1+1" if lam_quality in ("4", "5") else lam_sides
    if cover_lam_type:
        lam_result = calculate_lamination_price(cover_lam_type, cover_lam_sides, int(cover_sheets_a3))
        cover_lam_cost = lam_result.get("total_cost", 0)
    else:
        cover_lam_cost = 0

    # ── Подложка ──────────────────────────────────────────────
    backing_sheets = int(cover_sheets_a3)

    # Печать подложки (если указана)
    backing_print_cost = 0.0
    if backing_color_count and backing_color_count != "0":
        try:
            if backing_color_count in ("40", "44"):
                back_result = printdigi(cover_tirazh, cover_price, 1, 2, backing_color_count, 300)
            else:
                back_result = control_offset(cover_tirazh, 1, "1", cover_price, backing_color_count, 0, "0")
            if "error" not in back_result and "ошибка" not in back_result:
                backing_print_cost = back_result["стоимость_печати"]
        except Exception:
            backing_print_cost = 0.0

    backing_paper_cost = backing_sheets * cover_price

    # Ламинация подложки
    backing_lam_type = LAM_TYPE_MAP.get(str(backing_lam_quality))
    back_lam_sides_eff = "1+1" if backing_lam_quality in ("4", "5") else backing_lam_sides
    if backing_lam_type:
        back_lam_result = calculate_lamination_price(backing_lam_type, back_lam_sides_eff, backing_sheets)
        backing_lam_cost = back_lam_result.get("total_cost", 0)
    else:
        backing_lam_cost = 0.0

    # ── Итог ─────────────────────────────────────────────────
    total_cost = (
        block_print_cost + block_paper_cost
        + sum_rezka + schet_listov + sum_dyrki + sum_pruzhina
        + cover_print_cost + cover_paper_cost + cover_lam_cost
        + backing_print_cost + backing_paper_cost + backing_lam_cost
    )
    price_per_unit = total_cost / tirazh if tirazh > 0 else 0

    return {
        # Блок
        "стоимость_печати_блока":    block_print_cost,
        "количество_листов_а3_блок": block_sheets_a3,
        "стоимость_бумаги_блока":    block_paper_cost,
        # Обложка
        "стоимость_печати_обложки":    cover_print_cost,
        "количество_листов_а3_обложка": cover_sheets_a3,
        "стоимость_картона_обложки":   cover_paper_cost,
        "стоимость_ламинации_обложки": cover_lam_cost,
        "тип_ламинации_обложки":       lam_names.get(str(lam_quality), "нет"),
        # Подложка
        "стоимость_печати_подложки":    backing_print_cost,
        "стоимость_картона_подложки":   backing_paper_cost,
        "стоимость_ламинации_подложки": backing_lam_cost,
        "тип_ламинации_подложки":       lam_names.get(str(backing_lam_quality), "нет"),
        # Сборка
        "стоимость_пружины":      sum_pruzhina,
        "размер_пружины":         spring_size,
        "количество_петель":      int(col_petel_total),
        "стоимость_пробивки_дырок": sum_dyrki,
        "стоимость_счета_листов": schet_listov,
        "стоимость_резки":        sum_rezka,
        # Итог
        "общая_стоимость_сборки":       sum_rezka + schet_listov + sum_dyrki + sum_pruzhina,
        "общая_стоимость_изготовления": total_cost,
        "цена_за_единицу":              price_per_unit,
    }


if __name__ == "__main__":
    result = blocknote(
        tirazh=100, list_block=50, format_val=2,
        storona="1", cvetnost="11", list_price=2.0,
        cover_price=5.0, cover_color_count="44", lam_quality="2",
    )
    print(result)
