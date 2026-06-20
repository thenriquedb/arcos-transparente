from __future__ import annotations

from contextlib import contextmanager
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import agents.tools.sql_tools.planejamento as planejamento_tools
from database import session as session_manager
from database.models import Base, PlanejamentoDespesa


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


def _planejamento(
    *,
    mes: str,
    mes_num: int,
    subfuncao: str,
    acao: str,
    grupo: str,
    orcamento_atualizado: Decimal,
    valor_pago: Decimal,
    origem: str = "saude",
    funcao: str = "Saúde",
    unidade_gestora: str = "FUNDAÇÃO MUNIC. SAÚDE E ASSIST. ARCOS",
    orgao: str = "FUNDAÇÃO M. SAÚDE",
    unidade: str = "FUNDAÇÃO M. SAÚDE",
    programa: str = "Promoção das Ações de Saúde - FUMUSA",
) -> PlanejamentoDespesa:
    return PlanejamentoDespesa(
        origem=origem,
        exercicio=2025,
        mes=mes,
        mes_num=mes_num,
        unidade_gestora=unidade_gestora,
        orgao=orgao,
        unidade=unidade,
        funcao=funcao,
        subfuncao=subfuncao,
        programa=programa,
        tipo_acao="Atividade",
        descricao_acao=acao,
        fonte_recurso_identificacao="1500",
        fonte_recurso_descricao="Recursos não Vinculados de Impostos",
        esfera_administrativa="Seguridade Social",
        categoria_economica_identificacao="3.1.90.11",
        categoria_economica_descricao="Vencimentos e Vantagens Fixas - Pessoal Civil",
        grupo_despesa_identificacao="3.1.00.00.00.00.00",
        grupo_despesa_descricao=grupo,
        elemento_despesa_identificacao="3.1.90.00.00.00.00",
        elemento_despesa_descricao="Aplicações Diretas",
        modalidade_aplicacao_descricao="Não se aplica",
        dotacao_inicial=orcamento_atualizado,
        dotacao_atualizada=orcamento_atualizado,
        valor_empenhado=valor_pago,
        valor_liquidado=valor_pago,
        valor_pago=valor_pago,
    )


def test_consultar_planejamento_filtra_saude_por_acao_sem_acento(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            _planejamento(
                mes="JANEIRO",
                mes_num=1,
                subfuncao="Atenção Básica",
                acao="Manutenção da Atenção Primária à Saúde",
                grupo="PESSOAL E ENCARGOS SOCIAIS",
                orcamento_atualizado=Decimal("150000.00"),
                valor_pago=Decimal("9277.07"),
            ),
            _planejamento(
                mes="FEVEREIRO",
                mes_num=2,
                subfuncao="Vigilância Sanitária",
                acao="Manutenção da Vigilância Sanitária",
                grupo="OUTRAS DESPESAS CORRENTES",
                orcamento_atualizado=Decimal("60000.00"),
                valor_pago=Decimal("6580.68"),
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = planejamento_tools.consultar_planejamento(
        filtros={"acao": "atencao primaria", "ano": 2025},
        campos=["mes", "area", "subarea", "acao", "orcamento_atualizado"],
    )

    assert resultado["total"] == 1
    assert resultado["resultados"] == [
        {
            "mes": "JANEIRO",
            "area": "Saúde",
            "subarea": "Atenção Básica",
            "acao": "Manutenção da Atenção Primária à Saúde",
            "orcamento_atualizado": 150000.0,
        }
    ]

    session.close()


def test_consultar_planejamento_filtra_por_entidade_fumusa(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            _planejamento(
                mes="JANEIRO",
                mes_num=1,
                subfuncao="Atenção Básica",
                acao="Manutenção da Atenção Primária à Saúde",
                grupo="PESSOAL E ENCARGOS SOCIAIS",
                orcamento_atualizado=Decimal("150000.00"),
                valor_pago=Decimal("9277.07"),
                programa="Gestão da Saúde",
            ),
            _planejamento(
                mes="FEVEREIRO",
                mes_num=2,
                subfuncao="Administração Geral",
                acao="Gestão Administrativa da Fundação",
                grupo="OUTRAS DESPESAS CORRENTES",
                orcamento_atualizado=Decimal("60000.00"),
                valor_pago=Decimal("6580.68"),
                unidade_gestora="Prefeitura Municipal de Arcos",
                orgao="Secretaria de Obras",
                unidade="Secretaria de Obras",
                programa="Infraestrutura Urbana",
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = planejamento_tools.consultar_planejamento(
        filtros={"entidade": "fumusa", "ano": 2025},
        campos=["unidade_gestora", "programa", "acao"],
    )

    assert resultado["total"] == 1
    assert resultado["resultados"] == [
        {
            "unidade_gestora": "FUNDAÇÃO MUNIC. SAÚDE E ASSIST. ARCOS",
            "programa": "Gestão da Saúde",
            "acao": "Manutenção da Atenção Primária à Saúde",
        }
    ]

    session.close()


def test_consultar_planejamento_preserva_paginacao_ordenacao_e_projecao(
    monkeypatch,
) -> None:
    session = _build_session()
    session.add_all(
        [
            _planejamento(
                mes="JANEIRO",
                mes_num=1,
                subfuncao="Atenção Básica",
                acao="Manutenção da Atenção Primária à Saúde",
                grupo="PESSOAL E ENCARGOS SOCIAIS",
                orcamento_atualizado=Decimal("150000.00"),
                valor_pago=Decimal("9000.00"),
            ),
            _planejamento(
                mes="FEVEREIRO",
                mes_num=2,
                subfuncao="Atenção Básica",
                acao="Manutenção da Atenção Primária à Saúde",
                grupo="PESSOAL E ENCARGOS SOCIAIS",
                orcamento_atualizado=Decimal("150000.00"),
                valor_pago=Decimal("11000.00"),
            ),
            _planejamento(
                mes="MARCO",
                mes_num=3,
                subfuncao="Vigilância Sanitária",
                acao="Manutenção da Vigilância Sanitária",
                grupo="OUTRAS DESPESAS CORRENTES",
                orcamento_atualizado=Decimal("60000.00"),
                valor_pago=Decimal("5000.00"),
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = planejamento_tools.consultar_planejamento(
        filtros={"ano": 2025},
        ordenar_por="valor_pago",
        ordem="desc",
        limite=1,
        campos=["mes", "acao", "valor_pago"],
    )

    assert resultado["total"] == 3
    assert resultado["resultados"] == [
        {
            "mes": "FEVEREIRO",
            "acao": "Manutenção da Atenção Primária à Saúde",
            "valor_pago": 11000.0,
        }
    ]
    assert resultado["mensagem"] == "Mostrando 1 de 3 registros encontrados."
    assert resultado["metadata"]["campos"] == ["mes", "acao", "valor_pago"]

    session.close()


def test_agregar_planejamento_soma_valor_pago_por_subarea(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            _planejamento(
                mes="JANEIRO",
                mes_num=1,
                subfuncao="Atenção Básica",
                acao="Manutenção da Atenção Primária à Saúde",
                grupo="PESSOAL E ENCARGOS SOCIAIS",
                orcamento_atualizado=Decimal("150000.00"),
                valor_pago=Decimal("9000.00"),
            ),
            _planejamento(
                mes="FEVEREIRO",
                mes_num=2,
                subfuncao="Atenção Básica",
                acao="Manutenção da Atenção Primária à Saúde",
                grupo="PESSOAL E ENCARGOS SOCIAIS",
                orcamento_atualizado=Decimal("150000.00"),
                valor_pago=Decimal("11000.00"),
            ),
            _planejamento(
                mes="JANEIRO",
                mes_num=1,
                subfuncao="Vigilância Sanitária",
                acao="Manutenção da Vigilância Sanitária",
                grupo="OUTRAS DESPESAS CORRENTES",
                orcamento_atualizado=Decimal("60000.00"),
                valor_pago=Decimal("5000.00"),
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = planejamento_tools.agregar_planejamento(
        filtros={"ano": 2025, "area": "saude"},
        agrupar_por="subarea",
        metrica="soma_valor_pago",
        ordenar_por="metrica",
        ordem="desc",
    )

    assert resultado["total_grupos"] == 2
    assert resultado["resultados"] == [
        {"subarea": "Atenção Básica", "soma_valor_pago": 20000.0},
        {"subarea": "Vigilância Sanitária", "soma_valor_pago": 5000.0},
    ]

    session.close()


def test_agregar_planejamento_valida_periodo_de_mes_invalido() -> None:
    resultado = planejamento_tools.agregar_planejamento(
        filtros={"mes_inicio": 4, "mes_fim": 1},
    )

    assert resultado["total_grupos"] == 0
    assert "Parametros invalidos" in resultado["mensagem"]


def test_consultar_planejamento_suporta_prefeitura_por_origem_e_area(
    monkeypatch,
) -> None:
    session = _build_session()
    session.add_all(
        [
            _planejamento(
                origem="prefeitura",
                funcao="Educação",
                unidade_gestora="PREFEITURA MUNICIPAL",
                orgao="PREFEITURA MUNICIPAL",
                unidade="SECRETARIA MUNICIPAL DE EDUCACAO",
                programa="Apoio a Manutencao do Ensino",
                mes="ABRIL",
                mes_num=4,
                subfuncao="Administração Geral",
                acao="Manutenção das Atividades da Secretaria de Educação",
                grupo="PESSOAL E ENCARGOS SOCIAIS",
                orcamento_atualizado=Decimal("25000.00"),
                valor_pago=Decimal("2345.67"),
            ),
            _planejamento(
                origem="saude",
                funcao="Saúde",
                mes="ABRIL",
                mes_num=4,
                subfuncao="Atenção Básica",
                acao="Manutenção da Atenção Primária à Saúde",
                grupo="PESSOAL E ENCARGOS SOCIAIS",
                orcamento_atualizado=Decimal("150000.00"),
                valor_pago=Decimal("9277.07"),
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = planejamento_tools.consultar_planejamento(
        filtros={"origem": "prefeitura", "ano": 2025, "area": "educacao"},
        campos=["origem", "area", "acao", "valor_pago"],
    )

    assert resultado["total"] == 1
    assert resultado["resultados"] == [
        {
            "origem": "prefeitura",
            "area": "Educação",
            "acao": "Manutenção das Atividades da Secretaria de Educação",
            "valor_pago": 2345.67,
        }
    ]

    session.close()


def test_agregar_planejamento_suporta_prefeitura_por_origem(
    monkeypatch,
) -> None:
    session = _build_session()
    session.add_all(
        [
            _planejamento(
                origem="prefeitura",
                funcao="Educação",
                unidade_gestora="PREFEITURA MUNICIPAL",
                orgao="PREFEITURA MUNICIPAL",
                unidade="SECRETARIA MUNICIPAL DE EDUCACAO",
                programa="Apoio a Manutencao do Ensino",
                mes="ABRIL",
                mes_num=4,
                subfuncao="Administração Geral",
                acao="Manutenção das Atividades da Secretaria de Educação",
                grupo="PESSOAL E ENCARGOS SOCIAIS",
                orcamento_atualizado=Decimal("25000.00"),
                valor_pago=Decimal("2345.67"),
            ),
            _planejamento(
                origem="prefeitura",
                funcao="Educação",
                unidade_gestora="PREFEITURA MUNICIPAL",
                orgao="PREFEITURA MUNICIPAL",
                unidade="SECRETARIA MUNICIPAL DE EDUCACAO",
                programa="Apoio a Manutencao do Ensino",
                mes="MAIO",
                mes_num=5,
                subfuncao="Ensino Fundamental",
                acao="Manutenção do Ensino Fundamental",
                grupo="PESSOAL E ENCARGOS SOCIAIS",
                orcamento_atualizado=Decimal("30000.00"),
                valor_pago=Decimal("5000.00"),
            ),
            _planejamento(
                origem="saude",
                funcao="Saúde",
                mes="MAIO",
                mes_num=5,
                subfuncao="Atenção Básica",
                acao="Manutenção da Atenção Primária à Saúde",
                grupo="PESSOAL E ENCARGOS SOCIAIS",
                orcamento_atualizado=Decimal("100000.00"),
                valor_pago=Decimal("6000.00"),
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = planejamento_tools.agregar_planejamento(
        filtros={"origem": "prefeitura", "ano": 2025},
        metrica="soma_valor_pago",
    )

    assert resultado["valor_total"] == 7345.67

    session.close()


def test_consultar_planejamento_colapsa_rollups_hierarquicos_duplicados(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            _planejamento(
                origem="prefeitura",
                funcao="Educação",
                unidade_gestora="PREFEITURA MUNICIPAL",
                orgao="PREFEITURA MUNICIPAL",
                unidade="PREFEITURA MUNICIPAL",
                programa="Programa de Merenda Escolar",
                mes="NOVEMBRO",
                mes_num=11,
                subfuncao="Educação Infantil",
                acao="Distribuição de Merenda das Creches",
                grupo="OUTRAS DESPESAS CORRENTES",
                orcamento_atualizado=Decimal("1090.00"),
                valor_pago=Decimal("44875.35"),
            ),
            _planejamento(
                origem="prefeitura",
                funcao="Educação",
                unidade_gestora="PREFEITURA MUNICIPAL",
                orgao="PREFEITURA MUNICIPAL",
                unidade="SECRETARIA MUNICIPAL DE EDUCACAO",
                programa="Programa de Merenda Escolar",
                mes="NOVEMBRO",
                mes_num=11,
                subfuncao="Educação Infantil",
                acao="Distribuição de Merenda das Creches",
                grupo="OUTRAS DESPESAS CORRENTES",
                orcamento_atualizado=Decimal("1090.00"),
                valor_pago=Decimal("44875.35"),
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = planejamento_tools.consultar_planejamento(
        filtros={"ano": 2025, "programa": "merenda escolar"},
        campos=["unidade", "programa", "acao", "valor_pago"],
    )

    assert resultado["total"] == 1
    assert resultado["resultados"] == [
        {
            "unidade": "SECRETARIA MUNICIPAL DE EDUCACAO",
            "programa": "Programa de Merenda Escolar",
            "acao": "Distribuição de Merenda das Creches",
            "valor_pago": 44875.35,
        }
    ]

    session.close()


def test_agregar_planejamento_nao_dobra_totais_em_rollups_hierarquicos(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            _planejamento(
                origem="prefeitura",
                funcao="Educação",
                unidade_gestora="PREFEITURA MUNICIPAL",
                orgao="PREFEITURA MUNICIPAL",
                unidade="PREFEITURA MUNICIPAL",
                programa="Programa de Merenda Escolar",
                mes="NOVEMBRO",
                mes_num=11,
                subfuncao="Educação Infantil",
                acao="Distribuição de Merenda das Creches",
                grupo="OUTRAS DESPESAS CORRENTES",
                orcamento_atualizado=Decimal("1090.00"),
                valor_pago=Decimal("44875.35"),
            ),
            _planejamento(
                origem="prefeitura",
                funcao="Educação",
                unidade_gestora="PREFEITURA MUNICIPAL",
                orgao="PREFEITURA MUNICIPAL",
                unidade="SECRETARIA MUNICIPAL DE EDUCACAO",
                programa="Programa de Merenda Escolar",
                mes="NOVEMBRO",
                mes_num=11,
                subfuncao="Educação Infantil",
                acao="Distribuição de Merenda das Creches",
                grupo="OUTRAS DESPESAS CORRENTES",
                orcamento_atualizado=Decimal("1090.00"),
                valor_pago=Decimal("44875.35"),
            ),
            _planejamento(
                origem="prefeitura",
                funcao="Educação",
                unidade_gestora="PREFEITURA MUNICIPAL",
                orgao="PREFEITURA MUNICIPAL",
                unidade="PREFEITURA MUNICIPAL",
                programa="Programa de Merenda Escolar",
                mes="NOVEMBRO",
                mes_num=11,
                subfuncao="Ensino Fundamental",
                acao="Distribuição de Merenda das Escolas",
                grupo="OUTRAS DESPESAS CORRENTES",
                orcamento_atualizado=Decimal("4883.00"),
                valor_pago=Decimal("88944.53"),
            ),
            _planejamento(
                origem="prefeitura",
                funcao="Educação",
                unidade_gestora="PREFEITURA MUNICIPAL",
                orgao="PREFEITURA MUNICIPAL",
                unidade="SECRETARIA MUNICIPAL DE EDUCACAO",
                programa="Programa de Merenda Escolar",
                mes="NOVEMBRO",
                mes_num=11,
                subfuncao="Ensino Fundamental",
                acao="Distribuição de Merenda das Escolas",
                grupo="OUTRAS DESPESAS CORRENTES",
                orcamento_atualizado=Decimal("4883.00"),
                valor_pago=Decimal("88944.53"),
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = planejamento_tools.agregar_planejamento(
        filtros={"ano": 2025, "programa": "merenda escolar"},
        metrica="soma_valor_pago",
    )

    assert resultado["valor_total"] == 133819.88

    session.close()


def test_consultar_planejamento_aceita_alias_de_programa_fmas(monkeypatch) -> None:
    session = _build_session()
    session.add(
        _planejamento(
            origem="prefeitura",
            funcao="Assistência Social",
            unidade_gestora="PREFEITURA MUNICIPAL",
            orgao="SECRETARIA MUNICIPAL DE DESENVOLVIMENTO E INTEGRACAO SOCIAL",
            unidade="SECRETARIA MUNICIPAL DE DESENVOLVIMENTO E INTEGRACAO SOCIAL",
            programa="Fundo Municipal de Assistência Social",
            mes="ABRIL",
            mes_num=4,
            subfuncao="Assistência Comunitária",
            acao="Manutenção dos Serviços Administrativos Socioassistenciais",
            grupo="OUTRAS DESPESAS CORRENTES",
            orcamento_atualizado=Decimal("32000.00"),
            valor_pago=Decimal("8450.00"),
        )
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = planejamento_tools.consultar_planejamento(
        filtros={"ano": 2025, "programa": "fmas"},
        campos=["programa", "acao", "valor_pago"],
    )

    assert resultado["total"] == 1
    assert resultado["resultados"] == [
        {
            "programa": "Fundo Municipal de Assistência Social",
            "acao": "Manutenção dos Serviços Administrativos Socioassistenciais",
            "valor_pago": 8450.0,
        }
    ]

    session.close()


def test_consultar_planejamento_aceita_alias_de_programa_meio_ambiente(monkeypatch) -> None:
    session = _build_session()
    session.add(
        _planejamento(
            origem="prefeitura",
            funcao="Gestão Ambiental",
            unidade_gestora="PREFEITURA MUNICIPAL",
            orgao="SECRETARIA MUNICIPAL DO MEIO AMBIENTE E AGRICULTURA",
            unidade="SECRETARIA MUNICIPAL DO MEIO AMBIENTE E AGRICULTURA",
            programa="Cuidados e Preservacao do Meio Ambiente",
            mes="MAIO",
            mes_num=5,
            subfuncao="Preservação e Conservação Ambiental",
            acao="Manutenção das Atividades Secretaria Meio Ambiente e Agropecuária",
            grupo="OUTRAS DESPESAS CORRENTES",
            orcamento_atualizado=Decimal("41000.00"),
            valor_pago=Decimal("6200.00"),
        )
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = planejamento_tools.consultar_planejamento(
        filtros={"ano": 2025, "programa": "meio ambiente"},
        campos=["programa", "acao", "valor_pago"],
    )

    assert resultado["total"] == 1
    assert resultado["resultados"] == [
        {
            "programa": "Cuidados e Preservacao do Meio Ambiente",
            "acao": "Manutenção das Atividades Secretaria Meio Ambiente e Agropecuária",
            "valor_pago": 6200.0,
        }
    ]

    session.close()


def test_consultar_planejamento_aceita_alias_de_acao_limpeza_publica(monkeypatch) -> None:
    session = _build_session()
    session.add(
        _planejamento(
            origem="prefeitura",
            funcao="Urbanismo",
            unidade_gestora="PREFEITURA MUNICIPAL",
            orgao="SECRETARIA MUNICIPAL DE OBRAS E SERVICOS PUBLICOS",
            unidade="SECRETARIA MUNICIPAL DE OBRAS E SERVICOS PUBLICOS",
            programa="Programa de Limpeza Urbana",
            mes="JUNHO",
            mes_num=6,
            subfuncao="Serviços Urbanos",
            acao="Manutenção dos Serviços de Limpeza Pública",
            grupo="OUTRAS DESPESAS CORRENTES",
            orcamento_atualizado=Decimal("58000.00"),
            valor_pago=Decimal("21102.46"),
        )
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = planejamento_tools.consultar_planejamento(
        filtros={"ano": 2025, "acao": "limpeza publica"},
        campos=["programa", "acao", "valor_pago"],
    )

    assert resultado["total"] == 1
    assert resultado["resultados"] == [
        {
            "programa": "Programa de Limpeza Urbana",
            "acao": "Manutenção dos Serviços de Limpeza Pública",
            "valor_pago": 21102.46,
        }
    ]

    session.close()


def test_consultar_planejamento_filtra_por_area_urbanismo(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            _planejamento(
                origem="prefeitura",
                funcao="Urbanismo",
                unidade_gestora="PREFEITURA MUNICIPAL",
                orgao="SECRETARIA MUNICIPAL DE OBRAS E SERVICOS PUBLICOS",
                unidade="SECRETARIA MUNICIPAL DE OBRAS E SERVICOS PUBLICOS",
                programa="Programa de Limpeza Urbana",
                mes="JULHO",
                mes_num=7,
                subfuncao="Serviços Urbanos",
                acao="Manutenção dos Serviços de Limpeza Pública",
                grupo="OUTRAS DESPESAS CORRENTES",
                orcamento_atualizado=Decimal("60000.00"),
                valor_pago=Decimal("18000.00"),
            ),
            _planejamento(
                origem="prefeitura",
                funcao="Saúde",
                unidade_gestora="PREFEITURA MUNICIPAL",
                orgao="FUNDAÇÃO M. SAÚDE",
                unidade="FUNDAÇÃO M. SAÚDE",
                programa="Promoção das Ações de Saúde - FUMUSA",
                mes="JULHO",
                mes_num=7,
                subfuncao="Atenção Básica",
                acao="Manutenção da Atenção Primária à Saúde",
                grupo="PESSOAL E ENCARGOS SOCIAIS",
                orcamento_atualizado=Decimal("70000.00"),
                valor_pago=Decimal("9000.00"),
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = planejamento_tools.consultar_planejamento(
        filtros={"ano": 2025, "area": "urbanismo"},
        campos=["area", "programa", "acao"],
    )

    assert resultado["total"] == 1
    assert resultado["resultados"] == [
        {
            "area": "Urbanismo",
            "programa": "Programa de Limpeza Urbana",
            "acao": "Manutenção dos Serviços de Limpeza Pública",
        }
    ]

    session.close()


def _limpeza_urbana_e_distrator_de_urbanismo() -> list[PlanejamentoDespesa]:
    return [
        _planejamento(
            origem="prefeitura",
            funcao="Urbanismo",
            unidade_gestora="PREFEITURA MUNICIPAL",
            orgao="SECRETARIA MUNICIPAL DE OBRAS E SERVICOS PUBLICOS",
            unidade="SECRETARIA MUNICIPAL DE OBRAS E SERVICOS PUBLICOS",
            programa="Programa de Limpeza Urbana",
            mes="AGOSTO",
            mes_num=8,
            subfuncao="Serviços Urbanos",
            acao="Manutenção dos Serviços de Limpeza Pública",
            grupo="OUTRAS DESPESAS CORRENTES",
            orcamento_atualizado=Decimal("60000.00"),
            valor_pago=Decimal("18000.00"),
        ),
        _planejamento(
            origem="prefeitura",
            funcao="Urbanismo",
            unidade_gestora="PREFEITURA MUNICIPAL",
            orgao="SECRETARIA MUNICIPAL DE OBRAS E SERVICOS PUBLICOS",
            unidade="SECRETARIA MUNICIPAL DE OBRAS E SERVICOS PUBLICOS",
            programa="Programa de Infraestrutura Urbana e Rural",
            mes="AGOSTO",
            mes_num=8,
            subfuncao="Infraestrutura Urbana",
            acao="Manutenção de Vias Públicas",
            grupo="OUTRAS DESPESAS CORRENTES",
            orcamento_atualizado=Decimal("90000.00"),
            valor_pago=Decimal("25000.00"),
        ),
    ]


def test_consultar_planejamento_reancora_programa_informado_como_area(monkeypatch) -> None:
    """`limpeza urbana` é um *programa*; mesmo informado como `area`, deve casar.

    A função orçamentária dessas linhas é "Urbanismo", então um filtro literal por
    área não encontraria nada. O termo é reancorado na dimensão canônica
    (`programa`), sem arrastar as demais linhas de urbanismo.
    """

    session = _build_session()
    session.add_all(_limpeza_urbana_e_distrator_de_urbanismo())
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = planejamento_tools.consultar_planejamento(
        filtros={"ano": 2025, "area": "limpeza urbana"},
        campos=["programa", "acao", "valor_pago"],
    )

    assert resultado["total"] == 1
    assert resultado["resultados"] == [
        {
            "programa": "Programa de Limpeza Urbana",
            "acao": "Manutenção dos Serviços de Limpeza Pública",
            "valor_pago": 18000.0,
        }
    ]

    session.close()


def test_agregar_planejamento_reancora_programa_informado_como_acao(monkeypatch) -> None:
    """Mesma reancoragem para `agregar_planejamento` quando o termo vem em `acao`."""

    session = _build_session()
    session.add_all(_limpeza_urbana_e_distrator_de_urbanismo())
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = planejamento_tools.agregar_planejamento(
        filtros={"ano": 2025, "acao": "limpeza urbana"},
        metrica="soma_valor_pago",
    )

    assert resultado["valor_total"] == 18000.0
