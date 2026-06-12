"""Normalização de streaming e cadeia de fallback do backend (C4).

Streaming é a UX principal (Streamlit). Estes testes cobrem:
- achatamento de conteúdo (string e blocos lista/dict do LangChain);
- filtragem de mensagens de tool/system para não vazarem no stream do usuário;
- a cadeia de fallback do backend (sem `.stream` / `.stream` lança TypeError /
  stream vazio) — que garante que o usuário nunca receba resposta vazia.
"""

from __future__ import annotations

from agents.chatbot.backend import ChatbotAgentBackend
from agents.chatbot.streaming import (
    _is_user_visible_stream_message,
    content_to_text,
    extract_last_message_content,
    extract_stream_chunk_content,
)


class _Msg:
    """Mensagem tipo-AIMessage (nó model): visível ao usuário."""

    def __init__(self, content) -> None:
        self.content = content


class _ToolMsg:
    type = "tool"

    def __init__(self, content) -> None:
        self.content = content


# --- content_to_text --------------------------------------------------------


def test_content_to_text_string_passa_direto() -> None:
    assert content_to_text("olá mundo") == "olá mundo"


def test_content_to_text_achata_blocos_de_lista() -> None:
    # LangChain devolve conteúdo como lista de blocos {"type":"text","text":...}.
    blocos = [
        {"type": "text", "text": "Olá "},
        "mundo",
        {"content": "!"},
    ]
    assert content_to_text(blocos) == "Olá mundo!"


def test_content_to_text_ignora_blocos_sem_texto() -> None:
    assert content_to_text([{"type": "image", "url": "x"}, {"foo": "bar"}]) == ""


def test_content_to_text_tipo_inesperado_vira_vazio() -> None:
    assert content_to_text(None) == ""
    assert content_to_text(123) == ""


# --- extract_stream_chunk_content -------------------------------------------


def test_extract_stream_chunk_content_formatos_simples() -> None:
    assert extract_stream_chunk_content(None) == ""
    assert extract_stream_chunk_content("texto") == "texto"
    assert extract_stream_chunk_content(b"bytes") == "bytes"


def test_extract_stream_chunk_content_dict_content_text_delta_e_aninhado() -> None:
    assert extract_stream_chunk_content({"content": "a"}) == "a"
    assert extract_stream_chunk_content({"text": "b"}) == "b"
    assert extract_stream_chunk_content({"delta": "c"}) == "c"
    assert extract_stream_chunk_content({"message": {"content": "d"}}) == "d"


def test_extract_stream_chunk_content_evento_langgraph_do_modelo() -> None:
    evento = (_Msg("resposta"), {"langgraph_node": "model"})
    assert extract_stream_chunk_content(evento) == "resposta"


def test_extract_stream_chunk_content_filtra_evento_de_tool() -> None:
    evento = (_ToolMsg("SAIDA INTERNA DA TOOL"), {"langgraph_node": "tools"})
    assert extract_stream_chunk_content(evento) == ""


def test_extract_stream_chunk_content_achata_blocos_de_conteudo_da_mensagem() -> None:
    # Regressão: mensagem do modelo cujo `.content` é uma lista de blocos.
    evento = (_Msg([{"type": "text", "text": "parte 1 "}, {"text": "parte 2"}]), {"langgraph_node": "model"})
    assert extract_stream_chunk_content(evento) == "parte 1 parte 2"


# --- _is_user_visible_stream_message ----------------------------------------


def test_is_user_visible_aceita_mensagem_do_modelo() -> None:
    assert _is_user_visible_stream_message(_Msg("x"), {"langgraph_node": "model"}) is True


def test_is_user_visible_rejeita_no_de_tools() -> None:
    assert _is_user_visible_stream_message(_Msg("x"), {"langgraph_node": "tools"}) is False
    assert _is_user_visible_stream_message(_Msg("x"), {"node": "agent:tools"}) is False


def test_is_user_visible_rejeita_por_tipo_de_mensagem() -> None:
    assert _is_user_visible_stream_message(_ToolMsg("x"), {"langgraph_node": "model"}) is False


def test_is_user_visible_rejeita_por_classe_de_mensagem() -> None:
    class ToolMessage:
        content = "x"

    class SystemMessage:
        content = "x"

    assert _is_user_visible_stream_message(ToolMessage(), {}) is False
    assert _is_user_visible_stream_message(SystemMessage(), {}) is False


# --- extract_last_message_content -------------------------------------------


def test_extract_last_message_content_vazio_e_preenchido() -> None:
    assert extract_last_message_content({"messages": []}) == ""
    assert extract_last_message_content({}) == ""
    assert extract_last_message_content({"messages": [_Msg("final")]}) == "final"
    assert extract_last_message_content({"messages": ["texto cru"]}) == "texto cru"


# --- Backend: cadeia de fallback do streaming -------------------------------


def _backend_for(agent) -> ChatbotAgentBackend:
    return ChatbotAgentBackend(agent_factory=lambda: agent)


def test_stream_fallback_quando_agente_nao_suporta_stream() -> None:
    class _AgentSemStream:
        def invoke(self, *_a, **_k):
            return {"messages": [_Msg("resposta nao-stream")]}

    chunks = list(_backend_for(_AgentSemStream()).stream_answer("q", session_id="s"))

    assert chunks == ["resposta nao-stream"]  # nunca vazio


def test_stream_fallback_quando_stream_lanca_type_error() -> None:
    class _AgentStreamTypeError:
        def invoke(self, *_a, **_k):
            return {"messages": [_Msg("resposta do fallback")]}

        def stream(self, *_a, **_k):
            raise TypeError("stream_mode inesperado")

    chunks = list(_backend_for(_AgentStreamTypeError()).stream_answer("q", session_id="s"))

    assert chunks == ["resposta do fallback"]


def test_stream_fallback_quando_stream_so_produz_eventos_filtrados() -> None:
    class _AgentStreamVazio:
        def invoke(self, *_a, **_k):
            return {"messages": [_Msg("resposta final")]}

        def stream(self, *_a, **_k):
            # Só eventos de tool (filtrados) -> nada visível -> empty_stream.
            yield (_ToolMsg("interno"), {"langgraph_node": "tools"})

    chunks = list(_backend_for(_AgentStreamVazio()).stream_answer("q", session_id="s"))

    assert chunks == ["resposta final"]


def test_stream_filtra_mensagens_de_tool_e_achata_blocos() -> None:
    class _AgentStream:
        def stream(self, *_a, **_k):
            yield (_Msg("Olá "), {"langgraph_node": "model"})
            yield (_ToolMsg("NAO DEVE VAZAR"), {"langgraph_node": "tools"})
            yield (_Msg([{"text": "mundo"}]), {"langgraph_node": "model"})

    chunks = list(_backend_for(_AgentStream()).stream_answer("q", session_id="s"))

    assert chunks == ["Olá ", "mundo"]
    assert "NAO DEVE VAZAR" not in "".join(chunks)
