"""
Полиграфический калькулятор — RAG-архитектура.

Два агента:
- RAG-агент (qwen3-8b): понимает запрос, извлекает нужную документацию,
  формирует обогащённый запрос для calc-агента.
- Calc-агент (qwen3-235b): выполняет расчёты, имеет доступ ко всем
  инструментам калькулятора.
"""

import yaml
import os
import logging

from dotenv import load_dotenv
from openai import OpenAI
from smolagents import CodeAgent, OpenAIModel
from Gradio_UI import GradioUI

from tools.tools_agent import (
    calculate_layout,
    calculate_digital_printing,
    calculate_offset_printing,
    calculate_lamination,
    calculate_blocknote,
    calculate_kubarik,
)
from tools.bc7 import calculate_bc7_binding
from rag_retriever import retrieve_tool_docs
from final_answer import FinalAnswerTool

load_dotenv()
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
#  Загрузка промптов
# ─────────────────────────────────────────────────────────────

with open("prompts_calc_minimal.yaml", "r", encoding="utf-8") as f:
    calc_prompt_templates = yaml.safe_load(f)

with open("prompts_rag.yaml", "r", encoding="utf-8") as f:
    rag_prompt_templates = yaml.safe_load(f)

# ─────────────────────────────────────────────────────────────
#  OpenRouter клиент (общий для обеих моделей)
# ─────────────────────────────────────────────────────────────

client = OpenAI(
    api_key=OPENROUTER_KEY,
    base_url="https://openrouter.ai/api/v1",
)

# ─────────────────────────────────────────────────────────────
#  Модели
# ─────────────────────────────────────────────────────────────

# RAG-агент — лёгкая быстрая модель, только понять запрос и достать доки
rag_model = OpenAIModel(
    model_id="qwen/qwen3-8b",
    client=client,
    temperature=0.2,   # низкая температура — задача детерминированная
    top_p=0.9,
)

# Calc-агент — мощная модель для сложных многошаговых расчётов
calc_model = OpenAIModel(
    model_id="qwen/qwen3-235b-a22b-2507",
    client=client,
    temperature=0.2,
    top_p=0.95,
)

# ─────────────────────────────────────────────────────────────
#  Calc-агент — только расчёты, никакого RAG
# ─────────────────────────────────────────────────────────────

final_answer_tool = FinalAnswerTool()

calc_agent = CodeAgent(
    model=calc_model,
    tools=[
        calculate_layout,
        calculate_digital_printing,
        calculate_offset_printing,
        calculate_lamination,
        calculate_blocknote,
        calculate_kubarik,
        calculate_bc7_binding,
        final_answer_tool,
    ],
    prompt_templates=calc_prompt_templates,
    max_steps=10,
    verbosity_level=1,
    name="polygraphy_calculator",
    description="""
    Выполняет расчёты стоимости полиграфической продукции.
    Принимает полный обогащённый запрос, который уже содержит:
    - оригинальный запрос пользователя
    - контекст из истории диалога (если запрос продолжает предыдущий)
    - правила и примеры для нужных инструментов

    Возвращает подробный расчёт стоимости с разбивкой по операциям.
    """,
    # planning_interval не используем — задачи короткие и последовательные
)

# ─────────────────────────────────────────────────────────────
#  RAG-агент — оркестратор
# ─────────────────────────────────────────────────────────────

rag_agent = CodeAgent(
    model=rag_model,
    tools=[retrieve_tool_docs],
    managed_agents=[calc_agent],
    prompt_templates=rag_prompt_templates,
    max_steps=5,       # RAG-агент делает мало шагов: retrieve × N + передача
    verbosity_level=1,
)

# ─────────────────────────────────────────────────────────────
#  Запуск
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info("Запуск полиграфического калькулятора (RAG-архитектура)")
    logger.info(f"RAG-агент: qwen3-8b")
    logger.info(f"Calc-агент: qwen3-235b")
    logger.info(f"Документация: {os.path.join(os.path.dirname(__file__), 'docs', 'tool_docs')}")
    GradioUI(rag_agent).launch()
