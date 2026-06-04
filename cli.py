"""CLI principal do Observatório Arcos."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from loguru import logger
from rich.console import Console
from rich.progress import Progress
from rich.table import Table as RichTable
from sqlalchemy import MetaData, Table as SQLATable, func

from agents.rag.indexing import KnowledgeIndexError, build_knowledge_index
from agents.rag.indexing import get_knowledge_index_status
from database.models import (
    Contrato,
    DespesaDocumento,
    DespesaDocumentoComprobatorio,
    DespesaDocumentoItem,
    DespesaPorFuncao,
    EmendaParlamentar,
    Eleito,
    Fornecedor,
    FolhaCargo,
    FolhaLotacao,
    FolhaPagamentoRegistro,
    FolhaServidor,
    FrotaDespesa,
    FrotaVeiculo,
    InstrumentoContratual,
    Licitacao,
    MateriaInstrumento,
    Patrimonio,
    PlanejamentoDespesa,
    QuadroPessoal,
    ReceitaArrecadacao,
    ReceitaLancamento,
    ReceitaNatureza,
    Servidor,
    TransferenciaFinanceiraMovimento,
    VencedorLicitacao,
)
from database.session import engine, get_session
from ingestion.pipeline import IngestionPipeline

app = typer.Typer()
db_app = typer.Typer()
rag_app = typer.Typer()
app.add_typer(db_app, name="db")
app.add_typer(rag_app, name="rag")
console = Console()


def _configure_import_logging(verbose: bool) -> None:
    """Configura verbosidade do loguru para o fluxo de importacao."""

    logger.remove()
    logger.add(sys.stderr, level="INFO" if verbose else "ERROR")


def _recriar_base_importacao() -> None:
    """Recria o banco SQLite e reaplica as migrations antes da importação."""
    db_path = engine.url.database
    engine.dispose()

    if engine.url.get_backend_name() == "sqlite" and db_path:
        arquivo_banco = Path(db_path)
        arquivos_relacionados = [
            arquivo_banco,
            Path(f"{arquivo_banco}-shm"),
            Path(f"{arquivo_banco}-wal"),
        ]
        for arquivo in arquivos_relacionados:
            if arquivo.exists():
                arquivo.unlink()

    subprocess.run(["alembic", "upgrade", "head"], check=True)


def _contagem_despesas_por_tipo(session) -> dict[str, int]:
    """Retorna subtotal de documentos de despesa agrupado por `tipo_origem`."""

    return {
        tipo: quantidade
        for tipo, quantidade in session.query(
            DespesaDocumento.tipo_origem,
            func.count(DespesaDocumento.id),
        )
        .group_by(DespesaDocumento.tipo_origem)
        .all()
    }


@db_app.command("init")
def db_init() -> None:
    """Executa migrations do Alembic."""
    subprocess.run(["alembic", "upgrade", "head"], check=True)
    console.print(
        "[green]Banco inicializado e migrations aplicadas com sucesso.[/green]"
    )


@db_app.command("status")
def db_status() -> None:
    """Exibe contagem de registros por tabela e revisão atual."""
    tabela = RichTable(title="Status do Banco")
    tabela.add_column("Tabela")
    tabela.add_column("Registros", justify="right")

    with get_session() as session:
        tabela.add_row("contratos", str(session.query(Contrato).count()))
        tabela.add_row("licitacoes", str(session.query(Licitacao).count()))
        tabela.add_row(
            "vencedores_licitacao", str(session.query(VencedorLicitacao).count())
        )
        tabela.add_row(
            "instrumentos_contratuais",
            str(session.query(InstrumentoContratual).count()),
        )
        tabela.add_row(
            "materias_instrumento", str(session.query(MateriaInstrumento).count())
        )
        tabela.add_row("fornecedores", str(session.query(Fornecedor).count()))
        tabela.add_row("frota_veiculos", str(session.query(FrotaVeiculo).count()))
        tabela.add_row("frota_despesas", str(session.query(FrotaDespesa).count()))
        tabela.add_row("receita_naturezas", str(session.query(ReceitaNatureza).count()))
        tabela.add_row(
            "receita_arrecadacoes", str(session.query(ReceitaArrecadacao).count())
        )
        tabela.add_row(
            "receita_lancamentos", str(session.query(ReceitaLancamento).count())
        )
        tabela.add_row(
            "transferencias_financeiras_movimentos",
            str(session.query(TransferenciaFinanceiraMovimento).count()),
        )
        tabela.add_row(
            "emendas_parlamentares",
            str(session.query(EmendaParlamentar).count()),
        )
        tabela.add_row("folha_servidores", str(session.query(FolhaServidor).count()))
        tabela.add_row("folha_lotacoes", str(session.query(FolhaLotacao).count()))
        tabela.add_row("folha_cargos", str(session.query(FolhaCargo).count()))
        tabela.add_row(
            "folha_pagamentos", str(session.query(FolhaPagamentoRegistro).count())
        )
        tabela.add_row("servidores", str(session.query(Servidor).count()))
        tabela.add_row(
            "planejamento_despesas",
            str(session.query(PlanejamentoDespesa).count()),
        )
        tabela.add_row(
            "despesa_documentos", str(session.query(DespesaDocumento).count())
        )
        tabela.add_row(
            "despesas_por_funcao",
            str(session.query(DespesaPorFuncao).count()),
        )
        for tipo, quantidade in sorted(_contagem_despesas_por_tipo(session).items()):
            tabela.add_row(f"despesa_documentos:{tipo}", str(quantidade))
        tabela.add_row(
            "despesa_documento_itens",
            str(session.query(DespesaDocumentoItem).count()),
        )
        tabela.add_row(
            "despesa_documentos_comprobatorios",
            str(session.query(DespesaDocumentoComprobatorio).count()),
        )
        tabela.add_row("patrimonios", str(session.query(Patrimonio).count()))
        tabela.add_row("quadro_pessoal", str(session.query(QuadroPessoal).count()))
        tabela.add_row("eleitos", str(session.query(Eleito).count()))
        metadata = MetaData()
        alembic_version = SQLATable(
            "alembic_version", metadata, autoload_with=session.bind
        )
        revisao = session.execute(alembic_version.select()).scalar_one_or_none()

    console.print(tabela)
    console.print(f"Ultima migration aplicada: [bold]{revisao or 'nenhuma'}[/bold]")


@app.command("importar")
def importar(
    tipo: Optional[str] = typer.Option(
        default=None,
        help=(
            "Tipo: contratos|licitacoes|frotas|receitas|folha_pagamento|"
            "servidores|planejamentos|despesas|patrimonios|quadro_pessoal|"
            "eleitos|transferencias_financeiras"
        ),
    ),
    ano: Optional[int] = typer.Option(
        default=None, help="Filtra por ano no nome do arquivo"
    ),
    force: bool = typer.Option(default=False, help="Apaga dados antes de reimportar"),
    verbose: bool = typer.Option(
        default=False,
        help="Exibe logs detalhados da importacao",
    ),
) -> None:
    """Recria a base e importa XMLs para o banco com relatório consolidado."""
    tipos = [tipo] if tipo else None
    pipeline = IngestionPipeline(data_dir="data/xml")
    _configure_import_logging(verbose=verbose)

    if force:
        console.print(
            "[yellow]A opcao --force agora e redundante: a base inteira eh recriada antes de cada importacao.[/yellow]"
        )

    _recriar_base_importacao()
    console.print("[green]Base recriada com sucesso. Iniciando importacao...[/green]")

    tipos_resolvidos = tipos or [
        "contratos",
        "licitacoes",
        "frotas",
        "receitas",
        "folha_pagamento",
        "servidores",
        "planejamentos",
        "despesas",
        "patrimonios",
        "quadro_pessoal",
        "eleitos",
        "transferencias_financeiras",
    ]
    total_arquivos = sum(
        len(pipeline._arquivos_por_tipo(t, ano)) for t in tipos_resolvidos
    )

    with Progress() as progress:
        task = progress.add_task("Importando arquivos...", total=max(total_arquivos, 1))
        relatorio = pipeline.run(
            tipos=tipos,
            ano=ano,
            on_file_processed=lambda _tipo, _arquivo: progress.advance(task, 1),
        )

    tabela = RichTable(title="Resumo da Importação")
    tabela.add_column("Tipo")
    tabela.add_column("Inseridos", justify="right")
    tabela.add_column("Atualizados", justify="right")
    tabela.add_column("Ignorados", justify="right")
    tabela.add_column("Erros", justify="right")

    total_i = total_a = total_ig = total_e = 0
    for chave, resultado in relatorio.items():
        tabela.add_row(
            chave,
            str(resultado.inseridos),
            str(resultado.atualizados),
            str(resultado.ignorados),
            str(resultado.erros),
        )
        total_i += resultado.inseridos
        total_a += resultado.atualizados
        total_ig += resultado.ignorados
        total_e += resultado.erros

    console.print(tabela)
    console.print(
        f"Total -> inseridos={total_i}, atualizados={total_a}, ignorados={total_ig}, erros={total_e}",
        style="bold green" if total_e == 0 else "bold red",
    )

    if "despesas" in relatorio:
        with get_session() as session:
            subtotal = _contagem_despesas_por_tipo(session)
        if subtotal:
            detalhes = ", ".join(
                f"{tipo}={quantidade}" for tipo, quantidade in sorted(subtotal.items())
            )
            console.print(f"Despesas por tipo -> {detalhes}")


@rag_app.command("index")
def rag_index(
    rebuild: bool = typer.Option(
        default=False,
        help="Recria o indice vetorial do zero, substituindo o persistido atual.",
    ),
) -> None:
    """Gera ou reconstrói o indice local de conhecimento markdown."""

    try:
        status = build_knowledge_index(rebuild=rebuild)
    except KnowledgeIndexError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    color = "green" if status.state == "ready" else "yellow"
    console.print(f"[{color}]{status.message}[/{color}]")
    console.print(
        f"Chunks indexados: {status.total_chunks} | documentos: {status.document_count}"
    )
    console.print(f"Persistido em: [bold]{status.persist_directory}[/bold]")


@rag_app.command("status")
def rag_status() -> None:
    """Exibe o estado do indice local de conhecimento."""

    status = get_knowledge_index_status()
    color = {
        "ready": "green",
        "stale": "yellow",
        "missing": "yellow",
        "empty": "yellow",
        "unavailable": "red",
    }.get(status.state, "white")

    console.print(f"[{color}]Estado do indice RAG: {status.state}[/{color}]")
    console.print(status.message)
    console.print(f"Collection: [bold]{status.collection_name}[/bold]")
    console.print(f"Manifesto: [bold]{status.manifest_path}[/bold]")
    console.print(f"Persistência: [bold]{status.persist_directory}[/bold]")
    console.print(
        f"Chunks indexados: {status.total_chunks} | documentos: {status.document_count}"
    )

    if status.changed_files:
        console.print(f"Arquivos alterados: {', '.join(status.changed_files)}")
    if status.missing_files:
        console.print(f"Arquivos ausentes: {', '.join(status.missing_files)}")


if __name__ == "__main__":
    app()
