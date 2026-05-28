from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import agents.tools.sql_tools.frotas as frotas_tools
from database import session as session_manager
from database.models import Base, FrotaDespesa, FrotaVeiculo


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


def test_consultar_frota_lista_veiculos_da_prefeitura(monkeypatch) -> None:
    session = _build_session()
    prefeitura = FrotaVeiculo(
        codigo_veiculo="1",
        placa_veiculo="ABC-1234",
        descricao_material="CAMINHAO CACAMBA",
        unidade_gestora="PREFEITURA MUNICIPAL",
        tipo_veiculo="CAMINHAO",
        marca="IVECO",
        modelo="TECTOR",
        data_aquisicao=datetime(2025, 1, 10),
        situacao_veiculo="Ativo",
        valor_atual=Decimal("250000.00"),
    )
    camara = FrotaVeiculo(
        codigo_veiculo="2",
        placa_veiculo="DEF-5678",
        descricao_material="VEICULO PASSEIO",
        unidade_gestora="CAMARA MUNICIPAL",
        tipo_veiculo="AUTOMOVEL",
        marca="FIAT",
        modelo="ARGO",
        data_aquisicao=datetime(2025, 2, 20),
        situacao_veiculo="Ativo",
        valor_atual=Decimal("90000.00"),
    )
    session.add_all([prefeitura, camara])
    session.flush()
    session.add(
        FrotaDespesa(
            veiculo_id=prefeitura.id,
            descricao_evento="Abastecimento",
            valor_lancamento=Decimal("500.00"),
            total_despesa=Decimal("500.00"),
        )
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = frotas_tools.consultar_frota(
        filtros={"unidade_responsavel": "prefeitura"},
        campos=[
            "placa_veiculo",
            "descricao_material",
            "unidade_responsavel",
            "tipo_veiculo",
            "total_despesas",
        ],
    )

    assert resultado["total"] == 1
    assert resultado["resultados"] == [
        {
            "placa_veiculo": "ABC-1234",
            "descricao_material": "CAMINHAO CACAMBA",
            "unidade_responsavel": "PREFEITURA MUNICIPAL",
            "tipo_veiculo": "CAMINHAO",
            "total_despesas": 500.0,
        }
    ]

    session.close()


def test_consultar_frota_filtra_por_placa(monkeypatch) -> None:
    session = _build_session()
    session.add(
        FrotaVeiculo(
            codigo_veiculo="1",
            placa_veiculo="ABC-1234",
            unidade_gestora="PREFEITURA MUNICIPAL",
            tipo_veiculo="CAMINHAO",
        )
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = frotas_tools.consultar_frota(
        filtros={"placa": "abc"},
        campos=["placa_veiculo", "unidade_responsavel"],
    )

    assert resultado["total"] == 1
    assert resultado["resultados"] == [
        {
            "placa_veiculo": "ABC-1234",
            "unidade_responsavel": "PREFEITURA MUNICIPAL",
        }
    ]

    session.close()
