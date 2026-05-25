from __future__ import annotations

import pytest

from agents.router import route_user_query


@pytest.mark.parametrize(
    ("pergunta", "dominio", "tipo", "tool_name", "tool_kwargs"),
    [
        (
            "Quantas pessoas trabalham na saude?",
            "servidores",
            "agregacao_ranking",
            "agregar_servidores",
            {"filtros": {"secretaria": "saude"}, "metrica": "contagem"},
        ),
        (
            "Qual secretaria com mais funcionarios?",
            "servidores",
            "agregacao_ranking",
            "agregar_servidores",
            {
                "agrupar_por": "secretaria",
                "metrica": "contagem",
                "ordenar_por": "metrica",
                "ordem": "desc",
                "limite": 1,
            },
        ),
        (
            "Lista de todos os funcionarios da educacao",
            "servidores",
            "consulta_lista",
            "consultar_servidores",
            {
                "filtros": {"secretaria": "educacao"},
                "ordenar_por": "nome",
                "ordem": "asc",
            },
        ),
        (
            "Quais os 10 maiores salários da prefeitura?",
            "servidores",
            "consulta_lista",
            "consultar_servidores",
            {
                "ordenar_por": "salario_base",
                "ordem": "desc",
                "limite": 10,
                "campos": [
                    "nome",
                    "salario_base",
                    "cargo",
                    "secretaria",
                    "mes_de_referencia",
                ],
            },
        ),
    ],
)
def test_route_user_query_mapeia_exemplos_publicos(
    pergunta: str,
    dominio: str,
    tipo: str,
    tool_name: str,
    tool_kwargs: dict[str, object],
) -> None:
    decision = route_user_query(pergunta)

    assert decision.domain == dominio
    assert decision.operation_type == tipo
    assert decision.tool_name == tool_name
    assert decision.tool_kwargs == tool_kwargs
    assert decision.confident is True
