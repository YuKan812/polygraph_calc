"""
Расчёт стоимости брошюровки 7БЦ (твёрдый переплёт).
Порт JavaScript-калькулятора bc7_TF.html → Python + генерация PDF через reportlab.
"""

import os
import math
from datetime import datetime

# ─────────────────────────────────────────────
#  Данные для расчётов
# ─────────────────────────────────────────────
CALCULATION_DATA = {
    "A4": {
        "preliminary_cut": 0,
        "folding": 3,
        "sewing_multiplier": 3,
        "sewing_coefficient": 1.4,
        "sewing_fixed": 500,
        "endpapers": 6,
        "endpaper_gluing": 20,
        "block_cutting": 20,
        "impregnation": 21,
        "impregnation_minimum": 1120.0,
        "block_processing": 20,
        "cardboard_divisor": 4.5,
        "cover": 30,
        "insert": 20,
        "bumvinil": 37.50,
        "rounding": 30,
        "glue": 3,
        "lifting_a4": 2.0,
        "lifting_a5": 1.5,
    },
    "A5": {
        "preliminary_cut": 2,
        "folding": 2,
        "sewing_multiplier": 2,
        "sewing_coefficient": 1.4,
        "sewing_fixed": 500,
        "endpapers": 4,
        "endpaper_gluing": 18,
        "block_cutting": 20,
        "impregnation": 21,
        "impregnation_minimum": 1120.0,
        "block_processing": 20,
        "cardboard_divisor": 8,
        "cover": 30,
        "insert": 20,
        "bumvinil": 19,
        "rounding": 30,
        "glue": 2,
        "lifting_a4": 2.0,
        "lifting_a5": 1.5,
    },
    "A3": {
        "preliminary_cut": 0,
        "folding": 4,
        "sewing_multiplier": 4,
        "sewing_coefficient": 1.4,
        "sewing_fixed": 500,
        "endpapers": 8,
        "endpaper_gluing": 25,
        "block_cutting": 25,
        "impregnation": 21,
        "impregnation_minimum": 1120.0,
        "block_processing": 25,
        "cardboard_divisor": 3,
        "cover": 40,
        "insert": 25,
        "bumvinil": 50,
        "rounding": 35,
        "glue": 4,
        "lifting_a4": 2.0,
        "lifting_a5": 1.5,
    },
    "A6": {
        "preliminary_cut": 3,
        "folding": 1.5,
        "sewing_multiplier": 1.5,
        "sewing_coefficient": 1.4,
        "sewing_fixed": 500,
        "endpapers": 3,
        "endpaper_gluing": 15,
        "block_cutting": 15,
        "impregnation": 21,
        "impregnation_minimum": 1120.0,
        "block_processing": 15,
        "cardboard_divisor": 10,
        "cover": 25,
        "insert": 15,
        "bumvinil": 15,
        "rounding": 25,
        "glue": 1.5,
        "lifting_a4": 2.0,
        "lifting_a5": 1.5,
    },
}

CARDBOARD_PRICES = {
    "1.5": 94.0,
    "1.75": 105.0,
    "2.0": 119.0,
    "2.5": 167.0,
}

CARDBOARD_LABELS = {
    "1.5": "1,5мм — 94 р/л",
    "1.75": "1,75мм — 105 р/л",
    "2.0": "2,0мм — 119 р/л",
    "2.5": "2,5мм — 167 р/л",
}

MANAGERS = {
    "vladimirova": "Владимирова С.",
    "dmitriev": "Дмитриев С.",
    "dustova": "Дустова Н.",
    "minenkov": "Миненков А.",
    "kursanov": "Курсанов П.",
    "pokrovskaja": "Покровская Н.",
    "salnikova": "Сальникова С.",
    "hokhlova": "Хохлова О.",
    "feoktistova": "Феоктистова Н.",
    "chistyakova": "Чистякова Л.",
}

def _normalize_manager_name(manager: str) -> str:
    manager = (manager or "").strip()
    if not manager:
        return ""
    for key, value in MANAGERS.items():
        if manager.lower() == key.lower() or manager.lower() == value.lower():
            return value
    # Попытка найти по фамилии
    for key, value in MANAGERS.items():
        surname = value.split()[0].lower()
        if surname in manager.lower():
            return value
    return manager


def _manager_filename(manager_name: str) -> str:
    if not manager_name:
        return "unknown"
    surname = manager_name.split()[0]
    return surname.replace(" ", "_").replace('.', '')


# ─────────────────────────────────────────────
#  Основная функция расчёта
# ─────────────────────────────────────────────
def calculate_bc7(
    tirazh: int,
    format_val: str,
    grammazh: int,
    polosy: int,
    rounding: bool = False,
    cardboard: str = "2.0",
    cover_material: str = "paper",
    cover_color: str = "0",
    manager: str = "",
    notes: str = "",
) -> dict:
    if format_val not in CALCULATION_DATA:
        return {"ошибка": f"Неизвестный формат: {format_val}. Допустимые: A3, A4, A5, A6"}
    if cardboard not in CARDBOARD_PRICES:
        return {"ошибка": f"Неизвестный картон: {cardboard}. Допустимые: 1.5, 1.75, 2.0, 2.5"}
    if tirazh < 1 or grammazh < 1 or polosy < 1:
        return {"ошибка": "Тираж, граммаж и количество полос должны быть >= 1"}

    if grammazh < 100:
        tetrad = 24
    elif grammazh < 130:
        tetrad = 16
    else:
        tetrad = 8
    signatures = math.ceil(polosy / tetrad)

    fd = CALCULATION_DATA[format_val]
    price_karton = CARDBOARD_PRICES[cardboard]
    items = []
    total = 0.0

    def add(operation, formula, cost):
        nonlocal total
        items.append({"operation": operation, "formula": formula, "cost": cost})
        total += cost

    pre_cut = fd["preliminary_cut"] * tirazh
    formula = f"{fd['preliminary_cut']} × {tirazh}" if fd["preliminary_cut"] > 0 else "Не требуется"
    add("Предварительная резка", formula, pre_cut)

    if tirazh > 300:
        lift_price = fd["lifting_a4"] if format_val in ("A4", "A3") else fd["lifting_a5"]
        folding_cost = lift_price * signatures * tirazh
        folding_op = "Подъём"
        folding_formula = f"{lift_price} × {signatures} × {tirazh}"
    else:
        folding_cost = fd["folding"] * signatures * tirazh
        folding_op = "Фальцовка"
        folding_formula = f"{fd['folding']} × {signatures} × {tirazh}"
    add(folding_op, folding_formula, folding_cost)

    sewing_cost = (signatures * fd["sewing_multiplier"] * tirazh * fd["sewing_coefficient"]
                   + fd["sewing_fixed"])
    sewing_formula = (f"{signatures} × {fd['sewing_multiplier']} × {tirazh} "
                      f"× {fd['sewing_coefficient']} + {fd['sewing_fixed']}")
    add("Шитьё", sewing_formula, sewing_cost)

    add("Форзацы", f"{fd['endpapers']} × {tirazh}", fd["endpapers"] * tirazh)
    add("Приклейка форзацев", f"{fd['endpaper_gluing']} × {tirazh}", fd["endpaper_gluing"] * tirazh)
    add("Резка блока", f"{fd['block_cutting']} × {tirazh}", fd["block_cutting"] * tirazh)

    impregn_basic = fd["impregnation"] * tirazh
    impregn_cost = max(impregn_basic, fd["impregnation_minimum"])
    add("Промазка",
        f"max({fd['impregnation']} × {tirazh}, {fd['impregnation_minimum']})",
        impregn_cost)

    add("Обработка блока", f"{fd['block_processing']} × {tirazh}", fd["block_processing"] * tirazh)

    cardboard_cost = (price_karton / fd["cardboard_divisor"]) * tirazh
    add("Картон", f"{price_karton} ÷ {fd['cardboard_divisor']} × {tirazh}", cardboard_cost)

    cardboard_cut = (cardboard_cost / tirazh / 2) * tirazh
    add("Резка картона", f"{cardboard_cost / tirazh:.2f} ÷ 2 × {tirazh}", cardboard_cut)

    add("Крышка", f"{fd['cover']} × {tirazh}", fd["cover"] * tirazh)
    add("Вставка", f"{fd['insert']} × {tirazh}", fd["insert"] * tirazh)

    if cover_material == "bumvinil":
        add("Бумвинил", f"{fd['bumvinil']} × {tirazh}", fd["bumvinil"] * tirazh)

    if rounding:
        add("Кругление корешка", f"{fd['rounding']} × {tirazh}", fd["rounding"] * tirazh)
    else:
        add("Кругление корешка", "Не применяется", 0)

    add("Клей", f"{fd['glue']} × {tirazh}", fd["glue"] * tirazh)

    assembly_cost = folding_cost + sewing_cost
    items.append({
        "operation": "Сборка КШС",
        "formula": f"{folding_op} + Шитьё",
        "cost": assembly_cost,
        "is_summary": True,
    })

    manager_name = MANAGERS.get(manager, manager) if manager else ""

    return {
        "items": items,
        "total_cost": round(total, 2),
        "unit_price": round(total / tirazh, 2),
        "assembly_cost": round(assembly_cost, 2),
        "assembly_unit": round(assembly_cost / tirazh, 2),
        "params": {
            "manager": manager_name,
            "tirazh": tirazh,
            "format": format_val,
            "grammazh": grammazh,
            "polosy": polosy,
            "signatures": signatures,
            "rounding": rounding,
            "cardboard": CARDBOARD_LABELS.get(cardboard, cardboard),
            "cover_material": "Бумвинил" if cover_material == "bumvinil" else "Бумага",
            "cover_color": cover_color,
            "notes": notes,
        },
    }


# ─────────────────────────────────────────────
#  Генерация PDF
# ─────────────────────────────────────────────
def _fmt(number: float) -> str:
    s = f"{number:,.2f}"
    int_part, dec_part = s.split(".")
    int_part = int_part.replace(",", "\u00a0")
    return f"{int_part},{dec_part}"


def generate_pdf(result: dict, output_path: str) -> str:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    )
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    font_paths = [
        "/usr/share/fonts/truetype/dejavu",
        "C:\\Windows\\Fonts",
        "/System/Library/Fonts",
    ]
    for path in font_paths:
        normal_path = os.path.join(path, "DejaVuSans.ttf")
        bold_path = os.path.join(path, "DejaVuSans-Bold.ttf")
        if not os.path.exists(normal_path):
            normal_path = os.path.join(path, "arial.ttf")
            bold_path = os.path.join(path, "arialbd.ttf")
        if os.path.exists(normal_path) and os.path.exists(bold_path):
            pdfmetrics.registerFont(TTFont("DejaVu", normal_path))
            pdfmetrics.registerFont(TTFont("DejaVu-Bold", bold_path))
            pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold")
            break

    COLOR_CHARCOAL  = colors.Color(38/255, 40/255, 40/255)
    COLOR_GRAY_200  = colors.Color(245/255, 245/255, 245/255)
    COLOR_TEAL      = colors.Color(33/255, 128/255, 141/255)
    COLOR_SLATE_900 = colors.Color(19/255, 52/255, 59/255)

    def style(name, font="DejaVu", size=10, leading=14, color=COLOR_SLATE_900, bold=False, **kw):
        return ParagraphStyle(name, fontName="DejaVu-Bold" if bold else font,
                              fontSize=size, leading=leading, textColor=color, **kw)

    s_title   = style("title",   size=14, leading=18, bold=True)
    s_date    = style("date",    size=12, leading=16, bold=True, alignment=2)
    s_manager = style("manager", size=11, leading=15, bold=True)
    s_desc    = style("desc",    size=9,  leading=13)
    s_notes   = style("notes",   size=9,  leading=13, backColor=COLOR_GRAY_200,
                      borderPadding=(5, 6, 5, 6))
    s_section = style("section", size=11, leading=15, bold=True)
    s_cell    = style("cell",    size=9,  leading=12)
    s_cell_b  = style("cell_b",  size=9,  leading=12, bold=True)
    s_footer  = style("footer",  size=9,  leading=13)
    s_footer_b= style("footer_b",size=10, leading=14, bold=True)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=12*mm, bottomMargin=15*mm,
                            title="Расчёт 7БЦ")

    params = result["params"]
    story  = []
    W      = doc.width

    today = datetime.now().strftime("%d.%m.%Y")
    header_table = Table(
        [[Paragraph("Калькулятор стоимости брошюровки 7БЦ", s_title),
          Paragraph(today, s_date)]],
        colWidths=[W * 0.70, W * 0.30],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, COLOR_CHARCOAL),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 6*mm))

    if params["manager"]:
        story.append(Paragraph(f"Менеджер: {params['manager']}", s_manager))
        story.append(Spacer(1, 3*mm))

    rounding_txt = ", Кругление корешка: да" if params["rounding"] else ""
    desc = (f"Тираж: {params['tirazh']}, Формат: {params['format']}, "
            f"Полос (страниц): {params['polosy']}, Тетрадей: {params['signatures']}"
            f"{rounding_txt}, Картон: {params['cardboard']}, Обложка: {params['cover_material']}")
    story.append(Paragraph(desc, s_desc))
    story.append(Spacer(1, 3*mm))

    if params["notes"]:
        story.append(Paragraph(f"Заметки: {params['notes']}", s_notes))
        story.append(Spacer(1, 3*mm))

    story.append(Paragraph("Расчёт стоимости:", s_section))
    story.append(Spacer(1, 3*mm))

    col_op  = W * 0.35
    col_fml = W * 0.45
    col_sum = W * 0.20

    tbl_data = [[Paragraph("Операция", s_cell_b),
                 Paragraph("Расчёт", s_cell_b),
                 Paragraph("Стоимость, руб.", s_cell_b)]]

    summary_rows = []
    for i, item in enumerate(result["items"], start=1):
        is_summary = item.get("is_summary", False)
        cost_txt = _fmt(item["cost"]) if not is_summary else "= " + _fmt(item["cost"])
        cs = s_cell_b if is_summary else s_cell
        tbl_data.append([Paragraph(item["operation"], cs),
                         Paragraph(item["formula"], cs),
                         Paragraph(cost_txt, cs)])
        if is_summary:
            summary_rows.append(i)

    tbl = Table(tbl_data, colWidths=[col_op, col_fml, col_sum])
    tbl_style = [
        ("BACKGROUND",    (0, 0), (-1, 0),  COLOR_GRAY_200),
        ("FONTNAME",      (0, 0), (-1, 0),  "DejaVu-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("GRID",          (0, 0), (-1, -1), 0.5, COLOR_CHARCOAL),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
        ("ALIGN",         (2, 0), (2, -1),  "RIGHT"),
    ]
    TEAL_LIGHT = colors.Color(33/255, 128/255, 141/255, alpha=0.10)
    for r in summary_rows:
        tbl_style.append(("BACKGROUND", (0, r), (-1, r), TEAL_LIGHT))
        tbl_style.append(("LINEABOVE",  (0, r), (-1, r), 1.0, COLOR_TEAL))
    tbl.setStyle(TableStyle(tbl_style))
    story.append(tbl)
    story.append(Spacer(1, 5*mm))

    totals_data = [
        [Paragraph(f"Стоимость твёрдого переплёта: <b>{_fmt(result['total_cost'])}</b> руб.", s_footer_b), ""],
        [Paragraph(f"Цена за единицу: {_fmt(result['unit_price'])} руб.", s_footer), ""],
        [Paragraph(f"Стоимость сборки КШС: <b>{_fmt(result['assembly_cost'])}</b> руб.", s_footer_b), ""],
        [Paragraph(f"Цена сборки КШС за единицу: {_fmt(result['assembly_unit'])} руб.", s_footer), ""],
    ]
    totals_tbl = Table(totals_data, colWidths=[W * 0.80, W * 0.20])
    totals_tbl.setStyle(TableStyle([
        ("BOX",           (0, 0), (-1, -1), 1.5, COLOR_CHARCOAL),
        ("BACKGROUND",    (0, 0), (-1, -1), COLOR_GRAY_200),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("LINEBELOW",     (0, 1), (-1, 1),  0.5, COLOR_CHARCOAL),
        ("SPAN",          (0, 0), (-1, 0)),
        ("SPAN",          (0, 1), (-1, 1)),
        ("SPAN",          (0, 2), (-1, 2)),
        ("SPAN",          (0, 3), (-1, 3)),
    ]))
    story.append(totals_tbl)

    doc.build(story)
    return output_path


def generate_pdf_bytes(result: dict) -> bytes:
    """
    Генерирует PDF в памяти и возвращает bytes — без записи на диск.
    Используется в веб-интерфейсе (Streamlit Cloud и локально).
    """
    import io as _io
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    # Регистрация шрифтов (та же логика что в generate_pdf)
    font_paths = [
        "/usr/share/fonts/truetype/dejavu",
        "C:\\Windows\\Fonts",
        "/System/Library/Fonts",
    ]
    for path in font_paths:
        normal_path = os.path.join(path, "DejaVuSans.ttf")
        bold_path   = os.path.join(path, "DejaVuSans-Bold.ttf")
        if not os.path.exists(normal_path):
            normal_path = os.path.join(path, "arial.ttf")
            bold_path   = os.path.join(path, "arialbd.ttf")
        if os.path.exists(normal_path) and os.path.exists(bold_path):
            try:
                pdfmetrics.registerFont(TTFont("DejaVu", normal_path))
                pdfmetrics.registerFont(TTFont("DejaVu-Bold", bold_path))
                pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold")
            except Exception:
                pass  # шрифт уже зарегистрирован
            break

    COLOR_CHARCOAL  = colors.Color(38/255, 40/255, 40/255)
    COLOR_GRAY_200  = colors.Color(245/255, 245/255, 245/255)
    COLOR_TEAL      = colors.Color(33/255, 128/255, 141/255)
    COLOR_SLATE_900 = colors.Color(19/255, 52/255, 59/255)

    def style(name, font="DejaVu", size=10, leading=14, color=COLOR_SLATE_900, bold=False, **kw):
        return ParagraphStyle(name, fontName="DejaVu-Bold" if bold else font,
                              fontSize=size, leading=leading, textColor=color, **kw)

    s_title   = style("title2",   size=14, leading=18, bold=True)
    s_date    = style("date2",    size=12, leading=16, bold=True, alignment=2)
    s_manager = style("manager2", size=11, leading=15, bold=True)
    s_desc    = style("desc2",    size=9,  leading=13)
    s_notes   = style("notes2",   size=9,  leading=13, backColor=COLOR_GRAY_200,
                      borderPadding=(5, 6, 5, 6))
    s_section = style("section2", size=11, leading=15, bold=True)
    s_cell    = style("cell2",    size=9,  leading=12)
    s_cell_b  = style("cell_b2",  size=9,  leading=12, bold=True)
    s_footer  = style("footer2",  size=9,  leading=13)
    s_footer_b= style("footer_b2",size=10, leading=14, bold=True)

    # Ключевое отличие: пишем в BytesIO, не в файл
    buf = _io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=12*mm,  bottomMargin=15*mm,
                            title="Расчёт 7БЦ")

    params = result["params"]
    story  = []
    W      = doc.width

    today = datetime.now().strftime("%d.%m.%Y")
    header_table = Table(
        [[Paragraph("Калькулятор стоимости брошюровки 7БЦ", s_title),
          Paragraph(today, s_date)]],
        colWidths=[W * 0.70, W * 0.30],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN",      (0, 0), (-1, -1), "BOTTOM"),
        ("LINEBELOW",   (0, 0), (-1, 0),  1.5, COLOR_CHARCOAL),
        ("BOTTOMPADDING",(0, 0),(-1, 0),  6),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 6*mm))

    if params["manager"]:
        story.append(Paragraph(f"Менеджер: {params['manager']}", s_manager))
        story.append(Spacer(1, 3*mm))

    rounding_txt = ", Кругление корешка: да" if params["rounding"] else ""
    desc = (f"Тираж: {params['tirazh']}, Формат: {params['format']}, "
            f"Полос (страниц): {params['polosy']}, Тетрадей: {params['signatures']}"
            f"{rounding_txt}, Картон: {params['cardboard']}, Обложка: {params['cover_material']}")
    story.append(Paragraph(desc, s_desc))
    story.append(Spacer(1, 3*mm))

    if params["notes"]:
        story.append(Paragraph(f"Заметки: {params['notes']}", s_notes))
        story.append(Spacer(1, 3*mm))

    story.append(Paragraph("Расчёт стоимости:", s_section))
    story.append(Spacer(1, 3*mm))

    col_op  = W * 0.35
    col_fml = W * 0.45
    col_sum = W * 0.20

    tbl_data = [[Paragraph("Операция", s_cell_b),
                 Paragraph("Расчёт", s_cell_b),
                 Paragraph("Стоимость, руб.", s_cell_b)]]

    summary_rows = []
    for idx, item in enumerate(result["items"], start=1):
        is_summary = item.get("is_summary", False)
        cost_txt   = _fmt(item["cost"]) if not is_summary else "= " + _fmt(item["cost"])
        cs = s_cell_b if is_summary else s_cell
        tbl_data.append([Paragraph(item["operation"], cs),
                         Paragraph(item["formula"],   cs),
                         Paragraph(cost_txt,          cs)])
        if is_summary:
            summary_rows.append(idx)

    tbl = Table(tbl_data, colWidths=[col_op, col_fml, col_sum])
    tbl_style = [
        ("BACKGROUND",    (0, 0), (-1, 0),  COLOR_GRAY_200),
        ("FONTNAME",      (0, 0), (-1, 0),  "DejaVu-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("GRID",          (0, 0), (-1, -1), 0.5, COLOR_CHARCOAL),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
        ("ALIGN",         (2, 0), (2, -1),  "RIGHT"),
    ]
    TEAL_LIGHT = colors.Color(33/255, 128/255, 141/255, alpha=0.10)
    for r in summary_rows:
        tbl_style.append(("BACKGROUND", (0, r), (-1, r), TEAL_LIGHT))
        tbl_style.append(("LINEABOVE",  (0, r), (-1, r), 1.0, COLOR_TEAL))
    tbl.setStyle(TableStyle(tbl_style))
    story.append(tbl)
    story.append(Spacer(1, 5*mm))

    totals_data = [
        [Paragraph(f"Стоимость твёрдого переплёта: <b>{_fmt(result['total_cost'])}</b> руб.", s_footer_b), ""],
        [Paragraph(f"Цена за единицу: {_fmt(result['unit_price'])} руб.", s_footer), ""],
        [Paragraph(f"Стоимость сборки КШС: <b>{_fmt(result['assembly_cost'])}</b> руб.", s_footer_b), ""],
        [Paragraph(f"Цена сборки КШС за единицу: {_fmt(result['assembly_unit'])} руб.", s_footer), ""],
    ]
    totals_tbl = Table(totals_data, colWidths=[W * 0.80, W * 0.20])
    totals_tbl.setStyle(TableStyle([
        ("BOX",           (0, 0), (-1, -1), 1.5, COLOR_CHARCOAL),
        ("BACKGROUND",    (0, 0), (-1, -1), COLOR_GRAY_200),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("LINEBELOW",     (0, 1), (-1, 1),  0.5, COLOR_CHARCOAL),
        ("SPAN",          (0, 0), (-1, 0)),
        ("SPAN",          (0, 1), (-1, 1)),
        ("SPAN",          (0, 2), (-1, 2)),
        ("SPAN",          (0, 3), (-1, 3)),
    ]))
    story.append(totals_tbl)

    doc.build(story)
    return buf.getvalue()  # возвращаем bytes, не путь


# ─────────────────────────────────────────────
#  @tool обёртка
# ─────────────────────────────────────────────
def _make_tool():
    from smolagents import tool

    @tool
    def calculate_bc7_binding(
        tirazh: int,
        format_val: str,
        grammazh: int,
        polosy: int,
        rounding: bool = False,
        cardboard: str = "2.0",
        cover_material: str = "paper",
        cover_color: str = "0",
        manager: str = "",
        notes: str = "",
    ) -> dict:
        """
        Рассчитывает стоимость брошюровки 7БЦ (твёрдый переплёт) и создаёт PDF-отчёт.

        Args:
            tirazh: Тираж в штуках.

            format_val: Формат блока — "A4", "A5", "A3", "A6".
                Нестандартные размеры округлять до ближайшего:
                205×290 мм → "A4", 145×205 мм → "A5".

            grammazh: Плотность бумаги блока в г/м². Определяет страниц в тетради:
                менее 100 г/м²  → 24 стр/тетрадь
                100–129 г/м²   → 16 стр/тетрадь
                130 г/м² и выше → 8 стр/тетрадь

            polosy: Общее количество страниц (полос) в блоке.
                ВАЖНО: "страницы" и "полосы" — одно и то же понятие!
                Если написано "240 страниц" или "240 полос" — передавать polosy=240.
                НЕ удваивать и НЕ делить пополам.

            rounding: Кругление корешка.
                True  — только если в запросе явно написано "кругление" или "круглый корешок".
                False — если "прямой корешок", "без кругления", или не упомянуто (DEFAULT).

            cardboard: Толщина переплётного картона — "1.5", "1.75", "2.0", "2.5".
                ПРАВИЛО: если толщина в запросе НЕ указана явно — ВСЕГДА использовать "2.0".
                Не угадывать и не выбирать другое значение по умолчанию.

            cover_material: Материал крышки переплёта. Принимает ТОЛЬКО два значения:
                "paper"   — бумажная крышка (меловка, офсет, дизайнерская бумага, картон).
                            Использовать "paper" если обложка описана как:
                            • меловка (любой граммаж: 115, 130, 150, 200, 250 г/м²)
                            • офсет на обложку
                            • картон
                            • "плёнка глянцевая / матовая" (плёнка = ламинация поверх бумаги,
                              а не материал крышки — передать в notes)
                            • "ламинация 75 мкм / 125 мкм" (аналогично — это отделка, не материал)
                "bumvinil" — крышка из бумвинила (виниловое или тканевое покрытие).
                            Использовать "bumvinil" ТОЛЬКО если в запросе написано слово
                            "бумвинил" или "bumvinil".
                ЧАСТАЯ ОШИБКА: "плёнка глянцевая" ≠ бумвинил! Плёнка — это ламинация
                поверх бумажной обложки. cover_material при этом остаётся "paper".

            cover_color: Цветность печати обложки.
                "41"  ← "4+1"   (полноцвет лицо + чёрно-белая оборот)
                "40"  ← "4+0"   (полноцвет одна сторона)
                "44"  ← "4+4"   (полноцвет обе стороны)
                "10"  ← "1+0"   (чёрно-белая одна сторона)
                "0"   ← без печати, непечатная обложка (DEFAULT)
                Бумвинил — всегда без печати, поэтому при cover_material="bumvinil"
                использовать cover_color="0".

            manager: Ключ или имя менеджера (необязательно).
                Если запрос содержит подпись ("С уважением, ...", "Всегда рада, ...") —
                извлечь имя и передать сюда.
                Поддерживаемые ключи: vladimirova, dmitriev, dustova, minenkov,
                kursanov, pokrovskaja, salnikova, hokhlova, feoktistova, chistyakova.
                "Лидия Чистякова", "Чистякова" → manager="chistyakova".
                Если имя не в списке — передать как есть.

            notes: Заметки для менеджера — материалы, отделка, пожелания клиента.
                Сюда записывать: граммаж и цветность обложки, тип плёнки/ламинации,
                описание форзацев, любые детали из запроса которые не влияют
                на расчёт напрямую.
                Пример: "Обложка меловка 150 г/м² 4+1, плёнка глянцевая.
                         Форзацы офсет 120 г/м², непечатные."

        Returns:
            Словарь с результатами расчёта. Ключ "pdf_bytes" содержит PDF как bytes
            для отображения в браузере без сохранения на диск.

        Примеры разбора запросов:

            Запрос: "Формат 205×290, объём 240 с., офсет 80 г/м² 1+1,
                     форзацы офсет 120 г/м² непечатные, обложка меловка 150 г/м² 4+1,
                     корешок прямой, плёнка глянцевая, тираж 20 экз. Лидия Чистякова"
            Результат:
                tirazh=20, format_val="A4", grammazh=80, polosy=240,
                rounding=False,        ← "корешок прямой"
                cardboard="2.0",       ← не указана → по умолчанию
                cover_material="paper",← меловка = бумага, НЕ бумвинил!
                cover_color="41",      ← "4+1"
                manager="chistyakova", ← из подписи
                notes="Обложка меловка 150 г/м² 4+1, плёнка глянцевая. Форзацы офсет 120 г/м², непечатные."

            Запрос: "А5, 160 стр., бумвинил, тираж 500 шт., картон 1.75"
            Результат:
                tirazh=500, format_val="A5", grammazh=80, polosy=160,
                rounding=False,
                cardboard="1.75",      ← явно указан
                cover_material="bumvinil", ← явно написано "бумвинил"
                cover_color="0",       ← бумвинил всегда без печати
                notes=""
        """
        manager_cyrillic = _normalize_manager_name(manager)

        result = calculate_bc7(
            tirazh=tirazh,
            format_val=format_val,
            grammazh=grammazh,
            polosy=polosy,
            rounding=rounding,
            cardboard=cardboard,
            cover_material=cover_material,
            cover_color=cover_color,
            manager=manager,
            notes=notes,
        )

        if "ошибка" in result:
            return result

        # Генерируем PDF в памяти — диск не используется совсем
        date_str  = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename  = f"bc7_{date_str}_{_manager_filename(manager_cyrillic)}.pdf"
        pdf_bytes = generate_pdf_bytes(result)

        return {
            "тип_продукции": "Брошюровка 7БЦ",
            "тираж": tirazh,
            "формат": format_val,
            "граммаж": grammazh,
            "полосы": polosy,
            "тетрадей": result["params"]["signatures"],
            "картон": result["params"]["cardboard"],
            "материал": result["params"]["cover_material"],
            "цветность_обложки": cover_color,
            "кругление": "Да" if rounding else "Нет",
            "менеджер": manager_cyrillic,
            "полная_стоимость": f"{result['total_cost']:.2f} руб.",
            "цена_за_единицу": f"{result['unit_price']:.2f} руб.",
            "сборка_КШС_итог": f"{result['assembly_cost']:.2f} руб.",
            "сборка_КШС_ед": f"{result['assembly_unit']:.2f} руб.",
            # pdf_bytes передаётся в app.py для отображения в браузере
            "pdf_bytes": pdf_bytes,
            "pdf_filename": filename,
        }

    return calculate_bc7_binding


try:
    calculate_bc7_binding = _make_tool()
except ImportError:
    calculate_bc7_binding = None


# ─────────────────────────────────────────────
#  Быстрый тест
# ─────────────────────────────────────────────
if __name__ == "__main__":
    r = calculate_bc7(
        tirazh=500, format_val="A4", grammazh=80, polosy=192,
        rounding=True, cardboard="2.0", cover_material="bumvinil",
        manager="vladimirova", notes="Срочный заказ",
    )
    print(f"Итого: {r['total_cost']:.2f} руб.  /  {r['unit_price']:.2f} руб/шт")
