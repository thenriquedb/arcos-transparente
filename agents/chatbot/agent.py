"""Configuracao do agente usado pelo modulo de chatbot."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from agents.chatbot.observability import (
    ObservabilityConfig,
    ObservabilityProvider,
    build_observability_provider,
    load_observability_config_from_env,
)
from agents.tools.registry import get_public_tools
from shared.runtime_config import (
    get_chatbot_system_prompt_path,
    load_project_env,
    read_required_env,
)
from shared.utils.dates import build_current_date_prompt_block

SUPPORTED_LLM_PROVIDER = "openai"
SYSTEM_PROMPT_PATH = get_chatbot_system_prompt_path()
CHECKPOINTER = InMemorySaver()


def _read_required_env(var_name: str) -> str:
    return read_required_env(var_name)


def obter_configuracao_llm() -> dict[str, str]:
    provider = _read_required_env("LLM_PROVIDER").lower()
    if provider != SUPPORTED_LLM_PROVIDER:
        raise ValueError(
            f"Provider nao suportado pelo chatbot: {provider}. Defina LLM_PROVIDER=openai no ambiente ou no .env."
        )

    model_name = _read_required_env("OPENAI_MODEL")
    api_key = _read_required_env("OPENAI_API_KEY")

    return {
        "provider": provider,
        "model_name": model_name,
        "api_key": api_key,
    }


def obter_configuracao_observabilidade() -> ObservabilityConfig:
    load_project_env()
    return load_observability_config_from_env()


def criar_provider_observabilidade() -> ObservabilityProvider:
    return build_observability_provider(obter_configuracao_observabilidade())


def criar_modelo_llm():
    config = obter_configuracao_llm()
    return ChatOpenAI(
        model=config["model_name"],
        api_key=config["api_key"],
    )


def carregar_system_prompt(*, hoje: date | None = None) -> str:
    base = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()
    return f"{base}\n\n{build_current_date_prompt_block(hoje)}"


def criar_agente_chatbot(*, tools: Sequence[object] | None = None):
    return create_agent(
        tools=list(tools) if tools is not None else get_public_tools(),
        model=criar_modelo_llm(),
        system_prompt=carregar_system_prompt(),
        checkpointer=CHECKPOINTER,
    )
