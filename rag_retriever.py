"""
RAG-ретривер для полиграфического калькулятора.

Читает .md файлы из docs/tool_docs/ и возвращает релевантный контент.
Используется RAG-агентом (qwen3-8b) для обогащения запросов перед
передачей в calc-агент (qwen3-235b).
"""

import os
from smolagents import tool

# Путь к папке с документацией относительно этого файла
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, "docs", "tool_docs")

# Кэш файлов — читаем один раз при старте
_docs_cache: dict[str, str] = {}


def _load_all_docs() -> dict[str, str]:
    """Загружает все .md файлы в кэш при первом вызове."""
    global _docs_cache
    if _docs_cache:
        return _docs_cache

    if not os.path.exists(DOCS_DIR):
        raise FileNotFoundError(
            f"Папка документации не найдена: {DOCS_DIR}\n"
            f"Создайте папку и положите в неё .md файлы для инструментов."
        )

    for fname in os.listdir(DOCS_DIR):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(DOCS_DIR, fname)
        with open(fpath, encoding="utf-8") as f:
            _docs_cache[fname] = f.read()

    return _docs_cache


def list_available_docs() -> list[str]:
    """Возвращает список доступных файлов документации."""
    docs = _load_all_docs()
    return sorted(docs.keys())


@tool
def retrieve_tool_docs(filenames: str) -> str:
    """
    Читает документацию для указанных инструментов калькулятора.
    Возвращает правила, параметры и примеры кода для calc-агента.

    Доступные файлы:
    - layout.md             — calculate_layout (раскладка на листе)
    - digital_printing.md  — calculate_digital_printing (цифровая печать)
    - offset_printing.md   — calculate_offset_printing (офсетная печать)
    - lamination.md        — calculate_lamination (ламинация)
    - blocknote.md         — calculate_blocknote (блокноты с пружиной)
    - kubarik.md           — calculate_kubarik (кубарики)
    - bc7_binding.md       — calculate_bc7_binding (твёрдый переплёт 7БЦ)

    Args:
        filenames: Имена файлов через запятую.
                   Пример: "digital_printing.md, lamination.md"
                   Пример: "blocknote.md"
                   Пример: "layout.md, offset_printing.md"

    Returns:
        Содержимое запрошенных файлов — правила и примеры для calc-агента.
    """
    docs = _load_all_docs()

    # Парсим список файлов
    requested = [f.strip() for f in filenames.split(",") if f.strip()]

    results = []
    not_found = []

    for fname in requested:
        if fname in docs:
            results.append(f"{'=' * 60}\n{docs[fname]}\n{'=' * 60}")
        else:
            not_found.append(fname)

    output_parts = []

    if results:
        output_parts.append("\n\n".join(results))

    if not_found:
        available = ", ".join(sorted(docs.keys()))
        output_parts.append(
            f"⚠️ Файлы не найдены: {', '.join(not_found)}\n"
            f"Доступные файлы: {available}"
        )

    return "\n\n".join(output_parts) if output_parts else "Документация не найдена."
