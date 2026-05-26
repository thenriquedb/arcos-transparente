from __future__ import annotations

from decimal import Decimal

from ingestion.parsers.xml.despesas_parser import DespesasParser


def test_despesas_parser_parseia_empenho_com_item_e_comprobatorio(tmp_path) -> None:
    xml = """<?xml version="1.0" encoding="ISO-8859-1"?>
<Empenhos>
    <Principal>
        <Exercicio>2025</Exercicio>
        <UnidadeGestora>CÂMARA MUNICIPAL</UnidadeGestora>
        <Funcao>Legislativa</Funcao>
        <Acao><Tipo>Atividade</Tipo><Descricao>Manutenção da Câmara</Descricao></Acao>
        <NumeroEmpenho>000331</NumeroEmpenho>
        <DataEmissaoEmpenho>17/09/2025</DataEmissaoEmpenho>
        <CategoriaEmpenho>Comum</CategoriaEmpenho>
        <Credor>EDISON DOS SANTOS</Credor>
        <CPFCNPJ>123</CPFCNPJ>
        <ValorEmpenhado>R$ 18,00</ValorEmpenhado>
        <ValorLiquidado>R$ 18,00</ValorLiquidado>
        <ValorPago>R$ 18,00</ValorPago>
        <Itens>
            <Item>
                <Numero>1</Numero>
                <Item>Ressarcimento de despesa com locomoção</Item>
                <Quantidade>1.0000</Quantidade>
                <ValorUnitario>R$ 18,00</ValorUnitario>
                <ValorTotal>R$ 18,00</ValorTotal>
            </Item>
        </Itens>
        <documentosComprobatorios>
            <DocumentosComprobatorios>
                <dt_liquidacao>30/09/2025</dt_liquidacao>
                <num_documento>331</num_documento>
                <valor_documento>R$ 18,00</valor_documento>
            </DocumentosComprobatorios>
        </documentosComprobatorios>
    </Principal>
</Empenhos>
"""
    arquivo = tmp_path / "empenhos-2025.xml"
    arquivo.write_text(xml, encoding="ISO-8859-1")

    registros = DespesasParser().parse(str(arquivo))

    assert len(registros) == 1
    assert registros[0]["tipo_origem"] == "empenho"
    assert registros[0]["origem"] == "camara"
    assert registros[0]["numero_documento"] == "000331"
    assert registros[0]["valor_pago"] == Decimal("18.00")
    assert registros[0]["itens"][0]["descricao_item"] == (
        "Ressarcimento de despesa com locomoção"
    )
    assert registros[0]["documentos_comprobatorios"][0]["valor_documento"] == Decimal(
        "18.00"
    )


def test_despesas_parser_parseia_documento_extra(tmp_path) -> None:
    xml = """<?xml version="1.0" encoding="ISO-8859-1"?>
<DocumentosExtras>
    <Principal>
        <Exercicio>2025</Exercicio>
        <UnidadeGestora>PREFEITURA MUNICIPAL</UnidadeGestora>
        <NumeroDocumento>000001</NumeroDocumento>
        <DataEmissaoDocumento>01/01/2025</DataEmissaoDocumento>
        <ContaExtraorcamentaria>
            <Identificacao>5011</Identificacao>
            <Descricao>Repasse concedido Câmara</Descricao>
        </ContaExtraorcamentaria>
        <Credor>CAMARA MUNICIPAL DE ARCOS</Credor>
        <ValorDocumenro>R$ 541.666,67</ValorDocumenro>
        <ValorPago>R$ 541.666,67</ValorPago>
        <ValorAnulado>R$ 0,00</ValorAnulado>
    </Principal>
</DocumentosExtras>
"""
    arquivo = tmp_path / "documentos-extras-prefeitura-2025.xml"
    arquivo.write_text(xml, encoding="ISO-8859-1")

    registros = DespesasParser().parse(str(arquivo))

    assert len(registros) == 1
    assert registros[0]["tipo_origem"] == "documento_extra"
    assert registros[0]["origem"] == "prefeitura"
    assert registros[0]["conta_extra_identificacao"] == "5011"
    assert registros[0]["valor_documento"] == Decimal("541666.67")
