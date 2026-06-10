"""Normalização de eventos de stream e conteúdo de mensagens do agente.

O runtime do chatbot recebe eventos em formatos variados (LangGraph tuples,
dicts, strings, mensagens tipadas). Este módulo concentra a conversão desses
formatos em texto visível ao usuário, mantendo o `core` focado em orquestração.
"""

from __future__ import annotations

from typing import Any


def extract_last_message_content(result: dict[str, Any]) -> str:
    """Extrai o conteúdo textual da última mensagem de um resultado de invoke."""

    messages = result.get("messages") or []
    if not messages:
        return ""

    last_message = messages[-1]
    content = getattr(last_message, "content", last_message)
    return str(content)


def extract_stream_chunk_content(event: Any) -> str:
    """Converte um evento de stream (em qualquer formato) em texto visível."""

    if event is None:
        return ""

    if _is_langgraph_message_event(event):
        message, metadata = event
        if not _is_user_visible_stream_message(message, metadata):
            return ""
        return extract_stream_chunk_content(message)

    if isinstance(event, str):
        return event

    if isinstance(event, bytes):
        return event.decode("utf-8", errors="ignore")

    if isinstance(event, dict):
        for key in ("content", "text", "delta"):
            content = content_to_text(event.get(key))
            if content:
                return content
        for key in ("message", "messages", "chunk", "data"):
            content = extract_stream_chunk_content(event.get(key))
            if content:
                return content
        return ""

    if isinstance(event, (tuple, list)):
        if len(event) == 2 and isinstance(event[1], dict):
            return extract_stream_chunk_content(event[0])
        for item in event:
            content = extract_stream_chunk_content(item)
            if content:
                return content
        return ""

    return content_to_text(getattr(event, "content", None))


def _is_langgraph_message_event(event: Any) -> bool:
    return isinstance(event, (tuple, list)) and len(event) == 2 and isinstance(event[1], dict)


def _is_user_visible_stream_message(message: Any, metadata: dict[str, Any]) -> bool:
    node_name = str(metadata.get("langgraph_node") or metadata.get("node") or metadata.get("name") or "").lower()
    if node_name in {"tool", "tools"} or node_name.endswith(":tools"):
        return False

    message_kind = str(getattr(message, "type", None) or getattr(message, "role", None) or "").lower()
    if message_kind in {"tool", "human", "system"}:
        return False

    class_name = message.__class__.__name__.lower()
    hidden_message_classes = ("toolmessage", "humanmessage", "systemmessage")
    return not any(hidden_class in class_name for hidden_class in hidden_message_classes)


def content_to_text(content: Any) -> str:
    """Achata conteúdo string/lista-de-blocos no texto concatenado."""

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)

    return ""
