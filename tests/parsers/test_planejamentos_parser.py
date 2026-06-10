from __future__ import annotations

from decimal import Decimal

from ingestion.parsers.xml.planejamentos_parser import PlanejamentosParser


def test_planejamentos_parser_parseia_xml_de_saude(tmp_path) -> None:
    xml = """<?xml version="1.0" encoding="ISO-8859-1"?>
<Planejamento>
    <Principal>
        <Exercicio>2025</Exercicio>
        <UnidadeGestora>FUNDAÇÃO MUNIC. SAÚDE E ASSIST. ARCOS</UnidadeGestora>
        <Orgao>FUNDAÇÃO M. SAÚDE</Orgao>
        <Unidade>FUNDAÇÃO M. SAÚDE</Unidade>
        <Departamento> </Departamento>
        <Funcao>Saúde</Funcao>
        <SubFuncao>Atenção Básica</SubFuncao>
        <Programa>Promoção das Ações de Saúde - FUMUSA</Programa>
        <TipoAcao>Atividade</TipoAcao>
        <DescricaoAcao>Manutenção da Atenção Primária à Saúde</DescricaoAcao>
        <FonteRecurso>
            <Identificacao>1500</Identificacao>
            <Descricao>Recursos não Vinculados de Impostos</Descricao>
        </FonteRecurso>
        <EsferaAdministrativa>Seguridade Social</EsferaAdministrativa>
        <CategoriaEconomica>
            <Identificacao>3.1.90.11</Identificacao>
            <Descricao>Vencimentos e Vantagens Fixas - Pessoal Civil</Descricao>
        </CategoriaEconomica>
        <GrupoDespesa>
            <Identificacao>3.1.00.00.00.00.00</Identificacao>
            <Descricao>PESSOAL E ENCARGOS SOCIAIS</Descricao>
        </GrupoDespesa>
        <ElementoDespesa>
            <Identificacao>3.1.90.00.00.00.00</Identificacao>
            <Descricao>Aplicações Diretas</Descricao>
        </ElementoDespesa>
        <ModalidadeAplicacao>
            <Identificacao> </Identificacao>
            <Descricao>Não se aplica</Descricao>
        </ModalidadeAplicacao>
        <Mes>JANEIRO</Mes>
        <DotacaoInicial>R$ 150.000,00</DotacaoInicial>
        <CreditosAdicionais> </CreditosAdicionais>
        <DotacaoAtualizada>R$ 150.000,00</DotacaoAtualizada>
        <ValorEmpenhado>R$ 9.277,07</ValorEmpenhado>
        <ValorLiquidacao> </ValorLiquidacao>
        <ValorLiquidado>R$ 9.277,07</ValorLiquidado>
        <ValorPago>R$ 9.277,07</ValorPago>
        <ValorAnulado> </ValorAnulado>
    </Principal>
</Planejamento>
"""
    arquivo = tmp_path / "planejamento-saude-2025.xml"
    arquivo.write_text(xml, encoding="ISO-8859-1")

    registros = PlanejamentosParser().parse(str(arquivo))

    assert len(registros) == 1
    assert registros[0]["origem"] == "saude"
    assert registros[0]["mes_num"] == 1
    assert registros[0]["funcao"] == "Saúde"
    assert registros[0]["descricao_acao"] == "Manutenção da Atenção Primária à Saúde"
    assert registros[0]["dotacao_inicial"] == Decimal("150000.00")
    assert registros[0]["valor_pago"] == Decimal("9277.07")


def test_planejamentos_parser_parseia_xml_de_prefeitura(tmp_path) -> None:
    xml = """<?xml version="1.0" encoding="ISO-8859-1"?>
<Planejamento>
    <Principal>
        <Exercicio>2025</Exercicio>
        <UnidadeGestora>PREFEITURA MUNICIPAL</UnidadeGestora>
        <Orgao>PREFEITURA MUNICIPAL</Orgao>
        <Unidade>SECRETARIA MUNICIPAL DE EDUCACAO</Unidade>
        <Funcao>Educação</Funcao>
        <SubFuncao>Administração Geral</SubFuncao>
        <Programa>Apoio a Manutencao do Ensino</Programa>
        <TipoAcao>Atividade</TipoAcao>
        <DescricaoAcao>Manutenção das Atividades da Secretaria de Educação</DescricaoAcao>
        <FonteRecurso>
            <Identificacao>1500</Identificacao>
            <Descricao>Recursos não Vinculados de Impostos</Descricao>
        </FonteRecurso>
        <EsferaAdministrativa>Fiscal</EsferaAdministrativa>
        <CategoriaEconomica>
            <Identificacao>3.1.90.04</Identificacao>
            <Descricao>Contratação por Tempo Determinado</Descricao>
        </CategoriaEconomica>
        <GrupoDespesa>
            <Identificacao>3.1.00.00.00.00.00</Identificacao>
            <Descricao>PESSOAL E ENCARGOS SOCIAIS</Descricao>
        </GrupoDespesa>
        <ElementoDespesa>
            <Identificacao>3.1.90.00.00.00.00</Identificacao>
            <Descricao>Aplicações Diretas</Descricao>
        </ElementoDespesa>
        <ModalidadeAplicacao>
            <Descricao>Não se aplica</Descricao>
        </ModalidadeAplicacao>
        <Mes>ABRIL</Mes>
        <DotacaoInicial>R$ 25.000,00</DotacaoInicial>
        <ValorPago>R$ 2.345,67</ValorPago>
    </Principal>
</Planejamento>
"""
    arquivo = tmp_path / "planejamento-prefeitura-2025.xml"
    arquivo.write_text(xml, encoding="ISO-8859-1")

    registros = PlanejamentosParser().parse(str(arquivo))

    assert len(registros) == 1
    assert registros[0]["origem"] == "prefeitura"
    assert registros[0]["mes_num"] == 4
    assert registros[0]["funcao"] == "Educação"
    assert registros[0]["descricao_acao"] == ("Manutenção das Atividades da Secretaria de Educação")
    assert registros[0]["dotacao_inicial"] == Decimal("25000.00")
    assert registros[0]["valor_pago"] == Decimal("2345.67")
