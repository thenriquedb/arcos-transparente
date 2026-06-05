from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

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
    execute_statement_lookup,
)
from database.models import Base, FolhaServidor


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
        execution=AggregateExecutionResult(valor_total=total_execution.valor_total),
    )

    assert total_response["valor_total"] == 87000.0

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
