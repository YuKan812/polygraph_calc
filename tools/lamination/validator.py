ALLOWED_TYPES = {"standard", "softtouch", "75", "125"}
ALLOWED_SIDES = {"1+0", "1+1"}

MAX_SIZE_MM = 2000  # защита от мусора
MIN_SIZE_MM = 10


def validate_lamination_params(
    lamination_type: str,
    sides: str,
    width_mm: int,
    height_mm: int,
    quantity: int
) -> dict:
    """
    Проверяет и нормализует параметры ламинации.

    Возвращает очищенные параметры или выбрасывает ValueError.
    """

    # --- Тип ламинации ---
    if lamination_type not in ALLOWED_TYPES:
        raise ValueError(f"Недопустимый тип ламинации: {lamination_type}")

    # --- Стороны ---
    if sides not in ALLOWED_SIDES:
        raise ValueError(f"Недопустимое значение сторон: {sides}")

    # --- Размеры ---
    if not (MIN_SIZE_MM <= width_mm <= MAX_SIZE_MM):
        raise ValueError("Некорректная ширина листа")

    if not (MIN_SIZE_MM <= height_mm <= MAX_SIZE_MM):
        raise ValueError("Некорректная высота листа")
        
    if lamination_type is None:
        raise ValueError("Тип ламинации не определён")

    if sides is None:
        sides = "1+0"

    return {
        "lamination_type": lamination_type,
        "sides": sides,
        "width_mm": int(width_mm),
        "height_mm": int(height_mm),
        "quantity": int(quantity)
    }
