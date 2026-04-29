"""
Расчёт стоимости брошюровки 7БЦ (твёрдый переплёт).
Порт JavaScript-калькулятора bc7_TF.html → Python + генерация PDF через reportlab.
"""

import os
import math
from datetime import datetime

# ─────────────────────────────────────────────
#  Данные для расчётов (перенесены из app.js)
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
    """Возвращает имя менеджера в кириллице, если ключ известен."""
    manager = (manager or "").strip()
    if not manager:
        return ""
    for key, value in MANAGERS.items():
        if manager.lower() == key.lower() or manager.lower() == value.lower():
            return value
    return manager


def _manager_filename(manager_name: str) -> str:
    """Форматирует имя менеджера для имени файла: фамилия без инициалов."""
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
    """
    Рассчитывает стоимость брошюровки 7БЦ (твёрдый переплёт).

    ⚠️ ВАЖНО: Параметр 'polosy' (полосы) — это ОБЩЕЕ КОЛИЧЕСТВО СТРАНИЦ в блоке.
    Понятия "полосы" и "страницы" в полиграфии — ОДНО И ТО ЖЕ!
    Если в описании говорится "40 страниц" или "40 полос" — оба означают polosy=40 (не удваивайте!).

    Параметры
    ----------
    tirazh        : тираж (штук)
    format_val    : формат блока — "A4", "A5", "A3", "A6"
    grammazh      : плотность бумаги (г/м²) — определяет страниц в тетради:
                    < 100 г/м² → 24 стр/тетрадь
                    100–129 г/м² → 16 стр/тетрадь
                    ≥ 130 г/м² → 8 стр/тетрадь
    polosy        : ОБЩЕЕ КОЛИЧЕСТВО ПОЛОС (СТРАНИЦ) в блоке (ОДНО И ТО ЖЕ!)
                    Используется: signatures = ceil(polosy / стр_в_тетради)
    rounding      : кругление корешка (True / False)
    cardboard     : толщина картона — "1.5", "1.75", "2.0", "2.5"
    cover_material: материал обложки — "bumvinil" или "paper"
    cover_color   : цветность печати обложки (например, "41" для 4+1, "0" для без печати)
    manager       : ключ или имя менеджера (необязательно)
    notes         : произвольные заметки (необязательно)

    Возвращает
    ----------
    dict с ключами:
      "items"            — список строк расчёта (operation, formula, cost)
      "total_cost"       — итог брошюровки 7БЦ
      "unit_price"       — цена за единицу
      "assembly_cost"    — стоимость сборки КШС (фальцовка/подъём + шитьё)
      "assembly_unit"    — цена сборки КШС за единицу
      "params"           — сводка параметров для отчёта
    
    Пример
    ------
    >>> result = calculate_bc7(
    ...     tirazh=100,
    ...     format_val="A4",
    ...     grammazh=80,
    ...     polosy=40,      # ← 40 полос = 40 страниц! Не удваивайте!
    ...     cover_color="40"
    ... )
    """
    if format_val not in CALCULATION_DATA:
        return {"ошибка": f"Неизвестный формат: {format_val}. Допустимые: A3, A4, A5, A6"}
    if cardboard not in CARDBOARD_PRICES:
        return {"ошибка": f"Неизвестный картон: {cardboard}. Допустимые: 1.5, 1.75, 2.0, 2.5"}
    if tirazh < 1 or grammazh < 1 or polosy < 1:
        return {"ошибка": "Тираж, граммаж и количество полос должны быть >= 1"}

    # Расчёт количества тетрадей на основе граммажа
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

    # 1. Предварительная резка
    pre_cut = fd["preliminary_cut"] * tirazh
    formula = f"{fd['preliminary_cut']} × {tirazh}" if fd["preliminary_cut"] > 0 else "Не требуется"
    add("Предварительная резка", formula, pre_cut)

    # 2. Фальцовка / Подъём
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

    # 3. Шитьё
    sewing_cost = (signatures * fd["sewing_multiplier"] * tirazh * fd["sewing_coefficient"]
                   + fd["sewing_fixed"])
    sewing_formula = (f"{signatures} × {fd['sewing_multiplier']} × {tirazh} "
                      f"× {fd['sewing_coefficient']} + {fd['sewing_fixed']}")
    add("Шитьё", sewing_formula, sewing_cost)

    # 4. Форзацы
    add("Форзацы", f"{fd['endpapers']} × {tirazh}", fd["endpapers"] * tirazh)

    # 5. Приклейка форзацев
    add("Приклейка форзацев", f"{fd['endpaper_gluing']} × {tirazh}", fd["endpaper_gluing"] * tirazh)

    # 6. Резка блока
    add("Резка блока", f"{fd['block_cutting']} × {tirazh}", fd["block_cutting"] * tirazh)

    # 7. Промазка
    impregn_basic = fd["impregnation"] * tirazh
    impregn_cost = max(impregn_basic, fd["impregnation_minimum"])
    add("Промазка",
        f"max({fd['impregnation']} × {tirazh}, {fd['impregnation_minimum']})",
        impregn_cost)

    # 8. Обработка блока
    add("Обработка блока", f"{fd['block_processing']} × {tirazh}", fd["block_processing"] * tirazh)

    # 9. Картон
    cardboard_cost = (price_karton / fd["cardboard_divisor"]) * tirazh
    add("Картон",
        f"{price_karton} ÷ {fd['cardboard_divisor']} × {tirazh}",
        cardboard_cost)

    # 10. Резка картона
    cardboard_cut = (cardboard_cost / tirazh / 2) * tirazh
    add("Резка картона",
        f"{cardboard_cost / tirazh:.2f} ÷ 2 × {tirazh}",
        cardboard_cut)

    # 11. Крышка
    add("Крышка", f"{fd['cover']} × {tirazh}", fd["cover"] * tirazh)

    # 12. Вставка
    add("Вставка", f"{fd['insert']} × {tirazh}", fd["insert"] * tirazh)

    # 13. Бумвинил (только если материал обложки — бумвинил)
    if cover_material == "bumvinil":
        bumvinil_cost = fd["bumvinil"] * tirazh
        bumvinil_formula = f"{fd['bumvinil']} × {tirazh}"
        add("Бумвинил", bumvinil_formula, bumvinil_cost)
    # Если cover_material == "paper", бумвинил не добавляется вообще

    # 14. Кругление корешка
    if rounding:
        rounding_cost = fd["rounding"] * tirazh
        rounding_formula = f"{fd['rounding']} × {tirazh}"
    else:
        rounding_cost = 0
        rounding_formula = "Не применяется"
    add("Кругление корешка", rounding_formula, rounding_cost)

    # 15. Клей
    add("Клей", f"{fd['glue']} × {tirazh}", fd["glue"] * tirazh)

    # 16. Сборка КШС (справочная строка, НЕ прибавляется к итогу повторно)
    assembly_cost = folding_cost + sewing_cost
    items.append({
        "operation": "Сборка КШС",
        "formula": f"{folding_op} + Шитьё",
        "cost": assembly_cost,
        "is_summary": True,   # маркер: не суммировать дважды
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
    """Форматирует число в рублях: 1 234,56"""
    s = f"{number:,.2f}"
    # Python использует запятую для тысяч — нужен пробел + запятая для копеек
    int_part, dec_part = s.split(".")
    int_part = int_part.replace(",", "\u00a0")   # неразрывный пробел
    return f"{int_part},{dec_part}"


def generate_pdf(result: dict, output_path: str) -> str:
    """
    Генерирует PDF-отчёт из результата calculate_bc7().

    Параметры
    ----------
    result      : возвращаемое значение calculate_bc7()
    output_path : путь к выходному PDF-файлу

    Возвращает полный путь к созданному файлу.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    # ── Регистрация шрифтов с поддержкой кириллицы ──────────────────────────
    font_paths = [
        "/usr/share/fonts/truetype/dejavu",
        "C:\\Windows\\Fonts",
        "/System/Library/Fonts",
        os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts"),
    ]

    font_found = False
    for path in font_paths:
        normal_path = os.path.join(path, "DejaVuSans.ttf")
        bold_path = os.path.join(path, "DejaVuSans-Bold.ttf")
        
        # На Windows DejaVu может не быть, пробуем Arial как альтернативу
        if not os.path.exists(normal_path):
            normal_path = os.path.join(path, "arial.ttf")
            bold_path = os.path.join(path, "arialbd.ttf")

        if os.path.exists(normal_path) and os.path.exists(bold_path):
            pdfmetrics.registerFont(TTFont("DejaVu", normal_path))
            pdfmetrics.registerFont(TTFont("DejaVu-Bold", bold_path))
            pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold")
            font_found = True
            break

    if not font_found:
        # Если ничего не нашли, используем стандартные шрифты (могут быть проблемы с кириллицей)
        pass

    # ── Цвета из style.css ───────────────────────────────────────────────────
    COLOR_CHARCOAL  = colors.Color(38/255, 40/255, 40/255)     # --color-charcoal-800
    COLOR_GRAY_200  = colors.Color(245/255, 245/255, 245/255)  # --color-gray-200
    COLOR_TEAL      = colors.Color(33/255, 128/255, 141/255)   # --color-teal-500
    COLOR_SLATE_900 = colors.Color(19/255, 52/255, 59/255)     # --color-slate-900

    # ── Стили параграфов ─────────────────────────────────────────────────────
    def style(name, font="DejaVu", size=10, leading=14, color=COLOR_SLATE_900, bold=False, **kw):
        return ParagraphStyle(
            name,
            fontName="DejaVu-Bold" if bold else font,
            fontSize=size,
            leading=leading,
            textColor=color,
            **kw,
        )

    s_title   = style("title",   size=14, leading=18, bold=True)
    s_date    = style("date",    size=12, leading=16, bold=True, alignment=2)  # right
    s_manager = style("manager", size=11, leading=15, bold=True)
    s_desc    = style("desc",    size=9,  leading=13)
    s_notes   = style("notes",   size=9,  leading=13, backColor=COLOR_GRAY_200,
                      borderPadding=(5, 6, 5, 6))
    s_section = style("section", size=11, leading=15, bold=True)
    s_cell    = style("cell",    size=9,  leading=12)
    s_cell_b  = style("cell_b",  size=9,  leading=12, bold=True)
    s_footer  = style("footer",  size=9,  leading=13)
    s_footer_b= style("footer_b",size=10, leading=14, bold=True)

    # ── Документ ─────────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=12*mm,  bottomMargin=15*mm,
        title="Расчёт 7БЦ",
    )

    params = result["params"]
    story  = []
    W      = doc.width   # ширина рабочей зоны

    # ── 1. Шапка: название + дата ─────────────────────────────────────────
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

    # ── 2. Менеджер ──────────────────────────────────────────────────────
    if params["manager"]:
        story.append(Paragraph(f"Менеджер: {params['manager']}", s_manager))
        story.append(Spacer(1, 3*mm))

    # ── 3. Параметры расчёта ─────────────────────────────────────────────
    rounding_txt = ", Кругление корешка: да" if params["rounding"] else ""
    desc = (
        f"Тираж: {params['tirazh']}, "
        f"Формат: {params['format']}, "
        f"Полос (страниц): {params['polosy']}, "
        f"Тетрадей: {params['signatures']}"
        f"{rounding_txt}, "
        f"Картон: {params['cardboard']}, "
        f"Обложка: {params['cover_material']}"
    )
    story.append(Paragraph(desc, s_desc))
    story.append(Spacer(1, 3*mm))

    # ── 4. Заметки ───────────────────────────────────────────────────────
    if params["notes"]:
        story.append(Paragraph(f"Заметки: {params['notes']}", s_notes))
        story.append(Spacer(1, 3*mm))

    # ── 5. Заголовок таблицы ─────────────────────────────────────────────
    story.append(Paragraph("Расчёт стоимости:", s_section))
    story.append(Spacer(1, 3*mm))

    # ── 6. Таблица расчётов ──────────────────────────────────────────────
    col_op  = W * 0.35
    col_fml = W * 0.45
    col_sum = W * 0.20

    tbl_data = [[
        Paragraph("Операция", s_cell_b),
        Paragraph("Расчёт", s_cell_b),
        Paragraph("Стоимость, руб.", s_cell_b),
    ]]

    summary_rows = []   # индексы строк-справок (КШС)

    for i, item in enumerate(result["items"], start=1):
        is_summary = item.get("is_summary", False)
        cost_txt = _fmt(item["cost"]) if not is_summary else "= " + _fmt(item["cost"])
        cs = s_cell_b if is_summary else s_cell
        tbl_data.append([
            Paragraph(item["operation"], cs),
            Paragraph(item["formula"],   cs),
            Paragraph(cost_txt,          cs),
        ])
        if is_summary:
            summary_rows.append(i)

    tbl = Table(tbl_data, colWidths=[col_op, col_fml, col_sum])

    tbl_style = [
        # Шапка
        ("BACKGROUND",   (0, 0), (-1, 0),  COLOR_GRAY_200),
        ("FONTNAME",     (0, 0), (-1, 0),  "DejaVu-Bold"),
        ("FONTSIZE",     (0, 0), (-1, -1), 9),
        # Общее
        ("GRID",         (0, 0), (-1, -1), 0.5, COLOR_CHARCOAL),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ("LEFTPADDING",  (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        # Выравнивание суммы вправо
        ("ALIGN",        (2, 0), (2, -1),  "RIGHT"),
    ]

    # Строки КШС — лёгкий голубоватый фон
    TEAL_LIGHT = colors.Color(33/255, 128/255, 141/255, alpha=0.10)
    for r in summary_rows:
        tbl_style.append(("BACKGROUND", (0, r), (-1, r), TEAL_LIGHT))
        tbl_style.append(("LINEABOVE",  (0, r), (-1, r), 1.0, COLOR_TEAL))

    tbl.setStyle(TableStyle(tbl_style))
    story.append(tbl)
    story.append(Spacer(1, 5*mm))

    # ── 7. Итоги ─────────────────────────────────────────────────────────
    totals_data = [
        [Paragraph(
            f"Стоимость твёрдого переплёта: <b>{_fmt(result['total_cost'])}</b> руб.",
            s_footer_b), ""],
        [Paragraph(
            f"Цена за единицу: {_fmt(result['unit_price'])} руб.",
            s_footer), ""],
        [Paragraph(
            f"Стоимость сборки КШС: <b>{_fmt(result['assembly_cost'])}</b> руб.",
            s_footer_b), ""],
        [Paragraph(
            f"Цена сборки КШС за единицу: {_fmt(result['assembly_unit'])} руб.",
            s_footer), ""],
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

    # ── Сборка ───────────────────────────────────────────────────────────
    doc.build(story)
    return output_path


# ─────────────────────────────────────────────
#  @tool обёртка для smolagents
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
        save_path: str = "",
    ) -> dict:
        """
        Рассчитывает стоимость брошюровки 7БЦ (твёрдый переплёт) и создаёт PDF-отчёт.

        ⚠️ КРИТИЧНО: Параметр 'polosy' (полосы) — это ОБЩЕЕ КОЛИЧЕСТВО СТРАНИЦ в блоке!
        Понятия "полосы" и "страницы" в полиграфии — ОДНО И ТО ЖЕ!
        НЕ путайте и НЕ удваивайте значение (например, "32 страницы (64 полосы)" → это ошибка!
        Должно быть polosy=32, а не 64).

        Args:
            tirazh        : тираж (штук)
            format_val    : формат блока — "A4", "A5", "A3" или "A6"
            grammazh      : плотность бумаги (г/м²) — определяет страниц в тетради
            polosy        : ОБЩЕЕ КОЛИЧЕСТВО ПОЛОС (СТРАНИЦ) в блоке — ОДНО И ТО ЖЕ!
                            Пример: polosy=40 означает 40 страниц (полос)
            rounding      : кругление корешка True/False (по умолчанию False)
            cardboard     : толщина картона — "1.5", "1.75", "2.0" или "2.5" мм
            cover_material: материал обложки — "bumvinil" (бумвинил) или "paper" (бумага)
            cover_color   : цветность печати обложки (например, "41" для 4+1, "0" для без)
            manager       : имя или ключ менеджера (опционально)
            notes         : дополнительные заметки (опционально)
            save_path     : путь для сохранения PDF (если не указан, сохранится в папку output)

        Returns:
            Словарь с подробными результатами расчета и путем к PDF.
        """
        import os
        
        # Обработка имени менеджера (поддержка ключей и кириллицы)
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

        # Формирование имени файла: bc7_YYYY-MM-DD_HH-MM-SS_Фамилия.pdf
        date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        manager_filename = _manager_filename(manager_cyrillic)
        filename = f"bc7_{date_str}_{manager_filename}.pdf"

        # Определение пути сохранения
        if save_path:
            # Если указана папка, добавляем имя файла
            if os.path.isdir(save_path):
                final_pdf_path = os.path.join(save_path, filename)
            else:
                final_pdf_path = save_path
        else:
            base = os.path.dirname(os.path.abspath(__file__))
            out_dir = os.path.join(base, "output")
            os.makedirs(out_dir, exist_ok=True)
            final_pdf_path = os.path.join(out_dir, filename)

        generate_pdf(result, final_pdf_path)

        # Открываем PDF в системном просмотрщике
        try:
            import os
            os.startfile(final_pdf_path)
        except Exception as e:
            print(f"Не удалось открыть PDF: {e}")

        # ═══════════════════════════════════════════════════════════════════
        # Вывод результатов в терминал
        # ═══════════════════════════════════════════════════════════════════
        print("\n" + "═" * 70)
        print("✓ РАСЧЁТ БРОШЮРОВКИ 7БЦ")
        print("═" * 70)
        print(f"Тип: Брошюровка 7БЦ (твёрдый переплёт)")
        print(f"Тираж: {tirazh} шт.")
        print(f"Формат: {format_val}")
        print(f"Граммаж бумаги: {grammazh} г/м²")
        print(f"Количество полос (страниц): {polosy} ← одно и то же!")
        print(f"Тетрадей: {result['params']['signatures']}")
        print(f"Картон: {result['params']['cardboard']}")
        print(f"Материал обложки: {result['params']['cover_material']}")
        print(f"Цветность обложки: {cover_color}")
        print(f"Кругление корешка: {'Да' if rounding else 'Нет'}")
        print(f"Менеджер: {manager_cyrillic if manager_cyrillic else '—'}")
        if notes:
            print(f"Заметки: {notes}")
        print("─" * 70)
        print(f"📊 ИТОГОВАЯ СТОИМОСТЬ: {result['total_cost']:.2f} руб.")
        print(f"   Цена за единицу: {result['unit_price']:.2f} руб./шт")
        print(f"📊 СБОРКА КШС: {result['assembly_cost']:.2f} руб.")
        print(f"   Цена за единицу: {result['assembly_unit']:.2f} руб./шт")
        print("─" * 70)
        print(f"💾 PDF сохранён: {final_pdf_path}")
        print("═" * 70 + "\n")

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
            "pdf_path": final_pdf_path,
        }

    return calculate_bc7_binding


try:
    calculate_bc7_binding = _make_tool()
except ImportError:
    # smolagents не установлен — используем как обычный модуль
    calculate_bc7_binding = None


# ─────────────────────────────────────────────
#  Быстрый тест
# ─────────────────────────────────────────────
if __name__ == "__main__":
    r = calculate_bc7(
        tirazh=500,
        format_val="A4",
        grammazh=80,
        polosy=192,
        rounding=True,
        cardboard="2.0",
        cover_material="bumvinil",
        manager="vladimirova",
        notes="Срочный заказ, клиент ждёт к пятнице",
    )

    print(f"Итого: {r['total_cost']:.2f} руб.  /  {r['unit_price']:.2f} руб/шт")
    print(f"КШС: {r['assembly_cost']:.2f} руб.  /  {r['assembly_unit']:.2f} руб/шт")

    save_input = input("Куда сохранить PDF? Оставьте пустым для папки output: ").strip()
    if save_input:
        save_input = os.path.expanduser(save_input)
        if os.path.isdir(save_input):
            filename = f"bc7_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_{_manager_filename(_normalize_manager_name(r['params']['manager']))}.pdf"
            pdf_path = os.path.join(save_input, filename)
        else:
            pdf_path = save_input
    else:
        base = os.path.dirname(os.path.abspath(__file__))
        out_dir = os.path.join(base, "output")
        os.makedirs(out_dir, exist_ok=True)
        filename = f"bc7_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_{_manager_filename(_normalize_manager_name(r['params']['manager']))}.pdf"
        pdf_path = os.path.join(out_dir, filename)

    pdf = generate_pdf(r, pdf_path)
    print(f"PDF сохранён: {pdf}")

    # Открываем PDF в системном просмотрщике
    try:
        import os
        os.startfile(pdf_path)
    except Exception as e:
        print(f"Не удалось открыть PDF: {e}")
