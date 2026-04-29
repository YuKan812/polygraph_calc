# Инструмент: calculate_lamination

<!-- keywords: ламинация, ламинировать, глянец, матовая, софттач, плёнка, 75 мкм, 125 мкм, покрытие -->

## Когда использовать

Ламинация — защитное покрытие поверхности листов после печати.
Типовые запросы: "добавь ламинацию", "глянцевая ламинация", "матовая", "плёнка 75 мкм", "softouch".

## ВАЖНО: "матовая бумага" ≠ "матовая ламинация"

- "печать на матовой бумаге" → параметр grammage/material_name в инструменте печати
- "добавь матовую ламинацию" → инструмент calculate_lamination, type="standard"
- "матовый softouch" → lamination_type="softtouch"

## КРИТИЧНО: sheets_quantity — это листы из печати, НЕ тираж изделий

```python
# ПРАВИЛЬНО:
print_result = calculate_digital_printing(...)
lam_result = calculate_lamination(
    sheets_quantity=print_result["количество_листов_а3"]  # ← из печати!
)

# НЕПРАВИЛЬНО:
lam_result = calculate_lamination(sheets_quantity=tirazh)  # ← нельзя!
```

Если печати не было — вычислить: `sheets = math.ceil(tirazh / items_per_sheet)`

## Параметры

- lamination_type: тип ламинации
  - "standard" — глянцевая ИЛИ матовая (цена одинакова)
  - "softtouch" — мягкая сенсорная (бархатистая)
  - "75" — плёночная ламинация 75 мкм
  - "125" — плёночная ламинация 125 мкм
- sides: стороны
  - "1+0" — одна сторона (лицевая)
  - "1+1" — обе стороны
- sheets_quantity: количество листов А3+ из результата печати

## Интерпретация типа ламинации

- "глянцевая", "глянец" → lamination_type="standard"
- "матовая" (не softouch) → lamination_type="standard"
- "стандартная" → lamination_type="standard"
- "софттач", "softtouch", "мягкая", "бархатистая" → lamination_type="softtouch"
- "75", "75 мкм", "плёнка 75" → lamination_type="75"
- "125", "125 мкм", "плёнка 125" → lamination_type="125"
- Не указан → lamination_type="standard"

## Интерпретация сторон

- "одна сторона", "лицевая", "снаружи" → sides="1+0"
- "две стороны", "с обеих сторон", "1+1" → sides="1+1"
- Типы "75" и "125" — всегда sides="1+1" (цена включает обе стороны)
- Не указано → sides="1+0"

## Возвращает

```python
{
    "unit_price": 4.2,        # цена за сторону листа А3+
    "sides_multiplier": 1,
    "sheets_quantity": 250,
    "raw_cost": 1050.0,
    "min_price": 280.0,
    "total_cost": 1050.0      # ← итоговая стоимость ламинации
}
```

## Пример: добавить ламинацию глянец к предыдущей печати

```python
# sheets берётся из предыдущего расчёта печати
lam = calculate_lamination(
    lamination_type="standard",
    sides="1+0",
    sheets_quantity=print_result["количество_листов_а3"]
)
total = print_result["общая_стоимость"] + lam["total_cost"]
cost_per_unit = total / tirazh
```

## Пример: только ламинация, без печати

```python
import math
layout = calculate_layout(piece_width=210, piece_height=297)
items = layout["items_per_sheet"]
sheets = math.ceil(tirazh / items)

lam = calculate_lamination(
    lamination_type="softtouch",
    sides="1+1",
    sheets_quantity=sheets
)
```

## Пример: плёночная ламинация 75 мкм

```python
lam = calculate_lamination(
    lamination_type="75",
    sides="1+1",  # всегда 1+1 для плёнки
    sheets_quantity=print_result["количество_листов_а3"]
)
```
