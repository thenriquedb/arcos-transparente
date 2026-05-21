"""CLI principal do Observatório Arcos."""

from __future__ import annotations

import subprocess
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress
from rich.prompt import Confirm
from rich.table import Table as RichTable
from sqlalchemy import MetaData, Table as SQLATable, inspect

from database.models import (
    Contrato,
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


@db_app.command("init")
def db_init() -> None:
    """Executa migrations do Alembic."""
    subprocess.run(["alembic", "upgrade", "head"], check=True)
    console.print("[green]Banco inicializado e migrations aplicadas com sucesso.[/green]")


@db_app.command("status")
def db_status() -> None:
    """Exibe contagem de registros por tabela e revisão atual."""
    tabela = RichTable(title="Status do Banco")
    tabela.add_column("Tabela")
    tabela.add_column("Registros", justify="right")

    with get_session() as session:
        tabela.add_row("contratos", str(session.query(Contrato).count()))
        tabela.add_row("licitacoes", str(session.query(Licitacao).count()))
        tabela.add_row("vencedores_licitacao", str(session.query(VencedorLicitacao).count()))
        tabela.add_row("instrumentos_contratuais", str(session.query(InstrumentoContratual).count()))
        tabela.add_row("materias_instrumento", str(session.query(MateriaInstrumento).count()))
        tabela.add_row("fornecedores", str(session.query(Fornecedor).count()))
        tabela.add_row("frota_veiculos", str(session.query(FrotaVeiculo).count()))
        tabela.add_row("frota_despesas", str(session.query(FrotaDespesa).count()))
        tabela.add_row("receita_naturezas", str(session.query(ReceitaNatureza).count()))
        tabela.add_row("receita_arrecadacoes", str(session.query(ReceitaArrecadacao).count()))
        tabela.add_row("receita_lancamentos", str(session.query(ReceitaLancamento).count()))
        tabela.add_row("folha_servidores", str(session.query(FolhaServidor).count()))
        tabela.add_row("folha_lotacoes", str(session.query(FolhaLotacao).count()))
        tabela.add_row("folha_cargos", str(session.query(FolhaCargo).count()))
        tabela.add_row("folha_pagamentos", str(session.query(FolhaPagamentoRegistro).count()))
        tabela.add_row("servidores", str(session.query(Servidor).count()))
        metadata = MetaData()
        alembic_version = SQLATable("alembic_version", metadata, autoload_with=session.bind)
        revisao = session.execute(alembic_version.select()).scalar_one_or_none()

    console.print(tabela)
    console.print(f"Ultima migration aplicada: [bold]{revisao or 'nenhuma'}[/bold]")


@app.command("importar")
def importar(
    tipo: Optional[str] = typer.Option(default=None, help="Tipo: contratos|licitacoes|frotas|receitas|folha_pagamento|servidores"),
    ano: Optional[int] = typer.Option(default=None, help="Filtra por ano no nome do arquivo"),
    force: bool = typer.Option(default=False, help="Apaga dados antes de reimportar"),
) -> None:
    """Importa XMLs para o banco com relatório consolidado."""
    tipos = [tipo] if tipo else None
    pipeline = IngestionPipeline(data_dir="data/xml")

    if force:
        confirmar = Confirm.ask("Isso apagará dados existentes. Deseja continuar?", default=False)
        if not confirmar:
            console.print("[yellow]Operação cancelada.[/yellow]")
            raise typer.Exit(code=1)
        with get_session() as session:
            try:
                with session.begin():
                    existing_tables = set(inspect(session.bind).get_table_names())
                    ordered_models = [
                        Contrato,
                        MateriaInstrumento,
                        InstrumentoContratual,
                        VencedorLicitacao,
                        Fornecedor,
                        FrotaDespesa,
                        FrotaVeiculo,
                        ReceitaArrecadacao,
                        ReceitaLancamento,
                        ReceitaNatureza,
                        FolhaPagamentoRegistro,
                        FolhaCargo,
                        FolhaLotacao,
                        FolhaServidor,
                        Licitacao,
                        Servidor,
                    ]
                    for model in ordered_models:
                        if model.__tablename__ in existing_tables:
                            session.query(model).delete()
            except Exception:
                session.rollback()
                raise

    tipos_resolvidos = tipos or ["contratos", "licitacoes", "frotas", "receitas", "folha_pagamento", "servidores"]
    total_arquivos = sum(len(pipeline._arquivos_por_tipo(t, ano)) for t in tipos_resolvidos)

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
        tabela.add_row(chave, str(resultado.inseridos), str(resultado.atualizados), str(resultado.ignorados), str(resultado.erros))
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
