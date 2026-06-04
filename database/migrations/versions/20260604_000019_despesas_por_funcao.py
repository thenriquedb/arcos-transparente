"""adiciona tabela de despesas por funcao

Revision ID: 20260604_000019
Revises: 20260603_000018
Create Date: 2026-06-04 18:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260604_000019"
down_revision = "20260603_000018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "despesas_por_funcao",
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
        sa.Column("arquivo_origem", sa.String(length=255), nullable=False),
        sa.Column("linha_origem", sa.Integer(), nullable=False),
        sa.Column("origem", sa.String(length=80), nullable=False),
        sa.Column("exercicio", sa.Integer(), nullable=False),
        sa.Column("periodo_inicio", sa.Date(), nullable=False),
        sa.Column("periodo_fim", sa.Date(), nullable=False),
        sa.Column("unidade_gestora", sa.String(length=255), nullable=False),
        sa.Column("funcao", sa.String(length=120), nullable=False),
        sa.Column("dotacao_inicial", sa.Numeric(15, 2), nullable=True),
        sa.Column("creditos_adicionais", sa.Numeric(15, 2), nullable=True),
        sa.Column("dotacao_atualizada", sa.Numeric(15, 2), nullable=True),
        sa.Column("valor_empenhado", sa.Numeric(15, 2), nullable=True),
        sa.Column("valor_em_liquidacao", sa.Numeric(15, 2), nullable=True),
        sa.Column("valor_liquidado", sa.Numeric(15, 2), nullable=True),
        sa.Column("valor_pago", sa.Numeric(15, 2), nullable=True),
        sa.UniqueConstraint(
            "origem",
            "exercicio",
            "periodo_inicio",
            "periodo_fim",
            "unidade_gestora",
            "funcao",
            name="uq_despesa_funcao_periodo",
        ),
    )
    op.create_index(
        "ix_despesas_por_funcao_arquivo_origem",
        "despesas_por_funcao",
        ["arquivo_origem"],
    )
    op.create_index(
        "ix_despesas_por_funcao_exercicio",
        "despesas_por_funcao",
        ["exercicio"],
    )
    op.create_index(
        "ix_despesas_por_funcao_funcao",
        "despesas_por_funcao",
        ["funcao"],
    )
    op.create_index(
        "ix_despesas_por_funcao_origem_periodo",
        "despesas_por_funcao",
        ["origem", "periodo_fim"],
    )
    op.create_index(
        "ix_despesas_por_funcao_unidade_gestora",
        "despesas_por_funcao",
        ["unidade_gestora"],
    )
    op.create_index(
        "ix_despesas_por_funcao_exercicio_funcao",
        "despesas_por_funcao",
        ["exercicio", "funcao"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_despesas_por_funcao_exercicio_funcao",
        table_name="despesas_por_funcao",
    )
    op.drop_index(
        "ix_despesas_por_funcao_unidade_gestora",
        table_name="despesas_por_funcao",
    )
    op.drop_index(
        "ix_despesas_por_funcao_origem_periodo",
        table_name="despesas_por_funcao",
    )
    op.drop_index(
        "ix_despesas_por_funcao_funcao",
        table_name="despesas_por_funcao",
    )
    op.drop_index(
        "ix_despesas_por_funcao_exercicio",
        table_name="despesas_por_funcao",
    )
    op.drop_index(
        "ix_despesas_por_funcao_arquivo_origem",
        table_name="despesas_por_funcao",
    )
    op.drop_table("despesas_por_funcao")
