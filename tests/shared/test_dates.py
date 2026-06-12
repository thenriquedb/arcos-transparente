from __future__ import annotations

from datetime import date

from shared.utils.dates import build_current_date_prompt_block, current_date


def test_current_date_retorna_data_de_hoje() -> None:
    assert current_date() == date.today()


def test_bloco_de_data_inclui_data_em_dois_formatos() -> None:
    bloco = build_current_date_prompt_block(date(2026, 6, 11))

    assert "## Data Atual" in bloco
    assert "11/06/2026" in bloco
    assert "2026-06-11" in bloco


def test_bloco_de_data_ensina_expressoes_relativas() -> None:
    bloco = build_current_date_prompt_block(date(2026, 6, 11))

    for termo in ("hoje", "ontem", "anteontem", "amanhã", "mês passado", "ano passado", "últimos"):
        assert termo in bloco


def test_bloco_de_data_mantem_exemplo_de_contratos_vigente_em() -> None:
    bloco = build_current_date_prompt_block(date(2026, 6, 11))

    assert "vigente_em" in bloco


def test_bloco_de_data_usa_hoje_por_padrao() -> None:
    bloco = build_current_date_prompt_block()

    assert date.today().isoformat() in bloco
