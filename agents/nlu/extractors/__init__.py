"""Extractors de entidades, organizados por escopo e reexportados como uma API única.

Cada submódulo concentra a extração de um escopo (`text`, `public_object`,
`secretaria`, `historico`, `planejamento`, `contratos`, `receitas`). Importadores
continuam usando `from agents.nlu.extractors import _extract_*` sem conhecer a
divisão interna.
"""

from __future__ import annotations

from .contratos import (
    _extract_contrato_fornecedor,
    _extract_contratos_ranking_dimension,
    _has_contratos_dimension_count_signal,
    _is_contratos_dimension_count_ranking_query,
    _is_contratos_query,
)
from .historico import _extract_nome_para_historico
from .planejamento import (
    _extract_planejamento_acao,
    _extract_planejamento_area,
    _extract_planejamento_entidade,
    _extract_planejamento_fonte_recurso,
    _extract_planejamento_programa,
)
from .public_object import (
    _extract_contratos_descricao,
    _extract_festival_object,
    _extract_licitacoes_objeto,
    _extract_public_object_candidate,
)
from .receitas import _extract_receitas_tema, _extract_receitas_unidade
from .secretaria import _extract_secretaria
from .text import (
    _contains_any,
    _contains_any_term,
    _contains_prompt_injection,
    _contains_term,
    _count_keyword_hits,
    _extract_limit,
    _extract_year,
)


__all__ = [
    # text
    "_contains_any",
    "_contains_any_term",
    "_contains_prompt_injection",
    "_contains_term",
    "_count_keyword_hits",
    "_extract_limit",
    "_extract_year",
    # secretaria
    "_extract_secretaria",
    # historico
    "_extract_nome_para_historico",
    # public_object
    "_extract_contratos_descricao",
    "_extract_festival_object",
    "_extract_licitacoes_objeto",
    "_extract_public_object_candidate",
    # planejamento
    "_extract_planejamento_acao",
    "_extract_planejamento_area",
    "_extract_planejamento_entidade",
    "_extract_planejamento_fonte_recurso",
    "_extract_planejamento_programa",
    # contratos
    "_extract_contrato_fornecedor",
    "_extract_contratos_ranking_dimension",
    "_has_contratos_dimension_count_signal",
    "_is_contratos_dimension_count_ranking_query",
    "_is_contratos_query",
    # receitas
    "_extract_receitas_tema",
    "_extract_receitas_unidade",
]
