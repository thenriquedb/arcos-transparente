from __future__ import annotations

from agents.nlu.extractors import (
    _extract_limit,
    _extract_planejamento_entidade,
    _extract_secretaria,
)


def test_extract_limit_so_captura_numeros_em_contexto_de_quantidade() -> None:
    assert _extract_limit("top 15 salarios da prefeitura") == 15
    assert _extract_limit("top servidores de 2024") == 10
    assert _extract_limit("liste servidores com mais de 5 anos") == 10


def test_extract_secretaria_normaliza_para_secretaria_canonica() -> None:
    assert _extract_secretaria("quantas pessoas trabalham na saude publica municipal de arcos?") == "saude"
    assert _extract_secretaria("funcionarios da secretaria de assistencia social") == "assistencia social"


def test_extract_planejamento_entidade_reconhece_fumusa() -> None:
    assert _extract_planejamento_entidade("foi planejado algum recurso para a fumusa") == "fumusa"
