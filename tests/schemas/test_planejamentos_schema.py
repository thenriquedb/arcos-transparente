from __future__ import annotations

from decimal import Decimal

import pytest

from ingestion.schemas.planejamentos import PlanejamentoDespesaInSchema


def test_planejamento_schema_converte_moeda_e_mes() -> None:
    registro = PlanejamentoDespesaInSchema.model_validate(
        {
            "exercicio": "2025",
            "mes": "MARÇO",
            "unidade_gestora": " FUNDAÇÃO MUNIC. SAÚDE ",
            "funcao": " Saúde ",
            "descricao_acao": " Atenção Primária ",
            "dotacao_inicial": "R$ 10.000,50",
            "valor_pago": "R$ 1.250,25",
        }
    )

    assert registro.exercicio == 2025
    assert registro.mes == "MARÇO"
    assert registro.mes_num == 3
    assert registro.unidade_gestora == "FUNDAÇÃO MUNIC. SAÚDE"
    assert registro.funcao == "Saúde"
    assert registro.dotacao_inicial == Decimal("10000.50")
    assert registro.valor_pago == Decimal("1250.25")


def test_planejamento_schema_rejeita_mes_invalido() -> None:
    with pytest.raises(ValueError):
        PlanejamentoDespesaInSchema.model_validate(
            {
                "exercicio": 2025,
                "mes": "MES INEXISTENTE",
                "unidade_gestora": "FUNDAÇÃO MUNIC. SAÚDE",
                "funcao": "Saúde",
                "descricao_acao": "Atenção Primária",
            }
        )
