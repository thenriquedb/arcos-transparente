"""folha pagamento detalhada

Revision ID: 20260521_000005
Revises: 20260521_000004
Create Date: 2026-05-21 20:20:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260521_000005"
down_revision = "20260521_000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "folha_servidores",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.UniqueConstraint("nome", name="uq_folha_servidor_nome"),
    )
    op.create_index("ix_folha_servidores_nome", "folha_servidores", ["nome"])

    op.create_table(
        "folha_lotacoes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.UniqueConstraint("nome", name="uq_folha_lotacao_nome"),
    )
    op.create_index("ix_folha_lotacoes_nome", "folha_lotacoes", ["nome"])

    op.create_table(
        "folha_cargos",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.UniqueConstraint("nome", name="uq_folha_cargo_nome"),
    )
    op.create_index("ix_folha_cargos_nome", "folha_cargos", ["nome"])

    op.create_table(
        "folha_pagamentos",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("competencia", sa.Date(), nullable=False),
        sa.Column("servidor_id", sa.Integer(), sa.ForeignKey("folha_servidores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lotacao_id", sa.Integer(), sa.ForeignKey("folha_lotacoes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("cargo_id", sa.Integer(), sa.ForeignKey("folha_cargos.id", ondelete="SET NULL"), nullable=True),
        sa.Column("salario_base", sa.Numeric(15, 2), nullable=True),
        sa.Column("proventos", sa.Numeric(15, 2), nullable=True),
        sa.Column("vantagens", sa.Numeric(15, 2), nullable=True),
        sa.Column("vencimentos_totais", sa.Numeric(15, 2), nullable=True),
        sa.Column("descontos", sa.Numeric(15, 2), nullable=True),
        sa.Column("liquido", sa.Numeric(15, 2), nullable=True),
        sa.UniqueConstraint("competencia", "servidor_id", "cargo_id", "lotacao_id", name="uq_folha_comp_servidor_cargo_lotacao"),
    )
    op.create_index("ix_folha_pagamentos_competencia", "folha_pagamentos", ["competencia"])
    op.create_index("ix_folha_pagamentos_servidor_id", "folha_pagamentos", ["servidor_id"])
    op.create_index("ix_folha_pagamentos_lotacao_id", "folha_pagamentos", ["lotacao_id"])
    op.create_index("ix_folha_pagamentos_cargo_id", "folha_pagamentos", ["cargo_id"])


def downgrade() -> None:
    op.drop_index("ix_folha_pagamentos_cargo_id", table_name="folha_pagamentos")
    op.drop_index("ix_folha_pagamentos_lotacao_id", table_name="folha_pagamentos")
    op.drop_index("ix_folha_pagamentos_servidor_id", table_name="folha_pagamentos")
    op.drop_index("ix_folha_pagamentos_competencia", table_name="folha_pagamentos")
    op.drop_table("folha_pagamentos")

    op.drop_index("ix_folha_cargos_nome", table_name="folha_cargos")
    op.drop_table("folha_cargos")

    op.drop_index("ix_folha_lotacoes_nome", table_name="folha_lotacoes")
    op.drop_table("folha_lotacoes")

    op.drop_index("ix_folha_servidores_nome", table_name="folha_servidores")
    op.drop_table("folha_servidores")
