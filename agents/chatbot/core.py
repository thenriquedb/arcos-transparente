"""Nucleo reutilizavel para experiencias de chat com o agente.

Este modulo nao conhece terminal, HTTP ou framework web. Adaptadores externos
devem depender de ChatbotApplication e de um AgentBackend.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import re
from typing import Any, Protocol
from uuid import uuid4

from agents.chatbot.agent import criar_agente_chatbot


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

    def __init__(self, agent_factory: Callable[[], Any] = criar_agente_chatbot) -> None:
        self._agent_factory = agent_factory
        self._agent = None

    def answer(self, question: str, session_id: str) -> ChatResponse:
        if self._agent is None:
            self._agent = self._agent_factory()

        result = self._agent.invoke(
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
        normalized_question = question.strip()
        if not normalized_question:
            raise ValueError("A pergunta nao pode ser vazia.")

        response = _build_local_response(normalized_question)
        if response is None:
            response = self.backend.answer(
                normalized_question,
                session_id=self.session.id,
            )

        self.session.history.append(
            ChatMessage(role="user", content=normalized_question)
        )
        self.session.history.append(
            ChatMessage(role="assistant", content=response.content)
        )

        return response

    def reset(self, session_id: str | None = None) -> ChatSession:
        self.session = ChatSession(id=session_id or str(uuid4()))
        return self.session


def _extract_last_message_content(result: dict[str, Any]) -> str:
    messages = result.get("messages") or []
    if not messages:
        return ""

    last_message = messages[-1]
    content = getattr(last_message, "content", last_message)
    return str(content)


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


def _normalize_text(text: str) -> str:
    import unicodedata

    normalized = unicodedata.normalize("NFD", text)
    without_accents = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    return " ".join(without_accents.lower().strip().split())
