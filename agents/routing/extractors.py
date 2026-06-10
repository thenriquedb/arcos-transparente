"""Helpers de normalização e extração usados pelo router."""

from __future__ import annotations

from datetime import date
import re
from typing import Any

from agents.routing.conversation import normalize_conversation_text
from shared.planejamento_entidades import extract_planejamento_entidade_alias

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

REFERENTIAL_NAME_TOKENS = {
    "dele",
    "dela",
    "ele",
    "ela",
    "prefeito",
    "prefeita",
}

# Substantivos de domínio que NUNCA são nome de servidor. Quando o objeto
# extraído para histórico de folha começa com um destes, a pergunta é sobre
# um domínio público (contratos, licitações, despesas…), não sobre salário.
_HISTORICO_NAO_NOME_INICIAIS = frozenset(
    {
        "contrato",
        "contratos",
        "licitacao",
        "licitacoes",
        "pregao",
        "pregoes",
        "edital",
        "editais",
        "despesa",
        "despesas",
        "diaria",
        "diarias",
        "passagem",
        "passagens",
        "repasse",
        "repasses",
        "transferencia",
        "transferencias",
        "emenda",
        "emendas",
        "evento",
        "eventos",
        "show",
        "shows",
        "festival",
        "festivais",
        "gasto",
        "gastos",
        "servico",
        "servicos",
    }
)

# Objetos públicos curtos (eventos/shows) específicos o suficiente para acionar
# o fan-out de gasto-com-evento, mesmo quando aparecem isolados.
_EVENT_SHOW_OBJECT_TOKENS = frozenset(
    {
        "evento",
        "eventos",
        "show",
        "shows",
    }
)

_KNOWN_PUBLIC_OBJECT_ALIASES: tuple[tuple[str, str], ...] = (
    ("festival gastronomico", "festival gastronomico"),
    ("festival de gastronomia", "festival gastronomia"),
)

_GENERIC_PUBLIC_OBJECT_TOKENS = frozenset(
    {
        "evento",
        "eventos",
        "festival",
        "festivais",
        "show",
        "shows",
        "servico",
        "servicos",
        "objeto",
        "licitacao",
        "licitacoes",
        "pregao",
        "pregoes",
        "contrato",
        "contratos",
        "gasto",
        "gastos",
        "custo",
        "custos",
        "valor",
        "valores",
        "pago",
        "pagos",
    }
)

_PUBLIC_SCOPE_OBJECT_EXCLUSIONS = frozenset(
    {
        "administracao",
        "agricultura",
        "assistencia",
        "assistencia social",
        "camara",
        "cidadania",
        "cultura",
        "despesa",
        "despesas",
        "despesas por funcao",
        "diaria",
        "diarias",
        "educacao",
        "energia",
        "gestao ambiental",
        "habitacao",
        "legislativo",
        "legislativa",
        "meio ambiente",
        "passagem",
        "passagens",
        "prefeitura",
        "previdencia",
        "previdencia social",
        "relatorio de despesas por funcao",
        "saude",
        "saneamento",
        "seguranca",
        "seguranca publica",
        "trabalho",
        "transporte",
        "urbanismo",
    }
)

_LEADING_PUBLIC_OBJECT_ARTICLES = frozenset(
    {
        "a",
        "as",
        "da",
        "das",
        "de",
        "do",
        "dos",
        "na",
        "nas",
        "no",
        "nos",
        "o",
        "os",
        "um",
        "uma",
        "umas",
        "uns",
    }
)

_LEADING_PUBLIC_OBJECT_LABELS = frozenset({"evento", "eventos", "show", "shows"})

_PUBLIC_OBJECT_EXTRACTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "licitacoes",
        re.compile(
            r"\b(?:licitac(?:ao|oes)|preg(?:ao|oes)|edital(?:is)?)\s+"
            r"(?P<prep>para|de|do|da|sobre)\s+"
            r"(?P<object>[a-z0-9][a-z0-9\s.&/-]{1,80}?)"
            r"(?=\s+\b(?:em|de|do|da)\b\s+20\d{2}\b|\?|$)"
        ),
    ),
    (
        "contratos",
        re.compile(
            r"\b(?:contrato|contratos|contratad[oa]s?)\s+"
            r"(?P<prep>para|de|do|da|sobre)\s+"
            r"(?P<object>[a-z0-9][a-z0-9\s.&/-]{1,80}?)"
            r"(?=\s+\b(?:em|de|do|da)\b\s+20\d{2}\b|\?|$)"
        ),
    ),
    (
        "spend",
        re.compile(
            r"\b(?:gastos?|gastou|custos?|custou|valor gasto|valor pago|pagos?)\s+"
            r"(?P<prep>com|de|do|da|no|na)\s+"
            r"(?P<object>[a-z0-9][a-z0-9\s.&/-]{1,80}?)"
            r"(?=\s+\b(?:em|de|do|da)\b\s+20\d{2}\b|\?|$)"
        ),
    ),
    (
        "relation",
        re.compile(
            r"\b(?:relacionad[oa]s?\s+a|sobre)\s+"
            r"(?P<object>[a-z0-9][a-z0-9\s.&/-]{1,80}?)"
            r"(?=\s+\b(?:em|de|do|da)\b\s+20\d{2}\b|\?|$)"
        ),
    ),
)

_CONTRATOS_RANKING_DIMENSION_CUES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "fornecedor",
        (
            "qual fornecedor",
            "quais fornecedores",
            "qual empresa",
            "quais empresas",
            "por fornecedor",
            "por fornecedores",
            "por empresa",
            "por empresas",
        ),
    ),
    (
        "secretaria",
        (
            "qual secretaria",
            "quais secretarias",
            "por secretaria",
            "por secretarias",
        ),
    ),
    (
        "categoria",
        (
            "qual categoria",
            "quais categorias",
            "por categoria",
            "por categorias",
        ),
    ),
)

_CONTRATOS_RANKING_DIMENSION_PLURAL_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("fornecedor", ("fornecedores", "empresas")),
    ("secretaria", ("secretarias",)),
    ("categoria", ("categorias",)),
)

_CONTRATOS_DIMENSION_COUNT_SIGNAL_PATTERNS = (
    "mais contratos",
    "mais contrato",
    "maior quantidade de contratos",
    "maior numero de contratos",
    "maiores quantidades de contratos",
    "maiores numeros de contratos",
    "quantos contratos",
    "quantas contratos",
)

_CONTRATOS_ACTIVITY_TERMS = (
    "ativo",
    "ativos",
    "atual",
    "atuais",
    "hoje",
    "atualmente",
)


def _normalize(text: str) -> str:
    """Remove acentos e normaliza caixa para simplificar match por texto."""

    return normalize_conversation_text(text)


def _contains_any(normalized_text: str, keywords: tuple[str, ...]) -> bool:
    """Retorna True quando qualquer palavra-chave aparece no texto normalizado."""

    return any(keyword in normalized_text for keyword in keywords)


def _contains_term(normalized_text: str, term: str) -> bool:
    """Faz match por termo completo para evitar falsos positivos por substring."""

    return re.search(rf"\b{re.escape(term)}\b", normalized_text) is not None


def _contains_any_term(normalized_text: str, terms: tuple[str, ...]) -> bool:
    """Versão por termo completo de `_contains_any`."""

    return any(_contains_term(normalized_text, term) for term in terms)


def _normalize_public_object_candidate(raw_object: str) -> str | None:
    """Limpa um objeto textual antes de usá-lo como filtro público."""

    candidate = " ".join(raw_object.split()).strip(" .,-/")
    candidate = re.sub(r"\s+\b(?:em|de|do|da)\b\s+20\d{2}\b$", "", candidate).strip()
    if not candidate:
        return None

    tokens = candidate.split()
    while tokens and tokens[0] in _LEADING_PUBLIC_OBJECT_ARTICLES:
        tokens = tokens[1:]
    while len(tokens) > 1 and tokens[0] in _LEADING_PUBLIC_OBJECT_LABELS:
        tokens = tokens[1:]
        while tokens and tokens[0] in _LEADING_PUBLIC_OBJECT_ARTICLES:
            tokens = tokens[1:]

    if not tokens:
        return None

    normalized_candidate = " ".join(tokens).strip(" .,-/")
    if re.fullmatch(r"20\d{2}", normalized_candidate):
        return None
    return normalized_candidate or None


def _is_scope_or_department_object(candidate: str) -> bool:
    """Evita confundir secretaria/area publica com objeto contratual."""

    return candidate.startswith("secretaria de ") or (candidate in _PUBLIC_SCOPE_OBJECT_EXCLUSIONS)


def _is_too_generic_public_object(candidate: str) -> bool:
    """Rejeita frases vagas como `gasto` que pioram o roteamento."""

    tokens = tuple(re.findall(r"[a-z0-9]+", candidate))
    if not tokens:
        return True

    meaningful_tokens = tuple(
        token for token in tokens if token not in _LEADING_PUBLIC_OBJECT_ARTICLES and token != "e"
    )
    if not meaningful_tokens:
        return True

    # Objetos formados apenas por eventos/shows (ex.: "eventos", "shows e
    # eventos") são específicos o bastante para o fan-out de gasto-com-evento.
    if all(token in _EVENT_SHOW_OBJECT_TOKENS for token in meaningful_tokens):
        return False

    return all(token in _GENERIC_PUBLIC_OBJECT_TOKENS for token in meaningful_tokens)


def _extract_public_object_candidate(
    normalized_text: str,
    *,
    contexts: tuple[str, ...],
) -> str | None:
    """Extrai um objeto contratual nominal quando o contexto textual é forte."""

    for alias, canonical_value in _KNOWN_PUBLIC_OBJECT_ALIASES:
        if alias in normalized_text:
            return canonical_value

    for context_name, pattern in _PUBLIC_OBJECT_EXTRACTION_PATTERNS:
        if context_name not in contexts:
            continue
        match = pattern.search(normalized_text)
        if match is None:
            continue

        candidate = _normalize_public_object_candidate(match.group("object"))
        if candidate is None:
            continue
        if _is_scope_or_department_object(candidate):
            continue
        if _is_too_generic_public_object(candidate):
            continue
        return candidate

    return _extract_festival_object(normalized_text)


def _extract_festival_object(normalized_text: str) -> str | None:
    """Preserva a frase específica de festival; só o `festival` cru cai no default."""

    if "festival" not in normalized_text:
        return None

    match = re.search(r"\bfestival\b", normalized_text)
    if match is None:
        return None

    phrase_match = re.match(
        r"festival(?:\s+(?:de|do|da)\s+[a-z]+(?:\s+[a-z]+){0,2})?",
        normalized_text[match.start() :],
    )
    phrase = phrase_match.group(0) if phrase_match else "festival"
    return " ".join(phrase.split())


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

    # Verbos genéricos de busca (pesquise/busque/procure) NÃO geram nome de
    # histórico de folha: só pistas reais de salário/pagamento qualificam.
    patterns = [
        r"salario\s+(?:do|da|de)\s+([a-z\s]+?)(?:\?|$)",
        r"salario\s+([a-z\s]+?)(?:\?|$)",
        r"quanto\s+([a-z\s]+?)\s+(?:recebe|recebeu|ganha|ganhou)(?:\?|$)",
        r"quanto\s+(?:recebe|recebeu|ganha|ganhou)\s+([a-z\s]+?)(?:\?|$)",
        r"(?:quanto\s+e\s+)?(?:o\s+)?salario\s+(?:do|da|de)\s+([a-z\s]+?)(?:\?|$)",
        r"pagamentos\s+(?:do|da|de)\s+([a-z\s]+?)(?:\?|$)",
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
        nome = re.sub(r"^(?:do|da|de|o|a)\s+", "", nome)
        nome_tokens = nome.split()
        if set(nome_tokens).issubset(REFERENTIAL_NAME_TOKENS):
            continue
        # Objeto que começa com substantivo de domínio não é nome de pessoa.
        if nome_tokens and nome_tokens[0] in _HISTORICO_NAO_NOME_INICIAIS:
            continue
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

    if _extract_contratos_ranking_dimension(normalized_text) == "fornecedor" and _has_contratos_dimension_count_signal(
        normalized_text
    ):
        return None

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


def _extract_contratos_ranking_dimension(normalized_text: str) -> str | None:
    """Identifica quando o usuario quer agrupar contratos por uma dimensao."""

    for dimension, cues in _CONTRATOS_RANKING_DIMENSION_CUES:
        if any(cue in normalized_text for cue in cues):
            return dimension

    if not any(term in normalized_text for term in ("ranking", "top")):
        return None

    for dimension, aliases in _CONTRATOS_RANKING_DIMENSION_PLURAL_ALIASES:
        if _contains_any_term(normalized_text, aliases):
            return dimension
    return None


def _has_contratos_dimension_count_signal(normalized_text: str) -> bool:
    """Diferencia ranking por contagem de ranking de contratos individuais."""

    if any(pattern in normalized_text for pattern in _CONTRATOS_DIMENSION_COUNT_SIGNAL_PATTERNS):
        return True
    if any(term in normalized_text for term in ("valor", "media", "soma", "total")):
        return False
    return any(term in normalized_text for term in ("ranking", "top"))


def _is_contratos_dimension_count_ranking_query(normalized_text: str) -> bool:
    """Reconhece perguntas de ranking/contagem por dimensao no dominio de contratos."""

    if not _is_contratos_query(normalized_text):
        return False
    if _extract_contratos_ranking_dimension(normalized_text) is None:
        return False
    return _has_contratos_dimension_count_signal(normalized_text)


def _is_contratos_singular_dimension_ranking_query(
    normalized_text: str,
    *,
    dimension: str | None = None,
) -> bool:
    """Detecta formulacoes singulares para ampliar o limite e preservar empates."""

    resolved_dimension = dimension or _extract_contratos_ranking_dimension(normalized_text)
    singular_cues = {
        "fornecedor": ("qual fornecedor", "qual empresa"),
        "secretaria": ("qual secretaria",),
        "categoria": ("qual categoria",),
    }.get(resolved_dimension, ())
    return any(cue in normalized_text for cue in singular_cues)


def _extract_contratos_active_vigencia_filters(
    normalized_text: str,
) -> dict[str, str] | None:
    """Traduz `ativos hoje/atualmente` para vigência na data atual.

    Um contrato está em vigência hoje quando começou até hoje e ainda não
    terminou (`data_inicio <= hoje <= data_fim`, ou `data_fim` em aberto).
    """

    if _extract_year(normalized_text) is not None:
        return None
    if not _contains_any_term(normalized_text, _CONTRATOS_ACTIVITY_TERMS):
        return None

    return {"vigente_em": date.today().isoformat()}


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


_TRIMESTRE_RANGES: tuple[tuple[tuple[str, str], tuple[int, int]], ...] = (
    (("primeiro trimestre", "1 trimestre"), (1, 3)),
    (("segundo trimestre", "2 trimestre"), (4, 6)),
    (("terceiro trimestre", "3 trimestre"), (7, 9)),
    (("quarto trimestre", "4 trimestre"), (10, 12)),
)


def _extract_trimestre_range(normalized_text: str) -> tuple[int, int] | None:
    """Mapeia menções a trimestres para o intervalo de meses correspondente."""

    for cues, month_range in _TRIMESTRE_RANGES:
        if any(cue in normalized_text for cue in cues):
            return month_range
    return None


def _extract_receitas_filters_from_query(normalized_text: str) -> dict[str, Any]:
    """Converte sinais do texto em filtros públicos da tool de receitas."""

    filtros: dict[str, Any] = {"tipo_de_dado": _extract_receitas_tipo_de_dado(normalized_text)}

    if year := _extract_year(normalized_text):
        filtros["ano"] = year

    if trimestre := _extract_trimestre_range(normalized_text):
        filtros["mes_inicio"], filtros["mes_fim"] = trimestre

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
    if trimestre := _extract_trimestre_range(normalized_text):
        filtros["mes_inicio"], filtros["mes_fim"] = trimestre

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
    if _contains_any(
        normalized_text,
        ("pago", "pagos", "gasto", "investido", "investida", "investimento"),
    ):
        return "soma_valor_pago"
    return "soma_orcamento_atualizado"


def _extract_licitacoes_objeto(normalized_text: str) -> str | None:
    """Extrai alguns objetos recorrentes de licitações com alto valor prático."""

    return _extract_public_object_candidate(
        normalized_text,
        contexts=("licitacoes", "spend"),
    )


def _extract_contratos_descricao(normalized_text: str) -> str | None:
    """Extrai termos de descrição de contrato para alguns eventos recorrentes."""

    return _extract_public_object_candidate(
        normalized_text,
        contexts=("contratos", "spend", "relation"),
    )


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
    elif vigencia_filters := _extract_contratos_active_vigencia_filters(normalized_text):
        filtros.update(vigencia_filters)
    return filtros


def _contains_prompt_injection(normalized_text: str) -> bool:
    """Aplica patterns defensivos para bloquear tentativas de prompt injection."""

    return any(re.search(pattern, normalized_text) is not None for pattern in PROMPT_INJECTION_PATTERNS)


def _count_keyword_hits(normalized_text: str, keywords: tuple[str, ...]) -> int:
    """Conta quantas palavras-chave de um conjunto aparecem no texto."""

    return sum(1 for keyword in keywords if keyword in normalized_text)
