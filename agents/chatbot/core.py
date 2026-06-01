"""Nucleo reutilizavel para experiencias de chat com o agente.

Este modulo nao conhece terminal, HTTP ou framework web. Adaptadores externos
devem depender de ChatbotApplication e de um AgentBackend.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
import re
from typing import Any, Protocol
from uuid import uuid4

from agents.chatbot.agent import criar_agente_chatbot
from agents.guardrails import evaluate_public_query_guardrails
from agents.router import route_user_query


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


@dataclass(frozen=True)
class ChatResponse:
    content: str
    guardrail_triggered: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    raw_result: Any | None = None


@dataclass
class ChatSession:
    id: str = field(default_factory=lambda: str(uuid4()))
    history: list[ChatMessage] = field(default_factory=list)


class AgentBackend(Protocol):
    def answer(self, question: str, session_id: str) -> ChatResponse:
        """Responde uma pergunta usando a sessao informada."""


class ChatbotAgentBackend:
    """Backend que executa o agente conversacional do modulo de chatbot."""

    def __init__(
        self,
        agent_factory: Callable[[], Any] = criar_agente_chatbot,
    ) -> None:
        self._agent_factory = agent_factory
        self._agent = None

    def _get_agent(self):
        if self._agent is None:
            self._agent = self._agent_factory()
        return self._agent

    def answer(self, question: str, session_id: str) -> ChatResponse:
        agent = self._get_agent()

        result = agent.invoke(
            {"messages": [question]},
            {"configurable": {"thread_id": session_id}},
        )
        content = _extract_last_message_content(result)

        return ChatResponse(
            content=content,
            guardrail_triggered=bool(result.get("guardrail_triggered", False)),
            metadata={
                "guardrail_category": result.get("guardrail_category"),
            },
            raw_result=result,
        )

    def stream_answer(self, question: str, session_id: str) -> Iterator[str]:
        """Responde em chunks quando o agente LangGraph suportar streaming."""

        agent = self._get_agent()
        stream = getattr(agent, "stream", None)
        if stream is None:
            yield self.answer(question, session_id=session_id).content
            return

        try:
            events = stream(
                {"messages": [question]},
                {"configurable": {"thread_id": session_id}},
                stream_mode="messages",
            )
        except TypeError:
            yield self.answer(question, session_id=session_id).content
            return

        yielded = False
        for event in events:
            content = _extract_stream_chunk_content(event)
            if not content:
                continue
            yielded = True
            yield content

        if not yielded:
            yield self.answer(question, session_id=session_id).content


class ChatbotApplication:
    """Caso de uso de conversacao, independente do canal de entrada e saida."""

    def __init__(
        self,
        backend: AgentBackend | None = None,
        session: ChatSession | None = None,
    ) -> None:
        self.backend = backend or ChatbotAgentBackend()
        self.session = session or ChatSession()

    def ask(self, question: str) -> ChatResponse:
        normalized_question = _validate_question(question)

        response = _build_local_response(normalized_question)
        if response is None:
            response = _build_guardrail_response(
                normalized_question,
                has_history=bool(self.session.history),
            )
        if response is None:
            response = self.backend.answer(
                normalized_question,
                session_id=self.session.id,
            )

        self._record_exchange(normalized_question, response.content)

        return response

    def stream(self, question: str) -> Iterator[str]:
        """Responde uma pergunta em streaming, preservando o contrato de historico."""

        normalized_question = _validate_question(question)
        response = _build_local_response(normalized_question)
        if response is not None:
            self._record_exchange(normalized_question, response.content)
            return iter([response.content])

        response = _build_guardrail_response(
            normalized_question,
            has_history=bool(self.session.history),
        )
        if response is not None:
            self._record_exchange(normalized_question, response.content)
            return iter([response.content])

        stream_answer = getattr(self.backend, "stream_answer", None)
        if stream_answer is None:
            response = self.backend.answer(
                normalized_question,
                session_id=self.session.id,
            )
            self._record_exchange(normalized_question, response.content)
            return iter([response.content])

        return self._stream_backend_response(
            normalized_question,
            normalized_question,
            stream_answer,
        )

    def reset(self, session_id: str | None = None) -> ChatSession:
        self.session = ChatSession(id=session_id or str(uuid4()))
        return self.session

    def _record_exchange(self, question: str, answer: str) -> None:
        self.session.history.append(ChatMessage(role="user", content=question))
        self.session.history.append(ChatMessage(role="assistant", content=answer))

    def _stream_backend_response(
        self,
        display_question: str,
        backend_question: str,
        stream_answer: Callable[..., Iterator[str]],
    ) -> Iterator[str]:
        chunks: list[str] = []

        for chunk in stream_answer(backend_question, session_id=self.session.id):
            content = str(chunk)
            if not content:
                continue
            chunks.append(content)
            yield content

        final_content = "".join(chunks)
        if not final_content:
            response = self.backend.answer(
                backend_question,
                session_id=self.session.id,
            )
            final_content = response.content
            if final_content:
                yield final_content

        self._record_exchange(display_question, final_content)


def _extract_last_message_content(result: dict[str, Any]) -> str:
    messages = result.get("messages") or []
    if not messages:
        return ""

    last_message = messages[-1]
    content = getattr(last_message, "content", last_message)
    # return messages
    return str(content)


def _extract_stream_chunk_content(event: Any) -> str:
    if event is None:
        return ""

    if _is_langgraph_message_event(event):
        message, metadata = event
        if not _is_user_visible_stream_message(message, metadata):
            return ""
        return _extract_stream_chunk_content(message)

    if isinstance(event, str):
        return event

    if isinstance(event, bytes):
        return event.decode("utf-8", errors="ignore")

    if isinstance(event, dict):
        for key in ("content", "text", "delta"):
            content = _content_to_text(event.get(key))
            if content:
                return content
        for key in ("message", "messages", "chunk", "data"):
            content = _extract_stream_chunk_content(event.get(key))
            if content:
                return content
        return ""

    if isinstance(event, (tuple, list)):
        if len(event) == 2 and isinstance(event[1], dict):
            return _extract_stream_chunk_content(event[0])
        for item in event:
            content = _extract_stream_chunk_content(item)
            if content:
                return content
        return ""

    return _content_to_text(getattr(event, "content", None))


def _is_langgraph_message_event(event: Any) -> bool:
    return (
        isinstance(event, (tuple, list))
        and len(event) == 2
        and isinstance(event[1], dict)
    )


def _is_user_visible_stream_message(message: Any, metadata: dict[str, Any]) -> bool:
    node_name = str(
        metadata.get("langgraph_node")
        or metadata.get("node")
        or metadata.get("name")
        or ""
    ).lower()
    if node_name in {"tool", "tools"} or node_name.endswith(":tools"):
        return False

    message_kind = str(
        getattr(message, "type", None) or getattr(message, "role", None) or ""
    ).lower()
    if message_kind in {"tool", "human", "system"}:
        return False

    class_name = message.__class__.__name__.lower()
    hidden_message_classes = ("toolmessage", "humanmessage", "systemmessage")
    return not any(
        hidden_class in class_name for hidden_class in hidden_message_classes
    )


def _content_to_text(content: Any) -> str:
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


def _validate_question(question: str) -> str:
    normalized_question = question.strip()
    if not normalized_question:
        raise ValueError("A pergunta nao pode ser vazia.")
    return normalized_question


def _build_local_response(question: str) -> ChatResponse | None:
    normalized = _normalize_text(question)
    if re.fullmatch(r"(quem e voce|quem voce e|o que voce faz)\??", normalized):
        return ChatResponse(
            content=(
                "Sou o assistente do projeto Arcos Transparente. Ajudo a consultar "
                "os dados públicos municipais disponíveis na base local, como "
                "servidores, folha de pagamento, contratos, licitações, despesas, "
                "receitas, patrimônio, planejamento, quadro de pessoal e eleitos."
            ),
            metadata={"local_response": "identity"},
        )
    return None


def _build_guardrail_response(
    question: str,
    *,
    has_history: bool,
) -> ChatResponse | None:
    route = route_user_query(question)
    decision = evaluate_public_query_guardrails(
        question,
        compatibility_route=route,
        has_history=has_history,
    )
    if decision.allowed:
        return None

    return ChatResponse(
        content=decision.message or "",
        guardrail_triggered=True,
        metadata={"guardrail_category": decision.category},
    )


def _normalize_text(text: str) -> str:
    import unicodedata

    normalized = unicodedata.normalize("NFD", text)
    without_accents = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    return " ".join(without_accents.lower().strip().split())
