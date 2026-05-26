from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import ingestion.pipeline as pipeline_module
from database.models import Base, PlanejamentoDespesa
from ingestion.pipeline import IngestionPipeline


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


def _write_planejamento_file(
    path,
    *,
    unidade_gestora: str,
    unidade: str,
    funcao: str,
    subfuncao: str,
    programa: str,
    descricao_acao: str,
    mes: str,
    valor_pago: str,
) -> None:
    xml = f"""<?xml version="1.0" encoding="ISO-8859-1"?>
<Planejamento>
    <Principal>
        <Exercicio>2025</Exercicio>
        <UnidadeGestora>{unidade_gestora}</UnidadeGestora>
        <Orgao>PREFEITURA MUNICIPAL</Orgao>
        <Unidade>{unidade}</Unidade>
        <Funcao>{funcao}</Funcao>
        <SubFuncao>{subfuncao}</SubFuncao>
        <Programa>{programa}</Programa>
        <TipoAcao>Atividade</TipoAcao>
        <DescricaoAcao>{descricao_acao}</DescricaoAcao>
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
        <Mes>{mes}</Mes>
        <DotacaoInicial>R$ 10.000,00</DotacaoInicial>
        <ValorPago>{valor_pago}</ValorPago>
    </Principal>
</Planejamento>
"""
    path.write_text(xml, encoding="ISO-8859-1")


def test_arquivos_por_tipo_planejamentos_inclui_saude_e_prefeitura(tmp_path) -> None:
    planejamentos_dir = tmp_path / "planejamentos"
    planejamentos_dir.mkdir()
    _write_planejamento_file(
        planejamentos_dir / "planejamento-saude-2025.xml",
        unidade_gestora="FUNDAÇÃO MUNIC. SAÚDE E ASSIST. ARCOS",
        unidade="FUNDAÇÃO M. SAÚDE",
        funcao="Saúde",
        subfuncao="Atenção Básica",
        programa="Promoção das Ações de Saúde - FUMUSA",
        descricao_acao="Manutenção da Atenção Primária à Saúde",
        mes="JANEIRO",
        valor_pago="R$ 9.277,07",
    )
    _write_planejamento_file(
        planejamentos_dir / "planejamento-prefeitura-2025.xml",
        unidade_gestora="PREFEITURA MUNICIPAL",
        unidade="SECRETARIA MUNICIPAL DE EDUCACAO",
        funcao="Educação",
        subfuncao="Administração Geral",
        programa="Apoio a Manutencao do Ensino",
        descricao_acao="Manutenção das Atividades da Secretaria de Educação",
        mes="ABRIL",
        valor_pago="R$ 2.345,67",
    )

    pipeline = IngestionPipeline(data_dir=str(tmp_path))

    arquivos = pipeline._arquivos_por_tipo("planejamentos", 2025)

    assert [arquivo.name for arquivo in arquivos] == [
        "planejamento-prefeitura-2025.xml",
        "planejamento-saude-2025.xml",
    ]


def test_pipeline_planejamentos_persiste_saude_e_prefeitura(
    monkeypatch,
    tmp_path,
) -> None:
    planejamentos_dir = tmp_path / "planejamentos"
    planejamentos_dir.mkdir()
    _write_planejamento_file(
        planejamentos_dir / "planejamento-saude-2025.xml",
        unidade_gestora="FUNDAÇÃO MUNIC. SAÚDE E ASSIST. ARCOS",
        unidade="FUNDAÇÃO M. SAÚDE",
        funcao="Saúde",
        subfuncao="Atenção Básica",
        programa="Promoção das Ações de Saúde - FUMUSA",
        descricao_acao="Manutenção da Atenção Primária à Saúde",
        mes="JANEIRO",
        valor_pago="R$ 9.277,07",
    )
    _write_planejamento_file(
        planejamentos_dir / "planejamento-prefeitura-2025.xml",
        unidade_gestora="PREFEITURA MUNICIPAL",
        unidade="SECRETARIA MUNICIPAL DE EDUCACAO",
        funcao="Educação",
        subfuncao="Administração Geral",
        programa="Apoio a Manutencao do Ensino",
        descricao_acao="Manutenção das Atividades da Secretaria de Educação",
        mes="ABRIL",
        valor_pago="R$ 2.345,67",
    )
    session = _build_session()

    @contextmanager
    def fake_get_session():
        yield session

    monkeypatch.setattr(pipeline_module, "get_session", fake_get_session)

    pipeline = IngestionPipeline(data_dir=str(tmp_path))
    resultado = pipeline.run(tipos=["planejamentos"], ano=2025)

    total_registros = session.query(PlanejamentoDespesa).count()
    origens = {
        origem
        for (origem,) in session.query(PlanejamentoDespesa.origem)
        .distinct()
        .order_by(PlanejamentoDespesa.origem.asc())
        .all()
    }

    assert resultado["planejamentos"].inseridos == 2
    assert total_registros == 2
    assert origens == {"prefeitura", "saude"}

    session.close()
