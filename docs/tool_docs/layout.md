# Инструмент: calculate_layout

<!-- keywords: раскладка, расположение, формат, размер, изделие, лист, вылет, поле, ориентация -->

## Когда использовать

Вызывать ПЕРВЫМ перед любой печатью, если формат изделия НЕ совпадает с форматом печатного листа.

НЕ вызывать если:
- Изделие = SRA3 (320×450 мм) → items_per_sheet = 1 напрямую
- Изделие = 330×480 мм (А3+) → items_per_sheet = 1 напрямую

## Форматы печатного листа

- SRA3: 320×450 мм — основной, по умолчанию
- 330×480 мм (А3+) — если SRA3 не подходит

## Стандартные результаты (справочно)

| Изделие | Лист | items_per_sheet |
|---------|------|-----------------|
| А4 (210×297) | SRA3 | 2 |
| А5 (148×210) | SRA3 | 4 |
| А6 (105×148) | SRA3 | 8 |

## Параметры

- piece_width, piece_height: размеры изделия в мм
- margin_around: вылет вокруг каждого изделия, мм (по умолчанию 2)
- sheet_size: "SRA3" (по умолчанию) или "330x480"
- orientation: "auto" (по умолчанию), "portrait", "landscape"

## Алгоритм выбора формата

```python
layout = calculate_layout(piece_width=210, piece_height=297)
items = layout["items_per_sheet"]

if items == 0:
    layout = calculate_layout(piece_width=210, piece_height=297, sheet_size="330x480")
    items = layout["items_per_sheet"]
```

## Возвращает

```python
{
    "sheet_size": "SRA3 (320×450)",
    "items_per_sheet": 2,   # ← передавать во все инструменты печати
    "columns": 1,
    "rows": 2,
    "orientation": "книжная"
}
```

## Пример: А5, вылет 2 мм

```python
layout = calculate_layout(piece_width=148, piece_height=210, margin_around=2)
items = layout["items_per_sheet"]  # → 4
```
