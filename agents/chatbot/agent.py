"""Configuracao do agente usado pelo modulo de chatbot."""

from __future__ import annotations

from collections.abc import Sequence
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from agents.tools.registry import get_public_tools

load_dotenv()

DEFAULT_MODEL_PROVIDER = "openai"
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SYSTEM_PROMPT_PATH = PROJECT_ROOT / "docs" / "agent-system-prompt.md"
CHECKPOINTER = InMemorySaver()


def obter_configuracao_llm() -> dict[str, str]:
    provider = (
        (
            os.getenv("LLM_PROVIDER")
            or os.getenv("MODEL_PROVIDER")
            or DEFAULT_MODEL_PROVIDER
        )
        .strip()
        .lower()
    )
    if provider != DEFAULT_MODEL_PROVIDER:
        raise ValueError(
            f"Provider nao suportado pelo chatbot: {provider}. Use apenas 'openai'."
        )

    model_name = (
        os.getenv("OPENAI_MODEL") or os.getenv("AGENT_MODEL") or DEFAULT_OPENAI_MODEL
    ).strip()
    if not model_name:
        raise ValueError("OPENAI_MODEL deve ser informado.")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY nao configurada.")

    return {
        "provider": provider,
        "model_name": model_name,
    }


def criar_modelo_llm():
    config = obter_configuracao_llm()
    return ChatOpenAI(model=config["model_name"])


def carregar_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()


def criar_agente_chatbot(*, tools: Sequence[object] | None = None):
    return create_agent(
        tools=list(tools) if tools is not None else get_public_tools(),
        model=criar_modelo_llm(),
        system_prompt=carregar_system_prompt(),
        checkpointer=CHECKPOINTER,
    )
