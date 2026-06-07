from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import agents.tools.sql_tools.receitas as receitas_tools
from database import session as session_manager
from database.models import Base, ReceitaArrecadacao, ReceitaLancamento, ReceitaNatureza


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


def _natureza(*, identificacao: str, nome: str) -> ReceitaNatureza:
    return ReceitaNatureza(
        identificacao=identificacao,
        nome=nome,
        nivel=1,
        identificacao_superior=None,
    )


def _arrecadacao(
    *,
    natureza: ReceitaNatureza,
    mes: str,
    data_arrecadacao: date,
    unidade_gestora: str,
    fonte_recurso: str,
    valor_previsto_liquido: str,
    valor_arrecadado_liquido: str,
) -> ReceitaArrecadacao:
    return ReceitaArrecadacao(
        exercicio=2025,
        mes=mes,
        data_arrecadacao=data_arrecadacao,
        unidade_gestora=unidade_gestora,
        natureza=natureza,
        fonte_recurso=fonte_recurso,
        valor_previsto_bruto=Decimal(valor_previsto_liquido),
        valor_arrecadado_bruto=Decimal(valor_arrecadado_liquido),
        valor_previsto_deducoes=Decimal("0"),
        valor_realizado_deducoes=Decimal("0"),
        valor_previsto_liquido=Decimal(valor_previsto_liquido),
        valor_arrecadado_liquido=Decimal(valor_arrecadado_liquido),
    )


def _lancamento(
    *,
    mes: str,
    data_lancamento: date,
    tipo_receita: str,
    tributo: str,
    valor_lancado_exercicio: str,
    valor_lancado_divida_ativa: str = "0",
    valor_lancado_cobraca_judicial: str = "0",
) -> ReceitaLancamento:
    return ReceitaLancamento(
        exercicio=2025,
        mes=mes,
        data_lancamento=data_lancamento,
        tipo_receita=tipo_receita,
        tributo=tributo,
        valor_lancado_exercicio=Decimal(valor_lancado_exercicio),
        valor_lancado_divida_ativa=Decimal(valor_lancado_divida_ativa),
        valor_lancado_cobraca_judicial=Decimal(valor_lancado_cobraca_judicial),
    )


def test_consultar_receitas_filtra_arrecadacao_por_tema(monkeypatch) -> None:
    session = _build_session()
    natureza_fundeb = _natureza(
        identificacao="1.7.5.1",
        nome="Transferencias de Recursos do FUNDEB - Principal",
    )
    natureza_iptu = _natureza(
        identificacao="1.1.1.2",
        nome="Imposto Predial e Territorial Urbano - Principal",
    )
    session.add_all(
        [
            _arrecadacao(
                natureza=natureza_fundeb,
                mes="MARCO",
                data_arrecadacao=date(2025, 3, 20),
                unidade_gestora="PREFEITURA MUNICIPAL",
                fonte_recurso="FUNDEB",
                valor_previsto_liquido="50000.00",
                valor_arrecadado_liquido="48000.00",
            ),
            _arrecadacao(
                natureza=natureza_iptu,
                mes="ABRIL",
                data_arrecadacao=date(2025, 4, 10),
                unidade_gestora="PREFEITURA MUNICIPAL",
                fonte_recurso="Recursos proprios",
                valor_previsto_liquido="22000.00",
                valor_arrecadado_liquido="21500.00",
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = receitas_tools.consultar_receitas(
        filtros={"tema": "fundeb", "ano": 2025},
        campos=["mes", "categoria", "valor_recebido", "origem_do_recurso"],
    )

    assert resultado["total"] == 1
    assert resultado["resultados"] == [
        {
            "mes": "MARCO",
            "categoria": "Transferencias de Recursos do FUNDEB - Principal",
            "valor_recebido": 48000.0,
            "origem_do_recurso": "FUNDEB",
        }
    ]

    session.close()


def test_consultar_receitas_filtra_lancamento_por_tributo(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            _lancamento(
                mes="ABRIL",
                data_lancamento=date(2025, 4, 2),
                tipo_receita="IPTU",
                tributo="Imposto Predial e Territorial",
                valor_lancado_exercicio="12000.00",
            ),
            _lancamento(
                mes="ABRIL",
                data_lancamento=date(2025, 4, 8),
                tipo_receita="ITBI",
                tributo="ITBI",
                valor_lancado_exercicio="5000.00",
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = receitas_tools.consultar_receitas(
        filtros={"tipo_de_dado": "lancamento", "tributo": "ITBI"},
        campos=["mes", "tipo", "tributo", "valor_lancado"],
    )

    assert resultado["total"] == 1
    assert resultado["resultados"] == [
        {
            "mes": "ABRIL",
            "tipo": "ITBI",
            "tributo": "ITBI",
            "valor_lancado": 5000.0,
        }
    ]

    session.close()


def test_consultar_receitas_preserva_paginacao_ordenacao_e_projecao(
    monkeypatch,
) -> None:
    session = _build_session()
    natureza_iptu = _natureza(
        identificacao="1.1.1.2",
        nome="Imposto Predial e Territorial Urbano - Principal",
    )
    natureza_fundeb = _natureza(
        identificacao="1.7.5.1",
        nome="Transferencias de Recursos do FUNDEB - Principal",
    )
    session.add_all(
        [
            _arrecadacao(
                natureza=natureza_iptu,
                mes="JANEIRO",
                data_arrecadacao=date(2025, 1, 15),
                unidade_gestora="PREFEITURA MUNICIPAL",
                fonte_recurso="Recursos proprios",
                valor_previsto_liquido="20000.00",
                valor_arrecadado_liquido="19000.00",
            ),
            _arrecadacao(
                natureza=natureza_iptu,
                mes="FEVEREIRO",
                data_arrecadacao=date(2025, 2, 15),
                unidade_gestora="PREFEITURA MUNICIPAL",
                fonte_recurso="Recursos proprios",
                valor_previsto_liquido="21000.00",
                valor_arrecadado_liquido="20000.00",
            ),
            _arrecadacao(
                natureza=natureza_fundeb,
                mes="MARCO",
                data_arrecadacao=date(2025, 3, 20),
                unidade_gestora="PREFEITURA MUNICIPAL",
                fonte_recurso="FUNDEB",
                valor_previsto_liquido="50000.00",
                valor_arrecadado_liquido="47000.00",
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = receitas_tools.consultar_receitas(
        filtros={"tipo_de_dado": "arrecadacao", "ano": 2025},
        ordenar_por="valor_recebido",
        ordem="desc",
        limite=1,
        campos=["mes", "categoria", "valor_recebido"],
    )

    assert resultado["total"] == 3
    assert resultado["resultados"] == [
        {
            "mes": "MARCO",
            "categoria": "Transferencias de Recursos do FUNDEB - Principal",
            "valor_recebido": 47000.0,
        }
    ]
    assert resultado["mensagem"] == "Mostrando 1 de 3 registros encontrados."
    assert resultado["metadata"]["campos"] == ["mes", "categoria", "valor_recebido"]

    session.close()


def test_agregar_receitas_soma_valor_recebido_por_categoria(monkeypatch) -> None:
    session = _build_session()
    natureza_iptu = _natureza(
        identificacao="1.1.1.2",
        nome="Imposto Predial e Territorial Urbano - Principal",
    )
    natureza_fundeb = _natureza(
        identificacao="1.7.5.1",
        nome="Transferencias de Recursos do FUNDEB - Principal",
    )
    session.add_all(
        [
            _arrecadacao(
                natureza=natureza_iptu,
                mes="JANEIRO",
                data_arrecadacao=date(2025, 1, 15),
                unidade_gestora="PREFEITURA MUNICIPAL",
                fonte_recurso="Recursos proprios",
                valor_previsto_liquido="20000.00",
                valor_arrecadado_liquido="19000.00",
            ),
            _arrecadacao(
                natureza=natureza_iptu,
                mes="FEVEREIRO",
                data_arrecadacao=date(2025, 2, 15),
                unidade_gestora="PREFEITURA MUNICIPAL",
                fonte_recurso="Recursos proprios",
                valor_previsto_liquido="21000.00",
                valor_arrecadado_liquido="20000.00",
            ),
            _arrecadacao(
                natureza=natureza_fundeb,
                mes="FEVEREIRO",
                data_arrecadacao=date(2025, 2, 20),
                unidade_gestora="PREFEITURA MUNICIPAL",
                fonte_recurso="FUNDEB",
                valor_previsto_liquido="50000.00",
                valor_arrecadado_liquido="47000.00",
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = receitas_tools.agregar_receitas(
        filtros={"tipo_de_dado": "arrecadacao", "ano": 2025},
        agrupar_por="categoria",
        metrica="soma_valor_recebido",
        ordenar_por="metrica",
        ordem="desc",
    )

    assert resultado["total_grupos"] == 2
    assert resultado["resultados"] == [
        {
            "categoria": "Transferencias de Recursos do FUNDEB - Principal",
            "soma_valor_recebido": 47000.0,
        },
        {
            "categoria": "Imposto Predial e Territorial Urbano - Principal",
            "soma_valor_recebido": 39000.0,
        },
    ]

    session.close()


def test_agregar_receitas_soma_valor_lancado_total(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            _lancamento(
                mes="ABRIL",
                data_lancamento=date(2025, 4, 2),
                tipo_receita="IPTU",
                tributo="Imposto Predial e Territorial",
                valor_lancado_exercicio="12000.00",
                valor_lancado_divida_ativa="2000.00",
            ),
            _lancamento(
                mes="ABRIL",
                data_lancamento=date(2025, 4, 8),
                tipo_receita="ITBI",
                tributo="ITBI",
                valor_lancado_exercicio="5000.00",
                valor_lancado_divida_ativa="500.00",
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = receitas_tools.agregar_receitas(
        filtros={"tipo_de_dado": "lancamento", "ano": 2025},
        metrica="soma_valor_lancado",
    )

    assert resultado["valor_total"] == 17000.0
    assert resultado["metadata"]["filtros_aplicados"] == {
        "tipo_de_dado": "lancamento",
        "ano": 2025,
    }

    session.close()


def test_agregar_receitas_total_zero_mantem_correspondencia_sem_sugestao(
    monkeypatch,
) -> None:
    session = _build_session()
    natureza_iptu = _natureza(
        identificacao="1.1.1.2",
        nome="Imposto Predial e Territorial Urbano - Principal",
    )
    session.add(
        _arrecadacao(
            natureza=natureza_iptu,
            mes="JANEIRO",
            data_arrecadacao=date(2025, 1, 15),
            unidade_gestora="PREFEITURA MUNICIPAL",
            fonte_recurso="Recursos proprios",
            valor_previsto_liquido="100.00",
            valor_arrecadado_liquido="0.00",
        )
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = receitas_tools.agregar_receitas(
        filtros={"tipo_de_dado": "arrecadacao", "ano": 2025, "tema": "iptu"},
        metrica="soma_valor_recebido",
    )

    assert resultado["valor_total"] == 0.0
    assert resultado["sugestao"] is None
    assert resultado["mensagem"] == (
        "Agregacao sem agrupamento: `valor_total` e o resultado final; "
        "`resultados` vazio e `total_grupos` 0 sao esperados. "
        "1 registro correspondeu aos filtros."
    )

    session.close()


def test_agregar_receitas_valida_periodo_de_mes_invalido() -> None:
    resultado = receitas_tools.agregar_receitas(
        filtros={"mes_inicio": 10, "mes_fim": 3},
    )

    assert resultado["total_grupos"] == 0
    assert "Parametros invalidos" in resultado["mensagem"]
