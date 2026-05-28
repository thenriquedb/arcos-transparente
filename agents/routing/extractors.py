"""Helpers de normalização e extração usados pelo router."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from agents.tools.sql_tools.planejamento.shared.entities import (
    extract_planejamento_entidade_alias,
)

from .constants import (
    CONTRATOS_DOMAIN_KEYWORDS,
    LICITACOES_DOMAIN_KEYWORDS,
    PLANEJAMENTO_DIRECT_KEYWORDS,
    PLANEJAMENTO_ENTITY_HINT_KEYWORDS,
    PROMPT_INJECTION_PATTERNS,
    RECEITAS_DOMAIN_KEYWORDS,
    SECRETARIAS_CONHECIDAS,
)


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

RECEITAS_TEMA_ALIASES = (
    "iptu",
    "issqn",
    "iss",
    "itbi",
    "ipva",
    "fundeb",
    "enfermagem",
    "coleta de lixo",
    "taxa de servicos",
    "taxas",
)


def _normalize(text: str) -> str:
    """Remove acentos e normaliza caixa para simplificar match por texto."""

    normalized = unicodedata.normalize("NFD", text)
    without_accents = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    return without_accents.lower().strip()


def _contains_any(normalized_text: str, keywords: tuple[str, ...]) -> bool:
    """Retorna True quando qualquer palavra-chave aparece no texto normalizado."""

    return any(keyword in normalized_text for keyword in keywords)


def _contains_term(normalized_text: str, term: str) -> bool:
    """Faz match por termo completo para evitar falsos positivos por substring."""

    return re.search(rf"\b{re.escape(term)}\b", normalized_text) is not None


def _contains_any_term(normalized_text: str, terms: tuple[str, ...]) -> bool:
    """Versão por termo completo de `_contains_any`."""

    return any(_contains_term(normalized_text, term) for term in terms)


def _extract_limit(normalized_text: str, default: int = 10) -> int:
    """Extrai limite apenas quando o número aparece em contexto de quantidade."""

    match = re.search(
        r"\b(?:top|maiores|menores|primeiro|primeiros|listar?|mostrar?|exibir?)\s+(\d{1,3})\b",
        normalized_text,
    )
    if match is None:
        return default
    return int(match.group(1))


def _extract_secretaria(normalized_text: str) -> str | None:
    """Mapeia trechos do texto para uma secretaria canônica conhecida."""

    patterns = [
        r"\b(?:na|no|da|do)\b\s+(?:secretaria\s+de\s+)?((?:[a-z]+\s?){1,4})(?:\?|\s|$)",
        r"\b(?:pela|pelo)\b\s+(?:secretaria\s+de\s+)?((?:[a-z]+\s?){1,4})(?:\?|\s|$)",
        r"\bfuncionarios\b\s+\bda\b\s+((?:[a-z]+\s?){1,4})(?:\?|\s|$)",
        r"\btrabalham\b\s+\bna\b\s+((?:[a-z]+\s?){1,4})(?:\?|\s|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized_text)
        if match is None:
            continue

        # Condensa espaços antes de validar contra a lista canônica.
        candidato = " ".join(match.group(1).split())
        for secretaria in SECRETARIAS_CONHECIDAS:
            if secretaria in candidato:
                return secretaria
    return None


def _extract_nome_para_historico(normalized_text: str) -> str | None:
    """Extrai nomes em perguntas sobre salário ou histórico de pagamentos."""

    patterns = [
        r"salario\s+(?:do|da|de)\s+([a-z\s]+?)(?:\?|$)",
        r"salario\s+([a-z\s]+?)(?:\?|$)",
        r"quanto\s+([a-z\s]+?)\s+(?:recebe|recebeu|ganha|ganhou)(?:\?|$)",
        r"quanto\s+(?:recebe|recebeu|ganha|ganhou)\s+([a-z\s]+?)(?:\?|$)",
        r"(?:quanto\s+e\s+)?(?:o\s+)?salario\s+(?:do|da|de)\s+([a-z\s]+?)(?:\?|$)",
        r"pagamentos\s+(?:do|da|de)\s+([a-z\s]+?)(?:\?|$)",
        r"(?:pesquise|busque|procure|pesquisar|buscar|procurar)\s+(?:por\s+)?([a-z\s]+?)(?:\?|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized_text)
        if match is None:
            continue
        nome = re.sub(
            r"^(?:servidor publico|servidora publica|servidor|servidora|funcionario|funcionaria)\s+",
            "",
            match.group(1).strip(),
        )
        if nome:
            return nome
    return None


def _extract_planejamento_entidade(normalized_text: str) -> str | None:
    """Reconhece entidades de planejamento já conhecidas, como `fumusa`."""

    return extract_planejamento_entidade_alias(normalized_text)


def _extract_planejamento_area(normalized_text: str) -> str | None:
    """Mapeia termos comuns do usuário para as funções reais do planejamento."""

    for area, aliases in PLANEJAMENTO_AREA_ALIASES.items():
        if any(alias in normalized_text for alias in aliases):
            return area
    return None


def _is_licitacoes_query(normalized_text: str) -> bool:
    """Heurística simples para identificar perguntas sobre licitações."""

    return _contains_any(normalized_text, LICITACOES_DOMAIN_KEYWORDS)


def _is_contratos_query(normalized_text: str) -> bool:
    """Heurística simples para identificar perguntas sobre contratos."""

    return _contains_any(normalized_text, CONTRATOS_DOMAIN_KEYWORDS)


def _is_receitas_query(normalized_text: str) -> bool:
    """Heurística simples para identificar perguntas sobre receitas."""

    return _contains_any(normalized_text, RECEITAS_DOMAIN_KEYWORDS)


def _extract_licitacao_numero(normalized_text: str) -> str | None:
    """Extrai número de licitação quando a pergunta cita o identificador."""

    match = re.search(
        r"\b(?:numero|n|licitacao|pregao)\b\s+([0-9][0-9./-]*)\b",
        normalized_text,
    )
    if match is None:
        return None
    return match.group(1).strip()


def _extract_contrato_numero(normalized_text: str) -> str | None:
    """Extrai número de contrato quando a pergunta cita o identificador."""

    match = re.search(
        r"\b(?:contrato|numero|n)\b\s+([0-9][0-9./-]*)\b",
        normalized_text,
    )
    if match is None:
        return None
    return match.group(1).strip()


def _extract_contrato_fornecedor(normalized_text: str) -> str | None:
    """Extrai um nome de fornecedor em perguntas focadas em contratos."""

    patterns = [
        r"\bfornecedor\b\s+([a-z0-9 .&/-]+?)(?=\s+\b(?:em|com)\b\s+\d{4}\b|\?|$)",
        r"\bempresa\b\s+([a-z0-9 .&/-]+?)(?=\s+\b(?:em|com)\b\s+\d{4}\b|\?|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized_text)
        if match is None:
            continue
        fornecedor = " ".join(match.group(1).split())
        if fornecedor:
            return fornecedor
    return None


def _extract_year(normalized_text: str) -> int | None:
    """Extrai anos no formato 20XX quando presentes no texto."""

    match = re.search(r"\b(20\d{2})\b", normalized_text)
    if match is None:
        return None
    return int(match.group(1))


def _extract_receitas_tipo_de_dado(normalized_text: str) -> str:
    """Escolhe entre arrecadação efetiva e valores apenas lançados."""

    if any(
        keyword in normalized_text
        for keyword in (
            "lancamento",
            "lancamentos",
            "lancado",
            "lancada",
            "lancou",
            "divida ativa",
            "cobranca judicial",
        )
    ):
        return "lancamento"
    return "arrecadacao"


def _extract_receitas_unidade(normalized_text: str) -> str | None:
    """Identifica a unidade responsável mais citada em perguntas de receitas."""

    if "fumusa" in normalized_text or "fundacao" in normalized_text:
        return "saude"
    if "saude" in normalized_text:
        return "saude"
    if "prefeitura" in normalized_text:
        return "prefeitura"
    return None


def _extract_receitas_tema(normalized_text: str) -> str | None:
    """Extrai temas de receitas com alto valor prático para perguntas públicas."""

    for alias in RECEITAS_TEMA_ALIASES:
        if alias in normalized_text:
            return alias
    return None


def _extract_receitas_filters_from_query(normalized_text: str) -> dict[str, Any]:
    """Converte sinais do texto em filtros públicos da tool de receitas."""

    filtros: dict[str, Any] = {
        "tipo_de_dado": _extract_receitas_tipo_de_dado(normalized_text)
    }

    if year := _extract_year(normalized_text):
        filtros["ano"] = year

    if "primeiro trimestre" in normalized_text or "1 trimestre" in normalized_text:
        filtros["mes_inicio"] = 1
        filtros["mes_fim"] = 3
    elif "segundo trimestre" in normalized_text or "2 trimestre" in normalized_text:
        filtros["mes_inicio"] = 4
        filtros["mes_fim"] = 6
    elif "terceiro trimestre" in normalized_text or "3 trimestre" in normalized_text:
        filtros["mes_inicio"] = 7
        filtros["mes_fim"] = 9
    elif "quarto trimestre" in normalized_text or "4 trimestre" in normalized_text:
        filtros["mes_inicio"] = 10
        filtros["mes_fim"] = 12

    if unidade := _extract_receitas_unidade(normalized_text):
        filtros["unidade_responsavel"] = unidade

    if tema := _extract_receitas_tema(normalized_text):
        filtros["tema"] = tema

    return filtros


def _extract_receitas_metric(normalized_text: str, tipo_de_dado: str) -> str:
    """Seleciona a métrica compatível com o tipo de dado pedido."""

    if any(keyword in normalized_text for keyword in ("quantos", "quantas")):
        return "contagem"
    if tipo_de_dado == "lancamento":
        if "divida ativa" in normalized_text:
            return "soma_valor_em_divida_ativa"
        if "cobranca judicial" in normalized_text:
            return "soma_valor_em_cobranca_judicial"
        return "soma_valor_lancado"
    if any(keyword in normalized_text for keyword in ("previsto", "previsao")):
        return "soma_valor_previsto"
    return "soma_valor_recebido"


def _is_planejamento_query(normalized_text: str) -> bool:
    """Detecta perguntas de planejamento por termos explícitos ou entidades."""

    if _contains_any_term(normalized_text, PLANEJAMENTO_DIRECT_KEYWORDS):
        return True

    if _extract_planejamento_entidade(normalized_text) and _contains_any_term(
        normalized_text,
        PLANEJAMENTO_ENTITY_HINT_KEYWORDS,
    ):
        return True
    if _contains_any_term(normalized_text, PLANEJAMENTO_ENTITY_HINT_KEYWORDS) and (
        "prefeitura" in normalized_text
        or _extract_planejamento_area(normalized_text) is not None
        or _extract_secretaria(normalized_text) is not None
    ):
        return True

    return "saude" in normalized_text and _contains_any(
        normalized_text,
        ("gasto", "gastos", "pago", "pagos", "planejado"),
    )


def _extract_planejamento_filters_from_query(normalized_text: str) -> dict[str, Any]:
    """Converte sinais do texto em filtros públicos da tool de planejamento."""

    entidade = _extract_planejamento_entidade(normalized_text)
    area = _extract_planejamento_area(normalized_text)
    secretaria = _extract_secretaria(normalized_text)

    origem = "saude"
    if entidade is not None:
        origem = "saude"
    elif "prefeitura" in normalized_text:
        origem = "prefeitura"
    elif area is not None and area != "saude":
        origem = "prefeitura"
    elif secretaria is not None and secretaria != "saude":
        origem = "prefeitura"

    filtros: dict[str, Any] = {"origem": origem}

    if year := _extract_year(normalized_text):
        filtros["ano"] = year

    # Trimestres são transformados em intervalo de meses para a tool pública.
    if "primeiro trimestre" in normalized_text or "1 trimestre" in normalized_text:
        filtros["mes_inicio"] = 1
        filtros["mes_fim"] = 3
    elif "segundo trimestre" in normalized_text or "2 trimestre" in normalized_text:
        filtros["mes_inicio"] = 4
        filtros["mes_fim"] = 6
    elif "terceiro trimestre" in normalized_text or "3 trimestre" in normalized_text:
        filtros["mes_inicio"] = 7
        filtros["mes_fim"] = 9
    elif "quarto trimestre" in normalized_text or "4 trimestre" in normalized_text:
        filtros["mes_inicio"] = 10
        filtros["mes_fim"] = 12

    if entidade is not None:
        filtros["entidade"] = entidade

    if area is not None and entidade is None:
        filtros["area"] = area
    elif origem == "prefeitura" and secretaria is not None and secretaria != "saude":
        filtros["entidade"] = secretaria
    elif "saude" in normalized_text and entidade is None:
        filtros["area"] = "saude"

    return filtros


def _extract_planejamento_metric(normalized_text: str) -> str:
    """Escolhe a métrica mais adequada para perguntas agregadas de planejamento."""

    if "inicial" in normalized_text:
        return "soma_orcamento_inicial"
    if "empenhado" in normalized_text or "comprometido" in normalized_text:
        return "soma_valor_comprometido"
    if "liquidado" in normalized_text or "confirmado" in normalized_text:
        return "soma_valor_confirmado"
    if _contains_any(normalized_text, ("pago", "pagos", "gasto")):
        return "soma_valor_pago"
    return "soma_orcamento_atualizado"


def _extract_licitacoes_objeto(normalized_text: str) -> str | None:
    """Extrai alguns objetos recorrentes de licitações com alto valor prático."""

    if "festival gastronomico" in normalized_text:
        return "festival gastronomico"
    if "festival de gastronomia" in normalized_text:
        return "festival gastronomia"
    if "festival" in normalized_text:
        return "festival"
    return None


def _extract_contratos_descricao(normalized_text: str) -> str | None:
    """Extrai termos de descrição de contrato para alguns eventos recorrentes."""

    if objeto := _extract_licitacoes_objeto(normalized_text):
        return objeto

    patterns = [
        r"\brelacionad[oa]s?\s+a\s+([a-z0-9\s.&/-]+?)(?=\s+\bem\b\s+\d{4}\b|\?|$)",
        r"\bsobre\s+([a-z0-9\s.&/-]+?)(?=\s+\bem\b\s+\d{4}\b|\?|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized_text)
        if match is None:
            continue
        descricao = " ".join(match.group(1).split())
        if descricao:
            return descricao
    return None


def _build_licitacoes_filters_from_query(normalized_text: str) -> dict[str, Any]:
    """Monta filtros públicos de licitações com base na pergunta do usuário."""

    filtros: dict[str, Any] = {}
    if numero := _extract_licitacao_numero(normalized_text):
        filtros["numero"] = numero
        return filtros
    if secretaria := _extract_secretaria(normalized_text):
        filtros["secretaria"] = secretaria
    if objeto := _extract_licitacoes_objeto(normalized_text):
        filtros["objeto"] = objeto
    if year := _extract_year(normalized_text):
        filtros["data_abertura_inicio"] = f"{year}-01-01"
        filtros["data_abertura_fim"] = f"{year}-12-31"
    return filtros


def _build_contratos_filters_from_query(normalized_text: str) -> dict[str, Any]:
    """Monta filtros públicos de contratos com base na pergunta do usuário."""

    filtros: dict[str, Any] = {}
    if numero := _extract_contrato_numero(normalized_text):
        filtros["numero"] = numero
        return filtros
    if fornecedor := _extract_contrato_fornecedor(normalized_text):
        filtros["fornecedor"] = fornecedor
    if secretaria := _extract_secretaria(normalized_text):
        filtros["secretaria"] = secretaria
    if descricao := _extract_contratos_descricao(normalized_text):
        filtros["descricao"] = descricao
    if year := _extract_year(normalized_text):
        filtros["data_inicio_inicio"] = f"{year}-01-01"
        filtros["data_inicio_fim"] = f"{year}-12-31"
    return filtros


def _contains_prompt_injection(normalized_text: str) -> bool:
    """Aplica patterns defensivos para bloquear tentativas de prompt injection."""

    return any(
        re.search(pattern, normalized_text) is not None
        for pattern in PROMPT_INJECTION_PATTERNS
    )


def _count_keyword_hits(normalized_text: str, keywords: tuple[str, ...]) -> int:
    """Conta quantas palavras-chave de um conjunto aparecem no texto."""

    return sum(1 for keyword in keywords if keyword in normalized_text)
