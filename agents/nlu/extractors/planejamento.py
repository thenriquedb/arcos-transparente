"""Extração de entidades do domínio de planejamento (área, programa, ação...).

Mapeia termos comuns do cidadão para os valores canônicos do relatório de
planejamento, usando dicionários de aliases por dimensão.
"""

from __future__ import annotations

from shared.planejamento_entidades import extract_planejamento_entidade_alias
from shared.utils.text import normalize_search_text

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
    "urbanismo": ("urbanismo",),
    "encargos especiais": ("encargos especiais",),
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
    "promocao de acoes de saude": (
        "promocao de acoes de saude",
        "promocao das acoes de saude",
        "promocao de acoes de saude - fms",
        "promocao das acoes de saude - fumusa",
        "acoes de saude fumusa",
    ),
    "fundo municipal de assistencia social": (
        "fundo municipal de assistencia social",
        "fundo de assistencia social",
        "fmas",
    ),
    "cultura esporte lazer e turismo": (
        "programa municipal de cultura, esporte, lazer e turismo",
        "cultura esporte lazer e turismo",
        "turismo",
    ),
    "meio ambiente": (
        "cuidados e preservacao do meio ambiente",
        "preservacao do meio ambiente",
        "meio ambiente",
    ),
    "apoio a manutencao do ensino": (
        "apoio a manutencao do ensino",
        "apoio ao ensino",
        "manutencao do ensino",
    ),
    "planejamento e desenvolvimento sustentavel": (
        "planejamento e desenvolvimento sustentavel",
        "desenvolvimento sustentavel",
    ),
    "acoes judiciais": (
        "acompanhamento e controle das acoes judiciais",
        "acoes judiciais",
    ),
    "acoes complementares de educacao": (
        "implementacao das acoes complementares de educacao",
        "acoes complementares de educacao",
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
    "servicos administrativos de saude": (
        "manutencao dos servicos administrativos de saude",
        "servicos administrativos de saude",
    ),
    "secretaria de educacao": (
        "manutencao das atividades da secretaria de educacao",
        "secretaria de educacao",
    ),
    "ensino fundamental": (
        "manutencao do ensino fundamental",
        "ensino fundamental",
    ),
    "assistencia especializada": (
        "manutencao da assistencia especializada",
        "assistencia especializada",
    ),
    "atividades culturais e artes": (
        "manutencao de atividades culturais e artes",
        "atividades culturais e artes",
    ),
    "secretaria de governo": (
        "manutencao das atividades da secretaria de governo",
        "secretaria de governo",
    ),
    "atividades administrativas": (
        "manutencao das atividades administrativas",
        "atividades administrativas",
    ),
    "servicos administrativos socioassistenciais": (
        "manutencao dos servicos administrativos socioassistenciais",
        "servicos administrativos socioassistenciais",
    ),
    "alimentacao do servidor": (
        "manutencao do programa alimentacao do servidor",
        "alimentacao do servidor",
    ),
    "secretaria meio ambiente e agropecuaria": (
        "manutencao das atividades secretaria meio ambiente e agropecuaria",
        "secretaria meio ambiente e agropecuaria",
    ),
    "secretaria de obras": (
        "manutencao das atividades da secretaria de obras",
        "secretaria de obras",
    ),
    "limpeza publica": (
        "manutencao dos servicos de limpeza publica",
        "limpeza publica",
    ),
    "inativos e pensionistas": (
        "manutencao de inativos e pensionistas",
        "inativos e pensionistas",
    ),
    "transporte escolar": (
        "manutencao do transporte escolar",
        "transporte escolar",
    ),
    "gestao e operacionalizacao do sus": ("gestao e operacionalizacao do sus",),
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


def _build_alias_search_terms(
    value: str | None,
    aliases_by_key: dict[str, tuple[str, ...]],
    extractor,
) -> tuple[str, ...]:
    normalized_value = normalize_search_text(value)
    if not normalized_value:
        return ()

    canonical_value = extractor(normalized_value)
    if canonical_value is None:
        return (normalized_value,)

    aliases = aliases_by_key.get(canonical_value, ())
    ordered_terms = [canonical_value, *aliases]
    deduped_terms: list[str] = []
    seen_terms: set[str] = set()
    for term in ordered_terms:
        normalized_term = normalize_search_text(term)
        if not normalized_term or normalized_term in seen_terms:
            continue
        seen_terms.add(normalized_term)
        deduped_terms.append(normalized_term)
    return tuple(deduped_terms)


def get_planejamento_area_search_terms(value: str | None) -> tuple[str, ...]:
    return _build_alias_search_terms(value, PLANEJAMENTO_AREA_ALIASES, _extract_planejamento_area)


def get_planejamento_programa_search_terms(value: str | None) -> tuple[str, ...]:
    return _build_alias_search_terms(value, PLANEJAMENTO_PROGRAMA_ALIASES, _extract_planejamento_programa)


def get_planejamento_acao_search_terms(value: str | None) -> tuple[str, ...]:
    return _build_alias_search_terms(value, PLANEJAMENTO_ACAO_ALIASES, _extract_planejamento_acao)


def get_planejamento_fonte_recurso_search_terms(value: str | None) -> tuple[str, ...]:
    return _build_alias_search_terms(value, PLANEJAMENTO_FONTE_RECURSO_ALIASES, _extract_planejamento_fonte_recurso)
