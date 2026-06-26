from __future__ import annotations

from ui.errors import friendly_error_message


def test_openai_config_message() -> None:
    msg = friendly_error_message(RuntimeError("Missing OPENAI_API_KEY in environment"))
    assert "Configuracao do chatbot incompleta" in msg


def test_provider_message() -> None:
    msg = friendly_error_message(ValueError("Provider nao suportado pelo chatbot nesta fase"))
    assert "Provider nao suportado" in msg


def test_database_message() -> None:
    msg = friendly_error_message(RuntimeError("no such table: servidores"))
    assert "Banco local indisponivel" in msg


def test_fallback_message() -> None:
    msg = friendly_error_message(RuntimeError("erro qualquer e inesperado"))
    assert "Falha inesperada" in msg
