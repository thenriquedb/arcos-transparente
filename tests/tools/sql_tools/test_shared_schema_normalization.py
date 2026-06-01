from __future__ import annotations

import pytest
from pydantic import ValidationError

from agents.tools.sql_tools.eleitos.consultar_eleitos_schema import (
    ConsultarEleitosParams,
)
from agents.tools.sql_tools.frotas.consultar_frota_schema import FrotaFiltroSchema
from agents.tools.sql_tools.planejamento.shared.filters import CamposPlanejamentoSchema


def test_consultar_eleitos_normaliza_filtros_compartilhados() -> None:
    params = ConsultarEleitosParams.model_validate(
        {
            "filtros": {
                "tipo_politico": "Prefeito",
                "ano": "2024",
            },
            "campos": [" nome_completo ", "partido"],
        }
    )

    assert params.filtros.tipo_politico == "prefeito"
    assert params.filtros.ano == 2024
    assert params.campos == ["nome_completo", "partido"]


def test_consultar_eleitos_rejeita_campos_invalidos() -> None:
    with pytest.raises(ValidationError, match="campos nao suportados"):
        ConsultarEleitosParams.model_validate(
            {"campos": ["nome_completo", "campo_inexistente"]}
        )


def test_campos_planejamento_preserva_erro_de_lista() -> None:
    with pytest.raises(ValidationError, match="campos deve ser uma lista"):
        CamposPlanejamentoSchema.model_validate({"campos": "ano"})


def test_campos_planejamento_preserva_erro_de_campo() -> None:
    with pytest.raises(ValidationError, match="campo nao suportado: invalido"):
        CamposPlanejamentoSchema.model_validate({"campos": ["ano", "invalido"]})


def test_frota_filtro_to_metadata_dict_exclui_nulos() -> None:
    filtros = FrotaFiltroSchema.model_validate(
        {
            "placa": " ABC-1234 ",
            "modelo": None,
        }
    )

    assert filtros.to_metadata_dict() == {"placa": "ABC-1234"}
