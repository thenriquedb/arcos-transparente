"""Tool publica para consultar itens adquiridos em contratos."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from agents.tools.names import ToolName
from agents.tools.registry import PUBLIC_SCOPE, register, routing_metadata
from agents.tools.sql_tools.shared.validation import validate_tool_params
from database import session as session_manager
from database.models import ContratoItemAdquirido
from database.models.contracts import Contrato
from database.session import _normalizar_texto
from shared.utils.decimal_to_float import decimal_to_float

from .consultar_itens_adquiridos_contrato_schema import (
    ALLOWED_ITENS_FIELDS,
    ConsultarItensAdquiridosContratoMetadata,
    ConsultarItensAdquiridosContratoParams,
    ConsultarItensAdquiridosContratoResponse,
    ItensFiltroSchema,
)


def _load_itens(session, filtros: ItensFiltroSchema) -> list[ContratoItemAdquirido]:
    stmt = (
        select(ContratoItemAdquirido)
        .options(joinedload(ContratoItemAdquirido.contrato))
        .join(Contrato, ContratoItemAdquirido.contrato_id == Contrato.id)
    )
    if filtros.numero_contrato:
        normalized = _normalizar_texto(filtros.numero_contrato) or ""
        stmt = stmt.where(Contrato.numero.ilike(f"%{normalized}%"))
    if filtros.fornecedor:
        normalized = _normalizar_texto(filtros.fornecedor) or ""
        stmt = stmt.where(Contrato.fornecedor.ilike(f"%{normalized}%"))
    if filtros.secretaria:
        normalized = _normalizar_texto(filtros.secretaria) or ""
        stmt = stmt.where(Contrato.secretaria.ilike(f"%{normalized}%"))
    if filtros.identificacao:
        normalized = _normalizar_texto(filtros.identificacao) or ""
        stmt = stmt.where(ContratoItemAdquirido.identificacao.ilike(f"%{normalized}%"))
    if filtros.data_inicio_inicio is not None:
        stmt = stmt.where(Contrato.data_inicio >= filtros.data_inicio_inicio)
    if filtros.data_inicio_fim is not None:
        stmt = stmt.where(Contrato.data_inicio <= filtros.data_inicio_fim)
    return list(session.execute(stmt).unique().scalars())


def _sort_key(item: ContratoItemAdquirido, ordenar_por: str) -> Any:
    mapping = {
        "valor_total": item.valor_total or Decimal(0),
        "valor_unitario": item.valor_unitario or Decimal(0),
        "quantidade": item.quantidade or Decimal(0),
        "identificacao": (item.identificacao or "").lower(),
        "numero_contrato": (item.contrato.numero if item.contrato else "") or "",
    }
    return mapping[ordenar_por]


def _row_to_public_dict(item: ContratoItemAdquirido) -> dict[str, Any]:
    contrato = item.contrato
    return {
        "numero_contrato": contrato.numero if contrato else None,
        "fornecedor": contrato.fornecedor if contrato else None,
        "secretaria": contrato.secretaria if contrato else None,
        "categoria": contrato.categoria if contrato else None,
        "data_inicio": contrato.data_inicio.isoformat() if contrato and contrato.data_inicio else None,
        "numero_lote": item.numero_lote,
        "numero_item": item.numero_item,
        "identificacao": item.identificacao,
        "quantidade": decimal_to_float(item.quantidade),
        "valor_unitario": decimal_to_float(item.valor_unitario),
        "valor_total": decimal_to_float(item.valor_total),
    }


@register(
    name=ToolName.CONSULTAR_ITENS_ADQUIRIDOS_CONTRATO,
    scope=PUBLIC_SCOPE,
    tags=["domain:contratos", "shape:lookup"],
    routing=routing_metadata(
        examples=[
            "Quais itens foram comprados no contrato 45/2025?",
            "Qual o preco unitario pago por cadeiras escolares?",
            "Listar todos os contratos que adquiriram alcool gel em 2024.",
            "Quais materiais foram adquiridos pela secretaria de saude?",
        ],
        hints=[
            "item adquirido",
            "item contrato",
            "material comprado",
            "preco unitario",
            "quantidade adquirida",
            "objeto contratado",
            "produto contrato",
        ],
    ),
)
def consultar_itens_adquiridos_contrato(
    filtros: dict[str, Any] | None = None,
    ordenar_por: str = "valor_total",
    ordem: str = "desc",
    limite: int = 20,
    offset: int = 0,
    campos: list[str] | None = None,
) -> dict[str, Any]:
    """
    Lista os itens (materiais, servicos ou produtos) adquiridos em contratos.

    Cada item expoe: numero do contrato, fornecedor, secretaria, categoria,
    data de inicio, numero de lote, numero do item, descricao do material,
    quantidade, valor unitario e valor total.
    Use esta tool quando a pergunta pedir quais materiais ou produtos foram
    adquiridos num contrato especifico, ou quando quiser buscar contratos que
    compraram um determinado tipo de item.
    NAO use para dados gerais do contrato (valor total, vigencia, modalidade);
    para isso use `consultar_contratos`.
    NAO use para totais ou rankings de contratos; para isso use
    `agregar_contratos`.

    Args:
        filtros: Objeto com filtros opcionais. Campos aceitos: `numero_contrato`,
            `fornecedor`, `secretaria`, `identificacao` (texto do material/item),
            `data_inicio_inicio` e `data_inicio_fim` (formato `YYYY-MM-DD`).
        ordenar_por: Aceita `valor_total`, `valor_unitario`, `quantidade`,
            `identificacao` ou `numero_contrato`.
        ordem: Direcao da ordenacao: `asc` ou `desc`.
        limite: Tamanho da pagina. Inteiro de 1 a 100.
        offset: Deslocamento da pagina. Inteiro maior ou igual a 0.
        campos: Lista opcional com subconjunto dos campos publicos.

    Returns:
        dict com:
        - `total`: total de itens encontrados antes da paginacao.
        - `resultados`: lista de itens com dados do contrato e do item.
        - `metadata`: filtros aplicados, ordenacao e paginacao.
        - `mensagem`: aviso quando a resposta estiver paginada.
        - `sugestao`: dica quando nenhum item for encontrado.
    """
    validated = validate_tool_params(
        {
            "filtros": filtros,
            "ordenar_por": ordenar_por,
            "ordem": ordem,
            "limite": limite,
            "offset": offset,
            "campos": campos,
        },
        schema_type=ConsultarItensAdquiridosContratoParams,
        on_error=lambda exc: ConsultarItensAdquiridosContratoResponse(
            total=0,
            resultados=[],
            metadata=ConsultarItensAdquiridosContratoMetadata(
                ordenar_por="valor_total",
                ordem="desc",
                limite=20,
                offset=0,
            ),
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json"),
    )
    if isinstance(validated, dict):
        return validated
    params = validated

    with session_manager.get_session() as session:
        itens = _load_itens(session, params.filtros)
        reverse = params.ordem == "desc"
        ordenados = sorted(itens, key=lambda r: _sort_key(r, params.ordenar_por), reverse=reverse)
        total = len(ordenados)
        pagina = ordenados[params.offset : params.offset + params.limite]
        resultados = [_row_to_public_dict(r) for r in pagina]
        if params.campos:
            resultados = [{k: v for k, v in row.items() if k in params.campos} for row in resultados]

    metadata = ConsultarItensAdquiridosContratoMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
        offset=params.offset,
        campos=params.campos or list(ALLOWED_ITENS_FIELDS),
    )

    mensagem = None
    if total > params.offset + len(resultados):
        mensagem = f"Exibindo {len(resultados)} de {total} itens. Use limite e offset para navegar."

    return ConsultarItensAdquiridosContratoResponse(
        total=total,
        resultados=resultados,
        metadata=metadata,
        mensagem=mensagem,
        sugestao=("Nenhum item encontrado com os filtros informados." if not resultados else None),
    ).model_dump(mode="json")
