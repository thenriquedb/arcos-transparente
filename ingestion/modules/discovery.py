"""File discovery helpers for each tipo de importacao."""

from __future__ import annotations

from pathlib import Path


def discover_files_for_tipo(
    data_dir: Path,
    tipo: str,
    ano: int | None,
) -> list[Path]:
    """Discover input files for one tipo de importacao and optional year."""

    administracao_path = data_dir / "administracao"
    despesas_path = data_dir / "despesas"
    receitas_path = data_dir / "receitas"
    servidores_path = data_dir / "servidores"
    camara_path = data_dir / "camara"
    transferencias_path = data_dir / "transferencias-financeiras"

    if tipo == "receitas":
        arquivos = sorted(receitas_path.rglob("*arrecadacao*.xml")) + sorted(
            receitas_path.rglob("*lancamento*.xml")
        )
    elif tipo == "folha_pagamento":
        arquivos = sorted(servidores_path.rglob("*folha-pagamento*.xml"))
    elif tipo == "planejamentos":
        arquivos = sorted(despesas_path.rglob("*planejamento*.xml"))
        if not arquivos:
            arquivos = sorted(data_dir.rglob("*planejamento*.xml"))
    elif tipo == "despesas":
        arquivos = (
            sorted(despesas_path.rglob("*empenhos*.xml"))
            + sorted(despesas_path.rglob("*documentos-extras*.xml"))
            + sorted(despesas_path.rglob("*restos-a-pagar*.xml"))
            + sorted(despesas_path.rglob("*despesas-por-funcao*.csv"))
            + sorted(despesas_path.rglob("*diarias*.csv"))
            + sorted(despesas_path.rglob("*passagens*.csv"))
        )
    elif tipo == "patrimonios":
        arquivos = sorted(administracao_path.rglob("*patrimonio*.xml"))
    elif tipo == "estoques":
        arquivos = sorted(administracao_path.rglob("estoque-*.xml"))
    elif tipo == "quadro_pessoal":
        arquivos = sorted(servidores_path.rglob("*quadro-pessoal*.xml"))
    elif tipo == "eleitos":
        arquivos = sorted(camara_path.rglob("*eleitos*.xml"))
    elif tipo == "transferencias_financeiras":
        arquivos = sorted(transferencias_path.rglob("recebimentos-*.xml")) + sorted(
            transferencias_path.rglob("emendas-parlamentares-*.csv")
        )
    elif tipo == "servidores":
        arquivos = sorted(servidores_path.rglob("relacao-servidores*.json"))
    elif tipo == "contratos":
        arquivos = sorted(administracao_path.rglob("*contrato*.xml"))
        if not arquivos:
            arquivos = sorted(administracao_path.rglob("*licitacoes*.xml"))
    else:
        arquivos = sorted(data_dir.rglob(f"*{tipo}*.xml"))

    if ano is None or tipo in {"eleitos", "servidores"}:
        return arquivos

    marker = str(ano)
    return [arquivo for arquivo in arquivos if marker in arquivo.name]


def discover_contratos_files(data_dir: Path, ano: int | None) -> list[Path]:
    return discover_files_for_tipo(data_dir, "contratos", ano)


def discover_despesas_files(data_dir: Path, ano: int | None) -> list[Path]:
    return discover_files_for_tipo(data_dir, "despesas", ano)


def discover_eleitos_files(data_dir: Path, ano: int | None) -> list[Path]:
    return discover_files_for_tipo(data_dir, "eleitos", ano)


def discover_estoques_files(data_dir: Path, ano: int | None) -> list[Path]:
    return discover_files_for_tipo(data_dir, "estoques", ano)


def discover_folha_pagamento_files(data_dir: Path, ano: int | None) -> list[Path]:
    return discover_files_for_tipo(data_dir, "folha_pagamento", ano)


def discover_frotas_files(data_dir: Path, ano: int | None) -> list[Path]:
    return discover_files_for_tipo(data_dir, "frotas", ano)


def discover_licitacoes_files(data_dir: Path, ano: int | None) -> list[Path]:
    return discover_files_for_tipo(data_dir, "licitacoes", ano)


def discover_patrimonios_files(data_dir: Path, ano: int | None) -> list[Path]:
    return discover_files_for_tipo(data_dir, "patrimonios", ano)


def discover_planejamentos_files(data_dir: Path, ano: int | None) -> list[Path]:
    return discover_files_for_tipo(data_dir, "planejamentos", ano)


def discover_quadro_pessoal_files(data_dir: Path, ano: int | None) -> list[Path]:
    return discover_files_for_tipo(data_dir, "quadro_pessoal", ano)


def discover_receitas_files(data_dir: Path, ano: int | None) -> list[Path]:
    return discover_files_for_tipo(data_dir, "receitas", ano)


def discover_servidores_files(data_dir: Path, ano: int | None) -> list[Path]:
    return discover_files_for_tipo(data_dir, "servidores", ano)


def discover_transferencias_financeiras_files(
    data_dir: Path,
    ano: int | None,
) -> list[Path]:
    return discover_files_for_tipo(data_dir, "transferencias_financeiras", ano)
