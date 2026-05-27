import os
from pathlib import Path
from langchain.agents import create_agent
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from pprint import pprint

from agents.router import (
    evaluate_query_guardrails,
    route_user_query,
    select_public_tools_for_query,
)
from agents.tools.registry import get_public_tools

load_dotenv()

DEFAULT_MODEL_PROVIDER = "openai"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent / "docs" / "agent-system-prompt.md"


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
            f"Provider nao suportado nesta fase: {provider}. Use apenas 'openai'."
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


def criar_agente(pergunta: str | None = None):
    if pergunta is not None:
        guardrail = evaluate_query_guardrails(pergunta)
        if not guardrail.allowed:
            raise ValueError(
                guardrail.message or "Pergunta bloqueada pelos guardrails."
            )

    tools = select_public_tools_for_query(pergunta)

    return create_agent(
        tools=tools,
        model=criar_modelo_llm(),
        system_prompt=carregar_system_prompt(),
    )


def ferramentas_publicas_disponiveis() -> list[str]:
    return [
        getattr(tool_obj, "name", getattr(tool_obj, "__name__", ""))
        for tool_obj in get_public_tools()
    ]


def responder_pergunta(pergunta: str):
    guardrail = evaluate_query_guardrails(pergunta)
    if not guardrail.allowed:
        return {
            "guardrail_triggered": True,
            "guardrail_category": guardrail.category,
            "messages": [
                HumanMessage(content=pergunta),
                AIMessage(content=guardrail.message or "Pergunta bloqueada."),
            ],
        }

    agente = criar_agente(pergunta)
    return agente.invoke({"messages": [pergunta]})


if __name__ == "__main__":
    pergunta = "liste todos os contratos relacionados a Festividades"
    rota = route_user_query(pergunta)
    resultado = responder_pergunta(pergunta)

    pprint(
        {
            "rota": {
                "dominio": rota.domain,
                "tipo_de_operacao": rota.operation_type,
                "tool_publica": rota.tool_name,
                "parametros_sugeridos": rota.tool_kwargs,
            },
            "tools_publicas": ferramentas_publicas_disponiveis(),
        }
    )

    print("--------------------------------")
    print("Resposta do agente: ")
    print(resultado["messages"][-1].content)
