"""Camada de aplicacao de chatbot para o agente do projeto."""

from __future__ import annotations

from importlib import import_module
from typing import Any


__all__ = [
    "AgentBackend",
    "ChatbotAgentBackend",
    "ChatMessage",
    "ChatResponse",
    "ChatSession",
    "ChatbotApplication",
]


def __getattr__(name: str) -> Any:
    if name not in __all__:
        raise AttributeError(f"module 'agents.chatbot' has no attribute {name!r}")

    core = import_module("agents.chatbot.core")
    return getattr(core, name)
