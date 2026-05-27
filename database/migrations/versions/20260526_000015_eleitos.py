"""adiciona tabela de eleitos

Revision ID: 20260526_000015
Revises: 20260526_000014
Create Date: 2026-05-26 19:40:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260526_000015"
down_revision = "20260526_000014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "eleitos",
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
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column("tipo_politico", sa.String(length=30), nullable=False),
        sa.Column("id_origem", sa.Integer(), nullable=True),
        sa.Column("municipio", sa.String(length=120), nullable=False),
        sa.Column("estado", sa.String(length=10), nullable=False),
        sa.Column("nome_completo", sa.String(length=255), nullable=False),
        sa.Column("nome_popular", sa.String(length=255), nullable=True),
        sa.Column("partido", sa.String(length=60), nullable=True),
        sa.Column("telefone", sa.String(length=80), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("homepage", sa.String(length=255), nullable=True),
        sa.Column("numero_gabinete", sa.String(length=40), nullable=True),
        sa.Column("cargo", sa.String(length=255), nullable=True),
        sa.Column("biografia", sa.Text(), nullable=True),
        sa.Column("mandato_inicio", sa.Integer(), nullable=False),
        sa.Column("mandato_fim", sa.Integer(), nullable=False),
        sa.Column("mandato_status", sa.String(length=80), nullable=False),
        sa.Column("mandato_observacao", sa.Text(), nullable=True),
        sa.UniqueConstraint(
            "tipo_politico",
            "nome_completo",
            "mandato_inicio",
            "mandato_fim",
            name="uq_eleito_tipo_nome_mandato",
        ),
    )
    op.create_index("ix_eleitos_tipo_politico", "eleitos", ["tipo_politico"])
    op.create_index("ix_eleitos_municipio", "eleitos", ["municipio"])
    op.create_index("ix_eleitos_estado", "eleitos", ["estado"])
    op.create_index("ix_eleitos_nome_completo", "eleitos", ["nome_completo"])
    op.create_index("ix_eleitos_nome_popular", "eleitos", ["nome_popular"])
    op.create_index("ix_eleitos_partido", "eleitos", ["partido"])
    op.create_index("ix_eleitos_mandato_inicio", "eleitos", ["mandato_inicio"])
    op.create_index("ix_eleitos_mandato_fim", "eleitos", ["mandato_fim"])
    op.create_index("ix_eleitos_mandato_status", "eleitos", ["mandato_status"])
    op.create_index(
        "ix_eleitos_tipo_status_mandato",
        "eleitos",
        ["tipo_politico", "mandato_status", "mandato_inicio", "mandato_fim"],
    )


def downgrade() -> None:
    op.drop_index("ix_eleitos_tipo_status_mandato", table_name="eleitos")
    op.drop_index("ix_eleitos_mandato_status", table_name="eleitos")
    op.drop_index("ix_eleitos_mandato_fim", table_name="eleitos")
    op.drop_index("ix_eleitos_mandato_inicio", table_name="eleitos")
    op.drop_index("ix_eleitos_partido", table_name="eleitos")
    op.drop_index("ix_eleitos_nome_popular", table_name="eleitos")
    op.drop_index("ix_eleitos_nome_completo", table_name="eleitos")
    op.drop_index("ix_eleitos_estado", table_name="eleitos")
    op.drop_index("ix_eleitos_municipio", table_name="eleitos")
    op.drop_index("ix_eleitos_tipo_politico", table_name="eleitos")
    op.drop_table("eleitos")
