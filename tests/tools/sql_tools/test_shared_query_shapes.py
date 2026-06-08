from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from agents.tools.sql_tools.licitacoes.agregar_licitacoes_schema import (
    AgregacaoLicitacoesItem,
    AgregarLicitacoesMetadata,
    AgregarLicitacoesResponse,
)
from agents.tools.sql_tools.licitacoes.consultar_licitacoes_schema import (
    ConsultarLicitacoesMetadata,
    ConsultarLicitacoesResponse,
)
from agents.tools.sql_tools.licitacoes.shared.querying import (
    decimal_or_int_to_json,
    project_licitacao_fields,
)
from agents.tools.sql_tools.receitas.agregar_receitas_schema import (
    AgregacaoReceitasItem,
    AgregarReceitasMetadata,
    AgregarReceitasResponse,
)
from agents.tools.sql_tools.receitas.consultar_receitas_schema import (
    ConsultarReceitasMetadata,
    ConsultarReceitasResponse,
)
from agents.tools.sql_tools.receitas.shared.runtime import project_receita_fields
from agents.tools.sql_tools.servidores.agregar_servidores_schema import (
    AgregacaoServidoresItem,
    AgregarServidoresMetadata,
    AgregarServidoresResponse,
)
from agents.tools.sql_tools.servidores.consultar_servidores_schema import (
    ConsultarServidoresMetadata,
    ConsultarServidoresResponse,
)
from agents.tools.sql_tools.servidores.shared.querying import project_servidor_fields
from agents.tools.sql_tools.transferencias_financeiras.agregar_transferencias_financeiras_schema import (
    AgregarTransferenciasFinanceirasMetadata,
    AgregarTransferenciasFinanceirasResponse,
)
from agents.tools.sql_tools.transferencias_financeiras.consultar_transferencias_financeiras_query import (
    project_transferencia_financeira_fields,
)
from agents.tools.sql_tools.transferencias_financeiras.consultar_transferencias_financeiras_schema import (
    ConsultarTransferenciasFinanceirasMetadata,
    ConsultarTransferenciasFinanceirasResponse,
)
from agents.tools.sql_tools.shared.aggregate import (
    AggregateExecutionResult,
    build_aggregate_response,
    execute_collection_aggregate,
    execute_statement_grouped,
    execute_statement_total,
)
from agents.tools.sql_tools.shared.lookup import (
    LookupExecutionResult,
    build_lookup_response,
    execute_collection_lookup,
    execute_collection_lookup_result,
    execute_statement_lookup,
)
from agents.tools.sql_tools.shared.projection import (
    project_public_dict,
    project_public_fields,
)
from database.models import Base, FolhaServidor, Licitacao


def _build_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )
    return session_local()


def _servidor(
    *,
    nome: str,
    secretaria: str,
    salario_base,
    competencia_referencia: date = date(2025, 2, 1),
) -> FolhaServidor:
    return FolhaServidor(
        nome=nome,
        cargo="Cargo",
        secretaria=secretaria,
        salario_base=salario_base,
        competencia_referencia=competencia_referencia,
    )


def _licitacao(
    *,
    numero: str,
    modalidade: str,
    secretaria: str,
    valor_estimado,
    data_abertura: date,
    situacao: str = "Homologada",
    objeto: str = "Objeto",
) -> Licitacao:
    return Licitacao(
        numero=numero,
        modalidade=modalidade,
        objeto=objeto,
        valor_estimado=valor_estimado,
        data_abertura=data_abertura,
        situacao=situacao,
        secretaria=secretaria,
    )


def test_shared_statement_lookup_flow_preserves_order_projection_and_pagination() -> (
    None
):
    session = _build_session()
    session.add_all(
        [
            _servidor(
                nome="Alice Souza",
                secretaria="Saude",
                salario_base=Decimal("8200.00"),
            ),
            _servidor(
                nome="Bruno Costa",
                secretaria="Saude",
                salario_base=Decimal("9100.00"),
            ),
            _servidor(
                nome="Carla Sousa",
                secretaria="Obras",
                salario_base=Decimal("10400.00"),
            ),
        ]
    )
    session.commit()

    total, rows = execute_statement_lookup(
        session,
        stmt=select(FolhaServidor),
        ordenar_por="salario_base",
        ordem="desc",
        offset=0,
        limite=2,
        order_columns={"salario_base": FolhaServidor.salario_base},
        tie_breakers=(FolhaServidor.nome.asc(),),
        load_rows=lambda db_session, stmt: db_session.execute(stmt).scalars().all(),
    )
    response = build_lookup_response(
        response_type=ConsultarServidoresResponse,
        metadata=ConsultarServidoresMetadata(
            ordenar_por="salario_base",
            ordem="desc",
            limite=2,
            offset=0,
            campos=["nome", "salario_base"],
        ),
        execution=LookupExecutionResult(total=total, rows=rows),
        project_row=project_servidor_fields,
        campos=["nome", "salario_base"],
    )

    assert response["total"] == 3
    assert response["resultados"] == [
        {"nome": "Carla Sousa", "salario_base": 10400.0},
        {"nome": "Bruno Costa", "salario_base": 9100.0},
    ]
    assert response["mensagem"] == "Mostrando 2 de 3 registros encontrados."

    session.close()


def test_shared_collection_lookup_flow_preserves_order_projection_and_pagination() -> (
    None
):
    registros = [
        {
            "id": 1,
            "categoria": "IPTU",
            "valor_recebido": 9000.0,
            "data": date(2025, 1, 10),
        },
        {
            "id": 2,
            "categoria": "FUNDEB",
            "valor_recebido": 47000.0,
            "data": date(2025, 2, 20),
        },
        {
            "id": 3,
            "categoria": "ITBI",
            "valor_recebido": 12000.0,
            "data": date(2025, 2, 1),
        },
    ]

    total, rows = execute_collection_lookup(
        registros,
        ordenar_por="valor_recebido",
        ordem="desc",
        offset=1,
        limite=1,
        sort_key_getters={
            "valor_recebido": lambda row: row.get("valor_recebido") or 0.0,
        },
        tie_breaker_getters=(lambda row: row.get("id") or 0,),
    )
    response = build_lookup_response(
        response_type=ConsultarReceitasResponse,
        metadata=ConsultarReceitasMetadata(
            ordenar_por="valor_recebido",
            ordem="desc",
            limite=1,
            offset=1,
            campos=["categoria", "valor_recebido"],
        ),
        execution=LookupExecutionResult(total=total, rows=rows),
        project_row=project_receita_fields,
        campos=["categoria", "valor_recebido"],
    )

    assert response["total"] == 3
    assert response["resultados"] == [{"categoria": "ITBI", "valor_recebido": 12000.0}]
    assert response["mensagem"] == "Mostrando 1 de 3 registros encontrados."


def test_shared_collection_lookup_result_adds_empty_suggestion_only_when_page_is_empty() -> (
    None
):
    execution = execute_collection_lookup_result(
        [],
        ordenar_por="valor",
        ordem="desc",
        offset=0,
        limite=10,
        sort_key_getters={"valor": lambda row: row.get("valor") or 0},
        empty_suggestion="Nenhum registro encontrado.",
    )

    assert execution.total == 0
    assert list(execution.rows) == []
    assert execution.suggestion == "Nenhum registro encontrado."


def test_shared_projection_helpers_preserve_payload_or_requested_order() -> None:
    payload = {"origem": "camara", "ano": 2026, "valor": 552500.0}

    assert project_public_dict(
        payload,
        ["valor", "origem"],
        order="payload",
    ) == {"origem": "camara", "valor": 552500.0}
    assert project_public_dict(
        payload,
        ["valor", "origem"],
        order="requested",
    ) == {"valor": 552500.0, "origem": "camara"}
    assert project_public_fields(
        payload,
        ["ano", "origem"],
        serializer=lambda row: row,
        order="requested",
    ) == {"ano": 2026, "origem": "camara"}


def test_shared_lookup_flow_supports_response_supplements_and_row_decoration() -> None:
    session = _build_session()
    session.add_all(
        [
            _licitacao(
                numero="001/2025",
                modalidade="Pregao",
                secretaria="Saude",
                valor_estimado=Decimal("0.00"),
                data_abertura=date(2025, 1, 10),
            ),
            _licitacao(
                numero="002/2025",
                modalidade="Pregao",
                secretaria="Saude",
                valor_estimado=Decimal("250000.00"),
                data_abertura=date(2025, 2, 10),
            ),
            _licitacao(
                numero="003/2025",
                modalidade="Concorrencia",
                secretaria="Obras",
                valor_estimado=Decimal("500000.00"),
                data_abertura=date(2025, 3, 10),
            ),
        ]
    )
    session.commit()

    total, rows = execute_statement_lookup(
        session,
        stmt=select(Licitacao),
        ordenar_por="valor_estimado",
        ordem="asc",
        offset=0,
        limite=2,
        order_columns={"valor_estimado": Licitacao.valor_estimado},
        tie_breakers=(Licitacao.numero.asc(),),
        load_rows=lambda db_session, stmt: db_session.execute(stmt).scalars().all(),
    )
    response = build_lookup_response(
        response_type=ConsultarLicitacoesResponse,
        metadata=ConsultarLicitacoesMetadata(
            ordenar_por="valor_estimado",
            ordem="asc",
            limite=2,
            offset=0,
            campos=["numero", "valor_estimado"],
        ),
        execution=LookupExecutionResult(
            total=total,
            rows=rows,
            response_updates={"valor_total_estimado": 750000.0},
        ),
        project_row=lambda licitacao, campos: project_licitacao_fields(
            licitacao,
            campos,
            incluir_detalhes=False,
            max_vencedores=5,
            max_instrumentos=5,
            max_itens=10,
        ),
        campos=["numero", "valor_estimado"],
        transform_results=lambda resultados: [
            {
                **resultado,
                **(
                    {"aviso": "Consulte contratos para validar o valor contratado."}
                    if resultado.get("valor_estimado") == 0.0
                    else {}
                ),
            }
            for resultado in resultados
        ],
    )

    assert response["valor_total_estimado"] == 750000.0
    assert response["resultados"] == [
        {
            "numero": "001/2025",
            "valor_estimado": 0.0,
            "aviso": "Consulte contratos para validar o valor contratado.",
        },
        {"numero": "002/2025", "valor_estimado": 250000.0},
    ]
    assert response["mensagem"] == "Mostrando 2 de 3 registros encontrados."

    session.close()


def test_shared_lookup_flow_supports_mixed_record_collection_adopters() -> None:
    registros = [
        {
            "tipo_registro": "movimentacao",
            "ano": 2026,
            "data": "2026-01-16",
            "unidade_recebedora": "CAMARA MUNICIPAL",
            "tipo_movimento": "Recebimento",
            "valor": 552500.0,
        },
        {
            "tipo_registro": "emenda",
            "ano": 2026,
            "data": None,
            "autor": "Lafayete Andrada",
            "valor": 750000.0,
        },
        {
            "tipo_registro": "emenda",
            "ano": 2025,
            "data": None,
            "autor": "Cleitinho",
            "valor": 399046.98,
        },
    ]

    execution = execute_collection_lookup_result(
        registros,
        ordenar_por="valor",
        ordem="desc",
        offset=1,
        limite=1,
        sort_key_getters={"valor": lambda row: Decimal(str(row.get("valor") or 0))},
    )
    response = build_lookup_response(
        response_type=ConsultarTransferenciasFinanceirasResponse,
        metadata=ConsultarTransferenciasFinanceirasMetadata(
            ordenar_por="valor",
            ordem="desc",
            limite=1,
            offset=1,
            campos=["tipo_registro", "autor", "valor"],
        ),
        execution=execution,
        project_row=project_transferencia_financeira_fields,
        campos=["tipo_registro", "autor", "valor"],
    )

    assert response["total"] == 3
    assert response["resultados"] == [
        {"tipo_registro": "movimentacao", "valor": 552500.0}
    ]
    assert response["mensagem"] == "Mostrando 1 de 3 registros encontrados."


def test_shared_statement_aggregate_flow_orders_groups_and_adds_group_pagination() -> (
    None
):
    session = _build_session()
    session.add_all(
        [
            _servidor(
                nome="Alice Souza",
                secretaria="Saude",
                salario_base=Decimal("8200.00"),
            ),
            _servidor(
                nome="Bruno Costa",
                secretaria="Saude",
                salario_base=Decimal("9100.00"),
            ),
            _servidor(
                nome="Carla Sousa",
                secretaria="Obras",
                salario_base=Decimal("10400.00"),
            ),
        ]
    )
    session.commit()

    total_match, valor_total = execute_statement_total(
        session,
        count_stmt=select(func.count(FolhaServidor.id)),
        value_stmt=select(func.coalesce(func.sum(FolhaServidor.salario_base), 0)),
    )
    assert total_match == 3
    assert float(valor_total) == 27700.0

    metric_expression = func.count(FolhaServidor.id).label("contagem")
    grouped_stmt = select(
        FolhaServidor.secretaria.label("secretaria"),
        metric_expression,
    ).group_by(FolhaServidor.secretaria)
    total_grupos, rows = execute_statement_grouped(
        session,
        grouped_stmt=grouped_stmt,
        ordenar_por="metrica",
        ordem="desc",
        limite=1,
        group_column=FolhaServidor.secretaria,
        metric_expression=metric_expression,
    )
    response = build_aggregate_response(
        response_type=AgregarServidoresResponse,
        metadata=AgregarServidoresMetadata(
            agrupar_por="secretaria",
            metrica="contagem",
            ordenar_por="metrica",
            ordem="desc",
            limite=1,
        ),
        execution=AggregateExecutionResult(total_grupos=total_grupos, rows=rows),
        item_model=AgregacaoServidoresItem,
        agrupar_por="secretaria",
        metrica="contagem",
    )

    assert response["total_grupos"] == 2
    assert response["resultados"] == [{"secretaria": "Saude", "contagem": 2}]
    assert response["mensagem"] == "Mostrando 1 de 2 grupos encontrados."

    session.close()


def test_shared_collection_aggregate_flow_supports_total_only_and_empty_results() -> (
    None
):
    registros = [
        {"categoria": "FUNDEB", "valor_recebido": 47000.0},
        {"categoria": "IPTU", "valor_recebido": 39000.0},
        {"categoria": "IPTU", "valor_recebido": 1000.0},
    ]

    total_execution = execute_collection_aggregate(
        registros,
        agrupar_por=None,
        metrica="soma_valor_recebido",
        ordenar_por="metrica",
        ordem="desc",
        limite=10,
        group_key_getters={"categoria": lambda row: row.get("categoria")},
        metric_getters={
            "soma_valor_recebido": lambda row: row.get("valor_recebido") or 0.0,
        },
        serialize_metric=lambda value: value,
    )
    total_response = build_aggregate_response(
        response_type=AgregarReceitasResponse,
        metadata=AgregarReceitasMetadata(
            metrica="soma_valor_recebido",
            ordenar_por="metrica",
            ordem="desc",
            limite=10,
        ),
        execution=AggregateExecutionResult(
            valor_total=total_execution.valor_total,
            source_count=total_execution.source_count,
        ),
    )

    assert total_response["valor_total"] == 87000.0
    assert total_response["mensagem"] == (
        "Agregacao sem agrupamento: `valor_total` e o resultado final; "
        "`resultados` vazio e `total_grupos` 0 sao esperados. "
        "3 registros corresponderam aos filtros."
    )

    empty_execution = execute_collection_aggregate(
        [],
        agrupar_por="categoria",
        metrica="soma_valor_recebido",
        ordenar_por="metrica",
        ordem="desc",
        limite=10,
        group_key_getters={"categoria": lambda row: row.get("categoria")},
        metric_getters={
            "soma_valor_recebido": lambda row: row.get("valor_recebido") or 0.0,
        },
        serialize_metric=lambda value: value,
    )
    empty_response = build_aggregate_response(
        response_type=AgregarReceitasResponse,
        metadata=AgregarReceitasMetadata(
            agrupar_por="categoria",
            metrica="soma_valor_recebido",
            ordenar_por="metrica",
            ordem="desc",
            limite=10,
        ),
        execution=AggregateExecutionResult(
            total_grupos=empty_execution.total_grupos,
            rows=empty_execution.rows,
            suggestion="Nenhum registro de receitas encontrado com os filtros.",
        ),
        item_model=AgregacaoReceitasItem,
        agrupar_por="categoria",
        metrica="soma_valor_recebido",
    )

    assert empty_response["total_grupos"] == 0
    assert empty_response["resultados"] == []
    assert (
        empty_response["sugestao"]
        == "Nenhum registro de receitas encontrado com os filtros."
    )


def test_shared_statement_aggregate_flow_supports_new_statement_backed_adopters() -> (
    None
):
    session = _build_session()
    session.add_all(
        [
            _licitacao(
                numero="001/2025",
                modalidade="Pregao",
                secretaria="Saude",
                valor_estimado=Decimal("100000.00"),
                data_abertura=date(2025, 1, 10),
            ),
            _licitacao(
                numero="002/2025",
                modalidade="Pregao",
                secretaria="Saude",
                valor_estimado=Decimal("250000.00"),
                data_abertura=date(2025, 2, 10),
            ),
            _licitacao(
                numero="003/2025",
                modalidade="Concorrencia",
                secretaria="Obras",
                valor_estimado=Decimal("500000.00"),
                data_abertura=date(2025, 3, 10),
            ),
        ]
    )
    session.commit()

    metric_expression = func.coalesce(func.sum(Licitacao.valor_estimado), 0).label(
        "soma_valor_estimado"
    )
    grouped_stmt = select(
        Licitacao.secretaria.label("secretaria"),
        metric_expression,
    ).group_by(Licitacao.secretaria)
    total_grupos, rows = execute_statement_grouped(
        session,
        grouped_stmt=grouped_stmt,
        ordenar_por="metrica",
        ordem="desc",
        limite=1,
        group_column=Licitacao.secretaria,
        metric_expression=metric_expression,
    )
    response = build_aggregate_response(
        response_type=AgregarLicitacoesResponse,
        metadata=AgregarLicitacoesMetadata(
            agrupar_por="secretaria",
            metrica="soma_valor_estimado",
            ordenar_por="metrica",
            ordem="desc",
            limite=1,
        ),
        execution=AggregateExecutionResult(total_grupos=total_grupos, rows=rows),
        item_model=AgregacaoLicitacoesItem,
        agrupar_por="secretaria",
        metrica="soma_valor_estimado",
        serialize_metric=decimal_or_int_to_json,
    )

    assert response["total_grupos"] == 2
    assert response["resultados"] == [
        {"secretaria": "Obras", "soma_valor_estimado": 500000.0}
    ]
    assert response["mensagem"] == "Mostrando 1 de 2 grupos encontrados."

    session.close()


def test_shared_collection_aggregate_flow_supports_new_mixed_record_adopters() -> None:
    registros = [
        {"autor": "Lafayete Andrada", "valor": Decimal("750000.00")},
        {"autor": "Cleitinho", "valor": Decimal("399046.98")},
        {"autor": "Cleitinho", "valor": Decimal("399046.98")},
    ]

    execution = execute_collection_aggregate(
        registros,
        agrupar_por="autor",
        metrica="soma_valor",
        ordenar_por="metrica",
        ordem="desc",
        limite=1,
        group_key_getters={"autor": lambda row: row.get("autor")},
        metric_getters={"soma_valor": lambda row: row.get("valor") or Decimal("0")},
        serialize_metric=lambda value: (
            float(value) if isinstance(value, Decimal) else value
        ),
    )
    response = build_aggregate_response(
        response_type=AgregarTransferenciasFinanceirasResponse,
        metadata=AgregarTransferenciasFinanceirasMetadata(
            agrupar_por="autor",
            metrica="soma_valor",
            ordenar_por="metrica",
            ordem="desc",
            limite=1,
        ),
        execution=AggregateExecutionResult(
            total_grupos=execution.total_grupos,
            rows=execution.rows,
        ),
        project_group=lambda group_value, metric_value, agrupar_por, metrica: {
            agrupar_por: group_value,
            metrica: metric_value,
        },
        agrupar_por="autor",
        metrica="soma_valor",
    )

    assert response["total_grupos"] == 2
    assert response["resultados"] == [{"autor": "Cleitinho", "soma_valor": 798093.96}]
    assert response["mensagem"] == "Mostrando 1 de 2 grupos encontrados."
