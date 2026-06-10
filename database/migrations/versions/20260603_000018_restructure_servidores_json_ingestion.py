"""restructure servidores json ingestion

Revision ID: 20260603_000018
Revises: 20260602_000017
Create Date: 2026-06-03 00:18:00
"""

from __future__ import annotations

from datetime import date

from alembic import op
import sqlalchemy as sa


revision = "20260603_000018"
down_revision = "20260602_000017"
branch_labels = None
depends_on = None

NAO_INFORMADO = "nao_informado"


def upgrade() -> None:
    bind = op.get_bind()
    snapshot_rows, payment_rows = _load_legacy_upgrade_state(bind)

    op.drop_table("folha_pagamentos")
    op.drop_table("folha_servidores")
    op.drop_table("servidores")

    _create_snapshot_folha_servidores_table()
    _create_json_servidores_table()
    _create_folha_pagamentos_table()

    current_metadata = sa.MetaData()
    snapshot_table = sa.Table(
        "folha_servidores",
        current_metadata,
        autoload_with=bind,
    )
    folha_pagamentos_table = sa.Table(
        "folha_pagamentos",
        current_metadata,
        autoload_with=bind,
    )

    snapshot_ids: dict[tuple[str, str, str, date], int] = {}
    for row in snapshot_rows:
        result = bind.execute(
            snapshot_table.insert().values(
                criado_em=row["criado_em"],
                atualizado_em=row["atualizado_em"],
                nome=row["nome"],
                cargo=row["cargo"],
                secretaria=row["secretaria"],
                salario_base=row["salario_base"],
                competencia_referencia=row["competencia_referencia"],
            )
        )
        snapshot_ids[row["key"]] = int(result.inserted_primary_key[0])

    for row in payment_rows:
        bind.execute(
            folha_pagamentos_table.insert().values(
                id=row["id"],
                criado_em=row["criado_em"],
                atualizado_em=row["atualizado_em"],
                competencia_ano=row["competencia_ano"],
                competencia_mes_num=row["competencia_mes_num"],
                competencia_mes_nome=row["competencia_mes_nome"],
                servidor_id=snapshot_ids[row["snapshot_key"]],
                lotacao_id=row["lotacao_id"],
                cargo_id=row["cargo_id"],
                salario_base=row["salario_base"],
                proventos=row["proventos"],
                vantagens=row["vantagens"],
                vencimentos_totais=row["vencimentos_totais"],
                descontos=row["descontos"],
                liquido=row["liquido"],
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    legacy_server_rows, legacy_folha_rows, payment_rows = _load_legacy_downgrade_state(bind)

    op.drop_table("folha_pagamentos")
    op.drop_table("folha_servidores")
    op.drop_table("servidores")

    _create_legacy_servidores_table()
    _create_legacy_folha_servidores_table()
    _create_folha_pagamentos_table()

    legacy_metadata = sa.MetaData()
    servidores_table = sa.Table(
        "servidores",
        legacy_metadata,
        autoload_with=bind,
    )
    folha_servidores_table = sa.Table(
        "folha_servidores",
        legacy_metadata,
        autoload_with=bind,
    )
    folha_pagamentos_table = sa.Table(
        "folha_pagamentos",
        legacy_metadata,
        autoload_with=bind,
    )

    latest_server_id_by_name: dict[str, int] = {}
    server_sort_keys: dict[str, tuple[date, int]] = {}
    for row in legacy_server_rows:
        result = bind.execute(
            servidores_table.insert().values(
                criado_em=row["criado_em"],
                atualizado_em=row["atualizado_em"],
                nome=row["nome"],
                cargo=row["cargo"],
                secretaria=row["secretaria"],
                salario_base=row["salario_base"],
                competencia_referencia=row["competencia_referencia"],
            )
        )
        inserted_id = int(result.inserted_primary_key[0])
        sort_key = (row["competencia_referencia"], inserted_id)
        nome = row["nome"]
        if nome not in server_sort_keys or sort_key > server_sort_keys[nome]:
            server_sort_keys[nome] = sort_key
            latest_server_id_by_name[nome] = inserted_id

    folha_ids_by_name: dict[str, int] = {}
    for row in legacy_folha_rows:
        result = bind.execute(
            folha_servidores_table.insert().values(
                criado_em=row["criado_em"],
                atualizado_em=row["atualizado_em"],
                nome=row["nome"],
                servidor_id=latest_server_id_by_name.get(row["nome"]),
            )
        )
        folha_ids_by_name[row["nome"]] = int(result.inserted_primary_key[0])

    for row in payment_rows:
        bind.execute(
            folha_pagamentos_table.insert().values(
                id=row["id"],
                criado_em=row["criado_em"],
                atualizado_em=row["atualizado_em"],
                competencia_ano=row["competencia_ano"],
                competencia_mes_num=row["competencia_mes_num"],
                competencia_mes_nome=row["competencia_mes_nome"],
                servidor_id=folha_ids_by_name[row["nome"]],
                lotacao_id=row["lotacao_id"],
                cargo_id=row["cargo_id"],
                salario_base=row["salario_base"],
                proventos=row["proventos"],
                vantagens=row["vantagens"],
                vencimentos_totais=row["vencimentos_totais"],
                descontos=row["descontos"],
                liquido=row["liquido"],
            )
        )


def _load_legacy_upgrade_state(
    bind,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    metadata = sa.MetaData()
    servidores = sa.Table("servidores", metadata, autoload_with=bind)
    folha_servidores = sa.Table("folha_servidores", metadata, autoload_with=bind)
    folha_pagamentos = sa.Table("folha_pagamentos", metadata, autoload_with=bind)
    folha_cargos = sa.Table("folha_cargos", metadata, autoload_with=bind)
    folha_lotacoes = sa.Table("folha_lotacoes", metadata, autoload_with=bind)

    snapshot_rows_by_key: dict[tuple[str, str, str, date], dict[str, object]] = {}
    for row in bind.execute(sa.select(servidores)).mappings():
        key = _snapshot_key(
            row["nome"],
            row["cargo"],
            row["secretaria"],
            row["competencia_referencia"],
        )
        snapshot_rows_by_key[key] = {
            "key": key,
            "criado_em": row["criado_em"],
            "atualizado_em": row["atualizado_em"],
            "nome": key[0],
            "cargo": key[1],
            "secretaria": key[2],
            "salario_base": row["salario_base"],
            "competencia_referencia": key[3],
        }

    folha_nomes = {
        row["id"]: _normalize_text(row["nome"])
        for row in bind.execute(sa.select(folha_servidores.c.id, folha_servidores.c.nome)).mappings()
    }
    cargos = {
        row["id"]: _normalize_text(row["nome"])
        for row in bind.execute(sa.select(folha_cargos.c.id, folha_cargos.c.nome)).mappings()
    }
    lotacoes = {
        row["id"]: _normalize_text(row["nome"])
        for row in bind.execute(sa.select(folha_lotacoes.c.id, folha_lotacoes.c.nome)).mappings()
    }

    payment_rows: list[dict[str, object]] = []
    for row in bind.execute(sa.select(folha_pagamentos)).mappings():
        nome = folha_nomes[row["servidor_id"]]
        cargo = cargos.get(row["cargo_id"]) or NAO_INFORMADO
        secretaria = lotacoes.get(row["lotacao_id"]) or NAO_INFORMADO
        competencia = date(
            int(row["competencia_ano"]),
            int(row["competencia_mes_num"]),
            1,
        )
        key = _snapshot_key(nome, cargo, secretaria, competencia)
        existente = snapshot_rows_by_key.get(key)
        if existente is None:
            snapshot_rows_by_key[key] = {
                "key": key,
                "criado_em": row["criado_em"],
                "atualizado_em": row["atualizado_em"],
                "nome": key[0],
                "cargo": key[1],
                "secretaria": key[2],
                "salario_base": row["salario_base"],
                "competencia_referencia": key[3],
            }
        elif existente["salario_base"] is None and row["salario_base"] is not None:
            existente["salario_base"] = row["salario_base"]

        payment_rows.append(
            {
                "id": row["id"],
                "criado_em": row["criado_em"],
                "atualizado_em": row["atualizado_em"],
                "competencia_ano": row["competencia_ano"],
                "competencia_mes_num": row["competencia_mes_num"],
                "competencia_mes_nome": row["competencia_mes_nome"],
                "snapshot_key": key,
                "lotacao_id": row["lotacao_id"],
                "cargo_id": row["cargo_id"],
                "salario_base": row["salario_base"],
                "proventos": row["proventos"],
                "vantagens": row["vantagens"],
                "vencimentos_totais": row["vencimentos_totais"],
                "descontos": row["descontos"],
                "liquido": row["liquido"],
            }
        )

    snapshot_rows = sorted(
        snapshot_rows_by_key.values(),
        key=lambda item: (
            item["competencia_referencia"],
            item["nome"],
            item["cargo"],
            item["secretaria"],
        ),
    )
    payment_rows.sort(key=lambda item: int(item["id"]))
    return snapshot_rows, payment_rows


def _load_legacy_downgrade_state(
    bind,
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    metadata = sa.MetaData()
    folha_servidores = sa.Table("folha_servidores", metadata, autoload_with=bind)
    folha_pagamentos = sa.Table("folha_pagamentos", metadata, autoload_with=bind)

    snapshot_rows = list(bind.execute(sa.select(folha_servidores)).mappings())
    payment_rows = list(bind.execute(sa.select(folha_pagamentos)).mappings())

    legacy_server_rows = [
        {
            "criado_em": row["criado_em"],
            "atualizado_em": row["atualizado_em"],
            "nome": row["nome"],
            "cargo": row["cargo"],
            "secretaria": row["secretaria"],
            "salario_base": row["salario_base"],
            "competencia_referencia": row["competencia_referencia"],
        }
        for row in snapshot_rows
    ]
    legacy_server_rows.sort(
        key=lambda item: (
            item["competencia_referencia"],
            item["nome"],
            item["cargo"],
            item["secretaria"],
        )
    )

    latest_snapshot_by_name: dict[str, dict[str, object]] = {}
    for row in snapshot_rows:
        nome = row["nome"]
        current = latest_snapshot_by_name.get(nome)
        sort_key = (row["competencia_referencia"], row["id"])
        if current is None or sort_key > (
            current["competencia_referencia"],
            current["id"],
        ):
            latest_snapshot_by_name[nome] = row

    legacy_folha_rows = [
        {
            "nome": nome,
            "criado_em": row["criado_em"],
            "atualizado_em": row["atualizado_em"],
        }
        for nome, row in sorted(latest_snapshot_by_name.items())
    ]

    snapshot_names_by_id = {row["id"]: row["nome"] for row in snapshot_rows}
    normalized_payment_rows = [
        {
            "id": row["id"],
            "criado_em": row["criado_em"],
            "atualizado_em": row["atualizado_em"],
            "competencia_ano": row["competencia_ano"],
            "competencia_mes_num": row["competencia_mes_num"],
            "competencia_mes_nome": row["competencia_mes_nome"],
            "nome": snapshot_names_by_id[row["servidor_id"]],
            "lotacao_id": row["lotacao_id"],
            "cargo_id": row["cargo_id"],
            "salario_base": row["salario_base"],
            "proventos": row["proventos"],
            "vantagens": row["vantagens"],
            "vencimentos_totais": row["vencimentos_totais"],
            "descontos": row["descontos"],
            "liquido": row["liquido"],
        }
        for row in payment_rows
    ]
    normalized_payment_rows.sort(key=lambda item: int(item["id"]))

    return legacy_server_rows, legacy_folha_rows, normalized_payment_rows


def _create_snapshot_folha_servidores_table() -> None:
    op.create_table(
        "folha_servidores",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("cargo", sa.String(length=255), nullable=False),
        sa.Column("secretaria", sa.String(length=255), nullable=False),
        sa.Column("salario_base", sa.Numeric(15, 2), nullable=True),
        sa.Column("competencia_referencia", sa.Date(), nullable=False),
        sa.UniqueConstraint(
            "nome",
            "cargo",
            "secretaria",
            "competencia_referencia",
            name="uq_folha_servidor_nome_cargo_sec_comp_ref",
        ),
    )
    op.create_index("ix_folha_servidores_nome", "folha_servidores", ["nome"])
    op.create_index("ix_folha_servidores_cargo", "folha_servidores", ["cargo"])
    op.create_index(
        "ix_folha_servidores_secretaria",
        "folha_servidores",
        ["secretaria"],
    )
    op.create_index(
        "ix_folha_servidores_secretaria_cargo_comp_ref",
        "folha_servidores",
        ["secretaria", "cargo", "competencia_referencia"],
    )


def _create_json_servidores_table() -> None:
    op.create_table(
        "servidores",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("competencia_referencia", sa.Date(), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("cpf", sa.String(length=20), nullable=True),
        sa.Column("matricula", sa.String(length=50), nullable=True),
        sa.Column("cargo_funcao", sa.String(length=255), nullable=True),
        sa.Column("fundamento_legal", sa.String(length=255), nullable=True),
        sa.Column("lotacao", sa.String(length=255), nullable=True),
        sa.Column("situacao_funcional", sa.String(length=120), nullable=True),
        sa.Column(
            "forma_contratacao_investidura",
            sa.String(length=120),
            nullable=True,
        ),
        sa.Column("data_admissao", sa.Date(), nullable=True),
        sa.Column("data_desligamento", sa.Date(), nullable=True),
        sa.Column("horario_trabalho", sa.String(length=80), nullable=True),
        sa.Column("carga_horaria", sa.String(length=40), nullable=True),
        sa.Column("local_origem_cedencia", sa.String(length=255), nullable=True),
        sa.Column("local_destino_cedencia", sa.String(length=255), nullable=True),
        sa.Column(
            "onus_pagamento_cedencia",
            sa.String(length=120),
            nullable=True,
        ),
        sa.Column("data_inicio_cessao", sa.Date(), nullable=True),
        sa.Column("data_fim_cessao", sa.Date(), nullable=True),
        sa.Column("regime_aposentadoria", sa.String(length=120), nullable=True),
        sa.Column("vinculo_empregaticio", sa.String(length=255), nullable=True),
        sa.UniqueConstraint("source_id", name="uq_servidores_source_id"),
    )
    op.create_index("ix_servidores_nome", "servidores", ["nome"])
    op.create_index("ix_servidores_matricula", "servidores", ["matricula"])
    op.create_index("ix_servidores_lotacao", "servidores", ["lotacao"])
    op.create_index(
        "ix_servidores_competencia_referencia",
        "servidores",
        ["competencia_referencia"],
    )


def _create_legacy_servidores_table() -> None:
    op.create_table(
        "servidores",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("cargo", sa.String(length=150), nullable=False),
        sa.Column("secretaria", sa.String(length=120), nullable=False),
        sa.Column("salario_base", sa.Numeric(15, 2), nullable=True),
        sa.Column("competencia_referencia", sa.Date(), nullable=False),
        sa.UniqueConstraint(
            "nome",
            "cargo",
            "secretaria",
            "competencia_referencia",
            name="uq_servidor_nome_cargo_sec_comp_ref",
        ),
    )
    op.create_index("ix_servidores_secretaria", "servidores", ["secretaria"])
    op.create_index("ix_servidores_cargo", "servidores", ["cargo"])
    op.create_index(
        "ix_servidores_competencia_referencia",
        "servidores",
        ["competencia_referencia"],
    )
    op.create_index(
        "ix_servidores_secretaria_cargo_comp_ref",
        "servidores",
        ["secretaria", "cargo", "competencia_referencia"],
    )


def _create_legacy_folha_servidores_table() -> None:
    op.create_table(
        "folha_servidores",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column(
            "servidor_id",
            sa.Integer(),
            sa.ForeignKey("servidores.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.UniqueConstraint("nome", name="uq_folha_servidor_nome"),
    )
    op.create_index("ix_folha_servidores_nome", "folha_servidores", ["nome"])
    op.create_index(
        "ix_folha_servidores_servidor_id",
        "folha_servidores",
        ["servidor_id"],
    )


def _create_folha_pagamentos_table() -> None:
    op.create_table(
        "folha_pagamentos",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("competencia_ano", sa.Integer(), nullable=False),
        sa.Column("competencia_mes_num", sa.Integer(), nullable=False),
        sa.Column("competencia_mes_nome", sa.String(length=20), nullable=False),
        sa.Column(
            "servidor_id",
            sa.Integer(),
            sa.ForeignKey("folha_servidores.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "lotacao_id",
            sa.Integer(),
            sa.ForeignKey("folha_lotacoes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "cargo_id",
            sa.Integer(),
            sa.ForeignKey("folha_cargos.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("salario_base", sa.Numeric(15, 2), nullable=True),
        sa.Column("proventos", sa.Numeric(15, 2), nullable=True),
        sa.Column("vantagens", sa.Numeric(15, 2), nullable=True),
        sa.Column("vencimentos_totais", sa.Numeric(15, 2), nullable=True),
        sa.Column("descontos", sa.Numeric(15, 2), nullable=True),
        sa.Column("liquido", sa.Numeric(15, 2), nullable=True),
        sa.UniqueConstraint(
            "competencia_ano",
            "competencia_mes_nome",
            "servidor_id",
            "cargo_id",
            "lotacao_id",
            name="uq_folha_comp_servidor_cargo_lotacao",
        ),
    )
    op.create_index(
        "ix_folha_pagamentos_competencia_ano",
        "folha_pagamentos",
        ["competencia_ano"],
    )
    op.create_index(
        "ix_folha_pagamentos_competencia_mes_num",
        "folha_pagamentos",
        ["competencia_mes_num"],
    )
    op.create_index(
        "ix_folha_pagamentos_competencia_mes_nome",
        "folha_pagamentos",
        ["competencia_mes_nome"],
    )
    op.create_index("ix_folha_pagamentos_servidor_id", "folha_pagamentos", ["servidor_id"])
    op.create_index("ix_folha_pagamentos_lotacao_id", "folha_pagamentos", ["lotacao_id"])
    op.create_index("ix_folha_pagamentos_cargo_id", "folha_pagamentos", ["cargo_id"])
    op.create_index(
        "ix_folha_pagamentos_ano_mes_lotacao",
        "folha_pagamentos",
        ["competencia_ano", "competencia_mes_num", "lotacao_id"],
    )
    op.create_index(
        "ix_folha_pagamentos_ano_mes_servidor",
        "folha_pagamentos",
        ["competencia_ano", "competencia_mes_num", "servidor_id"],
    )


def _snapshot_key(
    nome: object,
    cargo: object,
    secretaria: object,
    competencia_referencia: object,
) -> tuple[str, str, str, date]:
    nome_normalizado = _normalize_text(nome) or ""
    cargo_normalizado = _normalize_text(cargo) or NAO_INFORMADO
    secretaria_normalizada = _normalize_text(secretaria) or NAO_INFORMADO
    if not isinstance(competencia_referencia, date):
        raise ValueError("competencia_referencia deve ser uma data")
    return (
        nome_normalizado,
        cargo_normalizado,
        secretaria_normalizada,
        competencia_referencia,
    )


def _normalize_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return str(value).strip() or None
