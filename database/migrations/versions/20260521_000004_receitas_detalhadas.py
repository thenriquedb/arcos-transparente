"""receitas detalhadas

Revision ID: 20260521_000004
Revises: 20260521_000003
Create Date: 2026-05-21 01:20:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260521_000004"
down_revision = "20260521_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "receita_naturezas",
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
        sa.Column("identificacao", sa.String(length=40), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=True),
        sa.Column("nivel", sa.Integer(), nullable=True),
        sa.Column("identificacao_superior", sa.String(length=40), nullable=True),
        sa.UniqueConstraint("identificacao", name="uq_receita_natureza_identificacao"),
    )
    op.create_index("ix_receita_naturezas_identificacao", "receita_naturezas", ["identificacao"])
    op.create_index("ix_receita_naturezas_nome", "receita_naturezas", ["nome"])
    op.create_index(
        "ix_receita_naturezas_identificacao_superior",
        "receita_naturezas",
        ["identificacao_superior"],
    )

    op.create_table(
        "receita_arrecadacoes",
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
        sa.Column("exercicio", sa.Integer(), nullable=False),
        sa.Column("mes", sa.String(length=20), nullable=False),
        sa.Column("data_arrecadacao", sa.Date(), nullable=False),
        sa.Column("unidade_gestora", sa.String(length=255), nullable=False),
        sa.Column(
            "natureza_id",
            sa.Integer(),
            sa.ForeignKey("receita_naturezas.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("fonte_recurso", sa.Text(), nullable=True),
        sa.Column("valor_previsto_bruto", sa.Numeric(15, 2), nullable=True),
        sa.Column("valor_arrecadado_bruto", sa.Numeric(15, 2), nullable=True),
        sa.Column("valor_previsto_deducoes", sa.Numeric(15, 2), nullable=True),
        sa.Column("valor_realizado_deducoes", sa.Numeric(15, 2), nullable=True),
        sa.Column("valor_previsto_liquido", sa.Numeric(15, 2), nullable=True),
        sa.Column("valor_arrecadado_liquido", sa.Numeric(15, 2), nullable=True),
        sa.UniqueConstraint(
            "data_arrecadacao",
            "unidade_gestora",
            "natureza_id",
            "fonte_recurso",
            name="uq_receita_arrec_base",
        ),
    )
    op.create_index("ix_receita_arrecadacoes_exercicio", "receita_arrecadacoes", ["exercicio"])
    op.create_index("ix_receita_arrecadacoes_mes", "receita_arrecadacoes", ["mes"])
    op.create_index(
        "ix_receita_arrecadacoes_data_arrecadacao",
        "receita_arrecadacoes",
        ["data_arrecadacao"],
    )
    op.create_index(
        "ix_receita_arrecadacoes_unidade_gestora",
        "receita_arrecadacoes",
        ["unidade_gestora"],
    )
    op.create_index("ix_receita_arrecadacoes_natureza_id", "receita_arrecadacoes", ["natureza_id"])

    op.create_table(
        "receita_lancamentos",
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
        sa.Column("exercicio", sa.Integer(), nullable=False),
        sa.Column("mes", sa.String(length=20), nullable=False),
        sa.Column("data_lancamento", sa.Date(), nullable=False),
        sa.Column("tipo_receita", sa.String(length=120), nullable=False),
        sa.Column("tributo", sa.String(length=180), nullable=False),
        sa.Column("valor_lancado_exercicio", sa.Numeric(15, 2), nullable=True),
        sa.Column("valor_lancado_divida_ativa", sa.Numeric(15, 2), nullable=True),
        sa.Column("valor_lancado_cobraca_judicial", sa.Numeric(15, 2), nullable=True),
        sa.UniqueConstraint(
            "data_lancamento",
            "tipo_receita",
            "tributo",
            "valor_lancado_exercicio",
            name="uq_receita_lanc_base",
        ),
    )
    op.create_index("ix_receita_lancamentos_exercicio", "receita_lancamentos", ["exercicio"])
    op.create_index("ix_receita_lancamentos_mes", "receita_lancamentos", ["mes"])
    op.create_index(
        "ix_receita_lancamentos_data_lancamento",
        "receita_lancamentos",
        ["data_lancamento"],
    )
    op.create_index("ix_receita_lancamentos_tipo_receita", "receita_lancamentos", ["tipo_receita"])
    op.create_index("ix_receita_lancamentos_tributo", "receita_lancamentos", ["tributo"])


def downgrade() -> None:
    op.drop_index("ix_receita_lancamentos_tributo", table_name="receita_lancamentos")
    op.drop_index("ix_receita_lancamentos_tipo_receita", table_name="receita_lancamentos")
    op.drop_index("ix_receita_lancamentos_data_lancamento", table_name="receita_lancamentos")
    op.drop_index("ix_receita_lancamentos_mes", table_name="receita_lancamentos")
    op.drop_index("ix_receita_lancamentos_exercicio", table_name="receita_lancamentos")
    op.drop_table("receita_lancamentos")

    op.drop_index("ix_receita_arrecadacoes_natureza_id", table_name="receita_arrecadacoes")
    op.drop_index("ix_receita_arrecadacoes_unidade_gestora", table_name="receita_arrecadacoes")
    op.drop_index("ix_receita_arrecadacoes_data_arrecadacao", table_name="receita_arrecadacoes")
    op.drop_index("ix_receita_arrecadacoes_mes", table_name="receita_arrecadacoes")
    op.drop_index("ix_receita_arrecadacoes_exercicio", table_name="receita_arrecadacoes")
    op.drop_table("receita_arrecadacoes")

    op.drop_index("ix_receita_naturezas_identificacao_superior", table_name="receita_naturezas")
    op.drop_index("ix_receita_naturezas_nome", table_name="receita_naturezas")
    op.drop_index("ix_receita_naturezas_identificacao", table_name="receita_naturezas")
    op.drop_table("receita_naturezas")
