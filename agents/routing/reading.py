"""Leitura de consulta: lê uma pergunta cidadã em fatos estruturados de uma vez.

Este módulo é a interface profunda sobre os extractors privados. Em vez de cada
chamador (guardrails, seleção de tools) importar dezenas de funções `_extract_*`
e reparsear a mesma pergunta, eles dependem de `read_query` e leem os campos do
`QueryReading`. Os extractors continuam sendo a implementação privada por trás
desta interface.
"""

from __future__ import annotations

from dataclasses import dataclass

from agents.routing.conversation import normalize_conversation_text
from agents.routing.constants import (
    SUPPORTED_SCOPE_STRONG_KEYWORDS,
    SUPPORTED_SCOPE_WEAK_KEYWORDS,
)
from agents.routing.extractors import (
    _contains_prompt_injection,
    _count_keyword_hits,
    _extract_contrato_fornecedor,
    _extract_contratos_descricao,
    _extract_licitacoes_objeto,
    _extract_nome_para_historico,
    _extract_planejamento_area,
    _extract_planejamento_entidade,
    _extract_receitas_tema,
    _extract_receitas_unidade,
    _extract_secretaria,
    _extract_year,
)


@dataclass(frozen=True, slots=True)
class QueryReading:
    """Fatos estruturados extraídos de uma pergunta, lidos uma vez.

    `normalized_text` é a forma normalizada (sem acento, minúscula) sobre a qual
    todos os demais campos foram derivados, para que chamadores façam checagens
    textuais adicionais sem reparsear.
    """

    normalized_text: str
    is_prompt_injection: bool
    scope_strong_hits: int
    scope_weak_hits: int
    nome_historico: str | None
    licitacoes_objeto: str | None
    contratos_descricao: str | None
    contrato_fornecedor: str | None
    secretaria: str | None
    year: int | None
    planejamento_entidade: str | None
    planejamento_area: str | None
    receitas_tema: str | None
    receitas_unidade: str | None


def read_query(text: str) -> QueryReading:
    """Lê uma pergunta (ou fragmento) em um `QueryReading`.

    Aceita texto cru ou já normalizado — a normalização é idempotente.
    """

    normalized_text = normalize_conversation_text(text)
    return QueryReading(
        normalized_text=normalized_text,
        is_prompt_injection=_contains_prompt_injection(normalized_text),
        scope_strong_hits=_count_keyword_hits(normalized_text, SUPPORTED_SCOPE_STRONG_KEYWORDS),
        scope_weak_hits=_count_keyword_hits(normalized_text, SUPPORTED_SCOPE_WEAK_KEYWORDS),
        nome_historico=_extract_nome_para_historico(normalized_text),
        licitacoes_objeto=_extract_licitacoes_objeto(normalized_text),
        contratos_descricao=_extract_contratos_descricao(normalized_text),
        contrato_fornecedor=_extract_contrato_fornecedor(normalized_text),
        secretaria=_extract_secretaria(normalized_text),
        year=_extract_year(normalized_text),
        planejamento_entidade=_extract_planejamento_entidade(normalized_text),
        planejamento_area=_extract_planejamento_area(normalized_text),
        receitas_tema=_extract_receitas_tema(normalized_text),
        receitas_unidade=_extract_receitas_unidade(normalized_text),
    )
