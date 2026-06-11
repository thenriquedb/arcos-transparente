from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import agents.tools.sql_tools.estoques as estoques_tools
from agents.tools import registry as tools_registry
from database import session as session_manager
from database.models import Base, EstoqueMaterial, EstoqueMovimentacao


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


def _seed_estoques(session) -> None:
    alcool = EstoqueMaterial(
        arquivo_origem="estoque-prefeitura-2025.xml",
        sequencia_material=1,
        origem="prefeitura",
        exercicio=2025,
        material="ALCOOL 70",
        unidade_medida="frasco",
        periodo_inicio=date(2025, 1, 1),
        periodo_fim=date(2025, 12, 31),
        entrada_quantidade=Decimal("9.0000"),
        saldo_quantidade=Decimal("12.0000"),
        saldo_valor=Decimal("120.0000"),
        entrada_valor=Decimal("50.0000"),
        saida_quantidade=Decimal("4.0000"),
        saida_valor=Decimal("30.0000"),
    )
    luva = EstoqueMaterial(
        arquivo_origem="estoque-prefeitura-2025.xml",
        sequencia_material=2,
        origem="prefeitura",
        exercicio=2025,
        material="LUVA DESCARTAVEL",
        unidade_medida="caixa",
        periodo_inicio=date(2025, 1, 1),
        periodo_fim=date(2025, 12, 31),
        entrada_quantidade=Decimal("20.0000"),
        saldo_quantidade=Decimal("12.0000"),
        saldo_valor=Decimal("220.0000"),
        entrada_valor=Decimal("300.0000"),
        saida_quantidade=Decimal("8.0000"),
        saida_valor=Decimal("80.0000"),
    )
    session.add_all([alcool, luva])
    session.flush()
    session.add_all(
        [
            EstoqueMovimentacao(
                material_id=luva.id,
                sequencia_movimentacao=1,
                data_movimento=date(2025, 1, 10),
                tipo_movimento="Nota Fiscal de Compra",
                unidade_gestora="PREFEITURA MUNICIPAL",
                almoxarifado="ALMOXARIFADO SAUDE",
                localizacao="Geral",
                classificacao="Material Hospitalar",
                quantidade=Decimal("10.0000"),
                valor_unitario=Decimal("4.00000000"),
                valor_total=Decimal("40.0000"),
                custo_medio=Decimal("4.00000000"),
            ),
            EstoqueMovimentacao(
                material_id=luva.id,
                sequencia_movimentacao=2,
                data_movimento=date(2025, 1, 15),
                tipo_movimento="Requisicao",
                unidade_gestora="PREFEITURA MUNICIPAL",
                almoxarifado="ALMOXARIFADO SAUDE",
                localizacao="Geral",
                classificacao="Material Hospitalar",
                quantidade=Decimal("2.0000"),
                valor_unitario=Decimal("4.00000000"),
                valor_total=Decimal("-8.0000"),
                custo_medio=Decimal("4.00000000"),
            ),
            EstoqueMovimentacao(
                material_id=alcool.id,
                sequencia_movimentacao=1,
                data_movimento=date(2025, 5, 10),
                tipo_movimento="Requisicao",
                unidade_gestora="PREFEITURA MUNICIPAL",
                almoxarifado="ALMOXARIFADO CENTRAL",
                localizacao="Geral",
                classificacao="Material Hospitalar",
                quantidade=Decimal("4.0000"),
                valor_unitario=Decimal("10.00000000"),
                valor_total=Decimal("-40.0000"),
                custo_medio=Decimal("10.00000000"),
            ),
            EstoqueMovimentacao(
                material_id=luva.id,
                sequencia_movimentacao=3,
                data_movimento=date(2025, 5, 12),
                tipo_movimento="Requisicao",
                unidade_gestora="PREFEITURA MUNICIPAL",
                almoxarifado="ALMOXARIFADO SAUDE",
                localizacao="Geral",
                classificacao="Material Hospitalar",
                quantidade=Decimal("6.0000"),
                valor_unitario=Decimal("4.00000000"),
                valor_total=Decimal("-24.0000"),
                custo_medio=Decimal("4.00000000"),
            ),
        ]
    )
    session.commit()


def test_consultar_estoques_lista_por_material(monkeypatch) -> None:
    session = _build_session()
    _seed_estoques(session)
    _patch_session(monkeypatch, session)

    resultado = estoques_tools.consultar_estoques(
        filtros={"material": "alcool", "ano": 2025},
        campos=["material", "saldo_quantidade", "saldo_valor"],
    )

    assert resultado["total"] == 1
    assert resultado["resultados"] == [
        {
            "material": "ALCOOL 70",
            "saldo_quantidade": 12.0,
            "saldo_valor": 120.0,
        }
    ]

    session.close()


def test_agregar_estoques_por_material(monkeypatch) -> None:
    session = _build_session()
    _seed_estoques(session)
    _patch_session(monkeypatch, session)

    resultado = estoques_tools.agregar_estoques(
        filtros={"ano": 2025},
        agrupar_por="material",
        metrica="soma_saldo_valor",
    )

    assert resultado["total_grupos"] == 2
    assert resultado["resultados"][0] == {
        "material": "LUVA DESCARTAVEL",
        "soma_saldo_valor": 220.0,
    }

    session.close()


def test_agregar_estoques_agrega_saidas_por_material_em_periodo(monkeypatch) -> None:
    session = _build_session()
    _seed_estoques(session)
    _patch_session(monkeypatch, session)

    resultado = estoques_tools.agregar_estoques(
        filtros={
            "data_movimento_inicio": "2025-05-01",
            "data_movimento_fim": "2025-05-31",
        },
        agrupar_por="material",
        metrica="soma_saida_quantidade",
    )

    assert resultado["total_grupos"] == 2
    assert resultado["resultados"] == [
        {
            "material": "LUVA DESCARTAVEL",
            "soma_saida_quantidade": 6.0,
            "soma_saida_valor": 24.0,
        },
        {
            "material": "ALCOOL 70",
            "soma_saida_quantidade": 4.0,
            "soma_saida_valor": 40.0,
        },
    ]

    session.close()


def test_agregar_estoques_agrega_saidas_por_valor_sem_perder_quantidade(
    monkeypatch,
) -> None:
    session = _build_session()
    _seed_estoques(session)
    _patch_session(monkeypatch, session)

    resultado = estoques_tools.agregar_estoques(
        filtros={
            "data_movimento_inicio": "2025-05-01",
            "data_movimento_fim": "2025-05-31",
        },
        agrupar_por="material",
        metrica="soma_saida_valor",
    )

    assert resultado["total_grupos"] == 2
    assert resultado["resultados"] == [
        {
            "material": "ALCOOL 70",
            "soma_saida_valor": 40.0,
            "soma_saida_quantidade": 4.0,
        },
        {
            "material": "LUVA DESCARTAVEL",
            "soma_saida_valor": 24.0,
            "soma_saida_quantidade": 6.0,
        },
    ]

    session.close()


def test_agregar_estoques_aceita_aliases_naturais_de_parametros(monkeypatch) -> None:
    session = _build_session()
    _seed_estoques(session)
    _patch_session(monkeypatch, session)

    resultado = estoques_tools.agregar_estoques(
        filtros={"ano": 2025},
        agrupar_por="descricao do material",
        metrica="soma_quantidade",
    )

    assert resultado["total_grupos"] == 2
    assert {item["material"] for item in resultado["resultados"]} == {
        "ALCOOL 70",
        "LUVA DESCARTAVEL",
    }
    assert all("soma_saldo_quantidade" in item for item in resultado["resultados"])

    session.close()


@pytest.mark.parametrize("agrupar_por", ["nome", "tipo"])
def test_agregar_estoques_aceita_aliases_de_nome_e_tipo_do_material(
    monkeypatch,
    agrupar_por: str,
) -> None:
    session = _build_session()
    _seed_estoques(session)
    _patch_session(monkeypatch, session)

    resultado = estoques_tools.agregar_estoques(
        filtros={"ano": 2025},
        agrupar_por=agrupar_por,
        metrica="soma_quantidade",
    )

    assert resultado["total_grupos"] == 2
    assert {item["material"] for item in resultado["resultados"]} == {
        "ALCOOL 70",
        "LUVA DESCARTAVEL",
    }
    assert all(item["soma_saldo_quantidade"] == 12.0 for item in resultado["resultados"])

    session.close()


def test_agregar_estoques_resolve_alias_de_quantidade_em_contexto_de_movimentacao(
    monkeypatch,
) -> None:
    session = _build_session()
    _seed_estoques(session)
    _patch_session(monkeypatch, session)

    resultado = estoques_tools.agregar_estoques(
        filtros={
            "data_movimento_inicio": "2025-05-01",
            "data_movimento_fim": "2025-05-31",
        },
        agrupar_por="descricao do material",
        metrica="soma_quantidade",
    )

    assert resultado["resultados"] == [
        {
            "material": "LUVA DESCARTAVEL",
            "soma_movimentacao_quantidade": 6.0,
            "soma_movimentacao_valor": 24.0,
        },
        {
            "material": "ALCOOL 70",
            "soma_movimentacao_quantidade": 4.0,
            "soma_movimentacao_valor": 40.0,
        },
    ]

    session.close()


def test_consultar_movimentacoes_de_estoque_filtra_por_almoxarifado(
    monkeypatch,
) -> None:
    session = _build_session()
    _seed_estoques(session)
    _patch_session(monkeypatch, session)

    resultado = estoques_tools.consultar_movimentacoes_de_estoque(
        filtros={"almoxarifado": "saude", "tipo_movimento": "requisicao"},
        campos=["material", "tipo_movimento", "almoxarifado", "valor_total"],
    )

    assert resultado["total"] == 2
    assert resultado["resultados"] == [
        {
            "material": "LUVA DESCARTAVEL",
            "tipo_movimento": "Requisicao",
            "almoxarifado": "ALMOXARIFADO SAUDE",
            "valor_total": -24.0,
        },
        {
            "material": "LUVA DESCARTAVEL",
            "tipo_movimento": "Requisicao",
            "almoxarifado": "ALMOXARIFADO SAUDE",
            "valor_total": -8.0,
        },
    ]

    session.close()


def test_registry_expoe_tools_publicas_de_estoques() -> None:
    tool_names = {
        getattr(tool_obj, "name", "") for tool_obj in tools_registry.get_public_tools(tags=["domain:estoques"])
    }

    assert "consultar_estoques" in tool_names
    assert "agregar_estoques" in tool_names
    assert "consultar_movimentacoes_de_estoque" in tool_names


def test_agregar_estoques_saldo_total_anual(monkeypatch) -> None:
    session = _build_session()
    _seed_estoques(session)
    _patch_session(monkeypatch, session)

    resultado = estoques_tools.agregar_estoques(
        filtros={"ano": 2025},
        metrica="soma_saldo_valor",
    )

    assert resultado["valor_total"] == 340.0

    session.close()


def test_consultar_movimentacoes_de_estoque_lista_por_almoxarifado(monkeypatch) -> None:
    session = _build_session()
    _seed_estoques(session)
    _patch_session(monkeypatch, session)

    resultado = estoques_tools.consultar_movimentacoes_de_estoque(
        filtros={"almoxarifado": "saude", "ano": 2025},
    )

    assert resultado["total"] == 3

    session.close()
