"""Caso de uso de conversacao, independente do canal de entrada e saida.

Este modulo nao conhece terminal, HTTP ou framework web. Adaptadores externos
devem depender de ChatbotApplication e de um AgentBackend.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
import inspect
import re
from typing import Any
from uuid import uuid4

from agents.chatbot._shared import (
    AgentBackend,
    ChatMessage,
    ChatResponse,
    ChatSession,
)
from agents.chatbot.agent import criar_provider_observabilidade
from agents.chatbot.backend import ChatbotAgentBackend
from agents.chatbot.help_messages import build_scope_help_message
from agents.chatbot.hybrid_selection import HybridToolSelection, HybridToolSelector
from agents.chatbot.observability import (
    ObservabilityProvider,
    build_error_payload,
    build_event_payload,
    use_observability_provider,
)
from agents.chatbot.policy import evaluate_deterministic_policy


@dataclass(frozen=True)
class PreparedRuntimeRequest:
    immediate_response: ChatResponse | None = None
    backend_question: str | None = None
    user_metadata: dict[str, Any] = field(default_factory=dict)
    selection: HybridToolSelection | None = None


class ChatbotApplication:
    """Caso de uso de conversacao, independente do canal de entrada e saida."""

    def __init__(
        self,
        backend: AgentBackend | None = None,
        session: ChatSession | None = None,
        selector: HybridToolSelector | None = None,
        observability_provider: ObservabilityProvider | None = None,
    ) -> None:
        provider = observability_provider or criar_provider_observabilidade()
        self.observability_provider = provider
        self.backend = backend or ChatbotAgentBackend(observability_provider=provider)
        if isinstance(self.backend, ChatbotAgentBackend):
            self.backend.set_observability_provider(provider)
        self.session = session or ChatSession()
        self.selector = selector or _build_default_selector(
            self.backend,
            observability_provider=provider,
        )
        if hasattr(self.selector, "set_observability_provider"):
            self.selector.set_observability_provider(provider)

    def ask(self, question: str) -> ChatResponse:
        normalized_question = _normalize_question(question)
        request_id = str(uuid4())
        with use_observability_provider(self.observability_provider):
            with self.observability_provider.span(
                "chatbot.request",
                inputs=build_event_payload(
                    {
                        "request_id": request_id,
                        "session_id": self.session.id,
                        "question": normalized_question,
                        "history_size": len(self.session.history),
                    }
                ),
                metadata=build_event_payload(
                    {
                        "surface": "ask",
                        "provider": self.observability_provider.name,
                    }
                ),
                tags=("chatbot", "request"),
            ) as request_span:
                try:
                    prepared = _prepare_runtime_request(
                        normalized_question,
                        history=self.session.history,
                        selector=self.selector,
                        observability_provider=self.observability_provider,
                        request_id=request_id,
                        session_id=self.session.id,
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
                    request_span.set_outputs(
                        _build_request_completion_payload(
                            request_id=request_id,
                            session_id=self.session.id,
                            response=response,
                            selection=prepared.selection,
                            status=(
                                "blocked"
                                if response.guardrail_triggered
                                else _infer_request_status(prepared, response)
                            ),
                        )
                    )
                    return response
                except Exception as exc:
                    request_span.set_metadata(
                        build_error_payload(
                            exc,
                            extra={
                                "request_id": request_id,
                                "session_id": self.session.id,
                                "status": "error",
                            },
                        )
                    )
                    raise

    def stream(self, question: str) -> Iterator[str]:
        """Responde uma pergunta em streaming, preservando o contrato de historico."""

        normalized_question = _normalize_question(question)
        request_id = str(uuid4())

        def response_stream() -> Iterator[str]:
            with use_observability_provider(self.observability_provider):
                with self.observability_provider.span(
                    "chatbot.request",
                    inputs=build_event_payload(
                        {
                            "request_id": request_id,
                            "session_id": self.session.id,
                            "question": normalized_question,
                            "history_size": len(self.session.history),
                            "streaming": True,
                        }
                    ),
                    metadata=build_event_payload(
                        {
                            "surface": "stream",
                            "provider": self.observability_provider.name,
                        }
                    ),
                    tags=("chatbot", "request", "stream"),
                ) as request_span:
                    try:
                        prepared = _prepare_runtime_request(
                            normalized_question,
                            history=self.session.history,
                            selector=self.selector,
                            observability_provider=self.observability_provider,
                            request_id=request_id,
                            session_id=self.session.id,
                        )
                        if prepared.immediate_response is not None:
                            self._record_exchange(
                                normalized_question,
                                prepared.immediate_response.content,
                                user_metadata=prepared.user_metadata,
                                metadata=prepared.immediate_response.metadata,
                                guardrail_triggered=prepared.immediate_response.guardrail_triggered,
                            )
                            request_span.set_outputs(
                                _build_request_completion_payload(
                                    request_id=request_id,
                                    session_id=self.session.id,
                                    response=prepared.immediate_response,
                                    selection=prepared.selection,
                                    status=(
                                        "blocked"
                                        if prepared.immediate_response.guardrail_triggered
                                        else _infer_request_status(
                                            prepared,
                                            prepared.immediate_response,
                                        )
                                    ),
                                    streaming=True,
                                )
                            )
                            yield prepared.immediate_response.content
                            return

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
                            request_span.set_outputs(
                                _build_request_completion_payload(
                                    request_id=request_id,
                                    session_id=self.session.id,
                                    response=response,
                                    selection=prepared.selection,
                                    status="completed",
                                    streaming=True,
                                )
                            )
                            yield response.content
                            return

                        final_content = yield from self._stream_backend_response(
                            normalized_question,
                            prepared.backend_question or normalized_question,
                            prepared.user_metadata,
                            _selection_metadata(prepared.selection),
                            prepared.selection,
                        )
                        request_span.set_outputs(
                            build_event_payload(
                                {
                                    "request_id": request_id,
                                    "session_id": self.session.id,
                                    "status": "completed",
                                    "streaming": True,
                                    "selected_tool_names": (
                                        list(prepared.selection.candidate_tool_names) if prepared.selection else []
                                    ),
                                    "response_preview": final_content,
                                }
                            )
                        )
                    except Exception as exc:
                        request_span.set_metadata(
                            build_error_payload(
                                exc,
                                extra={
                                    "request_id": request_id,
                                    "session_id": self.session.id,
                                    "status": "error",
                                },
                            )
                        )
                        raise

        return response_stream()

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
        return final_content


def _normalize_question(question: str) -> str:
    return question.strip()


def _prepare_runtime_request(
    question: str,
    *,
    history: list[ChatMessage],
    selector: HybridToolSelector,
    observability_provider: ObservabilityProvider,
    request_id: str,
    session_id: str,
) -> PreparedRuntimeRequest:
    local_response = _build_local_response(question)
    if local_response is not None:
        observability_provider.emit_event(
            "chatbot.local_response",
            inputs=build_event_payload(
                {
                    "request_id": request_id,
                    "session_id": session_id,
                    "question": question,
                    "history_size": len(history),
                }
            ),
            outputs=build_event_payload(
                {
                    "status": "local_response",
                    "local_response": local_response.metadata.get("local_response"),
                    "response_preview": local_response.content,
                }
            ),
            tags=("chatbot", "policy", "local"),
        )
        return PreparedRuntimeRequest(immediate_response=local_response)

    policy = evaluate_deterministic_policy(question, history=history)
    observability_provider.emit_event(
        "chatbot.policy",
        inputs=build_event_payload(
            {
                "request_id": request_id,
                "session_id": session_id,
                "question": question,
                "history_size": len(history),
            }
        ),
        outputs=build_event_payload(
            {
                "policy_action": policy.action,
                "policy_category": policy.category,
                "resolved_question": policy.resolved_question,
                "status": policy.action,
            }
        ),
        tags=("chatbot", "policy"),
    )
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
    selection = _select_with_runtime_context(
        selector,
        backend_question,
        history=history,
        request_id=request_id,
        session_id=session_id,
    )
    if selection.action != "allow":
        return PreparedRuntimeRequest(
            immediate_response=ChatResponse(
                content=selection.message or "",
                metadata=_selection_metadata(selection),
            ),
            user_metadata=policy.user_metadata,
            selection=selection,
        )

    return PreparedRuntimeRequest(
        backend_question=backend_question,
        user_metadata=policy.user_metadata,
        selection=selection,
    )


def _normalize_text(text: str) -> str:
    import unicodedata

    normalized = unicodedata.normalize("NFD", text)
    without_accents = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
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


def _build_default_selector(
    backend: AgentBackend,
    *,
    observability_provider: ObservabilityProvider,
) -> HybridToolSelector:
    if isinstance(backend, ChatbotAgentBackend):
        return HybridToolSelector(observability_provider=observability_provider)
    return HybridToolSelector(
        runner=_non_agent_backend_selector_runner,
        observability_provider=observability_provider,
    )


def _select_with_runtime_context(
    selector: HybridToolSelector,
    question: str,
    *,
    history: list[ChatMessage],
    request_id: str,
    session_id: str,
) -> HybridToolSelection:
    select_signature = inspect.signature(selector.select)
    if "request_id" in select_signature.parameters:
        return selector.select(
            question,
            history=history,
            request_id=request_id,
            session_id=session_id,
        )
    return selector.select(question, history=history)


def _non_agent_backend_selector_runner(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    return {
        "action": "allow",
        "candidate_tool_names": [],
        "confidence": "low",
        "reason_code": "backend_without_selector_support",
    }


def _build_request_completion_payload(
    *,
    request_id: str,
    session_id: str,
    response: ChatResponse,
    selection: HybridToolSelection | None,
    status: str,
    streaming: bool = False,
) -> dict[str, Any]:
    payload = {
        "request_id": request_id,
        "session_id": session_id,
        "status": status,
        "response_preview": response.content,
        "guardrail_triggered": response.guardrail_triggered,
        "streaming": streaming,
    }
    payload.update(_selection_metadata(selection))
    return build_event_payload(payload)


def _infer_request_status(
    prepared: PreparedRuntimeRequest,
    response: ChatResponse,
) -> str:
    if prepared.selection is not None and prepared.selection.action != "allow":
        return prepared.selection.action
    if response.metadata.get("policy_action") == "clarify":
        return "clarify"
    if response.metadata.get("local_response"):
        return "local_response"
    if prepared.immediate_response is not None:
        return "completed"
    return "completed"
