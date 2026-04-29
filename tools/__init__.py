"""
Пакет инструментов полиграфического калькулятора.

Все @tool функции доступны через единый импорт:

    from tools import (
        calculate_layout,
        calculate_digital_printing,
        calculate_offset_printing,
        calculate_lamination,
        calculate_blocknote,
        calculate_kubarik,
        calculate_bc7_binding,
    )
"""

from .tools_agent import (
    calculate_layout,
    calculate_digital_printing,
    calculate_offset_printing,
    calculate_lamination,
    calculate_blocknote,
    calculate_kubarik,
)
from .bc7 import calculate_bc7_binding

__all__ = [
    "calculate_layout",
    "calculate_digital_printing",
    "calculate_offset_printing",
    "calculate_lamination",
    "calculate_blocknote",
    "calculate_kubarik",
    "calculate_bc7_binding",
]
