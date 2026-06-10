"""folha competencia em colunas separadas

Revision ID: 20260521_000006
Revises: 20260521_000005
Create Date: 2026-05-21 20:40:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260521_000006"
down_revision = "20260521_000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_folha_pagamentos_cargo_id", table_name="folha_pagamentos")
    op.drop_index("ix_folha_pagamentos_lotacao_id", table_name="folha_pagamentos")
    op.drop_index("ix_folha_pagamentos_servidor_id", table_name="folha_pagamentos")
    op.drop_index("ix_folha_pagamentos_competencia", table_name="folha_pagamentos")
    op.drop_table("folha_pagamentos")

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
    op.create_index("ix_folha_pagamentos_competencia_ano", "folha_pagamentos", ["competencia_ano"])
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


def downgrade() -> None:
    op.drop_index("ix_folha_pagamentos_cargo_id", table_name="folha_pagamentos")
    op.drop_index("ix_folha_pagamentos_lotacao_id", table_name="folha_pagamentos")
    op.drop_index("ix_folha_pagamentos_servidor_id", table_name="folha_pagamentos")
    op.drop_index("ix_folha_pagamentos_competencia_mes_nome", table_name="folha_pagamentos")
    op.drop_index("ix_folha_pagamentos_competencia_mes_num", table_name="folha_pagamentos")
    op.drop_index("ix_folha_pagamentos_competencia_ano", table_name="folha_pagamentos")
    op.drop_table("folha_pagamentos")

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
        sa.Column("competencia", sa.Date(), nullable=False),
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
            "competencia",
            "servidor_id",
            "cargo_id",
            "lotacao_id",
            name="uq_folha_comp_servidor_cargo_lotacao",
        ),
    )
    op.create_index("ix_folha_pagamentos_competencia", "folha_pagamentos", ["competencia"])
    op.create_index("ix_folha_pagamentos_servidor_id", "folha_pagamentos", ["servidor_id"])
    op.create_index("ix_folha_pagamentos_lotacao_id", "folha_pagamentos", ["lotacao_id"])
    op.create_index("ix_folha_pagamentos_cargo_id", "folha_pagamentos", ["cargo_id"])
