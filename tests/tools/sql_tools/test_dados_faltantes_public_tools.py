from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import agents.tools.sql_tools.despesas as despesas_tools
import agents.tools.sql_tools.patrimonios as patrimonios_tools
import agents.tools.sql_tools.quadro_pessoal as quadro_tools
from database import session as session_manager
from database.models import Base, DespesaDocumento, Patrimonio, QuadroPessoal


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


def test_consultar_e_agregar_despesas_filtram_diarias(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            DespesaDocumento(
                tipo_origem="empenho",
                arquivo_origem="empenhos-2025.xml",
                sequencia_origem=1,
                origem="camara",
                exercicio=2025,
                unidade_gestora="CÂMARA MUNICIPAL",
                numero_documento="000331",
                data_documento=date(2025, 9, 17),
                credor="EDISON DOS SANTOS",
                funcao="Legislativa",
                descricao_acao="Diárias e locomoção",
                valor_documento=Decimal("18.00"),
                valor_empenhado=Decimal("18.00"),
                valor_pago=Decimal("18.00"),
            ),
            DespesaDocumento(
                tipo_origem="documento_extra",
                arquivo_origem="documentos-extras-prefeitura-2025.xml",
                sequencia_origem=1,
                origem="prefeitura",
                exercicio=2025,
                unidade_gestora="PREFEITURA MUNICIPAL",
                numero_documento="000001",
                data_documento=date(2025, 1, 1),
                credor="CAMARA MUNICIPAL DE ARCOS",
                valor_documento=Decimal("541666.67"),
                valor_pago=Decimal("541666.67"),
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    consulta = despesas_tools.consultar_despesas(
        filtros={"descricao": "diaria", "ano": 2025},
        campos=["numero", "credor", "valor_pago"],
    )
    agregacao = despesas_tools.agregar_despesas(
        filtros={"descricao": "diaria", "ano": 2025},
        metrica="soma_valor_pago",
    )

    assert consulta["total"] == 1
    assert consulta["resultados"] == [
        {"numero": "000331", "credor": "EDISON DOS SANTOS", "valor_pago": 18.0}
    ]
    assert agregacao["valor_total"] == 18.0

    session.close()


def test_consultar_e_agregar_patrimonios_por_localizacao(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            Patrimonio(
                unidade_gestora="PREFEITURA MUNICIPAL",
                placa="27982",
                descricao_item="REFRIGERADOR",
                localizacao="L005 - SEC. MUNIC. DE EDUCAÇÃO",
                status="Normal",
                tipo_ingresso="Compra",
                data_aquisicao=date(2025, 3, 7),
                valor_atualizado=Decimal("1995.00"),
            ),
            Patrimonio(
                unidade_gestora="PREFEITURA MUNICIPAL",
                placa="27983",
                descricao_item="CADEIRA",
                localizacao="L004 - SEC. MUNIC. DE FAZENDA",
                status="Normal",
                tipo_ingresso="Compra",
                data_aquisicao=date(2025, 4, 1),
                valor_atualizado=Decimal("100.00"),
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    consulta = patrimonios_tools.consultar_patrimonios(
        filtros={"localizacao": "educacao"},
        campos=["placa", "descricao", "valor_atualizado"],
    )
    agregacao = patrimonios_tools.agregar_patrimonios(
        filtros={"localizacao": "educacao"},
        metrica="soma_valor_atualizado",
    )

    assert consulta["total"] == 1
    assert consulta["resultados"] == [
        {"placa": "27982", "descricao": "REFRIGERADOR", "valor_atualizado": 1995.0}
    ]
    assert agregacao["valor_total"] == 1995.0

    session.close()


def test_agregar_quadro_pessoal_por_regime(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            QuadroPessoal(
                origem="prefeitura",
                competencia_referencia=date(2025, 1, 1),
                regime_contratacao="Comissionado",
                vagas_criadas=62,
                vagas_preenchidas=77,
            ),
            QuadroPessoal(
                origem="prefeitura",
                competencia_referencia=date(2025, 1, 1),
                regime_contratacao="Efetivo",
                vagas_criadas=465,
                vagas_preenchidas=843,
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = quadro_tools.agregar_quadro_pessoal(
        filtros={"origem": "prefeitura", "ano": 2025},
        agrupar_por="regime",
        metrica="soma_vagas_preenchidas",
    )

    assert resultado["total_grupos"] == 2
    assert resultado["resultados"] == [
        {"regime": "Efetivo", "soma_vagas_preenchidas": 843},
        {"regime": "Comissionado", "soma_vagas_preenchidas": 77},
    ]

    session.close()
