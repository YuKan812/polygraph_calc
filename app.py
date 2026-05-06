"""
Полиграфический калькулятор — Streamlit UI.

Архитектура двух агентов:
  RAG-агент  (лёгкая модель) — понимает запрос, достаёт нужные RAG-документы,
                                формирует обогащённый запрос для calc-агента.
  Calc-агент (мощная модель) — выполняет расчёты, имеет доступ ко всем инструментам.

RAG-документы лежат в  docs/tool_docs/*.md
Каждый файл описывает правила и примеры для одного инструмента.
"""
import base64, io, logging, os, sys, yaml
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Полиграфический калькулятор",
    page_icon="🖨️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Секреты ───────────────────────────────────────────────────────────────────
def _get_secret(key: str):
    try:
        return st.secrets[key]
    except Exception:
        pass
    try:
        from dotenv import load_dotenv; load_dotenv()
    except ImportError:
        pass
    return os.environ.get(key)

OPENROUTER_KEY = _get_secret("OPENROUTER_API_KEY")
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# ── PDF viewer: открыть в новой вкладке как data URI ──────────────────────────
def pdf_viewer(pdf_bytes: bytes, filename: str, key: str):
    """PDF открывается в новой вкладке браузера. Диск клиента не используется."""
    b64  = base64.b64encode(pdf_bytes).decode()
    sid  = ("pdf_" + key).replace("-","_").replace(".","_").replace(" ","_")
    components.html(
        f'<style>#{sid}{{display:inline-block;padding:.4rem 1.1rem;background:#21808D;'
        f'color:white!important;border-radius:6px;font-size:.875rem;font-weight:500;'
        f'text-decoration:none;margin:4px 0}}#{sid}:hover{{background:#1a6570}}</style>'
        f'<a id="{sid}" href="data:application/pdf;base64,{b64}"'
        f' target="_blank" rel="noopener noreferrer">📄 Открыть PDF: {filename}</a>',
        height=52,
    )

# ── Двухагентный пайплайн ─────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Загрузка агентов…")
def _build_pipeline():
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
    from rag_retriever import retrieve_tool_docs
    from final_answer import FinalAnswerTool

    # ── Промпты ───────────────────────────────────────────────────────────────
    # Calc-агент использует минимальный промпт (без примеров — они в RAG-доках)
    calc_pf = "prompts_calc_minimal.yaml"
    if not os.path.exists(calc_pf):
        calc_pf = "prompts.yaml"
    with open(calc_pf, "r", encoding="utf-8") as f:
        calc_tpl = yaml.safe_load(f)

    rag_pf = "prompts_rag.yaml"
    with open(rag_pf, "r", encoding="utf-8") as f:
        rag_tpl = yaml.safe_load(f)

    # ── OpenRouter клиент (общий) ─────────────────────────────────────────────
    client = OpenAI(api_key=OPENROUTER_KEY, base_url="https://openrouter.ai/api/v1")

    # ── RAG-агент: лёгкая быстрая модель ─────────────────────────────────────
    # Задача — понять запрос и достать нужные doc-файлы, не считать.
    rag_model = OpenAIModel(
        model_id="qwen/qwen3-8b",
        client=client,
        temperature=0.2,
        top_p=0.9,
    )

    # ── Calc-агент: мощная модель для многошаговых расчётов ───────────────────
    calc_model = OpenAIModel(
        model_id="qwen/qwen3-235b-a22b-2507",
        client=client,
        temperature=0.2,
        top_p=0.95,
    )

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
            FinalAnswerTool(),
        ],
        prompt_templates=calc_tpl,
        max_steps=10,
        verbosity_level=0,
        name="polygraphy_calculator",
        description=(
            "Выполняет расчёты стоимости полиграфической продукции. "
            "Принимает обогащённый запрос с правилами и примерами из RAG. "
            "Возвращает подробный расчёт стоимости."
        ),
    )

    rag_agent = CodeAgent(
        model=rag_model,
        tools=[retrieve_tool_docs],
        managed_agents=[calc_agent],
        prompt_templates=rag_tpl,
        max_steps=5,   # retrieve × N + передача calc-агенту
        verbosity_level=0,
    )

    return rag_agent


# ── Запуск пайплайна ──────────────────────────────────────────────────────────
def run_agent(rag_agent, user_input: str) -> tuple[str, list[dict]]:
    """Возвращает (текст_ответа, список_pdf)."""
    old, sys.stdout = sys.stdout, io.StringIO()
    pdfs, answer = [], ""
    try:
        result = rag_agent.run(user_input)

        if isinstance(result, dict):
            # PDF передаётся как bytes напрямую из bc7 — без чтения с диска
            pdf_b = result.get("pdf_bytes")
            pdf_n = result.get("pdf_filename", "bc7.pdf")
            if pdf_b:
                pdfs.append({"name": pdf_n, "bytes": pdf_b})
            skip = {"items", "pdf_path", "pdf_bytes", "pdf_filename", "params"}
            answer = "\n".join(
                f"**{k}:** {v}" for k, v in result.items() if k not in skip
            )
        else:
            answer = str(result)

    except Exception as e:
        logger.exception("Pipeline error")
        answer = f"⚠️ Ошибка при расчёте: {e}"
    finally:
        sys.stdout = old
    return answer, pdfs


# ── Интерфейс ─────────────────────────────────────────────────────────────────
st.markdown("<style>.block-container{padding-top:1.5rem}</style>", unsafe_allow_html=True)
st.title("🖨️ Полиграфический калькулятор")
st.caption("Цифровая и офсетная печать · Ламинация · Блокноты · Кубарики · Брошюровка 7БЦ")

if not OPENROUTER_KEY:
    st.error(
        "Не найден **OPENROUTER_API_KEY**.\n\n"
        "**Локально:** `.streamlit/secrets.toml`:\n```\nOPENROUTER_API_KEY = \"sk-or-...\"\n```\n"
        "**Streamlit Cloud:** Settings → Secrets"
    )
    st.stop()

if "messages" not in st.session_state: st.session_state.messages = []
if "pipeline" not in st.session_state: st.session_state.pipeline = _build_pipeline()

# История чата
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        for pdf in msg.get("pdfs", []):
            pdf_viewer(pdf["bytes"], pdf["name"], key=f"h{i}_{pdf['name']}")

# Ввод пользователя
if user_input := st.chat_input("Введите запрос…"):
    st.session_state.messages.append({"role": "user", "content": user_input, "pdfs": []})
    with st.chat_message("user"):
        st.markdown(user_input)
    with st.chat_message("assistant"):
        with st.spinner("Считаю…"):
            answer, pdfs = run_agent(st.session_state.pipeline, user_input)
        st.markdown(answer)
        for pdf in pdfs:
            pdf_viewer(pdf["bytes"], pdf["name"], key=f"n_{pdf['name']}")
    st.session_state.messages.append({
        "role": "assistant", "content": answer, "pdfs": pdfs,
    })

# Боковая панель
with st.sidebar:
    st.header("Примеры запросов")
    EXAMPLES = [
        "Цифровая печать 4+4, 250 экз. А4 + ламинация стандарт 1+0",
        "Офсет 1+1, тираж 500 листов, бумага 2 р/лист",
        "Блокнот А5, 50 листов, тираж 100 шт, 1+1, ламинация глянц",
        "Кубарик 80 листов, тираж 500 шт, 1+1",
        "7БЦ А4, 240 стр., тираж 20 шт., меловка 150 г/м² 4+1, плёнка глянцевая",
        "7БЦ А5, 160 стр., тираж 500 шт., бумвинил",
        "Ламинация софттач 1+1, 300 листов А4",
    ]
    for ex in EXAMPLES:
        if st.button(ex, use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": ex, "pdfs": []})
            with st.spinner("Считаю…"):
                a, p = run_agent(st.session_state.pipeline, ex)
            st.session_state.messages.append({"role": "assistant", "content": a, "pdfs": p})
            st.rerun()

    st.divider()
    if st.button("🗑️ Очистить историю", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    st.divider()
    st.caption("RAG: Qwen3-8B · Calc: Qwen3-235B · OpenRouter")
