from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import agents.tools.sql_tools.passagens as passagens_tools
from agents.tools import registry as tools_registry
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


def test_consultar_passagens_lista_por_beneficiario(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            DespesaDocumento(
                tipo_origem="passagem",
                arquivo_origem="passagens-2026.csv",
                sequencia_origem=1,
                origem="camara",
                exercicio=2026,
                unidade_gestora="CAMARA MUNICIPAL",
                numero_documento="PASSAGEM-2026-00001",
                data_documento=date(2026, 6, 30),
                periodo_referencia_inicio=date(2026, 1, 1),
                periodo_referencia_fim=date(2026, 6, 30),
                categoria_documento="PASSAGENS E DESPESAS COM LOCOMOCAO",
                credor="EDISON DOS SANTOS",
                cpf_cnpj="000",
                valor_empenhado=Decimal("2000.00"),
                valor_liquidado=Decimal("1500.09"),
                valor_pago=Decimal("1500.09"),
            ),
            DespesaDocumento(
                tipo_origem="passagem",
                arquivo_origem="passagens-2026.csv",
                sequencia_origem=2,
                origem="camara",
                exercicio=2026,
                unidade_gestora="CAMARA MUNICIPAL",
                numero_documento="PASSAGEM-2026-00002",
                data_documento=date(2026, 6, 30),
                periodo_referencia_inicio=date(2026, 1, 1),
                periodo_referencia_fim=date(2026, 6, 30),
                categoria_documento="PASSAGENS E DESPESAS COM LOCOMOCAO",
                credor="RENATO GONCALVES MARCIANO",
                cpf_cnpj="111",
                valor_empenhado=Decimal("113.50"),
                valor_liquidado=Decimal("113.50"),
                valor_pago=Decimal("113.50"),
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = passagens_tools.consultar_passagens(
        filtros={"ano": 2026, "beneficiario": "edison"},
        campos=["beneficiario", "categoria", "valor_pago", "periodo_fim"],
    )

    assert resultado["total"] == 1
    assert resultado["resultados"] == [
        {
            "beneficiario": "EDISON DOS SANTOS",
            "categoria": "PASSAGENS E DESPESAS COM LOCOMOCAO",
            "valor_pago": 1500.09,
            "periodo_fim": "2026-06-30",
        }
    ]

    session.close()


def test_consultar_passagens_preserva_mensagem_de_paginacao(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            DespesaDocumento(
                tipo_origem="passagem",
                arquivo_origem="passagens-2026.csv",
                sequencia_origem=1,
                origem="camara",
                exercicio=2026,
                unidade_gestora="CAMARA MUNICIPAL",
                numero_documento="PASSAGEM-2026-00001",
                data_documento=date(2026, 6, 30),
                periodo_referencia_inicio=date(2026, 1, 1),
                periodo_referencia_fim=date(2026, 6, 30),
                categoria_documento="PASSAGENS E DESPESAS COM LOCOMOCAO",
                credor="EDISON DOS SANTOS",
                valor_pago=Decimal("1500.09"),
            ),
            DespesaDocumento(
                tipo_origem="passagem",
                arquivo_origem="passagens-2026.csv",
                sequencia_origem=2,
                origem="camara",
                exercicio=2026,
                unidade_gestora="CAMARA MUNICIPAL",
                numero_documento="PASSAGEM-2026-00002",
                data_documento=date(2026, 6, 29),
                periodo_referencia_inicio=date(2026, 1, 1),
                periodo_referencia_fim=date(2026, 6, 29),
                categoria_documento="PASSAGENS E DESPESAS COM LOCOMOCAO",
                credor="RENATO GONCALVES MARCIANO",
                valor_pago=Decimal("113.50"),
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = passagens_tools.consultar_passagens(
        filtros={"ano": 2026},
        limite=1,
        campos=["beneficiario", "valor_pago"],
    )

    assert resultado["total"] == 2
    assert resultado["mensagem"] == "Mostrando 1 de 2 passagens encontradas."

    session.close()


def test_agregar_passagens_por_beneficiario(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            DespesaDocumento(
                tipo_origem="passagem",
                arquivo_origem="passagens-2026.csv",
                sequencia_origem=1,
                origem="camara",
                exercicio=2026,
                unidade_gestora="CAMARA MUNICIPAL",
                numero_documento="PASSAGEM-2026-00001",
                data_documento=date(2026, 6, 30),
                periodo_referencia_inicio=date(2026, 1, 1),
                periodo_referencia_fim=date(2026, 6, 30),
                categoria_documento="PASSAGENS E DESPESAS COM LOCOMOCAO",
                credor="EDISON DOS SANTOS",
                valor_pago=Decimal("1500.09"),
            ),
            DespesaDocumento(
                tipo_origem="passagem",
                arquivo_origem="passagens-2026.csv",
                sequencia_origem=2,
                origem="camara",
                exercicio=2026,
                unidade_gestora="CAMARA MUNICIPAL",
                numero_documento="PASSAGEM-2026-00002",
                data_documento=date(2026, 6, 30),
                periodo_referencia_inicio=date(2026, 1, 1),
                periodo_referencia_fim=date(2026, 6, 30),
                categoria_documento="PASSAGENS E DESPESAS COM LOCOMOCAO",
                credor="RENATO GONCALVES MARCIANO",
                valor_pago=Decimal("113.50"),
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = passagens_tools.agregar_passagens(
        filtros={"ano": 2026},
        agrupar_por="beneficiario",
        metrica="soma_valor_pago",
    )

    assert resultado["total_grupos"] == 2
    assert resultado["resultados"][0] == {
        "beneficiario": "EDISON DOS SANTOS",
        "soma_valor_pago": 1500.09,
    }

    session.close()


def test_agregar_passagens_por_mes(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            DespesaDocumento(
                tipo_origem="passagem",
                arquivo_origem="passagens-prefeitura-2025.csv",
                sequencia_origem=1,
                origem="prefeitura",
                exercicio=2025,
                unidade_gestora="PREFEITURA MUNICIPAL",
                numero_documento="PASSAGEM-2025-00001",
                data_documento=date(2025, 1, 31),
                periodo_referencia_inicio=date(2025, 1, 1),
                periodo_referencia_fim=date(2025, 1, 31),
                categoria_documento="PASSAGENS E DESPESAS COM LOCOMOCAO",
                credor="ALFA",
                valor_pago=Decimal("75.00"),
            ),
            DespesaDocumento(
                tipo_origem="passagem",
                arquivo_origem="passagens-prefeitura-2025.csv",
                sequencia_origem=2,
                origem="prefeitura",
                exercicio=2025,
                unidade_gestora="PREFEITURA MUNICIPAL",
                numero_documento="PASSAGEM-2025-00002",
                data_documento=date(2025, 2, 28),
                periodo_referencia_inicio=date(2025, 2, 1),
                periodo_referencia_fim=date(2025, 2, 28),
                categoria_documento="PASSAGENS E DESPESAS COM LOCOMOCAO",
                credor="BETA",
                valor_pago=Decimal("125.00"),
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = passagens_tools.agregar_passagens(
        filtros={"ano": 2025, "origem": "prefeitura"},
        agrupar_por="mes",
        metrica="soma_valor_pago",
        ordenar_por="mes",
        ordem="asc",
    )

    assert resultado["total_grupos"] == 2
    assert resultado["resultados"] == [
        {"mes": 1, "soma_valor_pago": 75.0},
        {"mes": 2, "soma_valor_pago": 125.0},
    ]

    session.close()


def test_registry_expoe_tools_publicas_de_passagens() -> None:
    tool_names = {
        getattr(tool_obj, "name", "") for tool_obj in tools_registry.get_public_tools(tags=["domain:passagens"])
    }

    assert "consultar_passagens" in tool_names
    assert "agregar_passagens" in tool_names


def test_agregar_passagens_total_anual(monkeypatch) -> None:
    session = _build_session()
    session.add(
        DespesaDocumento(
            tipo_origem="passagem",
            arquivo_origem="passagens-2026.csv",
            sequencia_origem=1,
            origem="camara",
            exercicio=2026,
            unidade_gestora="CAMARA MUNICIPAL",
            numero_documento="PASSAGEM-2026-00001",
            data_documento=date(2026, 6, 30),
            periodo_referencia_inicio=date(2026, 1, 1),
            periodo_referencia_fim=date(2026, 6, 30),
            categoria_documento="PASSAGENS E DESPESAS COM LOCOMOCAO",
            credor="EDISON DOS SANTOS",
            valor_pago=Decimal("1500.09"),
        )
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = passagens_tools.agregar_passagens(
        filtros={"ano": 2026},
        metrica="soma_valor_pago",
    )

    assert resultado["valor_total"] == 1500.09

    session.close()
