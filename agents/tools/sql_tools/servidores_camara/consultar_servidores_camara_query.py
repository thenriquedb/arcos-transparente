"""Tool publica para consultas de servidores da Camara Municipal."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from agents.tools.names import ToolName
from agents.tools.registry import PUBLIC_SCOPE, register, routing_metadata
from agents.tools.sql_tools.shared.lookup import (
    LookupExecutionResult,
    build_lookup_response,
    execute_statement_lookup,
)
from agents.tools.sql_tools.shared.validation import validate_tool_params
from database import session as session_manager
from database.models import ServidorCamara

from .consultar_servidores_camara_schema import (
    ConsultarServidoresCamaraMetadata,
    ConsultarServidoresCamaraParams,
    ConsultarServidoresCamaraResponse,
)
from .shared.filters import ALLOWED_CAMARA_FIELDS
from .shared.querying import (
    apply_servidores_camara_filters,
    project_servidor_camara_fields,
    resolve_mes_de_referencia_padrao_camara,
)


_ORDER_COLUMNS = {
    "nome": ServidorCamara.nome,
    "cargo": ServidorCamara.cargo,
    "lotacao": ServidorCamara.lotacao,
    "salario_base": ServidorCamara.salario_base,
    "liquido": ServidorCamara.liquido,
    "mes_de_referencia": ServidorCamara.competencia_referencia,
}


@register(
    name=ToolName.CONSULTAR_SERVIDORES_CAMARA,
    scope=PUBLIC_SCOPE,
    tags=["domain:servidores_camara", "shape:lookup"],
    routing=routing_metadata(
        examples=[
            "Quais sao os servidores da Camara Municipal?",
            "Quais vereadores estao em atividade na Camara?",
            "Liste os assessores da Camara de Arcos.",
        ],
        hints=[
            "camara municipal",
            "vereador",
            "legislativo",
            "servidor da camara",
            "assessor legislativo",
        ],
    ),
)
def consultar_servidores_camara(
    filtros: dict[str, Any] | None = None,
    ordenar_por: str = "nome",
    ordem: str = "asc",
    limite: int = 10,
    offset: int = 0,
    campos: list[str] | None = None,
) -> dict[str, Any]:
    """
    Lista servidores e cargos da Camara Municipal de Arcos.

    Use esta tool para perguntas sobre quem trabalha na Camara Municipal
    (vereadores, assessores, secretaria da camara, comissionados etc.), cargos,
    lotacoes e situacao funcional dos servidores do Legislativo.
    NAO use para servidores da Prefeitura; para esses use `consultar_servidores`.
    Para salario individual de vereador ou de servidor da Camara com nome informado,
    use esta tool com filtro `nome` + `mes_de_referencia`.

    Se `mes_de_referencia` nao for informado, a consulta usa o mes mais recente
    com dados para evitar misturar snapshots de meses diferentes.

    Args:
        filtros: Filtros opcionais. Campos: `nome`, `cargo`, `lotacao`,
            `situacao_funcional`, `vinculo`, `mes_de_referencia`,
            `mes_de_referencia_inicio`, `mes_de_referencia_fim`,
            `salario_min`, `salario_max`. Datas em `YYYY-MM-DD`.
        ordenar_por: Campo de ordenacao. Aceita `nome`, `cargo`, `lotacao`,
            `salario_base`, `liquido` ou `mes_de_referencia`.
        ordem: `asc` ou `desc`.
        limite: Tamanho da pagina (1 a 100).
        offset: Deslocamento de pagina.
        campos: Lista de campos por item. Disponiveis: `id`, `nome`, `matricula`,
            `cargo`, `lotacao`, `situacao_funcional`, `salario_base`,
            `proventos`, `descontos`, `liquido`, `mes_de_referencia`.

    Returns:
        dict com `total`, `resultados`, `metadata`, `mensagem`, `sugestao`.
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
        schema_type=ConsultarServidoresCamaraParams,
        on_error=lambda exc: ConsultarServidoresCamaraResponse(
            total=0,
            resultados=[],
            metadata=ConsultarServidoresCamaraMetadata(
                ordenar_por="nome",
                ordem="asc",
                limite=10,
                offset=0,
            ),
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json"),
    )
    if isinstance(validated, dict):
        return validated
    params = validated

    with session_manager.get_session() as session:
        mes_de_referencia_considerado, mes_padrao_aplicado = resolve_mes_de_referencia_padrao_camara(
            session, params.filtros
        )
        base_stmt = apply_servidores_camara_filters(
            select(ServidorCamara),
            params.filtros,
            mes_de_referencia_considerado=mes_de_referencia_considerado,
        )
        total, servidores = execute_statement_lookup(
            session,
            stmt=base_stmt,
            ordenar_por=params.ordenar_por,
            ordem=params.ordem,
            offset=params.offset,
            limite=params.limite,
            order_columns=_ORDER_COLUMNS,
            tie_breakers=(ServidorCamara.nome.asc(),),
            load_rows=lambda db_session, stmt: db_session.execute(stmt).scalars().all(),
        )

    metadata = ConsultarServidoresCamaraMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
        offset=params.offset,
        campos=params.campos or list(ALLOWED_CAMARA_FIELDS),
        mes_de_referencia_considerado=mes_de_referencia_considerado,
        mes_de_referencia_padrao_aplicado=mes_padrao_aplicado,
    )
    execution = LookupExecutionResult(
        total=total,
        rows=servidores,
        suggestion=("Nenhum servidor da Camara encontrado com os filtros informados." if not servidores else None),
    )
    return build_lookup_response(
        response_type=ConsultarServidoresCamaraResponse,
        metadata=metadata,
        execution=execution,
        project_row=project_servidor_camara_fields,
        campos=params.campos,
    )
