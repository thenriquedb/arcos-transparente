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

SUPPORTED_LLM_PROVIDER = "openai"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SYSTEM_PROMPT_PATH = PROJECT_ROOT / "docs" / "agent-system-prompt.md"
CHECKPOINTER = InMemorySaver()


def _read_required_env(var_name: str) -> str:
    value = os.getenv(var_name)
    if value is None or not value.strip():
        raise ValueError(f"{var_name} deve ser informado no ambiente ou no .env.")
    return value.strip()


def obter_configuracao_llm() -> dict[str, str]:
    provider = _read_required_env("LLM_PROVIDER").lower()
    if provider != SUPPORTED_LLM_PROVIDER:
        raise ValueError(
            f"Provider nao suportado pelo chatbot: {provider}. "
            "Defina LLM_PROVIDER=openai no ambiente ou no .env."
        )

    model_name = _read_required_env("OPENAI_MODEL")
    api_key = _read_required_env("OPENAI_API_KEY")

    return {
        "provider": provider,
        "model_name": model_name,
        "api_key": api_key,
    }


def criar_modelo_llm():
    config = obter_configuracao_llm()
    return ChatOpenAI(
        model=config["model_name"],
        api_key=config["api_key"],
    )


def carregar_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()


def criar_agente_chatbot(*, tools: Sequence[object] | None = None):
    return create_agent(
        tools=list(tools) if tools is not None else get_public_tools(),
        model=criar_modelo_llm(),
        system_prompt=carregar_system_prompt(),
        checkpointer=CHECKPOINTER,
    )
