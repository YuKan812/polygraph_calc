"""
Полиграфический калькулятор — Streamlit UI
Замена GradioUI для деплоя на Streamlit Cloud.
"""

import io
import logging
import os
import sys
import yaml
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
#  Настройка страницы (ОБЯЗАТЕЛЬНО первая команда Streamlit)
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Полиграфический калькулятор",
    page_icon="🖨️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
#  Секреты и переменные окружения
#  Локально: .env файл или .streamlit/secrets.toml
#  В Streamlit Cloud: Settings → Secrets
# ─────────────────────────────────────────────────────────────────────────────

def _get_secret(key: str) -> str | None:
    """Читает секрет из st.secrets (Cloud) или os.environ (локально)."""
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        pass
    # Fallback: dotenv (только локально)
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    return os.environ.get(key)


OPENROUTER_KEY = _get_secret("OPENROUTER_API_KEY")

# ─────────────────────────────────────────────────────────────────────────────
#  Логирование
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
#  Кэшированная инициализация агента (один раз на сессию приложения)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner="Загрузка агента…")
def _build_agent():
    """Строит агентный пайплайн. Вызывается один раз при старте."""
    from openai import OpenAI
    from smolagents import CodeAgent, OpenAIModel

    from tools.tools_agent import (
        calculate_layout,
        calculate_digital_printing,
        calculate_offset_printing,
        calculate_lamination,
        calculate_blocknote,
        calculate_kubarik,
    )
    from tools.bc7 import calculate_bc7_binding
    from final_answer import FinalAnswerTool

    # ── Загрузка промптов ──────────────────────────────────────────────────
    prompt_file = "prompts_calc_minimal.yaml"
    if not os.path.exists(prompt_file):
        # Fallback на основной промпт
        prompt_file = "prompts.yaml"

    with open(prompt_file, "r", encoding="utf-8") as f:
        calc_prompt_templates = yaml.safe_load(f)

    # ── Модель ────────────────────────────────────────────────────────────
    client = OpenAI(
        api_key=OPENROUTER_KEY,
        base_url="https://openrouter.ai/api/v1",
    )

    model = OpenAIModel(
        model_id="qwen/qwen3-235b-a22b-2507",
        client=client,
        temperature=0.2,
        top_p=0.95,
    )

    # ── Агент ─────────────────────────────────────────────────────────────
    agent = CodeAgent(
        model=model,
        tools=[
            calculate_layout,
            calculate_digital_printing,
            calculate_offset_printing,
            calculate_lamination,
            calculate_blocknote,
            calculate_kubarik,
            calculate_bc7_binding,
            FinalAnswerTool(),
        ],
        prompt_templates=calc_prompt_templates,
        max_steps=10,
        verbosity_level=0,   # stdout-шум отключён — управляем выводом сами
    )
    return agent


# ─────────────────────────────────────────────────────────────────────────────
#  Запуск агента с перехватом stdout (промежуточные шаги)
# ─────────────────────────────────────────────────────────────────────────────

def run_agent(agent, user_input: str) -> tuple[str, list[dict]]:
    """
    Запускает агент и возвращает (ответ, список_pdf).

    Перехватывает stdout чтобы промежуточные шаги smolagents не попали
    в интерфейс напрямую.

    Returns
    -------
    answer : str   — итоговый текст ответа
    pdfs   : list  — [{"name": ..., "bytes": ...}, ...]
    """
    # Перехват stdout
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    pdfs = []
    answer = ""
    try:
        result = agent.run(user_input)

        # result может быть строкой или dict (bc7 возвращает dict)
        if isinstance(result, dict):
            pdf_path = result.get("pdf_path")
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, "rb") as fh:
                    pdfs.append({
                        "name": os.path.basename(pdf_path),
                        "bytes": fh.read(),
                    })
            # Форматируем читаемый текст из dict
            answer = _format_dict_answer(result)
        else:
            answer = str(result)

    except Exception as exc:
        logger.exception("Ошибка агента")
        answer = f"⚠️ Ошибка при расчёте: {exc}"
    finally:
        captured = sys.stdout.getvalue()
        sys.stdout = old_stdout
        if captured.strip():
            logger.debug("Агент stdout:\n%s", captured)

    return answer, pdfs


def _format_dict_answer(d: dict) -> str:
    """Форматирует dict-результат агента в читаемый текст."""
    lines = []
    skip_keys = {"items", "pdf_path", "params"}
    for k, v in d.items():
        if k in skip_keys:
            continue
        lines.append(f"**{k}:** {v}")
    return "\n".join(lines)


def _format_answer(answer: str) -> str:
    """
    Форматирует текстовый ответ для лучшей читаемости.
    - Разбивает на строки по ключевым разделителям
    - Добавляет переносы строк между позициями
    """
    if not answer:
        return answer
    
    # Убираем лишние разделители из начала/конца
    answer = answer.strip()
    
    # Заменяем основные разделители на переносы строк
    # Ищем паттерны типа "Наименование: значение" или "параметр = значение"
    import re
    
    # Разбиваем по строкам, сохраняя разделители
    lines = answer.split('\n')
    
    formatted_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Добавляем маркеры списков если строка начинается с • или -
        if line.startswith('•') or line.startswith('- '):
            formatted_lines.append(line)
        # Добавляем перенос перед новыми секциями
        elif any(marker in line for marker in ['РАСЧЕТ', 'ИТОГО', 'СТОИМОСТЬ', 'ЦЕНА', 'Тираж', 'Формат', 'Бумага', 'Печать', 'Ламинация']):
            formatted_lines.append(f"\n{line}")
        else:
            formatted_lines.append(line)
    
    result = '\n'.join(formatted_lines)
    
    # Добавляем markdown-блок для кода/чисел если есть
    result = re.sub(r'(\d+\s*руб)', r'**\1**', result)
    result = re.sub(r'(\d+\s*р\.)', r'**\1**', result)
    
    return result.strip()


# ─────────────────────────────────────────────────────────────────────────────
#  Стили
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
/* Убираем лишние отступы сверху */
.block-container { padding-top: 1.5rem; }

/* Кнопка скачать PDF */
.stDownloadButton > button {
    background-color: #21808D;
    color: white;
    border-radius: 6px;
    border: none;
}
.stDownloadButton > button:hover {
    background-color: #1a6570;
    color: white;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  Заголовок
# ─────────────────────────────────────────────────────────────────────────────

st.title("🖨️ Полиграфический калькулятор")
st.caption(
    "Рассчитывает стоимость цифровой и офсетной печати, ламинации, "
    "блокнотов, кубариков, брошюровки 7БЦ."
)

# ─────────────────────────────────────────────────────────────────────────────
#  Проверка API ключа
# ─────────────────────────────────────────────────────────────────────────────

if not OPENROUTER_KEY:
    st.error(
        "Не найден **OPENROUTER_API_KEY**.\n\n"
        "- **Локально**: добавьте ключ в `.streamlit/secrets.toml` или `.env`\n"
        "- **Streamlit Cloud**: Settings → Secrets → `OPENROUTER_API_KEY = \"sk-...\"`"
    )
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
#  Инициализация состояния
# ─────────────────────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []   # [{"role": "user"|"assistant", "content": str, "pdfs": list}]

if "agent" not in st.session_state:
    st.session_state.agent = _build_agent()

# ─────────────────────────────────────────────────────────────────────────────
#  Вывод истории чата
# ─────────────────────────────────────────────────────────────────────────────

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # Кнопки скачивания PDF (если есть)
        for pdf in msg.get("pdfs", []):
            st.download_button(
                label=f"📄 Скачать {pdf['name']}",
                data=pdf["bytes"],
                file_name=pdf["name"],
                mime="application/pdf",
                key=f"dl_{pdf['name']}_{id(pdf)}",
            )

# ─────────────────────────────────────────────────────────────────────────────
#  Ввод пользователя
# ─────────────────────────────────────────────────────────────────────────────

if user_input := st.chat_input("Введите запрос, например: цифровая печать 4+4, 250 экз. А4 + ламинация"):

    # Сохраняем сообщение пользователя
    st.session_state.messages.append({"role": "user", "content": user_input, "pdfs": []})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Запускаем агент
    with st.chat_message("assistant"):
        with st.spinner("Считаю…"):
            answer, pdfs = run_agent(st.session_state.agent, user_input)

        st.markdown(answer)

        for pdf in pdfs:
            st.download_button(
                label=f"📄 Скачать {pdf['name']}",
                data=pdf["bytes"],
                file_name=pdf["name"],
                mime="application/pdf",
                key=f"dl_new_{pdf['name']}",
            )

    # Сохраняем ответ в историю
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "pdfs": pdfs,
    })

# ─────────────────────────────────────────────────────────────────────────────
#  Боковая панель: быстрые примеры и кнопка очистки
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Примеры запросов")

    examples = [
        "Цифровая печать 4+4, 250 экз. А4 + ламинация стандарт 1+0",
        "Офсет 1+1, тираж 500 листов, бумага 2 р/лист",
        "Блокнот А5, 50 листов, тираж 100 шт, 1+1, ламинация глянц",
        "Кубарик 80 листов, тираж 500 шт, 1+1",
        "Брошюровка 7БЦ, А4, 200 страниц, тираж 100 шт, бумвинил",
        "Ламинация софттач 1+1, 300 листов А4",
    ]

    for ex in examples:
        if st.button(ex, use_container_width=True):
            # Программно подставляем пример в чат
            st.session_state.messages.append({"role": "user", "content": ex, "pdfs": []})
            with st.spinner("Считаю…"):
                answer, pdfs = run_agent(st.session_state.agent, ex)
            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
                "pdfs": pdfs,
            })
            st.rerun()

    st.divider()

    if st.button("🗑️ Очистить историю", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.caption("Модель: Qwen3-235B via OpenRouter")
