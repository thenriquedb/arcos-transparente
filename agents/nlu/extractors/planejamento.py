"""Extração de entidades do domínio de planejamento (área, programa, ação...).

Mapeia termos comuns do cidadão para os valores canônicos do relatório de
planejamento, usando dicionários de aliases por dimensão.
"""

from __future__ import annotations

from shared.planejamento_entidades import extract_planejamento_entidade_alias

from .text import _contains_term


PLANEJAMENTO_AREA_ALIASES = {
    "saude": ("saude",),
    "educacao": ("educacao",),
    "assistencia social": ("assistencia social", "assistencia"),
    "administracao": ("administracao",),
    "transporte": ("transporte",),
    "cultura": ("cultura",),
    "desporto e lazer": ("desporto", "esporte", "lazer"),
    "seguranca publica": ("seguranca publica", "seguranca"),
    "gestao ambiental": ("meio ambiente", "ambiental", "gestao ambiental"),
    "saneamento": ("saneamento",),
    "agricultura": ("agricultura",),
    "judiciaria": ("judiciaria", "juridica", "procuradoria"),
    "legislativa": ("legislativa", "camara", "legislativo"),
    "direitos da cidadania": ("cidadania",),
    "habitacao": ("habitacao",),
    "trabalho": ("trabalho",),
    "energia": ("energia",),
    "comercio e servicos": ("comercio", "servicos"),
}

PLANEJAMENTO_PROGRAMA_ALIASES = {
    "merenda escolar": (
        "merenda escolar",
        "programa de merenda escolar",
        "alimentacao escolar",
        "programa nacional de alimentacao escolar",
        "pnae",
        "distribuicao de merenda das escolas",
        "distribuicao de merenda das creches",
        "setor de merenda escolar",
        "deposito de merenda escolar",
    ),
    "transporte escolar": (
        "transporte escolar",
        "programa de apoio ao transporte escolar",
        "pnate",
        "programa nacional de apoio ao transporte escolar",
    ),
    "ensino fundamental": (
        "ensino fundamental",
        "atendimento ao ensino fundamental",
    ),
    "educacao infantil": (
        "educacao infantil",
        "ensino infantil",
        "atendimento a educacao infantil",
    ),
    "tempo integral": (
        "tempo integral",
        "escola em tempo integral",
        "programa escola em tempo integral",
    ),
    "ensino universitario e profissionalizante": (
        "ensino universitario e profissionalizante",
        "apoio ao ensino universitario e profissionalizante",
    ),
    "infraestrutura urbana e rural": (
        "infraestrutura urbana e rural",
        "programa de infraestrutura urbana e rural",
    ),
    "socioassistencial": (
        "socioassistencial",
        "atendimento socioassistencial",
    ),
    "alimentacao e nutricao": (
        "alimentacao e nutricao",
        "promocao de acoes de alimentacao e nutricao",
    ),
    "saneamento urbano e rural": (
        "saneamento urbano e rural",
        "programa de saneamento urbano e rural",
    ),
    "limpeza urbana": (
        "limpeza urbana",
        "programa de limpeza urbana",
    ),
    "acoes administrativas": (
        "coordenacao das acoes administrativas",
        "acoes administrativas",
    ),
    "acoes governamentais": (
        "gerenciamento das acoes governamentais",
        "acoes governamentais",
    ),
    "financas publicas": (
        "controle das financas publicas",
        "financas publicas",
    ),
    "camara municipal": (
        "aplicacao recursos da camara municipal",
        "recursos da camara municipal",
    ),
    "seguranca publica": ("reforco da seguranca publica",),
    "transporte urbano e rodoviario": (
        "servicos de transporte urbano e rodoviario",
        "transporte urbano e rodoviario",
    ),
}

PLANEJAMENTO_ACAO_ALIASES = {
    "caps": (
        "caps",
        "centro de atencao psicossocial",
    ),
    "cras": (
        "cras",
        "centro de referencia de assistencia social",
    ),
    "creas": (
        "creas",
        "centro de referencia especializado de assistencia social",
    ),
    "atencao primaria": (
        "atencao primaria a saude",
        "atencao primaria",
    ),
    "assistencia hospitalar": ("assistencia hospitalar",),
    "tratamento fora domicilio": (
        "tratamento fora domicilio",
        "tratamento fora do domicilio",
        "tfd",
    ),
    "assistencia farmaceutica": ("assistencia farmaceutica",),
    "analises clinicas": ("analises clinicas",),
    "diagnostico por imagem": ("diagnostico por imagem",),
    "vigilancia sanitaria": ("vigilancia sanitaria",),
    "vigilancia em saude": ("vigilancia em saude",),
    "saude bucal": ("saude bucal",),
    "lactario": (
        "lactario",
        "lactario municipal",
    ),
    "acs": (
        "acs",
        "agentes comunitarios de saude",
    ),
    "acolhimento institucional": (
        "acolhimento institucional",
        "centro de acolhimento institucional",
    ),
    "ifmg": ("ifmg",),
    "caixas escolares": (
        "caixas escolares",
        "caixas escolares municipais",
    ),
    "creches": (
        "construcao e ampliacao de creches",
        "ampliacao de creches",
    ),
    "unidades escolares": (
        "construcao e ampliacao de unidades escolares",
        "unidades escolares",
    ),
    "pre escolar": (
        "pre escolar",
        "ensino pre escolar",
    ),
    "fundeb 70": ("fundeb 70",),
    "fundeb 30": ("fundeb 30",),
    "transporte coletivo urbano": ("transporte coletivo urbano",),
    "terminal rodoviario": ("terminal rodoviario",),
    "contabilidade municipal": ("contabilidade municipal",),
    "tesouraria e tributacao": ("tesouraria e tributacao",),
    "sentencas judiciais": (
        "sentencas judiciais",
        "cumprimento de sentencas judiciais",
    ),
    "cidade inteligente": ("cidade inteligente",),
    "reurb": ("reurb",),
    "plano diretor": ("plano diretor",),
    "distrito industrial": ("distrito industrial",),
}

PLANEJAMENTO_FONTE_RECURSO_ALIASES = {
    "fundeb": ("fundeb",),
    "fnde": (
        "fnde",
        "fundo nacional de desenvolvimento da educacao",
    ),
    "pnae": (
        "pnae",
        "programa nacional de alimentacao escolar",
    ),
    "pnate": (
        "pnate",
        "programa nacional de apoio ao transporte escolar",
    ),
    "salario educacao": (
        "salario educacao",
        "salario-educacao",
    ),
    "transf do sus": (
        "sus",
        "sistema unico de saude",
        "bloco de manutencao do sus",
        "bloco de estruturacao do sus",
    ),
    "fundo nacional de assistencia social": (
        "fnas",
        "fundo nacional de assistencia social",
    ),
    "recursos nao vinculados de impostos": ("recursos nao vinculados de impostos",),
}

_MERENDA_ESCOLAR_CONTEXT_TERMS = (
    "educacao",
    "escola",
    "escolas",
    "creche",
    "creches",
    "aluno",
    "alunos",
    "infantil",
    "fundamental",
)


def _extract_planejamento_entidade(normalized_text: str) -> str | None:
    """Reconhece entidades de planejamento já conhecidas, como `fumusa`."""

    return extract_planejamento_entidade_alias(normalized_text)


def _extract_planejamento_programa(normalized_text: str) -> str | None:
    """Mapeia temas comuns do planejamento para um programa canônico."""

    for programa, aliases in PLANEJAMENTO_PROGRAMA_ALIASES.items():
        if any(_contains_term(normalized_text, alias) for alias in aliases):
            return programa

    if "generos alimenticios" in normalized_text and any(
        context_term in normalized_text for context_term in _MERENDA_ESCOLAR_CONTEXT_TERMS
    ):
        return "merenda escolar"

    return None


def _extract_planejamento_acao(normalized_text: str) -> str | None:
    """Mapeia temas comuns do planejamento para uma acao canônica."""

    for acao, aliases in PLANEJAMENTO_ACAO_ALIASES.items():
        if any(_contains_term(normalized_text, alias) for alias in aliases):
            return acao
    return None


def _extract_planejamento_fonte_recurso(normalized_text: str) -> str | None:
    """Mapeia siglas e fontes comuns do planejamento para um filtro canônico."""

    for fonte_recurso, aliases in PLANEJAMENTO_FONTE_RECURSO_ALIASES.items():
        if any(_contains_term(normalized_text, alias) for alias in aliases):
            return fonte_recurso
    return None


def _extract_planejamento_area(normalized_text: str) -> str | None:
    """Mapeia termos comuns do usuário para as funções reais do planejamento."""

    for area, aliases in PLANEJAMENTO_AREA_ALIASES.items():
        if any(_contains_term(normalized_text, alias) for alias in aliases):
            return area
    return None
