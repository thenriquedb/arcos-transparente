from __future__ import annotations

from agents.nlu.extractors import (
    _extract_limit,
    _extract_planejamento_acao,
    _extract_planejamento_entidade,
    _extract_planejamento_fonte_recurso,
    _extract_planejamento_programa,
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


def test_extract_planejamento_programa_reconhece_merenda_e_aliases_comuns() -> None:
    assert _extract_planejamento_programa("qual foi o gasto com merenda escolar em 2025?") == "merenda escolar"
    assert _extract_planejamento_programa("quanto foi gasto com alimentacao escolar em 2025?") == "merenda escolar"
    assert _extract_planejamento_programa("quanto foi gasto com pnae em 2025?") == "merenda escolar"
    assert (
        _extract_planejamento_programa("quanto foi gasto com generos alimenticios da educacao em 2025?")
        == "merenda escolar"
    )


def test_extract_planejamento_programa_reconhece_aliases_comuns_da_base() -> None:
    assert _extract_planejamento_programa("quanto foi gasto com transporte escolar em 2025?") == "transporte escolar"
    assert _extract_planejamento_programa("qual foi o gasto com ensino fundamental em 2025?") == "ensino fundamental"
    assert _extract_planejamento_programa("quanto foi pago com educacao infantil em 2025?") == "educacao infantil"
    assert _extract_planejamento_programa("quanto foi gasto com escola em tempo integral em 2025?") == "tempo integral"
    assert (
        _extract_planejamento_programa("quanto foi gasto com ensino universitario e profissionalizante em 2025?")
        == "ensino universitario e profissionalizante"
    )


def test_extract_planejamento_acao_reconhece_aliases_comuns_da_base() -> None:
    assert _extract_planejamento_acao("quanto foi gasto com caps em 2025?") == "caps"
    assert _extract_planejamento_acao("quanto foi gasto com cras em 2025?") == "cras"
    assert _extract_planejamento_acao("quanto foi gasto com creas em 2025?") == "creas"
    assert _extract_planejamento_acao("quanto foi gasto com tratamento fora do domicilio em 2025?") == (
        "tratamento fora domicilio"
    )
    assert _extract_planejamento_acao("quanto foi gasto com assistencia farmaceutica em 2025?") == (
        "assistencia farmaceutica"
    )
    assert _extract_planejamento_acao("quanto foi gasto com vigilancia sanitaria em 2025?") == ("vigilancia sanitaria")
    assert _extract_planejamento_acao("quanto foi gasto com saude bucal em 2025?") == "saude bucal"
    assert _extract_planejamento_acao("quanto foi gasto com ifmg em 2025?") == "ifmg"
    assert _extract_planejamento_acao("quanto foi gasto com caixas escolares em 2025?") == "caixas escolares"
    assert _extract_planejamento_acao("quanto foi gasto com fundeb 70 em 2025?") == "fundeb 70"


def test_extract_planejamento_fonte_recurso_reconhece_aliases_comuns_da_base() -> None:
    assert _extract_planejamento_fonte_recurso("quanto foi gasto com recursos do fundeb em 2025?") == "fundeb"
    assert _extract_planejamento_fonte_recurso("quanto foi gasto com fnde em 2025?") == "fnde"
    assert _extract_planejamento_fonte_recurso("quanto foi gasto com salario educacao em 2025?") == (
        "salario educacao"
    )
    assert _extract_planejamento_fonte_recurso("quanto foi gasto com sus em 2025?") == "transf do sus"
    assert _extract_planejamento_fonte_recurso("quanto foi gasto com fnas em 2025?") == (
        "fundo nacional de assistencia social"
    )
