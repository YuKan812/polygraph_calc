# Инструмент: calculate_digital_printing

<!-- keywords: цифровая печать, цифра, полноцвет, ч/б, черно-белая, 4+4, 4+0, 1+1, 1+0, inkjet, laser -->

## Когда использовать

Цифровая печать — малые и средние тиражи, полноцвет, быстрые сроки.
Типовые запросы: "цифровая печать", "напечатать 100 листов", "полноцвет 4+4".

## Обязательный порядок

1. calculate_layout → получить items_per_sheet
2. calculate_digital_printing(tirazh, items_per_sheet, ...)
3. "количество_листов_а3" передать в calculate_lamination если нужна ламинация

## Параметры

- tirazh: количество экземпляров изделий
- items_per_sheet: из результата calculate_layout (или 1 для SRA3/А3+)
- colorness: цветность печати
  - "40" — 4+0 (полноцвет одна сторона)
  - "44" — 4+4 (полноцвет две стороны)
  - "10" — 1+0 (ч/б одна сторона)
  - "11" — 1+1 (ч/б две стороны)
  - "41" — 4+1 (полноцвет + ч/б)
- paper_price: цена листа А3 в рублях (по умолчанию 2.0)
- grammage: плотность бумаги г/м² (по умолчанию 80)

## Интерпретация цветности

- "4+4", "полноцвет двусторонняя" → colorness="44"
- "4+0", "полноцвет односторонняя" → colorness="40"
- "1+1", "ч/б двусторонняя" → colorness="11"
- "1+0", "ч/б односторонняя" → colorness="10"

## Возвращает

```python
{
    "тип_печати": "Цифровая",
    "стоимость_печати": 2100.0,
    "стоимость_бумаги": 500.0,
    "общая_стоимость": 2600.0,
    "количество_листов_а3": 250,  # ← передавать в calculate_lamination
    "цена_за_единицу": 5.20
}
```

## Пример: 500 экз. А4, 4+4, бумага 2 р/лист

```python
layout = calculate_layout(piece_width=210, piece_height=297)
items = layout["items_per_sheet"]  # → 2

result = calculate_digital_printing(
    tirazh=500,
    items_per_sheet=items,
    colorness="44",
    paper_price=2.0
)
sheets = result["количество_листов_а3"]  # → 250
total = result["общая_стоимость"]
```

## Пример: формат не указан (SRA3 по умолчанию)

```python
# Изделие = SRA3, items_per_sheet = 1 напрямую
result = calculate_digital_printing(
    tirazh=250,
    items_per_sheet=1,
    colorness="44",
    paper_price=2.0
)
```

## Цена за единицу в final_answer

```python
cost_per_unit = result["общая_стоимость"] / tirazh
```
