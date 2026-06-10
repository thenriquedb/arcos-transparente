"""Compatibilidade: reexporta a API publica do nucleo de chatbot.

A implementacao foi dividida em modulos focados:

- ``agents.chatbot._shared``: tipos compartilhados que cruzam a fronteira
  backend/aplicacao (ChatMessage, ChatResponse, ChatSession, AgentBackend).
- ``agents.chatbot.backend``: ChatbotAgentBackend, que executa o agente.
- ``agents.chatbot.application``: ChatbotApplication, o caso de uso de conversa.

Importadores existentes podem continuar usando ``agents.chatbot.core``.
"""

from __future__ import annotations

from agents.chatbot._shared import (
    AgentBackend,
    ChatMessage,
    ChatResponse,
    ChatSession,
)
from agents.chatbot.application import ChatbotApplication, PreparedRuntimeRequest
from agents.chatbot.backend import ChatbotAgentBackend


__all__ = [
    "AgentBackend",
    "ChatMessage",
    "ChatResponse",
    "ChatSession",
    "ChatbotAgentBackend",
    "ChatbotApplication",
    "PreparedRuntimeRequest",
]
