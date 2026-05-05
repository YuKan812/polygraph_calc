"""
Полиграфический калькулятор — Streamlit UI
"""
import base64, io, logging, os, sys, yaml
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Полиграфический калькулятор", page_icon="🖨️",
                   layout="wide", initial_sidebar_state="collapsed")

def _get_secret(key):
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

# ── PDF viewer: открывает в новой вкладке как data URI ────────────────────────
def pdf_viewer(pdf_bytes: bytes, filename: str, key: str):
    b64 = base64.b64encode(pdf_bytes).decode()
    btn_id = f"pdf_{key}".replace("-", "_").replace(".", "_")
    html = f"""
    <style>
    #{btn_id}{{display:inline-block;padding:.4rem 1rem;background:#21808D;
    color:white!important;border:none;border-radius:6px;font-size:.875rem;
    font-weight:500;cursor:pointer;text-decoration:none;margin:4px 0}}
    #{btn_id}:hover{{background:#1a6570}}
    </style>
    <a id="{btn_id}" href="data:application/pdf;base64,{b64}"
       target="_blank" rel="noopener noreferrer">📄 Открыть PDF: {filename}</a>"""
    components.html(html, height=52)

# ── Агент ─────────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Загрузка агента…")
def _build_agent():
    from openai import OpenAI
    from smolagents import CodeAgent, OpenAIModel
    from tools.tools_agent import (calculate_layout, calculate_digital_printing,
        calculate_offset_printing, calculate_lamination,
        calculate_blocknote, calculate_kubarik)
    from tools.bc7 import calculate_bc7_binding
    from final_answer import FinalAnswerTool

    pf = "prompts_calc_minimal.yaml" if os.path.exists("prompts_calc_minimal.yaml") else "prompts.yaml"
    with open(pf, "r", encoding="utf-8") as f:
        tpl = yaml.safe_load(f)

    client = OpenAI(api_key=OPENROUTER_KEY, base_url="https://openrouter.ai/api/v1")
    model = OpenAIModel(model_id="qwen/qwen3-235b-a22b-2507", client=client,
                        temperature=0.2, top_p=0.95)
    return CodeAgent(model=model, tools=[
        calculate_layout, calculate_digital_printing, calculate_offset_printing,
        calculate_lamination, calculate_blocknote, calculate_kubarik,
        calculate_bc7_binding, FinalAnswerTool()],
        prompt_templates=tpl, max_steps=10, verbosity_level=0)

def run_agent(agent, user_input):
    old, sys.stdout = sys.stdout, io.StringIO()
    pdfs, answer = [], ""
    try:
        result = agent.run(user_input)
        if isinstance(result, dict):
            pp = result.get("pdf_path")
            if pp and os.path.exists(pp):
                with open(pp, "rb") as fh:
                    pdfs.append({"name": os.path.basename(pp), "bytes": fh.read()})
            skip = {"items", "pdf_path", "params"}
            answer = "\n".join(f"**{k}:** {v}" for k, v in result.items() if k not in skip)
        else:
            answer = str(result)
    except Exception as e:
        answer = f"⚠️ Ошибка: {e}"
    finally:
        sys.stdout = old
    return answer, pdfs

# ── UI ────────────────────────────────────────────────────────────────────────
st.markdown("<style>.block-container{padding-top:1.5rem}</style>", unsafe_allow_html=True)
st.title("🖨️ Полиграфический калькулятор")
st.caption("Цифровая и офсетная печать, ламинация, блокноты, кубарики, брошюровка 7БЦ.")

if not OPENROUTER_KEY:
    st.error("Не найден **OPENROUTER_API_KEY**.\n\n"
             "- **Локально**: `.streamlit/secrets.toml` или `.env`\n"
             "- **Streamlit Cloud**: Settings → Secrets")
    st.stop()

if "messages" not in st.session_state: st.session_state.messages = []
if "agent" not in st.session_state:    st.session_state.agent = _build_agent()

for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        for pdf in msg.get("pdfs", []):
            pdf_viewer(pdf["bytes"], pdf["name"], key=f"h{i}_{pdf['name']}")

if user_input := st.chat_input("Введите запрос…"):
    st.session_state.messages.append({"role": "user", "content": user_input, "pdfs": []})
    with st.chat_message("user"):
        st.markdown(user_input)
    with st.chat_message("assistant"):
        with st.spinner("Считаю…"):
            answer, pdfs = run_agent(st.session_state.agent, user_input)
        st.markdown(answer)
        for pdf in pdfs:
            pdf_viewer(pdf["bytes"], pdf["name"], key=f"n_{pdf['name']}")
    st.session_state.messages.append({"role": "assistant", "content": answer, "pdfs": pdfs})

with st.sidebar:
    st.header("Примеры запросов")
    for ex in [
        "Цифровая печать 4+4, 250 экз. А4 + ламинация стандарт 1+0",
        "Офсет 1+1, тираж 500 листов, бумага 2 р/лист",
        "Блокнот А5, 50 листов, тираж 100 шт, 1+1, ламинация глянц",
        "Кубарик 80 листов, тираж 500 шт, 1+1",
        "Брошюровка 7БЦ, А4, 200 страниц, тираж 100 шт, бумвинил",
        "Ламинация софттач 1+1, 300 листов А4",
    ]:
        if st.button(ex, use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": ex, "pdfs": []})
            with st.spinner("Считаю…"):
                a, p = run_agent(st.session_state.agent, ex)
            st.session_state.messages.append({"role": "assistant", "content": a, "pdfs": p})
            st.rerun()
    st.divider()
    if st.button("🗑️ Очистить историю", use_container_width=True):
        st.session_state.messages = []; st.rerun()
    st.divider()
    st.caption("Модель: Qwen3-235B via OpenRouter")
