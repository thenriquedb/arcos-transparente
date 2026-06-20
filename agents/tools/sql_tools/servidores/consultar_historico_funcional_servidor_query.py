"""Tool publica para consultar historico funcional de servidores municipais."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select

from agents.tools.names import ToolName
from agents.tools.registry import PUBLIC_SCOPE, register, routing_metadata
from agents.tools.sql_tools.shared.empty_state import resolve_empty_result_suggestion
from agents.tools.sql_tools.shared.lookup import (
    LookupExecutionResult,
    build_lookup_response,
    execute_statement_lookup,
)
from agents.tools.sql_tools.shared.validation import validate_tool_params
from database import session as session_manager
from database.models import Servidor
from database.session import _normalizar_texto

from .consultar_historico_funcional_servidor_schema import (
    ALLOWED_FUNCIONAL_FIELDS,
    ConsultarHistoricoFuncionalServidorMetadata,
    ConsultarHistoricoFuncionalServidorParams,
    ConsultarHistoricoFuncionalServidorResponse,
    ServidorFuncionalFiltroSchema,
)


FUNCIONAL_ORDER_COLUMNS = {
    "nome": Servidor.nome,
    "data_admissao": Servidor.data_admissao,
    "data_desligamento": Servidor.data_desligamento,
    "lotacao": Servidor.lotacao,
    "situacao_funcional": Servidor.situacao_funcional,
    "cargo_funcao": Servidor.cargo_funcao,
}


def _apply_filters(stmt, filtros: ServidorFuncionalFiltroSchema):
    if filtros.nome:
        normalized = _normalizar_texto(filtros.nome) or ""
        stmt = stmt.where(func.normalizar(Servidor.nome).like(f"%{normalized}%"))
    if filtros.lotacao:
        normalized = _normalizar_texto(filtros.lotacao) or ""
        stmt = stmt.where(func.normalizar(Servidor.lotacao).like(f"%{normalized}%"))
    if filtros.situacao_funcional:
        normalized = _normalizar_texto(filtros.situacao_funcional) or ""
        stmt = stmt.where(Servidor.situacao_funcional.ilike(f"%{normalized}%"))
    if filtros.forma_contratacao:
        normalized = _normalizar_texto(filtros.forma_contratacao) or ""
        stmt = stmt.where(Servidor.forma_contratacao_investidura.ilike(f"%{normalized}%"))
    if filtros.vinculo_empregaticio:
        normalized = _normalizar_texto(filtros.vinculo_empregaticio) or ""
        stmt = stmt.where(Servidor.vinculo_empregaticio.ilike(f"%{normalized}%"))
    if filtros.cargo_funcao:
        normalized = _normalizar_texto(filtros.cargo_funcao) or ""
        stmt = stmt.where(func.normalizar(Servidor.cargo_funcao).like(f"%{normalized}%"))
    if filtros.data_admissao_inicio is not None:
        stmt = stmt.where(Servidor.data_admissao >= filtros.data_admissao_inicio)
    if filtros.data_admissao_fim is not None:
        stmt = stmt.where(Servidor.data_admissao <= filtros.data_admissao_fim)
    if filtros.data_desligamento_inicio is not None:
        stmt = stmt.where(Servidor.data_desligamento >= filtros.data_desligamento_inicio)
    if filtros.data_desligamento_fim is not None:
        stmt = stmt.where(Servidor.data_desligamento <= filtros.data_desligamento_fim)
    if filtros.em_cessao is True:
        stmt = stmt.where(Servidor.data_inicio_cessao.is_not(None))
    elif filtros.em_cessao is False:
        stmt = stmt.where(Servidor.data_inicio_cessao.is_(None))
    return stmt


def _project_servidor_funcional(row: Servidor, campos: list[str] | None) -> dict[str, Any]:
    full = {
        "nome": row.nome,
        "matricula": row.matricula,
        "cargo_funcao": row.cargo_funcao,
        "lotacao": row.lotacao,
        "situacao_funcional": row.situacao_funcional,
        "forma_contratacao_investidura": row.forma_contratacao_investidura,
        "data_admissao": row.data_admissao.isoformat() if row.data_admissao else None,
        "data_desligamento": row.data_desligamento.isoformat() if row.data_desligamento else None,
        "vinculo_empregaticio": row.vinculo_empregaticio,
        "regime_aposentadoria": row.regime_aposentadoria,
        "horario_trabalho": row.horario_trabalho,
        "carga_horaria": row.carga_horaria,
        "fundamento_legal": row.fundamento_legal,
        "local_origem_cedencia": row.local_origem_cedencia,
        "local_destino_cedencia": row.local_destino_cedencia,
        "onus_pagamento_cedencia": row.onus_pagamento_cedencia,
        "data_inicio_cessao": row.data_inicio_cessao.isoformat() if row.data_inicio_cessao else None,
        "data_fim_cessao": row.data_fim_cessao.isoformat() if row.data_fim_cessao else None,
        "competencia_referencia": row.competencia_referencia.isoformat() if row.competencia_referencia else None,
    }
    if campos:
        return {k: v for k, v in full.items() if k in campos}
    return full


@register(
    name=ToolName.CONSULTAR_HISTORICO_FUNCIONAL_SERVIDOR,
    scope=PUBLIC_SCOPE,
    tags=["domain:servidores", "shape:lookup"],
    routing=routing_metadata(
        examples=[
            "Quando o servidor Joao Silva foi admitido na prefeitura?",
            "Quais servidores foram desligados em 2024?",
            "Quais servidores estao em cessao para outros orgaos?",
            "Quantos servidores foram admitidos em 2023?",
        ],
        hints=[
            "data admissao",
            "data desligamento",
            "situacao funcional",
            "forma contratacao",
            "cessao",
            "vinculo empregaticio",
            "historico funcional",
            "cargo funcao",
            "regime aposentadoria",
            "desligado",
            "admitido",
        ],
    ),
)
def consultar_historico_funcional_servidor(
    filtros: dict[str, Any] | None = None,
    ordenar_por: str = "nome",
    ordem: str = "asc",
    limite: int = 20,
    offset: int = 0,
    campos: list[str] | None = None,
) -> dict[str, Any]:
    """
    Lista dados funcionais dos servidores municipais.

    Expoe informacoes funcionais que nao estao em `consultar_servidores`:
    data de admissao, data de desligamento, situacao funcional,
    forma de contratacao, vinculo empregaticio, regime de aposentadoria,
    horario de trabalho, carga horaria, fundamento legal e dados de cessao.
    Use esta tool para perguntas sobre quando um servidor foi admitido ou
    desligado, quais estao em cessao, ou filtragens por situacao funcional.
    NAO use para valores salariais; para isso use
    `buscar_historico_de_pagamentos_do_servidor`.
    NAO use para contagens agregadas; para isso use `agregar_servidores`.

    Args:
        filtros: Objeto com filtros opcionais. Campos aceitos: `nome`,
            `lotacao`, `situacao_funcional`, `forma_contratacao`,
            `vinculo_empregaticio`, `cargo_funcao`, `data_admissao_inicio`,
            `data_admissao_fim`, `data_desligamento_inicio`,
            `data_desligamento_fim` (formato `YYYY-MM-DD`) e `em_cessao`
            (booleano: `true` para listar apenas servidores em cessao).
        ordenar_por: Aceita `nome`, `data_admissao`, `data_desligamento`,
            `lotacao`, `situacao_funcional` ou `cargo_funcao`.
        ordem: Direcao da ordenacao: `asc` ou `desc`.
        limite: Tamanho da pagina. Inteiro de 1 a 100.
        offset: Deslocamento da pagina. Inteiro maior ou igual a 0.
        campos: Lista opcional com subconjunto dos campos publicos.

    Returns:
        dict com:
        - `total`: total de registros encontrados antes da paginacao.
        - `resultados`: lista de servidores com dados funcionais.
        - `metadata`: filtros aplicados, ordenacao e paginacao.
        - `mensagem`: aviso quando a resposta estiver paginada.
        - `sugestao`: dica quando nenhum registro for encontrado.
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
        schema_type=ConsultarHistoricoFuncionalServidorParams,
        on_error=lambda exc: ConsultarHistoricoFuncionalServidorResponse(
            total=0,
            resultados=[],
            metadata=ConsultarHistoricoFuncionalServidorMetadata(
                ordenar_por="nome",
                ordem="asc",
                limite=20,
                offset=0,
            ),
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json"),
    )
    if isinstance(validated, dict):
        return validated
    params = validated

    base_stmt = _apply_filters(select(Servidor), params.filtros)

    with session_manager.get_session() as session:
        total, servidores = execute_statement_lookup(
            session,
            stmt=base_stmt,
            ordenar_por=params.ordenar_por,
            ordem=params.ordem,
            offset=params.offset,
            limite=params.limite,
            order_columns=FUNCIONAL_ORDER_COLUMNS,
            tie_breakers=(Servidor.nome.asc(), Servidor.id.asc()),
            load_rows=lambda db_session, stmt: db_session.execute(stmt).scalars().all(),
        )
        empty_suggestion = resolve_empty_result_suggestion(
            session,
            domain_key="servidores_funcional",
            filters=params.filtros,
            default_suggestion="Nenhum servidor encontrado com os filtros informados.",
        )

    metadata = ConsultarHistoricoFuncionalServidorMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
        offset=params.offset,
        campos=params.campos or list(ALLOWED_FUNCIONAL_FIELDS),
    )

    execution = LookupExecutionResult(
        total=total,
        rows=servidores,
        suggestion=(empty_suggestion if not servidores else None),
    )
    return build_lookup_response(
        response_type=ConsultarHistoricoFuncionalServidorResponse,
        metadata=metadata,
        execution=execution,
        project_row=_project_servidor_funcional,
        campos=params.campos,
    )
