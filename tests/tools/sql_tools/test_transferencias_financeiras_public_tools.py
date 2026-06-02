from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import agents.tools.sql_tools.transferencias_financeiras as transferencias_tools
from agents.router import route_user_query, select_public_tools_for_query
from agents.tools import registry as tools_registry
from database import session as session_manager
from database.models import Base, EmendaParlamentar, TransferenciaFinanceiraMovimento


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


def _patch_session(monkeypatch, session) -> None:
    @contextmanager
    def fake_get_session():
        yield session

    monkeypatch.setattr(session_manager, "get_session", fake_get_session)


def test_consultar_transferencias_financeiras_lista_movimentos(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            TransferenciaFinanceiraMovimento(
                arquivo_origem="recebimentos-2026.xml",
                sequencia_origem=1,
                exercicio=2026,
                identificacao="27",
                unidade_gestora_concessora="PREFEITURA MUNICIPAL",
                unidade_gestora_recebedora="CAMARA MUNICIPAL",
                finalidade="Transferência para Câmara",
                fonte_recurso="Recursos não Vinculados de Impostos",
                detalhamento_fonte="Não se aplica",
                programacao_inicial=Decimal("6630000.00"),
                data_movimento=date(2026, 1, 1),
                tipo_movimento="Programação Inicial",
                valor_movimento=Decimal("6630000.00"),
            ),
            TransferenciaFinanceiraMovimento(
                arquivo_origem="recebimentos-2026.xml",
                sequencia_origem=2,
                exercicio=2026,
                identificacao="27",
                unidade_gestora_concessora="PREFEITURA MUNICIPAL",
                unidade_gestora_recebedora="CAMARA MUNICIPAL",
                finalidade="Transferência para Câmara",
                fonte_recurso="Recursos não Vinculados de Impostos",
                detalhamento_fonte="Não se aplica",
                programacao_inicial=Decimal("552500.00"),
                data_movimento=date(2026, 1, 16),
                tipo_movimento="Recebimento",
                valor_movimento=Decimal("552500.00"),
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = transferencias_tools.consultar_transferencias_financeiras(
        filtros={
            "tipo_registro": "movimentacao",
            "ano": 2026,
            "unidade_recebedora": "camara",
            "tipo_movimento": "recebimento",
        },
        campos=["tipo_registro", "ano", "unidade_recebedora", "tipo_movimento", "valor"],
    )

    assert resultado["total"] == 1
    assert resultado["resultados"] == [
        {
            "tipo_registro": "movimentacao",
            "ano": 2026,
            "unidade_recebedora": "CAMARA MUNICIPAL",
            "tipo_movimento": "Recebimento",
            "valor": 552500.0,
        }
    ]

    session.close()


def test_agregar_transferencias_financeiras_por_autor_de_emenda(
    monkeypatch,
) -> None:
    session = _build_session()
    session.add_all(
        [
            EmendaParlamentar(
                arquivo_origem="emendas-parlamentares-2026.csv",
                sequencia_origem=1,
                exercicio_consulta=2026,
                ano=2026,
                ano_numero="2026/39600006",
                autor="Dr Frederico",
                objeto="Incremento da média e alta complexidade (MAC)",
                tipo_emenda="Emendas Individuais Impositivas por Transferência Especial",
                funcao="Saúde",
                valor=Decimal("100000.00"),
            ),
            EmendaParlamentar(
                arquivo_origem="emendas-parlamentares-2026.csv",
                sequencia_origem=2,
                exercicio_consulta=2026,
                ano=2026,
                ano_numero="2026/40290001",
                autor="Lafayete Andrada",
                objeto="Incremento da média e alta complexidade (MAC)",
                tipo_emenda="Emendas Individuais Impositivas por Transferência Especial",
                funcao="Saúde",
                valor=Decimal("750000.00"),
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = transferencias_tools.agregar_transferencias_financeiras(
        filtros={"tipo_registro": "emenda", "ano": 2026},
        agrupar_por="autor",
        metrica="soma_valor",
    )

    assert resultado["total_grupos"] == 2
    assert resultado["resultados"][0] == {
        "autor": "Lafayete Andrada",
        "soma_valor": 750000.0,
    }

    session.close()


def test_registry_expoe_tools_publicas_de_transferencias_financeiras() -> None:
    tool_names = {
        getattr(tool_obj, "name", "")
        for tool_obj in tools_registry.get_public_tools(
            tags=["domain:transferencias_financeiras"]
        )
    }

    assert "consultar_transferencias_financeiras" in tool_names
    assert "agregar_transferencias_financeiras" in tool_names


def test_query_de_transferencias_financeiras_rota_para_tool_publica_dedicada(
    monkeypatch,
) -> None:
    session = _build_session()
    session.add(
        TransferenciaFinanceiraMovimento(
            arquivo_origem="recebimentos-2026.xml",
            sequencia_origem=1,
            exercicio=2026,
            identificacao="27",
            unidade_gestora_concessora="PREFEITURA MUNICIPAL",
            unidade_gestora_recebedora="CAMARA MUNICIPAL",
            finalidade="Transferência para Câmara",
            fonte_recurso="Recursos não Vinculados de Impostos",
            detalhamento_fonte="Não se aplica",
            programacao_inicial=Decimal("552500.00"),
            data_movimento=date(2026, 1, 16),
            tipo_movimento="Recebimento",
            valor_movimento=Decimal("552500.00"),
        )
    )
    session.commit()
    _patch_session(monkeypatch, session)

    route = route_user_query("Quanto foi transferido para a camara em 2026?")
    tool = select_public_tools_for_query("Quanto foi transferido para a camara em 2026?")[0]
    resultado = tool.invoke(route.tool_kwargs)

    assert route.tool_name == "agregar_transferencias_financeiras"
    assert getattr(tool, "name", "") == "agregar_transferencias_financeiras"
    assert resultado["valor_total"] == 552500.0

    session.close()
