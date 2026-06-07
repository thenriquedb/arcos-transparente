"""Interface web local do chatbot Arcos Transparente via Streamlit."""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys
from uuid import uuid4

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.chatbot import ChatbotAgentBackend, ChatSession, ChatbotApplication  # noqa: E402

APP_TITLE = "Arcos Transparente"
INPUT_PLACEHOLDER = "Pergunte sobre servidores, folha, frota, contratos, receitas..."
BACKEND_CACHE_FILES = (
    PROJECT_ROOT / "docs" / "agent-system-prompt.md",
    PROJECT_ROOT / "agents" / "chatbot" / "agent.py",
)
BACKEND_CACHE_DIRS = (PROJECT_ROOT / "agents" / "tools" / "sql_tools",)


@st.cache_resource
def get_backend(cache_token: str) -> ChatbotAgentBackend:
    _ = cache_token
    return ChatbotAgentBackend()


def build_backend_cache_token() -> str:
    digest = hashlib.sha256()
    for path in _iter_backend_dependency_files():
        try:
            stat = path.stat()
        except FileNotFoundError:
            continue
        digest.update(str(path.relative_to(PROJECT_ROOT)).encode("utf-8"))
        digest.update(str(stat.st_mtime_ns).encode("utf-8"))
        digest.update(str(stat.st_size).encode("utf-8"))
    return digest.hexdigest()


def _iter_backend_dependency_files():
    yield from BACKEND_CACHE_FILES
    for directory in BACKEND_CACHE_DIRS:
        yield from sorted(directory.rglob("*.py"))


def build_application(
    session_id: str,
    cache_token: str | None = None,
) -> ChatbotApplication:
    backend_cache_token = cache_token or build_backend_cache_token()
    return ChatbotApplication(
        backend=get_backend(backend_cache_token),
        session=ChatSession(id=session_id),
    )


def reset_chat_session() -> None:
    session_id = str(uuid4())
    cache_token = build_backend_cache_token()
    st.session_state.chat_session_id = session_id
    st.session_state.backend_cache_token = cache_token
    st.session_state.messages = []
    st.session_state.is_loading = False
    st.session_state.app = build_application(session_id, cache_token)


def ensure_session_state() -> None:
    cache_token = build_backend_cache_token()

    if "chat_session_id" not in st.session_state:
        st.session_state.chat_session_id = str(uuid4())

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "is_loading" not in st.session_state:
        st.session_state.is_loading = False

    if (
        "app" not in st.session_state
        or st.session_state.get("backend_cache_token") != cache_token
    ):
        st.session_state.backend_cache_token = cache_token
        st.session_state.app = build_application(
            st.session_state.chat_session_id,
            cache_token,
        )


def configure_page() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="AT",
        layout="centered",
    )


def render_header() -> None:
    title_col, action_col = st.columns([0.72, 0.28], vertical_alignment="center")
    with title_col:
        st.title(APP_TITLE)
        st.caption("Chat local conectado ao agente e aos dados públicos importados.")
    with action_col:
        if st.button("Nova conversa", use_container_width=True):
            reset_chat_session()
            st.rerun()


def render_history() -> None:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def friendly_error_message(exc: Exception) -> str:
    message = str(exc).strip()
    normalized = message.lower()

    if "openai_api_key" in normalized or "openai_model" in normalized:
        return (
            "Configuracao do chatbot incompleta. Defina LLM_PROVIDER=openai, "
            "OPENAI_MODEL e OPENAI_API_KEY no ambiente ou no .env antes de iniciar "
            "o chat."
        )

    if (
        "provider nao suportado pelo chatbot" in normalized
        or "llm_provider" in normalized
    ):
        return (
            "Provider nao suportado para o chatbot nesta fase. Use "
            "LLM_PROVIDER=openai no ambiente ou no .env."
        )

    database_markers = (
        "no such table",
        "unable to open database",
        "database is locked",
        "sqlite",
        "transparencia.db",
    )
    if any(marker in normalized for marker in database_markers):
        return (
            "Banco local indisponivel ou sem dados importados. Importe a base SQLite "
            "antes de consultar o chat."
        )

    return (
        "Falha inesperada ao consultar o agente ou uma ferramenta. "
        "Tente novamente ou veja os detalhes tecnicos abaixo."
    )


def handle_prompt(prompt: str) -> None:
    app: ChatbotApplication = st.session_state.app
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        st.session_state.is_loading = True
        try:
            response = app.ask(prompt)
            assistant_content = response.content
            st.markdown(assistant_content)
        except ValueError as exc:
            assistant_content = str(exc)
            st.warning(assistant_content)
        except Exception as exc:
            assistant_content = friendly_error_message(exc)
            st.error(assistant_content)
            with st.expander("Detalhes tecnicos"):
                st.code(str(exc) or repr(exc))
        finally:
            st.session_state.is_loading = False

    if assistant_content:
        st.session_state.messages.append(
            {"role": "assistant", "content": assistant_content}
        )


def render_question_suggestions() -> None:
    suggestions = [
        "Quantos servidores ativos existem atualmente?",
        "Qual é a receita total do último mês?",
        "Quais contratos estão prestes a vencer?",
        "Quantos veículos estão na frota e quais são os modelos mais comuns?",
        "Qual é a folha de pagamento atual e como ela se compara ao mês anterior?",
    ]

    st.subheader("Sugestões de perguntas")

    for suggestion in suggestions:
        if st.button(suggestion, use_container_width=True):
            handle_prompt(suggestion)
            st.rerun()


def main() -> None:
    configure_page()
    ensure_session_state()
    render_header()
    render_history()

    # if not st.session_state.messages:
    #     render_question_suggestions()

    prompt = st.chat_input(
        INPUT_PLACEHOLDER,
        disabled=st.session_state.is_loading,
    )
    if prompt:
        handle_prompt(prompt)


if __name__ == "__main__":
    main()
