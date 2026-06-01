"""Tool publica para consultas amplas de despesas."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import selectinload

from agents.tools.registry import PUBLIC_SCOPE, register
from database import session as session_manager
from database.models import DespesaDocumento
from shared.utils.decimal_to_float import decimal_to_float
from shared.utils.text import matches_text_query

from .consultar_despesas_schema import (
    ALLOWED_DESPESA_FIELDS,
    ConsultarDespesasMetadata,
    ConsultarDespesasParams,
    ConsultarDespesasResponse,
    DespesaFiltroSchema,
)


def _descricao_documento(registro: DespesaDocumento) -> str | None:
    if registro.descricao_acao:
        return registro.descricao_acao
    for item in registro.itens:
        if item.descricao_item:
            return item.descricao_item
    return None


def _row_to_public_dict(registro: DespesaDocumento) -> dict[str, Any]:
    return {
        "tipo": registro.tipo_origem,
        "origem": registro.origem,
        "ano": registro.exercicio,
        "data": registro.data_documento.isoformat(),
        "numero": registro.numero_documento,
        "unidade_responsavel": registro.unidade_gestora,
        "area": registro.funcao,
        "credor": registro.credor,
        "valor_documento": decimal_to_float(registro.valor_documento),
        "valor_empenhado": decimal_to_float(registro.valor_empenhado),
        "valor_pago": decimal_to_float(registro.valor_pago),
        "valor_anulado": decimal_to_float(registro.valor_anulado),
        "descricao": _descricao_documento(registro),
        "conta_extra": registro.conta_extra_descricao,
        "contrato": registro.numero_contrato,
    }


def _matches_descricao(registro: DespesaDocumento, descricao: str | None) -> bool:
    if not descricao:
        return True
    textos = [
        registro.descricao_acao,
        registro.programa,
        registro.objetivo_viagem,
        registro.destino,
        registro.conta_extra_descricao,
        registro.categoria_economica_descricao,
        registro.grupo_despesa_descricao,
        registro.elemento_despesa_descricao,
    ]
    textos.extend(item.descricao_item for item in registro.itens)
    return any(matches_text_query(texto, descricao) for texto in textos)


def load_filtered_despesas(
    session,
    filtros: DespesaFiltroSchema,
) -> list[DespesaDocumento]:
    query = session.query(DespesaDocumento).options(
        selectinload(DespesaDocumento.itens)
    )
    registros = query.all()

    if filtros.tipo:
        registros = [r for r in registros if r.tipo_origem == filtros.tipo]
    if filtros.origem:
        registros = [
            r for r in registros if matches_text_query(r.origem, filtros.origem)
        ]
    if filtros.ano:
        registros = [r for r in registros if r.exercicio == filtros.ano]
    if filtros.data_inicio:
        registros = [r for r in registros if r.data_documento >= filtros.data_inicio]
    if filtros.data_fim:
        registros = [r for r in registros if r.data_documento <= filtros.data_fim]
    if filtros.numero:
        registros = [
            r
            for r in registros
            if matches_text_query(r.numero_documento, filtros.numero)
        ]
    if filtros.credor:
        registros = [
            r for r in registros if matches_text_query(r.credor, filtros.credor)
        ]
    if filtros.cpf_cnpj:
        registros = [
            r for r in registros if matches_text_query(r.cpf_cnpj, filtros.cpf_cnpj)
        ]
    if filtros.unidade_responsavel:
        registros = [
            r
            for r in registros
            if matches_text_query(r.unidade_gestora, filtros.unidade_responsavel)
        ]
    if filtros.area:
        registros = [r for r in registros if matches_text_query(r.funcao, filtros.area)]
    if filtros.conta_extra:
        registros = [
            r
            for r in registros
            if matches_text_query(r.conta_extra_descricao, filtros.conta_extra)
            or matches_text_query(r.conta_extra_identificacao, filtros.conta_extra)
        ]
    if filtros.contrato:
        registros = [
            r
            for r in registros
            if matches_text_query(r.numero_contrato, filtros.contrato)
        ]
    if filtros.descricao:
        registros = [r for r in registros if _matches_descricao(r, filtros.descricao)]

    return registros


def sort_despesas(
    registros: list[DespesaDocumento],
    ordenar_por: str,
    ordem: str,
) -> list[DespesaDocumento]:
    reverse = ordem == "desc"

    def key(registro: DespesaDocumento) -> Any:
        mapping = {
            "data": registro.data_documento,
            "valor_documento": registro.valor_documento or Decimal("0"),
            "valor_empenhado": registro.valor_empenhado or Decimal("0"),
            "valor_pago": registro.valor_pago or Decimal("0"),
            "credor": registro.credor or "",
            "numero": registro.numero_documento or "",
        }
        return mapping[ordenar_por]

    return sorted(registros, key=key, reverse=reverse)


def project_despesas(
    registros: list[DespesaDocumento],
    campos: list[str],
) -> list[dict[str, Any]]:
    selected = campos or list(ALLOWED_DESPESA_FIELDS)
    return [
        {
            campo: value
            for campo, value in _row_to_public_dict(registro).items()
            if campo in selected
        }
        for registro in registros
    ]


@register(
    name="consultar_despesas",
    scope=PUBLIC_SCOPE,
    tags=["domain:despesas", "shape:lookup"],
)
def consultar_despesas(
    filtros: dict[str, Any] | None = None,
    ordenar_por: str = "data",
    ordem: str = "desc",
    limite: int = 10,
    offset: int = 0,
    campos: list[str] | None = None,
) -> dict[str, Any]:
    """
    Lista documentos de despesa por credor, area, numero, contrato e descricao.

    Use esta tool quando a pergunta pedir empenhos, restos a pagar ou documentos
    extras individuais, inclusive buscas por credor, area, contrato ou texto da
    despesa.
    NAO use para planejamento orcamentario; para isso use
    `consultar_planejamento`.
    NAO use para totais, comparacoes ou rankings agregados; para isso use
    `agregar_despesas`.

    Args:
        filtros: Objeto com filtros opcionais. Campos aceitos: `tipo`, `origem`,
            `ano`, `data_inicio`, `data_fim`, `numero`, `credor`, `cpf_cnpj`,
            `unidade_responsavel`, `area`, `conta_extra`, `contrato` e
            `descricao`. `tipo` aceita `empenho`, `restos_a_pagar`,
            `documento_extra`, `diaria` ou `passagem`. Datas em `YYYY-MM-DD`.
        ordenar_por: Campo de ordenacao. Aceita `data`, `valor_documento`,
            `valor_empenhado`, `valor_pago`, `credor` ou `numero`.
        ordem: Direcao da ordenacao: `asc` ou `desc`.
        limite: Tamanho da pagina. Inteiro de 1 a 100.
        offset: Deslocamento da pagina. Inteiro maior ou igual a 0.
        campos: Lista opcional com qualquer subconjunto dos campos publicos de
            despesa retornados em cada item.

    Returns:
        dict com:
        - `total`: total de registros encontrados antes da paginacao.
        - `resultados`: lista de despesas; cada item pode incluir `tipo`,
          `origem`, `ano`, `data`, `numero`, `unidade_responsavel`, `area`,
          `credor`, `valor_documento`, `valor_empenhado`, `valor_pago`,
          `valor_anulado`, `descricao`, `conta_extra` e `contrato`.
        - `metadata`: filtros aplicados, ordenacao, paginacao e campos pedidos.
        - `mensagem`: aviso quando a resposta estiver paginada.
        - `sugestao`: dica quando nenhuma despesa for encontrada.
    """
    try:
        params = ConsultarDespesasParams.model_validate(
            {
                "filtros": filtros,
                "ordenar_por": ordenar_por,
                "ordem": ordem,
                "limite": limite,
                "offset": offset,
                "campos": campos,
            }
        )
    except ValidationError as exc:
        fallback_metadata = ConsultarDespesasMetadata(
            ordenar_por="data",
            ordem="desc",
            limite=10,
            offset=0,
        )
        return ConsultarDespesasResponse(
            total=0,
            resultados=[],
            metadata=fallback_metadata,
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json")

    with session_manager.get_session() as session:
        registros = load_filtered_despesas(session, params.filtros)
        total = len(registros)
        ordenados = sort_despesas(registros, params.ordenar_por, params.ordem)
        pagina = ordenados[params.offset : params.offset + params.limite]
        resultados = project_despesas(pagina, params.campos)

    metadata = ConsultarDespesasMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
        offset=params.offset,
        campos=params.campos or list(ALLOWED_DESPESA_FIELDS),
    )

    if not resultados:
        return ConsultarDespesasResponse(
            total=0,
            resultados=[],
            metadata=metadata,
            sugestao="Nenhuma despesa encontrada com os filtros.",
        ).model_dump(mode="json")

    mensagem = None
    if total > len(resultados):
        mensagem = f"Mostrando {len(resultados)} de {total} despesas encontradas."

    return ConsultarDespesasResponse(
        total=total,
        resultados=resultados,
        metadata=metadata,
        mensagem=mensagem,
    ).model_dump(mode="json")
