from __future__ import annotations

from contextlib import contextmanager
from datetime import date
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import ingestion.pipeline as pipeline_module
from database.models import Base, FolhaServidor, Servidor
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


def test_pipeline_descobre_apenas_relacao_servidores_json(tmp_path) -> None:
    relacao_dir = tmp_path / "servidores" / "relacao-servidores"
    folha_dir = tmp_path / "servidores" / "folha-pagamento"
    relacao_dir.mkdir(parents=True)
    folha_dir.mkdir(parents=True)

    json_path = relacao_dir / "relacao-servidores.json"
    json_path.write_text("[]", encoding="utf-8")
    (folha_dir / "folha-pagamento-2026.xml").write_text("<xml />", encoding="utf-8")

    pipeline = IngestionPipeline(data_dir=str(tmp_path))

    assert pipeline._arquivos_por_tipo("servidores", None) == [json_path]


def test_pipeline_importa_e_reimporta_servidores_json_sem_duplicar(
    monkeypatch,
    tmp_path,
) -> None:
    relacao_dir = tmp_path / "servidores" / "relacao-servidores"
    relacao_dir.mkdir(parents=True)
    arquivo = relacao_dir / "relacao-servidores.json"
    arquivo.write_text(
        json.dumps(
            [
                {
                    "id": 501,
                    "Competencia": "01/2026",
                    "Nome": "Maria da Silva",
                    "CPF": "***345.678-**",
                    "Matricula": "90001-1",
                    "CargoFuncao": "Enfermeira",
                    "FundamentoLegal": " ",
                    "Lotacao": "UPA Central",
                    "SituacaoFuncional": "Em atividade",
                    "FormaContratacaoInvestidura": "Processo Seletivo",
                    "DataAdmissao": "02/01/2025",
                    "DataDesligamento": "",
                    "HorarioTrabalho": "12:00 as 18:00",
                    "CargaHoraria": "",
                    "LocalOrigemCedencia": "",
                    "LocalDestinoCedencia": "",
                    "OnusPagamentoCedencia": "",
                    "DataInicioCessao": "",
                    "DataFimCessao": "",
                    "RegimeAposentadoria": "Geral",
                    "VinculoEmpregaticio": "Temporario",
                }
            ]
        ),
        encoding="utf-8",
    )

    session = _build_session()

    @contextmanager
    def fake_get_session():
        yield session

    monkeypatch.setattr(pipeline_module, "get_session", fake_get_session)

    pipeline = IngestionPipeline(data_dir=str(tmp_path))
    resultado_inicial = pipeline.run(tipos=["servidores"], ano=2026)

    assert resultado_inicial["servidores"].inseridos == 1
    assert session.query(Servidor).count() == 1
    session.rollback()

    atualizado = json.loads(arquivo.read_text(encoding="utf-8"))
    atualizado[0]["Lotacao"] = "Hospital Municipal"
    arquivo.write_text(json.dumps(atualizado), encoding="utf-8")

    resultado_reimportado = pipeline.run(tipos=["servidores"], ano=2026)

    assert resultado_reimportado["servidores"].atualizados == 1
    assert session.query(Servidor).count() == 1

    servidor = session.query(Servidor).one()
    assert servidor.source_id == 501
    assert servidor.competencia_referencia == date(2026, 1, 1)
    assert servidor.lotacao == "Hospital Municipal"

    session.close()


def test_get_or_create_folha_servidor_reutiliza_snapshot_por_chave() -> None:
    session = _build_session()

    primeiro = IngestionPipeline._get_or_create_folha_servidor(
        session=session,
        nome="Maria da Silva",
        cargo="Enfermeira",
        lotacao="UPA Central",
        competencia_referencia=date(2025, 3, 1),
        salario_base=2500,
    )
    segundo = IngestionPipeline._get_or_create_folha_servidor(
        session=session,
        nome="Maria da Silva",
        cargo="Enfermeira",
        lotacao="UPA Central",
        competencia_referencia=date(2025, 3, 1),
        salario_base=2600,
    )
    session.commit()

    assert primeiro.id == segundo.id
    assert session.query(FolhaServidor).count() == 1
    snapshot = session.query(FolhaServidor).one()
    assert snapshot.salario_base == 2600

    session.close()


def test_pipeline_ignora_novo_servidor_quando_matricula_ja_existe(
    monkeypatch,
    tmp_path,
) -> None:
    relacao_dir = tmp_path / "servidores" / "relacao-servidores"
    relacao_dir.mkdir(parents=True)
    arquivo = relacao_dir / "relacao-servidores.json"
    arquivo.write_text(
        json.dumps(
            [
                {
                    "id": 501,
                    "Competencia": "01/2026",
                    "Nome": "Maria da Silva",
                    "CPF": "***345.678-**",
                    "Matricula": "90001-1",
                    "CargoFuncao": "Enfermeira",
                    "FundamentoLegal": " ",
                    "Lotacao": "UPA Central",
                    "SituacaoFuncional": "Em atividade",
                    "FormaContratacaoInvestidura": "Processo Seletivo",
                    "DataAdmissao": "02/01/2025",
                    "DataDesligamento": "",
                    "HorarioTrabalho": "12:00 as 18:00",
                    "CargaHoraria": "",
                    "LocalOrigemCedencia": "",
                    "LocalDestinoCedencia": "",
                    "OnusPagamentoCedencia": "",
                    "DataInicioCessao": "",
                    "DataFimCessao": "",
                    "RegimeAposentadoria": "Geral",
                    "VinculoEmpregaticio": "Temporario",
                },
                {
                    "id": 999,
                    "Competencia": "01/2026",
                    "Nome": "Maria da Silva",
                    "CPF": "***345.678-**",
                    "Matricula": "90001-1",
                    "CargoFuncao": "Enfermeira Responsavel",
                    "FundamentoLegal": " ",
                    "Lotacao": "Hospital Municipal",
                    "SituacaoFuncional": "Em atividade",
                    "FormaContratacaoInvestidura": "Processo Seletivo",
                    "DataAdmissao": "02/01/2025",
                    "DataDesligamento": "",
                    "HorarioTrabalho": "12:00 as 18:00",
                    "CargaHoraria": "",
                    "LocalOrigemCedencia": "",
                    "LocalDestinoCedencia": "",
                    "OnusPagamentoCedencia": "",
                    "DataInicioCessao": "",
                    "DataFimCessao": "",
                    "RegimeAposentadoria": "Geral",
                    "VinculoEmpregaticio": "Temporario",
                },
            ]
        ),
        encoding="utf-8",
    )

    session = _build_session()

    @contextmanager
    def fake_get_session():
        yield session

    monkeypatch.setattr(pipeline_module, "get_session", fake_get_session)

    pipeline = IngestionPipeline(data_dir=str(tmp_path))
    resultado = pipeline.run(tipos=["servidores"], ano=2026)

    assert resultado["servidores"].inseridos == 1
    assert resultado["servidores"].ignorados == 1
    assert session.query(Servidor).count() == 1

    servidor = session.query(Servidor).one()
    assert servidor.source_id == 501
    assert servidor.matricula == "90001-1"
    assert servidor.lotacao == "UPA Central"

    session.close()
