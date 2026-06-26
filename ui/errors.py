"""Mensagens de erro amigaveis para as interfaces do chatbot.

Independente de framework (Streamlit, Chainlit, CLI): traduz excecoes tecnicas
em mensagens acionaveis para o cidadao, sem vazar detalhes internos.
"""

from __future__ import annotations


def friendly_error_message(exc: Exception) -> str:
    """Traduz uma excecao do agente/ferramentas em mensagem amigavel."""

    message = str(exc).strip()
    normalized = message.lower()

    if "openai_api_key" in normalized or "openai_model" in normalized:
        return (
            "Configuracao do chatbot incompleta. Defina LLM_PROVIDER=openai, "
            "OPENAI_MODEL e OPENAI_API_KEY no ambiente ou no .env antes de iniciar "
            "o chat."
        )

    if "provider nao suportado pelo chatbot" in normalized or "llm_provider" in normalized:
        return "Provider nao suportado para o chatbot nesta fase. Use LLM_PROVIDER=openai no ambiente ou no .env."

    database_markers = (
        "no such table",
        "unable to open database",
        "database is locked",
        "sqlite",
        "transparencia.db",
    )
    if any(marker in normalized for marker in database_markers):
        return "Banco local indisponivel ou sem dados importados. Importe a base SQLite antes de consultar o chat."

    return "Falha inesperada ao consultar o agente ou uma ferramenta. Tente novamente em instantes."
