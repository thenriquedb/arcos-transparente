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


def test_migration_reestrutura_snapshot_de_servidores_em_folha(tmp_path) -> None:
    db_path = tmp_path / "migrations-servidores.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path}"

    subprocess.run(
        ["alembic", "upgrade", "20260602_000017"],
        cwd=PROJECT_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO servidores (
            nome,
            cargo,
            secretaria,
            salario_base,
            competencia_referencia
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
            "Maria da Silva",
            "Enfermeira",
            "Secretaria de Saude",
            2500.00,
            "2025-01-01",
        ),
    )
    servidor_janeiro_id = cursor.lastrowid
    cursor.execute(
        """
        INSERT INTO servidores (
            nome,
            cargo,
            secretaria,
            salario_base,
            competencia_referencia
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
            "Maria da Silva",
            "Enfermeira",
            "Secretaria de Saude",
            2600.00,
            "2025-02-01",
        ),
    )

    cursor.execute(
        """
        INSERT INTO folha_servidores (nome, servidor_id)
        VALUES (?, ?)
        """,
        ("Maria da Silva", servidor_janeiro_id),
    )
    folha_servidor_legacy_id = cursor.lastrowid

    cursor.execute("INSERT INTO folha_cargos (nome) VALUES (?)", ("Enfermeira",))
    cargo_id = cursor.lastrowid
    cursor.execute(
        "INSERT INTO folha_lotacoes (nome) VALUES (?)",
        ("Secretaria de Saude",),
    )
    lotacao_id = cursor.lastrowid

    cursor.execute(
        """
        INSERT INTO folha_pagamentos (
            competencia_ano,
            competencia_mes_num,
            competencia_mes_nome,
            servidor_id,
            lotacao_id,
            cargo_id,
            salario_base,
            proventos,
            vantagens,
            vencimentos_totais,
            descontos,
            liquido
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            2025,
            1,
            "Janeiro",
            folha_servidor_legacy_id,
            lotacao_id,
            cargo_id,
            2500.00,
            3000.00,
            150.00,
            3150.00,
            350.00,
            2800.00,
        ),
    )
    cursor.execute(
        """
        INSERT INTO folha_pagamentos (
            competencia_ano,
            competencia_mes_num,
            competencia_mes_nome,
            servidor_id,
            lotacao_id,
            cargo_id,
            salario_base,
            proventos,
            vantagens,
            vencimentos_totais,
            descontos,
            liquido
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            2025,
            2,
            "Fevereiro",
            folha_servidor_legacy_id,
            lotacao_id,
            cargo_id,
            2600.00,
            3100.00,
            200.00,
            3300.00,
            400.00,
            2900.00,
        ),
    )
    conn.commit()
    conn.close()

    subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=PROJECT_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    conn = sqlite3.connect(db_path)
    colunas_folha = {
        row[1] for row in conn.execute("PRAGMA table_info('folha_servidores')")
    }
    assert "servidor_id" not in colunas_folha
    assert {
        "cargo",
        "secretaria",
        "salario_base",
        "competencia_referencia",
    } <= colunas_folha

    colunas_servidores = {
        row[1] for row in conn.execute("PRAGMA table_info('servidores')")
    }
    assert "source_id" in colunas_servidores
    assert "cargo" not in colunas_servidores

    snapshots = conn.execute(
        """
        SELECT nome, cargo, secretaria, salario_base, competencia_referencia
        FROM folha_servidores
        ORDER BY competencia_referencia
        """
    ).fetchall()
    assert snapshots == [
        (
            "Maria da Silva",
            "Enfermeira",
            "Secretaria de Saude",
            2500,
            "2025-01-01",
        ),
        (
            "Maria da Silva",
            "Enfermeira",
            "Secretaria de Saude",
            2600,
            "2025-02-01",
        ),
    ]

    pagamentos = conn.execute(
        """
        SELECT fp.competencia_mes_num, fs.competencia_referencia, fs.salario_base
        FROM folha_pagamentos fp
        JOIN folha_servidores fs ON fs.id = fp.servidor_id
        ORDER BY fp.competencia_mes_num
        """
    ).fetchall()
    assert pagamentos == [
        (1, "2025-01-01", 2500),
        (2, "2025-02-01", 2600),
    ]

    assert conn.execute("SELECT COUNT(*) FROM servidores").fetchone()[0] == 0
    conn.close()
