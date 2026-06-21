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


def test_agregar_frota_agrupa_por_placa_com_total_de_despesas(monkeypatch) -> None:
    session = _build_session()
    caminhao = FrotaVeiculo(
        codigo_veiculo="1",
        placa_veiculo="ABC-1234",
        descricao_material="CAMINHAO CACAMBA",
        unidade_gestora="PREFEITURA MUNICIPAL",
        tipo_veiculo="CAMINHAO",
        marca="IVECO",
        modelo="TECTOR",
    )
    passeio = FrotaVeiculo(
        codigo_veiculo="2",
        placa_veiculo="DEF-5678",
        descricao_material="VEICULO PASSEIO",
        unidade_gestora="PREFEITURA MUNICIPAL",
        tipo_veiculo="AUTOMOVEL",
        marca="FIAT",
        modelo="ARGO",
    )
    session.add_all([caminhao, passeio])
    session.flush()
    session.add_all(
        [
            FrotaDespesa(
                veiculo_id=caminhao.id,
                descricao_evento="Abastecimento",
                valor_lancamento=Decimal("500.00"),
                total_despesa=Decimal("500.00"),
            ),
            FrotaDespesa(
                veiculo_id=caminhao.id,
                descricao_evento="Manutencao",
                valor_lancamento=Decimal("700.00"),
                total_despesa=Decimal("700.00"),
            ),
            FrotaDespesa(
                veiculo_id=passeio.id,
                descricao_evento="Abastecimento",
                valor_lancamento=Decimal("300.00"),
                total_despesa=Decimal("300.00"),
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = frotas_tools.agregar_frota(
        agrupar_por="placa",
        metrica="soma_total_despesas",
    )

    assert resultado["total_grupos"] == 2
    assert resultado["resultados"] == [
        {
            "placa_veiculo": "ABC-1234",
            "codigo_veiculo": "1",
            "descricao_material": "CAMINHAO CACAMBA",
            "unidade_responsavel": "PREFEITURA MUNICIPAL",
            "tipo_veiculo": "CAMINHAO",
            "marca": "IVECO",
            "modelo": "TECTOR",
            "soma_total_despesas": 1200.0,
        },
        {
            "placa_veiculo": "DEF-5678",
            "codigo_veiculo": "2",
            "descricao_material": "VEICULO PASSEIO",
            "unidade_responsavel": "PREFEITURA MUNICIPAL",
            "tipo_veiculo": "AUTOMOVEL",
            "marca": "FIAT",
            "modelo": "ARGO",
            "soma_total_despesas": 300.0,
        },
    ]

    session.close()


def test_agregar_despesas_frota_prioriza_tipos_de_gasto(monkeypatch) -> None:
    session = _build_session()
    caminhao = FrotaVeiculo(
        codigo_veiculo="1",
        placa_veiculo="ABC-1234",
        descricao_material="CAMINHAO CACAMBA",
        unidade_gestora="PREFEITURA MUNICIPAL",
        tipo_veiculo="CAMINHAO",
    )
    ambulancia = FrotaVeiculo(
        codigo_veiculo="2",
        placa_veiculo="DEF-5678",
        descricao_material="AMBULANCIA",
        unidade_gestora="PREFEITURA MUNICIPAL",
        tipo_veiculo="AMBULANCIA",
    )
    session.add_all([caminhao, ambulancia])
    session.flush()
    session.add_all(
        [
            FrotaDespesa(
                veiculo_id=caminhao.id,
                descricao_evento="Troca de oleo",
                tipo_despesa="MANUTENCAO",
                valor_lancamento=Decimal("500.00"),
                total_despesa=Decimal("500.00"),
            ),
            FrotaDespesa(
                veiculo_id=ambulancia.id,
                descricao_evento="Revisao",
                tipo_despesa="MANUTENCAO",
                valor_lancamento=Decimal("700.00"),
                total_despesa=Decimal("700.00"),
            ),
            FrotaDespesa(
                veiculo_id=ambulancia.id,
                descricao_evento="Abastecimento",
                tipo_despesa="COMBUSTIVEL",
                valor_lancamento=Decimal("300.00"),
                total_despesa=Decimal("300.00"),
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = frotas_tools.agregar_despesas_frota()

    assert resultado["total_grupos"] == 2
    assert resultado["metadata"]["agrupar_por"] == "tipo_despesa"
    assert resultado["resultados"] == [
        {
            "tipo_despesa": "MANUTENCAO",
            "soma_total_despesa": 1200.0,
        },
        {
            "tipo_despesa": "COMBUSTIVEL",
            "soma_total_despesa": 300.0,
        },
    ]

    session.close()
