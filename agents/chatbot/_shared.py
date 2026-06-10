"""Tipos compartilhados entre o backend do agente e a aplicacao de chatbot.

Estes contratos descrevem as mensagens, respostas e sessoes que cruzam a
fronteira entre ChatbotAgentBackend e ChatbotApplication, alem do protocolo de
backend que a aplicacao consome. Nenhum deles conhece terminal, HTTP ou
framework web.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import uuid4


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


class AgentBackend(Protocol):
    def answer(self, question: str, session_id: str) -> ChatResponse:
        """Responde uma pergunta usando a sessao informada."""
