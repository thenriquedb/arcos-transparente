from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import agents.tools.sql_tools.diarias as diarias_tools
from agents.tools import registry as tools_registry
from agents.router import route_user_query, select_public_tools_for_query
from database import session as session_manager
from database.models import Base, DespesaDocumento


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


def test_consultar_diarias_lista_por_beneficiario(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            DespesaDocumento(
                tipo_origem="diaria",
                arquivo_origem="diarias-camara-2025.csv",
                sequencia_origem=1,
                origem="camara",
                exercicio=2025,
                unidade_gestora="CAMARA MUNICIPAL",
                numero_documento="DIARIA-2025-00001",
                data_documento=date(2025, 12, 31),
                periodo_referencia_inicio=date(2025, 1, 1),
                periodo_referencia_fim=date(2025, 12, 31),
                categoria_documento="DIARIAS",
                credor="EDISON DOS SANTOS",
                cpf_cnpj="000",
                valor_empenhado=Decimal("22800.47"),
                valor_liquidado=Decimal("22800.47"),
                valor_pago=Decimal("22800.47"),
            ),
            DespesaDocumento(
                tipo_origem="diaria",
                arquivo_origem="diarias-camara-2026.csv",
                sequencia_origem=1,
                origem="camara",
                exercicio=2026,
                unidade_gestora="CAMARA MUNICIPAL",
                numero_documento="DIARIA-2026-00001",
                data_documento=date(2026, 6, 30),
                periodo_referencia_inicio=date(2026, 1, 1),
                periodo_referencia_fim=date(2026, 6, 30),
                categoria_documento="DIARIAS",
                credor="RENATO GONCALVES MARCIANO",
                cpf_cnpj="111",
                valor_empenhado=Decimal("4500.00"),
                valor_liquidado=Decimal("4500.00"),
                valor_pago=Decimal("4500.00"),
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = diarias_tools.consultar_diarias(
        filtros={"ano": 2025, "beneficiario": "edison"},
        campos=["beneficiario", "valor_pago", "periodo_fim"],
    )

    assert resultado["total"] == 1
    assert resultado["resultados"] == [
        {
            "beneficiario": "EDISON DOS SANTOS",
            "valor_pago": 22800.47,
            "periodo_fim": "2025-12-31",
        }
    ]

    session.close()


def test_agregar_diarias_por_beneficiario(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            DespesaDocumento(
                tipo_origem="diaria",
                arquivo_origem="diarias-camara-2025.csv",
                sequencia_origem=1,
                origem="camara",
                exercicio=2025,
                unidade_gestora="CAMARA MUNICIPAL",
                numero_documento="DIARIA-2025-00001",
                data_documento=date(2025, 12, 31),
                periodo_referencia_inicio=date(2025, 1, 1),
                periodo_referencia_fim=date(2025, 12, 31),
                categoria_documento="DIARIAS",
                credor="EDISON DOS SANTOS",
                valor_pago=Decimal("22800.47"),
            ),
            DespesaDocumento(
                tipo_origem="diaria",
                arquivo_origem="diarias-camara-2025.csv",
                sequencia_origem=2,
                origem="camara",
                exercicio=2025,
                unidade_gestora="CAMARA MUNICIPAL",
                numero_documento="DIARIA-2025-00002",
                data_documento=date(2025, 12, 31),
                periodo_referencia_inicio=date(2025, 1, 1),
                periodo_referencia_fim=date(2025, 12, 31),
                categoria_documento="DIARIAS",
                credor="ALEX GRACIERES RIBEIRO",
                valor_pago=Decimal("4128.00"),
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = diarias_tools.agregar_diarias(
        filtros={"ano": 2025},
        agrupar_por="beneficiario",
        metrica="soma_valor_pago",
    )

    assert resultado["total_grupos"] == 2
    assert resultado["resultados"][0] == {
        "beneficiario": "EDISON DOS SANTOS",
        "soma_valor_pago": 22800.47,
    }

    session.close()


def test_registry_expoe_tools_publicas_de_diarias() -> None:
    tool_names = {
        getattr(tool_obj, "name", "")
        for tool_obj in tools_registry.get_public_tools(tags=["domain:diarias"])
    }

    assert "consultar_diarias" in tool_names
    assert "agregar_diarias" in tool_names


def test_query_de_diarias_rota_para_tool_publica_dedicada(monkeypatch) -> None:
    session = _build_session()
    session.add(
        DespesaDocumento(
            tipo_origem="diaria",
            arquivo_origem="diarias-camara-2025.csv",
            sequencia_origem=1,
            origem="camara",
            exercicio=2025,
            unidade_gestora="CAMARA MUNICIPAL",
            numero_documento="DIARIA-2025-00001",
            data_documento=date(2025, 12, 31),
            periodo_referencia_inicio=date(2025, 1, 1),
            periodo_referencia_fim=date(2025, 12, 31),
            categoria_documento="DIARIAS",
            credor="EDISON DOS SANTOS",
            valor_pago=Decimal("22800.47"),
        )
    )
    session.commit()
    _patch_session(monkeypatch, session)

    route = route_user_query("Quanto foi pago em diarias em 2025?")
    tool = select_public_tools_for_query("Quanto foi pago em diarias em 2025?")[0]
    resultado = tool.invoke(route.tool_kwargs)

    assert route.tool_name == "agregar_diarias"
    assert getattr(tool, "name", "") == "agregar_diarias"
    assert resultado["valor_total"] == 22800.47

    session.close()
