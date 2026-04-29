"""
Инструменты агента для полиграфического калькулятора.
Docstring намеренно краткие — полная документация в docs/tool_docs/*.md
и передаётся агенту через RAG-ретривер.
"""
import logging
import math

from smolagents import tool
from .control_digital import printdigi
from .control_offset import control_offset
from .lamination.calculator import calculate_lamination_price
from .blocknote import blocknote
from .kubarik import kubarik
from .bc7 import calculate_bc7_binding  # noqa: F401  (реэкспорт, @tool уже внутри)

logger = logging.getLogger(__name__)


@tool
def calculate_layout(
    piece_width: float,
    piece_height: float,
    margin_around: float = 2.0,
    margin_top: float = 5.0,
    margin_bottom: float = 5.0,
    margin_left: float = 5.0,
    margin_right: float = 5.0,
    orientation: str = "auto",
    sheet_size: str = "SRA3",
) -> dict:
    """
    Рассчитывает количество изделий на печатном листе.
    Вызывать перед печатью если формат изделия не SRA3/А3+.

    Args:
        piece_width: Ширина изделия, мм
        piece_height: Высота изделия, мм
        margin_around: Вылет вокруг изделия, мм (по умолчанию 2)
        margin_top: Поле сверху листа, мм (по умолчанию 5)
        margin_bottom: Поле снизу листа, мм (по умолчанию 5)
        margin_left: Поле слева листа, мм (по умолчанию 5)
        margin_right: Поле справа листа, мм (по умолчанию 5)
        orientation: "auto" (по умолчанию), "portrait", "landscape"
        sheet_size: "SRA3" (320×450, по умолчанию), "330x480", "auto"

    Returns:
        items_per_sheet, columns, rows, orientation, sheet_size.
        items_per_sheet=0 означает что изделие не помещается — повторить с другим sheet_size.
    """
    SHEETS = {
        "SRA3":    (320, 450),
        "330x480": (330, 480),
    }

    def calc_orientation(sheet_w, sheet_h, is_landscape):
        work_w = sheet_w - margin_left - margin_right
        work_h = sheet_h - margin_top - margin_bottom
        pw = piece_width + margin_around * 2
        ph = piece_height + margin_around * 2
        if is_landscape:
            cols = math.floor(work_h / pw)
            rows = math.floor(work_w / ph)
        else:
            cols = math.floor(work_w / pw)
            rows = math.floor(work_h / ph)
        return cols * rows, cols, rows

    def best_for_sheet(sheet_w, sheet_h):
        p_count, p_cols, p_rows = calc_orientation(sheet_w, sheet_h, False)
        l_count, l_cols, l_rows = calc_orientation(sheet_w, sheet_h, True)
        if orientation == "portrait":
            count, cols, rows, orient = p_count, p_cols, p_rows, "книжная"
        elif orientation == "landscape":
            count, cols, rows, orient = l_count, l_cols, l_rows, "альбомная"
        else:
            if p_count >= l_count:
                count, cols, rows, orient = p_count, p_cols, p_rows, "книжная"
            else:
                count, cols, rows, orient = l_count, l_cols, l_rows, "альбомная"
        return {
            "items_per_sheet": count,
            "columns": cols,
            "rows": rows,
            "orientation": orient,
            "portrait_count": p_count,
            "landscape_count": l_count,
        }

    valid_sheets = {"auto", "SRA3", "330x480"}
    if sheet_size not in valid_sheets:
        return {"ошибка": f"Недопустимый формат '{sheet_size}'. Используйте: {valid_sheets}"}

    if sheet_size == "auto":
        results = {}
        for name, (w, h) in SHEETS.items():
            results[name] = best_for_sheet(w, h)
            results[name]["sheet_size"] = f"{name} ({w}×{h})"
        recommended = max(SHEETS.keys(), key=lambda k: results[k]["items_per_sheet"])
        if results[recommended]["items_per_sheet"] == 0:
            return {"ошибка": "Изделие не помещается ни на один из доступных форматов"}
        results["recommended"] = recommended
        return results

    w, h = SHEETS[sheet_size]
    result = best_for_sheet(w, h)
    result["sheet_size"] = f"{sheet_size} ({w}×{h})"
    if result["items_per_sheet"] == 0:
        return {"ошибка": f"Изделие не помещается на формат {sheet_size}"}
    return result


@tool
def calculate_digital_printing(
    tirazh: int,
    items_per_sheet: int,
    colorness: str = "40",
    paper_price: float = 2.0,
    grammage: int = 80,
    material_name: str = None,
) -> dict:
    """
    Рассчитывает стоимость цифровой печати.

    Args:
        tirazh: Тираж изделий
        items_per_sheet: Изделий на листе — из calculate_layout (или 1 для SRA3/А3+)
        colorness: "40"=4+0, "44"=4+4, "10"=1+0, "11"=1+1, "41"=4+1
        paper_price: Цена листа А3, руб. (по умолчанию 2.0)
        grammage: Плотность бумаги, г/м² (по умолчанию 80)
        material_name: Тип материала ("мелованная", "офсетная", "картон") — опционально

    Returns:
        тип_печати, стоимость_печати, стоимость_бумаги, общая_стоимость,
        количество_листов_а3 (→ в calculate_lamination как sheets_quantity),
        цена_за_единицу.
    """
    try:
        valid_colorness = {"10", "40", "11", "44", "41"}
        if colorness not in valid_colorness:
            return {"ошибка": f"Недопустимая цветность '{colorness}'. Используйте: {valid_colorness}"}
        if items_per_sheet < 1:
            return {"ошибка": "items_per_sheet должен быть >= 1"}

        result = printdigi(
            tirazh=tirazh,
            cenalista_a3=paper_price,
            listov_na_a3=items_per_sheet,
            material=1,
            color_count=colorness,
            grammage=grammage,
            material_name=material_name,
        )

        if "ошибка" in result:
            return {"ошибка": result["ошибка"]}

        return {
            "тип_печати": "Цифровая",
            "стоимость_печати": round(result["стоимость_печати"], 2),
            "стоимость_бумаги": round(result["стоимость_бумаги"], 2),
            "общая_стоимость": round(result["стоимость_печати"] + result["стоимость_бумаги"], 2),
            "количество_листов_а3": result["количество_листов_а3"],
            "реальный_граммаж": result.get("реальный_граммаж", grammage),
            "примечание": result.get("примечание"),
            "цена_за_единицу": round(
                (result["стоимость_печати"] + result["стоимость_бумаги"]) / tirazh, 2
            ) if tirazh > 0 else 0,
        }
    except Exception as e:
        logger.error(f"❌ Ошибка в calculate_digital_printing: {e}")
        return {"ошибка": f"Ошибка расчета: {str(e)}"}


@tool
def calculate_offset_printing(
    tirazh: int,
    items_per_sheet: int,
    colorness: str = "10",
    paper_price: float = 2.0,
    material: str = "1",
    pantone_count: int = 0,
    pantone_accuracy: str = "0",
) -> dict:
    """
    Рассчитывает стоимость офсетной печати.

    Args:
        tirazh: Тираж изделий
        items_per_sheet: Изделий на листе — из calculate_layout
        colorness: "10"=1+0, "11"=1+1, "20"=2+0, "22"=2+2, "21"=2+1
        paper_price: Цена листа А3, руб. (по умолчанию 2.0)
        material: "1"=бумага (по умолчанию), "2"=картон
        pantone_count: Количество пантонов (по умолчанию 0)
        pantone_accuracy: "0"=приблизительный, "1"=точный подбор

    Returns:
        тип_печати, стоимость_печати, стоимость_бумаги, общая_стоимость,
        количество_листов_а3 (→ в calculate_lamination как sheets_quantity),
        количество_форм, цена_за_единицу.
    """
    try:
        valid_colorness = {"10", "11", "20", "22", "21"}
        if colorness not in valid_colorness:
            return {"ошибка": f"Недопустимая цветность '{colorness}'. Используйте: {valid_colorness}"}
        if items_per_sheet < 1:
            return {"ошибка": "items_per_sheet должен быть >= 1"}

        result = control_offset(
            tirazh=tirazh,
            listov_na_a3=items_per_sheet,
            material=material,
            cenalista_a3=paper_price,
            cvetnost=colorness,
            kolvo_pantone=pantone_count,
            tochnost=pantone_accuracy,
        )

        return {
            "тип_печати": "Офсетная",
            "стоимость_печати": round(result["стоимость_печати"], 2),
            "стоимость_бумаги": round(result["стоимость_бумаги"], 2),
            "общая_стоимость": round(result["стоимость_печати"] + result["стоимость_бумаги"], 2),
            "количество_листов_а3": result["количество_листов_а3"],
            "количество_форм": result["количество_форм"],
            "цена_за_единицу": round(
                (result["стоимость_печати"] + result["стоимость_бумаги"]) / tirazh, 2
            ) if tirazh > 0 else 0,
        }
    except Exception as e:
        logger.error(f"❌ Ошибка в calculate_offset_printing: {e}")
        return {"ошибка": f"Ошибка расчета: {str(e)}"}


@tool
def calculate_lamination(
    lamination_type: str = "standard",
    sides: str = "1+0",
    sheets_quantity: int = 1,
) -> dict:
    """
    Рассчитывает стоимость ламинации тиражных листов А3+.

    Args:
        lamination_type: "standard", "softtouch", "75", "125"
        sides: "1+0" (одна сторона) или "1+1" (обе стороны)
        sheets_quantity: Листов А3+ из результата печати
                         (поле "количество_листов_а3" — НЕ тираж изделий!)

    Returns:
        unit_price, sides_multiplier, sheets_quantity, raw_cost, min_price, total_cost.
    """
    if not lamination_type:
        lamination_type = "standard"
    if lamination_type not in ("standard", "softtouch", "75", "125"):
        return {"ошибка": f"Недопустимый тип ламинации: {lamination_type}"}
    if sides not in ("1+0", "1+1"):
        return {"ошибка": f"Недопустимое значение сторон: {sides}"}
    if sheets_quantity < 1:
        return {"ошибка": "sheets_quantity должен быть >= 1"}

    return calculate_lamination_price(lamination_type, sides, sheets_quantity)


@tool
def calculate_blocknote(
    tirazh: int,
    list_block: int,
    format_val: int = 4,
    storona: str = "1",
    cvetnost: str = "11",
    pantony: int = 0,
    tochnost: str = "0",
    list_price: float = 2.0,
    rezka: str = "1",
    pruzhina: int = 1,
    cover_price: float = 5.0,
    cover_color_count: str = "44",
    lam_quality: str = "1",
    lam_sides: str = "1+0",
    backing_color_count: str = "0",
    backing_lam_quality: str = "1",
    backing_lam_sides: str = "1+0",
) -> dict:
    """
    Рассчитывает стоимость изготовления блокнота/тетради с металлической пружиной.
    Включает: блок (офсет), обложку (цифра), подложку, пружину, ламинацию.

    Args:
        tirazh: Тираж, штук
        list_block: Листов в блоке
        format_val: A6=8, A5=4 (по умолчанию), A4=2, A3=1
        storona: Сторона пружины — "1" короткая, "2" длинная
        cvetnost: Цветность блока — "10","11","20","22","21"
        pantony: Пантонов в блоке (по умолчанию 0)
        tochnost: Точность пантона — "0" прибл., "1" точный
        list_price: Цена бумаги блока за А3, руб.
        rezka: "1"=один рез, "2"=два реза
        pruzhina: Размер пружины 0–5 (0=6.4мм…5=14.3мм, по умолчанию 1=7.9мм)
        cover_price: Цена картона обложки за А3, руб.
        cover_color_count: Цветность обложки — "40","44","10","11"
        lam_quality: Ламинация обложки — "1"=нет,"2"=глянец,"3"=мат,"4"=75мкм,"5"=125мкм
        lam_sides: Стороны ламинации обложки — "1+0" или "1+1"
        backing_color_count: Цветность подложки — "0"=без печати,"40","44","10","11"
        backing_lam_quality: Ламинация подложки — "1"=нет,"2"=глянец,"3"=мат,"4"=75мкм,"5"=125мкм
        backing_lam_sides: Стороны ламинации подложки — "1+0" или "1+1"

    Returns:
        Словарь с ключом "ответ" — передавать напрямую в final_answer(result["ответ"]).
        Также содержит числовые поля для программного использования.
    """
    try:
        def normalize_colorness(val):
            return str(val).replace(" ", "").replace("+", "")

        result = blocknote(
            tirazh=tirazh,
            list_block=list_block,
            format_val=format_val,
            storona=storona,
            cvetnost=normalize_colorness(cvetnost),
            pantony=pantony,
            tochnost=tochnost,
            list_price=list_price,
            rezka=rezka,
            pruzhina=pruzhina,
            cover_price=cover_price,
            cover_color_count=normalize_colorness(cover_color_count),
            lam_quality=lam_quality,
            lam_sides=lam_sides,
            backing_color_count=normalize_colorness(backing_color_count),
            backing_lam_quality=backing_lam_quality,
            backing_lam_sides=backing_lam_sides,
        )

        if "error" in result or "ошибка" in result:
            error_msg = result.get("error", result.get("ошибка", "Неизвестная ошибка"))
            return {"ошибка": f"Ошибка расчета блокнота: {error_msg}"}

        sep = "=" * 60
        format_map = {1: "А3", 2: "А4", 4: "А5", 8: "А6"}
        fmt = format_map.get(int(format_val), f"Формат {format_val}")
        spring_side = "короткой" if storona == "1" else "длинной"
        cvetnost_n = normalize_colorness(cvetnost)
        cover_n = normalize_colorness(cover_color_count)

        formatted = f"""Блокнот {fmt}, {list_block} листов, тираж {tirazh} штук:
Блок: {cvetnost_n} | Обложка: {cover_n} | Пружина: {result.get('размер_пружины','')} по {spring_side} стороне

{sep}
ПОДРОБНЫЙ РАСЧЕТ СТОИМОСТИ:
{sep}

БЛОК (офсетная печать):
  Печать: {round(result.get('стоимость_печати_блока', 0), 2)} руб.
  Бумага: {round(result.get('стоимость_бумаги_блока', 0), 2)} руб. ({int(result.get('количество_листов_а3_блок', 0))} листов А3)

ОБЛОЖКА (цифровая печать):
  Печать: {round(result.get('стоимость_печати_обложки', 0), 2)} руб.
  Картон: {round(result.get('стоимость_картона_обложки', 0), 2)} руб. ({int(result.get('количество_листов_а3_обложка', 0))} листов А3)
  Ламинация: {round(result.get('стоимость_ламинации_обложки', 0), 2)} руб. ({result.get('тип_ламинации_обложки', 'нет')})

ПОДЛОЖКА:
  Печать: {round(result.get('стоимость_печати_подложки', 0), 2)} руб.
  Картон: {round(result.get('стоимость_картона_подложки', 0), 2)} руб.
  Ламинация: {round(result.get('стоимость_ламинации_подложки', 0), 2)} руб. ({result.get('тип_ламинации_подложки', 'нет')})

СБОРКА:
  Пружина: {round(result.get('стоимость_пружины', 0), 2)} руб. ({int(result.get('количество_петель', 0))} петель)
  Пробивка: {round(result.get('стоимость_пробивки_дырок', 0), 2)} руб.
  Счет листов: {round(result.get('стоимость_счета_листов', 0), 2)} руб.
  Резка: {round(result.get('стоимость_резки', 0), 2)} руб.

{sep}
ИТОГО: {round(result.get('общая_стоимость_изготовления', 0), 2)} руб. / {round(result.get('цена_за_единицу', 0), 2)} руб. за шт.
{sep}"""

        return {
            "ответ": formatted.strip(),
            "тип_продукции": "Блокнот/Тетрадь",
            "тираж": tirazh,
            "стоимость_печати_блока": round(result.get("стоимость_печати_блока", 0), 2),
            "стоимость_бумаги_блока": round(result.get("стоимость_бумаги_блока", 0), 2),
            "количество_листов_а3_блок": int(result.get("количество_листов_а3_блок", 0)),
            "стоимость_печати_обложки": round(result.get("стоимость_печати_обложки", 0), 2),
            "количество_листов_а3_обложка": int(result.get("количество_листов_а3_обложка", 0)),
            "стоимость_картона_обложки": round(result.get("стоимость_картона_обложки", 0), 2),
            "стоимость_ламинации_обложки": round(result.get("стоимость_ламинации_обложки", 0), 2),
            "тип_ламинации_обложки": result.get("тип_ламинации_обложки", "нет"),
            "стоимость_печати_подложки": round(result.get("стоимость_печати_подложки", 0), 2),
            "стоимость_картона_подложки": round(result.get("стоимость_картона_подложки", 0), 2),
            "стоимость_ламинации_подложки": round(result.get("стоимость_ламинации_подложки", 0), 2),
            "тип_ламинации_подложки": result.get("тип_ламинации_подложки", "нет"),
            "стоимость_резки": round(result.get("стоимость_резки", 0), 2),
            "стоимость_счета_листов": round(result.get("стоимость_счета_листов", 0), 2),
            "стоимость_пробивки": round(result.get("стоимость_пробивки_дырок", 0), 2),
            "стоимость_пружины": round(result.get("стоимость_пружины", 0), 2),
            "размер_пружины": result.get("размер_пружины", ""),
            "количество_петель": int(result.get("количество_петель", 0)),
            "общая_стоимость": round(result.get("общая_стоимость_изготовления", 0), 2),
            "цена_за_единицу": round(result.get("цена_за_единицу", 0), 2),
        }
    except Exception as e:
        logger.error(f"❌ Ошибка в calculate_blocknote: {e}")
        return {"ошибка": f"Ошибка расчета блокнота: {str(e)}"}


@tool
def calculate_kubarik(
    tirazh: int,
    kubelist: int,
    listprice: float = 2.0,
    cvetnost: str = "11",
    pantony: int = 0,
    tochnost: str = "0",
) -> dict:
    """
    Рассчитывает стоимость производства кубарика (блок склеенных листов).
    Офсетная печать + предварительная резка + промазка клеем + финальная резка.

    Args:
        tirazh: Тираж, штук
        kubelist: Листов в одном кубарике
        listprice: Цена бумаги за А3, руб. (по умолчанию 2.0)
        cvetnost: "10","11" (по умолчанию),"20","22","21"
        pantony: Пантонов (по умолчанию 0)
        tochnost: "0"=приблизительный, "1"=точный пантон

    Returns:
        тип_продукции, тираж, листов_в_куб, стоимость_печати, стоимость_бумаги,
        стоимость_предварительной_резки, стоимость_промазки, стоимость_финальной_резки,
        количество_листов_а3, общая_стоимость, цена_за_единицу.
    """
    try:
        result = kubarik(
            tirazh=tirazh,
            kubelist=kubelist,
            listprice=listprice,
            cvetnost=cvetnost,
            pantony=pantony,
            tochnost=tochnost,
        )
        return {
            "тип_продукции": "Кубарик/Пазл",
            "тираж": tirazh,
            "листов_в_куб": kubelist,
            "стоимость_печати": round(result.get("стоимость_печати", 0), 2),
            "стоимость_бумаги": round(result.get("стоимость_бумаги", 0), 2),
            "стоимость_предварительной_резки": round(result.get("стоимость_предварительной_резки", 0), 2),
            "стоимость_промазки": round(result.get("стоимость_промазки", 0), 2),
            "стоимость_финальной_резки": round(result.get("стоимость_финальной_резки", 0), 2),
            "количество_листов_а3": result.get("количество_листов_а3", 0),
            "общая_стоимость": round(result.get("общая_стоимость", 0), 2),
            "цена_за_единицу": round(result.get("цена_за_единицу", 0), 2),
        }
    except Exception as e:
        logger.error(f"❌ Ошибка в calculate_kubarik: {e}")
        return {"ошибка": f"Ошибка расчета кубарика: {str(e)}"}
