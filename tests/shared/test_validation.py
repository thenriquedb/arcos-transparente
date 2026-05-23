from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from shared.utils.validation import (
    clean_text,
    normalize_limit,
    parse_competencia_as_date,
    parse_date,
    parse_decimal,
    validate_date_period,
)


def test_clean_text_normaliza_strings_e_numeros() -> None:
    assert clean_text("  abc  ") == "abc"
    assert clean_text("   ") is None
    assert clean_text(123) == "123"
    assert clean_text(Decimal("10.5")) == "10.5"


def test_clean_text_rejeita_tipo_invalido() -> None:
    with pytest.raises(ValueError, match="valor textual invalido"):
        clean_text(["invalido"])


def test_parse_decimal_suporta_moeda_numeros_e_vazio() -> None:
    assert parse_decimal("R$ 1.234,56") == Decimal("1234.56")
    assert parse_decimal(10) == Decimal("10")
    assert parse_decimal(10.5) == Decimal("10.5")
    assert parse_decimal("   ") is None


def test_parse_decimal_rejeita_valor_invalido() -> None:
    with pytest.raises(ValueError, match="valor decimal invalido"):
        parse_decimal("abc")


def test_parse_date_suporta_formatos_comuns() -> None:
    assert parse_date("07/02/2025") == date(2025, 2, 7)
    assert parse_date("2025-02-07") == date(2025, 2, 7)
    assert parse_date("2025-02-07T10:30:00Z") == date(2025, 2, 7)
    assert parse_date(datetime(2025, 2, 7, 10, 30)) == date(2025, 2, 7)


def test_parse_date_rejeita_valor_invalido() -> None:
    with pytest.raises(ValueError, match="data invalida"):
        parse_date("99/99/2025")


def test_parse_competencia_as_date_suporta_competencia_e_iso() -> None:
    assert parse_competencia_as_date("02/2025") == date(2025, 2, 1)
    assert parse_competencia_as_date("2025-02-01") == date(2025, 2, 1)


def test_parse_competencia_as_date_rejeita_competencia_invalida() -> None:
    with pytest.raises(ValueError, match="competencia invalida"):
        parse_competencia_as_date("13/2025")


def test_normalize_limit_aplica_clamp() -> None:
    assert normalize_limit(0) == 1
    assert normalize_limit(100) == 50
    assert normalize_limit("7") == 7


def test_normalize_limit_rejeita_valor_invalido() -> None:
    with pytest.raises(ValueError, match="limite invalido"):
        normalize_limit("abc")


def test_validate_date_period_aceita_periodo_valido() -> None:
    validate_date_period(date(2025, 1, 1), date(2025, 1, 31))


def test_validate_date_period_rejeita_periodo_invertido() -> None:
    with pytest.raises(
        ValueError, match="data_inicio deve ser menor ou igual a data_fim"
    ):
        validate_date_period(date(2025, 2, 1), date(2025, 1, 31))
