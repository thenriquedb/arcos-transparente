"""Backend que executa o agente conversacional LangChain do chatbot.

Adaptadores externos devem depender de ChatbotApplication; este modulo isola a
execucao do agente, o cache de agentes por subconjunto de tools e a emissao de
spans de observabilidade ao redor de cada invocacao.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterator
from typing import Any

from agents.chatbot._shared import ChatResponse
from agents.chatbot.agent import criar_agente_chatbot
from agents.chatbot.hybrid_selection import HybridToolSelection
from agents.chatbot.observability import (
    NoOpObservabilityProvider,
    ObservabilityProvider,
    build_error_payload,
    build_event_payload,
)
from agents.chatbot.streaming import (
    extract_last_message_content,
    extract_stream_chunk_content,
)
from agents.tools.registry import get_public_tools


class ChatbotAgentBackend:
    """Backend que executa o agente conversacional do modulo de chatbot."""

    def __init__(
        self,
        agent_factory: Callable[..., Any] = criar_agente_chatbot,
        observability_provider: ObservabilityProvider | None = None,
    ) -> None:
        self._agent_factory = agent_factory
        self._agents: dict[tuple[str, ...], Any] = {}
        # O backend e compartilhado entre sessoes e invocado concorrentemente
        # (ex.: Chainlit roda `ask` num threadpool). O lock garante criacao
        # atomica do agente por cache_key, evitando builds duplicados/corrida.
        self._agents_lock = threading.Lock()
        self._observability_provider = observability_provider or NoOpObservabilityProvider()

    def _get_agent(self, candidate_tools: tuple[object, ...] | None = None):
        normalized_tools = self._normalize_candidate_tools(candidate_tools)
        cache_key = tuple(_tool_name(tool_obj) for tool_obj in normalized_tools)
        cached_agent = self._agents.get(cache_key)

        if cached_agent is not None:
            return cached_agent

        with self._agents_lock:
            # Double-checked: outra thread pode ter criado enquanto aguardavamos.
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

    def set_observability_provider(
        self,
        provider: ObservabilityProvider,
    ) -> None:
        self._observability_provider = provider

    def answer(self, question: str, session_id: str) -> ChatResponse:
        return self.answer_with_selection(question, session_id=session_id)

    def answer_with_selection(
        self,
        question: str,
        *,
        session_id: str,
        selection: HybridToolSelection | None = None,
    ) -> ChatResponse:
        agent = self._get_agent(selection.candidate_tools if selection is not None else None)

        with self._observability_provider.span(
            "chatbot.agent.invoke",
            inputs=build_event_payload(
                {
                    "session_id": session_id,
                    "backend_question": question,
                    "selected_tool_names": (list(selection.candidate_tool_names) if selection else []),
                }
            ),
            metadata=build_event_payload({"surface": "backend_answer"}),
            tags=("chatbot", "backend"),
        ) as span:
            try:
                result = agent.invoke(
                    {"messages": [question]},
                    {"configurable": {"thread_id": session_id}},
                )
            except Exception as exc:
                span.set_metadata(
                    build_error_payload(
                        exc,
                        extra={"session_id": session_id, "status": "error"},
                    )
                )
                raise

            content = extract_last_message_content(result)
            response = ChatResponse(
                content=content,
                guardrail_triggered=bool(result.get("guardrail_triggered", False)),
                metadata={
                    "guardrail_category": result.get("guardrail_category"),
                },
                raw_result=result,
            )
            span.set_outputs(
                build_event_payload(
                    {
                        "session_id": session_id,
                        "status": "completed",
                        "response_preview": content,
                        "guardrail_triggered": response.guardrail_triggered,
                    }
                )
            )
            return response

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

        agent = self._get_agent(selection.candidate_tools if selection is not None else None)
        with self._observability_provider.span(
            "chatbot.agent.stream",
            inputs=build_event_payload(
                {
                    "session_id": session_id,
                    "backend_question": question,
                    "selected_tool_names": (list(selection.candidate_tool_names) if selection else []),
                    "streaming": True,
                }
            ),
            metadata=build_event_payload({"surface": "backend_stream"}),
            tags=("chatbot", "backend", "stream"),
        ) as span:
            stream = getattr(agent, "stream", None)
            if stream is None:
                span.set_outputs(
                    build_event_payload(
                        {
                            "session_id": session_id,
                            "status": "fallback",
                            "fallback_used": True,
                            "reason_code": "stream_not_supported",
                        }
                    )
                )
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
                span.set_outputs(
                    build_event_payload(
                        {
                            "session_id": session_id,
                            "status": "fallback",
                            "fallback_used": True,
                            "reason_code": "stream_type_error",
                        }
                    )
                )
                yield self.answer_with_selection(
                    question,
                    session_id=session_id,
                    selection=selection,
                ).content
                return
            except Exception as exc:
                span.set_metadata(
                    build_error_payload(
                        exc,
                        extra={"session_id": session_id, "status": "error"},
                    )
                )
                raise

            yielded = False
            chunks: list[str] = []

            for event in events:
                content = extract_stream_chunk_content(event)
                if not content:
                    continue
                yielded = True
                chunks.append(content)
                yield content

            if not yielded:
                span.set_outputs(
                    build_event_payload(
                        {
                            "session_id": session_id,
                            "status": "fallback",
                            "fallback_used": True,
                            "reason_code": "empty_stream",
                        }
                    )
                )
                yield self.answer_with_selection(
                    question,
                    session_id=session_id,
                    selection=selection,
                ).content
                return

            span.set_outputs(
                build_event_payload(
                    {
                        "session_id": session_id,
                        "status": "completed",
                        "streaming": True,
                        "response_preview": "".join(chunks),
                    }
                )
            )


def _tool_name(tool_obj: object) -> str:
    return str(getattr(tool_obj, "name", getattr(tool_obj, "__name__", "")))
