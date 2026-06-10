"""File discovery helpers for each tipo de importacao."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class _TipoDiscoverySpec:
    """Onde e com quais padroes procurar os arquivos de um tipo de importacao.

    `fallback` e tentado apenas quando os padroes primarios nao encontram nada
    (ex.: contratos antigos publicados sob o nome de licitacoes).
    """

    subdir: str | None
    patterns: tuple[str, ...]
    fallback: tuple[str | None, tuple[str, ...]] | None = None


_DISCOVERY_SPECS: dict[str, _TipoDiscoverySpec] = {
    "receitas": _TipoDiscoverySpec("receitas", ("*arrecadacao*.xml", "*lancamento*.xml")),
    "folha_pagamento": _TipoDiscoverySpec("servidores", ("*folha-pagamento*.xml",)),
    "planejamentos": _TipoDiscoverySpec(
        "despesas",
        ("*planejamento*.xml",),
        fallback=(None, ("*planejamento*.xml",)),
    ),
    "despesas": _TipoDiscoverySpec(
        "despesas",
        (
            "*empenhos*.xml",
            "*documentos-extras*.xml",
            "*restos-a-pagar*.xml",
            "*despesas-por-funcao*.csv",
            "*diarias*.csv",
            "*passagens*.csv",
        ),
    ),
    "patrimonios": _TipoDiscoverySpec("administracao", ("*patrimonio*.xml",)),
    "estoques": _TipoDiscoverySpec("administracao", ("estoque-*.xml",)),
    "quadro_pessoal": _TipoDiscoverySpec("servidores", ("*quadro-pessoal*.xml",)),
    "eleitos": _TipoDiscoverySpec("camara", ("*eleitos*.xml",)),
    "transferencias_financeiras": _TipoDiscoverySpec(
        "transferencias-financeiras",
        ("recebimentos-*.xml", "emendas-parlamentares-*.csv"),
    ),
    "servidores": _TipoDiscoverySpec("servidores", ("relacao-servidores*.json",)),
    "contratos": _TipoDiscoverySpec(
        "administracao",
        ("*contrato*.xml",),
        fallback=("administracao", ("*licitacoes*.xml",)),
    ),
}

# Tipos cujos arquivos nao carregam o ano no nome e por isso nao sao filtrados.
_YEAR_FILTER_EXEMPT_TIPOS = frozenset({"eleitos", "servidores"})


def _collect(data_dir: Path, subdir: str | None, patterns: tuple[str, ...]) -> list[Path]:
    base = data_dir / subdir if subdir is not None else data_dir
    arquivos: list[Path] = []
    for pattern in patterns:
        arquivos.extend(sorted(base.rglob(pattern)))
    return arquivos


def discover_files_for_tipo(
    data_dir: Path,
    tipo: str,
    ano: int | None,
) -> list[Path]:
    """Discover input files for one tipo de importacao and optional year."""

    spec = _DISCOVERY_SPECS.get(tipo)
    if spec is None:
        arquivos = _collect(data_dir, None, (f"*{tipo}*.xml",))
    else:
        arquivos = _collect(data_dir, spec.subdir, spec.patterns)
        if not arquivos and spec.fallback is not None:
            fallback_subdir, fallback_patterns = spec.fallback
            arquivos = _collect(data_dir, fallback_subdir, fallback_patterns)

    if ano is None or tipo in _YEAR_FILTER_EXEMPT_TIPOS:
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
