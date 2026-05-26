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
from sqlalchemy import MetaData, Table as SQLATable

from database.models import (
    Contrato,
    DespesaDocumento,
    DespesaDocumentoComprobatorio,
    DespesaDocumentoItem,
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
    VencedorLicitacao,
)
from database.session import engine, get_session
from ingestion.pipeline import IngestionPipeline

app = typer.Typer()
db_app = typer.Typer()
app.add_typer(db_app, name="db")
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
            "despesa_documento_itens",
            str(session.query(DespesaDocumentoItem).count()),
        )
        tabela.add_row(
            "despesa_documentos_comprobatorios",
            str(session.query(DespesaDocumentoComprobatorio).count()),
        )
        tabela.add_row("patrimonios", str(session.query(Patrimonio).count()))
        tabela.add_row("quadro_pessoal", str(session.query(QuadroPessoal).count()))
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
            "servidores|planejamentos|despesas|patrimonios|quadro_pessoal"
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


if __name__ == "__main__":
    app()
