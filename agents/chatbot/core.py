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
from agents.chatbot.help_messages import build_scope_help_message
from agents.chatbot.hybrid_selection import HybridToolSelection, HybridToolSelector
from agents.chatbot.policy import evaluate_deterministic_policy
from agents.tools.registry import get_public_tools


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


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


@dataclass(frozen=True)
class PreparedRuntimeRequest:
    immediate_response: ChatResponse | None = None
    backend_question: str | None = None
    user_metadata: dict[str, Any] = field(default_factory=dict)
    selection: HybridToolSelection | None = None


class AgentBackend(Protocol):
    def answer(self, question: str, session_id: str) -> ChatResponse:
        """Responde uma pergunta usando a sessao informada."""


class ChatbotAgentBackend:
    """Backend que executa o agente conversacional do modulo de chatbot."""

    def __init__(
        self,
        agent_factory: Callable[..., Any] = criar_agente_chatbot,
    ) -> None:
        self._agent_factory = agent_factory
        self._agents: dict[tuple[str, ...], Any] = {}

    def _get_agent(self, candidate_tools: tuple[object, ...] | None = None):
        normalized_tools = self._normalize_candidate_tools(candidate_tools)
        cache_key = tuple(_tool_name(tool_obj) for tool_obj in normalized_tools)
        cached_agent = self._agents.get(cache_key)
        if cached_agent is not None:
            return cached_agent

        try:
            agent = self._agent_factory(tools=normalized_tools)
        except TypeError:
            agent = self._agent_factory()
        self._agents[cache_key] = agent
        return agent

    def _normalize_candidate_tools(
        self,
        candidate_tools: tuple[object, ...] | None,
    ) -> list[object]:
        if candidate_tools is None:
            return list(get_public_tools())
        return list(candidate_tools)

    def answer(self, question: str, session_id: str) -> ChatResponse:
        return self.answer_with_selection(question, session_id=session_id)

    def answer_with_selection(
        self,
        question: str,
        *,
        session_id: str,
        selection: HybridToolSelection | None = None,
    ) -> ChatResponse:
        agent = self._get_agent(
            selection.candidate_tools if selection is not None else None
        )

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
        return self.stream_answer_with_selection(question, session_id=session_id)

    def stream_answer_with_selection(
        self,
        question: str,
        *,
        session_id: str,
        selection: HybridToolSelection | None = None,
    ) -> Iterator[str]:
        """Responde em chunks quando o agente LangGraph suportar streaming."""

        agent = self._get_agent(
            selection.candidate_tools if selection is not None else None
        )
        stream = getattr(agent, "stream", None)
        if stream is None:
            yield self.answer_with_selection(
                question,
                session_id=session_id,
                selection=selection,
            ).content
            return

        try:
            events = stream(
                {"messages": [question]},
                {"configurable": {"thread_id": session_id}},
                stream_mode="messages",
            )
        except TypeError:
            yield self.answer_with_selection(
                question,
                session_id=session_id,
                selection=selection,
            ).content
            return

        yielded = False
        for event in events:
            content = _extract_stream_chunk_content(event)
            if not content:
                continue
            yielded = True
            yield content

        if not yielded:
            yield self.answer_with_selection(
                question,
                session_id=session_id,
                selection=selection,
            ).content


class ChatbotApplication:
    """Caso de uso de conversacao, independente do canal de entrada e saida."""

    def __init__(
        self,
        backend: AgentBackend | None = None,
        session: ChatSession | None = None,
        selector: HybridToolSelector | None = None,
    ) -> None:
        self.backend = backend or ChatbotAgentBackend()
        self.session = session or ChatSession()
        self.selector = selector or _build_default_selector(self.backend)

    def ask(self, question: str) -> ChatResponse:
        normalized_question = _normalize_question(question)
        prepared = _prepare_runtime_request(
            normalized_question,
            history=self.session.history,
            selector=self.selector,
        )
        if prepared.immediate_response is not None:
            response = prepared.immediate_response
        else:
            response = _answer_backend_with_selection(
                self.backend,
                question=prepared.backend_question or normalized_question,
                session_id=self.session.id,
                selection=prepared.selection,
            )
            response = _merge_response_metadata(
                response,
                _selection_metadata(prepared.selection),
            )

        self._record_exchange(
            normalized_question,
            response.content,
            user_metadata=prepared.user_metadata,
            metadata=response.metadata,
            guardrail_triggered=response.guardrail_triggered,
        )

        return response

    def stream(self, question: str) -> Iterator[str]:
        """Responde uma pergunta em streaming, preservando o contrato de historico."""

        normalized_question = _normalize_question(question)
        prepared = _prepare_runtime_request(
            normalized_question,
            history=self.session.history,
            selector=self.selector,
        )
        if prepared.immediate_response is not None:
            self._record_exchange(
                normalized_question,
                prepared.immediate_response.content,
                user_metadata=prepared.user_metadata,
                metadata=prepared.immediate_response.metadata,
                guardrail_triggered=prepared.immediate_response.guardrail_triggered,
            )
            return iter([prepared.immediate_response.content])

        stream_answer = getattr(self.backend, "stream_answer", None)
        if stream_answer is None:
            response = _answer_backend_with_selection(
                self.backend,
                question=prepared.backend_question or normalized_question,
                session_id=self.session.id,
                selection=prepared.selection,
            )
            response = _merge_response_metadata(
                response,
                _selection_metadata(prepared.selection),
            )
            self._record_exchange(
                normalized_question,
                response.content,
                user_metadata=prepared.user_metadata,
                metadata=response.metadata,
            )
            return iter([response.content])

        return self._stream_backend_response(
            normalized_question,
            prepared.backend_question or normalized_question,
            prepared.user_metadata,
            _selection_metadata(prepared.selection),
            prepared.selection,
        )

    def reset(self, session_id: str | None = None) -> ChatSession:
        self.session = ChatSession(id=session_id or str(uuid4()))
        return self.session

    def _record_exchange(
        self,
        question: str,
        answer: str,
        *,
        user_metadata: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        guardrail_triggered: bool = False,
    ) -> None:
        self.session.history.append(
            ChatMessage(
                role="user",
                content=question,
                metadata=dict(user_metadata or {}),
            )
        )
        assistant_metadata = dict(metadata or {})
        if guardrail_triggered:
            assistant_metadata["guardrail_triggered"] = True
        self.session.history.append(
            ChatMessage(
                role="assistant",
                content=answer,
                metadata=assistant_metadata,
            )
        )

    def _stream_backend_response(
        self,
        display_question: str,
        backend_question: str,
        user_metadata: dict[str, Any],
        assistant_metadata: dict[str, Any],
        selection: HybridToolSelection | None,
    ) -> Iterator[str]:
        chunks: list[str] = []
        stream_answer_with_selection = getattr(
            self.backend,
            "stream_answer_with_selection",
            None,
        )
        if stream_answer_with_selection is not None:
            chunk_stream = stream_answer_with_selection(
                backend_question,
                session_id=self.session.id,
                selection=selection,
            )
        else:
            stream_answer = getattr(self.backend, "stream_answer")
            chunk_stream = stream_answer(backend_question, session_id=self.session.id)

        for chunk in chunk_stream:
            content = str(chunk)
            if not content:
                continue
            chunks.append(content)
            yield content

        final_content = "".join(chunks)
        if not final_content:
            response = _answer_backend_with_selection(
                self.backend,
                question=backend_question,
                session_id=self.session.id,
                selection=selection,
            )
            response = _merge_response_metadata(response, assistant_metadata)
            final_content = response.content
            if final_content:
                yield final_content
            assistant_metadata = dict(response.metadata)

        self._record_exchange(
            display_question,
            final_content,
            user_metadata=user_metadata,
            metadata=assistant_metadata,
        )


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


def _normalize_question(question: str) -> str:
    return question.strip()


def _prepare_runtime_request(
    question: str,
    *,
    history: list[ChatMessage],
    selector: HybridToolSelector,
) -> PreparedRuntimeRequest:
    local_response = _build_local_response(question)
    if local_response is not None:
        return PreparedRuntimeRequest(immediate_response=local_response)

    policy = evaluate_deterministic_policy(question, history=history)
    if policy.action == "block":
        return PreparedRuntimeRequest(
            immediate_response=ChatResponse(
                content=policy.message or "",
                guardrail_triggered=True,
                metadata={
                    "guardrail_category": policy.category,
                    **policy.assistant_metadata,
                },
            ),
            user_metadata=policy.user_metadata,
        )
    if policy.action == "clarify":
        return PreparedRuntimeRequest(
            immediate_response=ChatResponse(
                content=policy.message or "",
                metadata=policy.assistant_metadata,
            ),
            user_metadata=policy.user_metadata,
        )

    backend_question = policy.resolved_question or question
    selection = selector.select(backend_question, history=history)
    if selection.action != "allow":
        return PreparedRuntimeRequest(
            immediate_response=ChatResponse(
                content=selection.message or "",
                metadata=_selection_metadata(selection),
            ),
            user_metadata=policy.user_metadata,
        )

    return PreparedRuntimeRequest(
        backend_question=backend_question,
        user_metadata=policy.user_metadata,
        selection=selection,
    )


def _normalize_text(text: str) -> str:
    import unicodedata

    normalized = unicodedata.normalize("NFD", text)
    without_accents = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    return " ".join(without_accents.lower().strip().split())


def _build_local_response(question: str) -> ChatResponse | None:
    normalized = _normalize_text(question)
    if re.fullmatch(r"(quem e voce|quem voce e|o que voce faz)\??", normalized):
        return ChatResponse(
            content=(
                "Sou o assistente do projeto Arcos Transparente. Ajudo a consultar "
                "os dados públicos municipais disponíveis na base local, como "
                "servidores, folha de pagamento, contratos, licitações, despesas, "
                "diárias, passagens, frota e veículos, receitas, transferências "
                "financeiras, emendas parlamentares, patrimônio, planejamento, "
                "quadro de pessoal e eleitos."
            ),
            metadata={"local_response": "identity"},
        )
    if re.fullmatch(
        r"(o que posso perguntar|o que eu posso perguntar|o que posso consultar|sobre o que voce pode responder)\??",
        normalized,
    ):
        return ChatResponse(
            content=build_scope_help_message(),
            metadata={"local_response": "scope_help"},
        )
    return None


def _answer_backend_with_selection(
    backend: AgentBackend,
    *,
    question: str,
    session_id: str,
    selection: HybridToolSelection | None,
) -> ChatResponse:
    answer_with_selection = getattr(backend, "answer_with_selection", None)
    if answer_with_selection is not None:
        return answer_with_selection(
            question,
            session_id=session_id,
            selection=selection,
        )
    return backend.answer(question, session_id=session_id)


def _selection_metadata(
    selection: HybridToolSelection | None,
) -> dict[str, Any]:
    if selection is None:
        return {}
    return {
        "selection_action": selection.action,
        "selected_tool_names": list(selection.candidate_tool_names),
        "selection_confidence": selection.confidence,
        "selection_reason_code": selection.reason_code,
        "selection_fallback": selection.used_fallback,
    }


def _merge_response_metadata(
    response: ChatResponse,
    extra_metadata: dict[str, Any],
) -> ChatResponse:
    if not extra_metadata:
        return response
    merged_metadata = dict(response.metadata)
    merged_metadata.update(extra_metadata)
    return ChatResponse(
        content=response.content,
        guardrail_triggered=response.guardrail_triggered,
        metadata=merged_metadata,
        raw_result=response.raw_result,
    )


def _build_default_selector(backend: AgentBackend) -> HybridToolSelector:
    if isinstance(backend, ChatbotAgentBackend):
        return HybridToolSelector()
    return HybridToolSelector(runner=_non_agent_backend_selector_runner)


def _non_agent_backend_selector_runner(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    return {
        "action": "allow",
        "candidate_tool_names": [],
        "confidence": "low",
        "reason_code": "backend_without_selector_support",
    }


def _tool_name(tool_obj: object) -> str:
    return str(getattr(tool_obj, "name", getattr(tool_obj, "__name__", "")))
