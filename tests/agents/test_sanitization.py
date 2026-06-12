"""Sanitização de payloads de observabilidade (prevenção de vazamento).

`agents/chatbot/observability/sanitization.py` é a única barreira entre payloads
do runtime (args/resultados de tools, erros, histórico) e um serviço externo
(LangSmith). Estes testes cobrem a redação de segredos, o allowlisting de chaves,
os limites de profundidade/tamanho e o tratamento de floats não-finitos.
"""

from __future__ import annotations

from agents.chatbot.observability.sanitization import (
    _looks_sensitive,
    sanitize_error,
    sanitize_mapping,
    sanitize_value,
    summarize_result,
)


_REDACTED = "[REDACTED]"


# --- _looks_sensitive -------------------------------------------------------


def test_looks_sensitive_reconhece_chaves_de_credencial() -> None:
    for chave in (
        "api_key",
        "API-KEY",
        "apiKey",
        "authorization",
        "Authorization",
        "auth_token",
        "password",
        "user_password",
        "access_token",
        "client_secret",
    ):
        assert _looks_sensitive(chave) is True, chave


def test_looks_sensitive_ignora_chaves_de_negocio_comuns() -> None:
    for chave in ("nome", "valor_pago", "ano", "fornecedor", "competencia"):
        assert _looks_sensitive(chave) is False, chave


def test_looks_sensitive_over_redige_secretaria_por_conter_secret() -> None:
    # SHARP EDGE conhecido: `secretaria` (campo de domínio onipresente) contém o
    # substring `secret`, então é redigido na observabilidade. É seguro (over-
    # redaction), mas significa que valores de `secretaria` aparecem como
    # [REDACTED] no LangSmith. Se o match passar a ser por palavra, atualize aqui.
    assert _looks_sensitive("secretaria") is True


# --- sanitize_value: redação de chave sensível ------------------------------


def test_sanitize_value_redige_chave_sensivel_independente_do_valor() -> None:
    assert sanitize_value("sk-1234567890", key="api_key") == _REDACTED
    # A chave sensível curto-circuita antes de qualquer recursão.
    assert sanitize_value({"x": 1}, key="authorization") == _REDACTED


def test_sanitize_value_redige_chave_sensivel_aninhada() -> None:
    resultado = sanitize_value({"headers": {"authorization": "Bearer xyz"}})
    assert resultado == {"headers": {"authorization": _REDACTED}}


# --- sanitize_value: tipos primitivos ---------------------------------------


def test_sanitize_value_passa_primitivos() -> None:
    assert sanitize_value(None) is None
    assert sanitize_value(True) is True
    assert sanitize_value(42) == 42
    assert sanitize_value(1.5) == 1.5


def test_sanitize_value_neutraliza_floats_nao_finitos() -> None:
    assert sanitize_value(float("nan")) is None
    assert sanitize_value(float("inf")) is None
    assert sanitize_value(float("-inf")) is None


def test_sanitize_value_resume_bytes_sem_expor_conteudo() -> None:
    assert sanitize_value(b"hello") == "<bytes:5>"


# --- sanitize_value: limites de tamanho e profundidade ----------------------


def test_sanitize_value_trunca_string_longa() -> None:
    resultado = sanitize_value("x" * 700)
    assert len(resultado) == 600
    assert resultado.endswith("...")


def test_sanitize_value_trunca_lista_em_max_items() -> None:
    resultado = sanitize_value(list(range(15)))
    assert resultado == list(range(10))


def test_sanitize_value_trunca_mapping_em_max_items() -> None:
    resultado = sanitize_value({f"k{i}": i for i in range(15)})
    assert len(resultado) == 10


def test_sanitize_value_corta_em_profundidade_maxima() -> None:
    resultado = sanitize_value({"a": {"b": {"c": {"d": 1}}}})
    assert resultado == {"a": {"b": {"c": "<max-depth>"}}}


# --- sanitize_mapping: allowlist + redação ----------------------------------


def test_sanitize_mapping_sem_allowlist_redige_segredos() -> None:
    resultado = sanitize_mapping({"nome": "Maria", "token": "abc123"})
    assert resultado == {"nome": "Maria", "token": _REDACTED}


def test_sanitize_mapping_descarta_chaves_fora_do_allowlist() -> None:
    resultado = sanitize_mapping(
        {"session_id": "s1", "objeto_arbitrario": {"x": 1}, "secret": "s"},
        allowed_keys=["session_id"],
    )
    assert resultado == {"session_id": "s1"}


def test_sanitize_mapping_allowlist_nao_dispensa_redacao_do_valor() -> None:
    # A chave passa pelo allowlist, mas o valor sensível ainda é redigido.
    resultado = sanitize_mapping({"token": "abc"}, allowed_keys=["token"])
    assert resultado == {"token": _REDACTED}


def test_sanitize_mapping_vazio_retorna_dict_vazio() -> None:
    assert sanitize_mapping(None) == {}
    assert sanitize_mapping({}) == {}


# --- sanitize_error ---------------------------------------------------------


def test_sanitize_error_resume_tipo_e_mensagem() -> None:
    resultado = sanitize_error(ValueError("falha de conexao"))
    assert resultado == {"error_type": "ValueError", "error_message": "falha de conexao"}


# --- summarize_result: não vaza valores de resultado (PII) ------------------


def test_summarize_result_de_mapping_expoe_so_chaves_e_tamanho() -> None:
    # Garantia de privacidade: resultados de tool (salário, CPF, nomes) NÃO são
    # enviados — apenas os NOMES das chaves e o tamanho.
    resultado = summarize_result({"cpf": "123.456.789-00", "salario_base": 8500.0, "nome": "Maria"})
    assert resultado == {"kind": "mapping", "size": 3, "keys": ["cpf", "salario_base", "nome"]}


def test_summarize_result_de_sequence_limita_preview_a_tres() -> None:
    resultado = summarize_result([1, 2, 3, 4, 5])
    assert resultado["kind"] == "sequence"
    assert resultado["size"] == 5
    assert resultado["preview"] == [1, 2, 3]


def test_summarize_result_de_texto_e_de_escalar() -> None:
    assert summarize_result("ok") == {"kind": "text", "preview": "ok"}
    assert summarize_result(7) == {"kind": "int", "preview": 7}


def test_sanitize_value_preserva_zero_finito() -> None:
    # 0.0 é finito (e falsy): deve passar como 0.0, não virar None.
    resultado = sanitize_value(0.0)
    assert resultado == 0.0
    assert resultado is not None
