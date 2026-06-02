from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import subprocess


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_migration_de_transferencias_define_defaults_de_timestamp(tmp_path) -> None:
    db_path = tmp_path / "migrations-transferencias.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path}"

    subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=PROJECT_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO transferencias_financeiras_movimentos (
            arquivo_origem,
            sequencia_origem,
            exercicio,
            identificacao,
            unidade_gestora_concessora,
            unidade_gestora_recebedora,
            finalidade,
            fonte_recurso,
            detalhamento_fonte,
            programacao_inicial,
            data_movimento,
            tipo_movimento,
            valor_movimento
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "recebimentos-2026.xml",
            1,
            2026,
            "27",
            "PREFEITURA MUNICIPAL",
            "CAMARA MUNICIPAL",
            "Transferencia para Camara",
            "Recursos nao Vinculados de Impostos",
            "Nao se aplica",
            552500.00,
            "2026-01-16",
            "Recebimento",
            552500.00,
        ),
    )
    conn.execute(
        """
        INSERT INTO emendas_parlamentares (
            arquivo_origem,
            sequencia_origem,
            exercicio_consulta,
            ano,
            ano_numero,
            autor,
            objeto,
            tipo_emenda,
            funcao,
            valor
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "emendas-parlamentares-2026.csv",
            1,
            2026,
            2026,
            "2026/39600006",
            "Dr Frederico",
            "Incremento MAC",
            "Emenda Individual",
            "Saude",
            100000.00,
        ),
    )
    conn.commit()

    movimento = conn.execute(
        """
        SELECT criado_em, atualizado_em
        FROM transferencias_financeiras_movimentos
        WHERE arquivo_origem = 'recebimentos-2026.xml'
        """
    ).fetchone()
    emenda = conn.execute(
        """
        SELECT criado_em, atualizado_em
        FROM emendas_parlamentares
        WHERE arquivo_origem = 'emendas-parlamentares-2026.csv'
        """
    ).fetchone()

    assert movimento is not None
    assert movimento[0] is not None
    assert movimento[1] is not None
    assert emenda is not None
    assert emenda[0] is not None
    assert emenda[1] is not None

    conn.close()
