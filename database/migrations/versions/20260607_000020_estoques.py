"""adiciona tabelas de estoques

Revision ID: 20260607_000020
Revises: 20260604_000019
Create Date: 2026-06-07 16:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260607_000020"
down_revision = "20260604_000019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "estoque_materiais",
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
        sa.Column("sequencia_material", sa.Integer(), nullable=False),
        sa.Column("origem", sa.String(length=80), nullable=False),
        sa.Column("exercicio", sa.Integer(), nullable=False),
        sa.Column("material", sa.Text(), nullable=False),
        sa.Column("unidade_medida", sa.String(length=80), nullable=False),
        sa.Column("periodo_inicio", sa.Date(), nullable=False),
        sa.Column("periodo_fim", sa.Date(), nullable=False),
        sa.Column("saldo_anterior_quantidade", sa.Numeric(18, 4), nullable=True),
        sa.Column("saldo_anterior_valor", sa.Numeric(18, 4), nullable=True),
        sa.Column("entrada_quantidade", sa.Numeric(18, 4), nullable=True),
        sa.Column("entrada_valor", sa.Numeric(18, 4), nullable=True),
        sa.Column("saida_quantidade", sa.Numeric(18, 4), nullable=True),
        sa.Column("saida_valor", sa.Numeric(18, 4), nullable=True),
        sa.Column("saldo_quantidade", sa.Numeric(18, 4), nullable=True),
        sa.Column("saldo_valor", sa.Numeric(18, 4), nullable=True),
        sa.UniqueConstraint(
            "origem",
            "arquivo_origem",
            "sequencia_material",
            name="uq_estoque_material_linhagem",
        ),
    )
    op.create_index(
        "ix_estoque_materiais_arquivo_origem",
        "estoque_materiais",
        ["arquivo_origem"],
    )
    op.create_index(
        "ix_estoque_materiais_origem",
        "estoque_materiais",
        ["origem"],
    )
    op.create_index(
        "ix_estoque_materiais_exercicio",
        "estoque_materiais",
        ["exercicio"],
    )
    op.create_index(
        "ix_estoque_materiais_periodo_fim",
        "estoque_materiais",
        ["periodo_fim"],
    )
    op.create_index(
        "ix_estoque_materiais_exercicio_material",
        "estoque_materiais",
        ["exercicio", "material"],
    )
    op.create_index(
        "ix_estoque_materiais_origem_periodo",
        "estoque_materiais",
        ["origem", "periodo_fim"],
    )
    op.create_index(
        "ix_estoque_materiais_unidade_medida",
        "estoque_materiais",
        ["unidade_medida"],
    )

    op.create_table(
        "estoque_movimentacoes",
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
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column("sequencia_movimentacao", sa.Integer(), nullable=False),
        sa.Column("data_movimento", sa.Date(), nullable=False),
        sa.Column("tipo_movimento", sa.String(length=120), nullable=False),
        sa.Column("unidade_gestora", sa.String(length=255), nullable=True),
        sa.Column("almoxarifado", sa.String(length=255), nullable=True),
        sa.Column("localizacao", sa.String(length=255), nullable=True),
        sa.Column("classificacao", sa.String(length=255), nullable=True),
        sa.Column("quantidade", sa.Numeric(18, 4), nullable=True),
        sa.Column("valor_unitario", sa.Numeric(18, 8), nullable=True),
        sa.Column("valor_total", sa.Numeric(18, 4), nullable=True),
        sa.Column("custo_medio", sa.Numeric(18, 8), nullable=True),
        sa.ForeignKeyConstraint(
            ["material_id"],
            ["estoque_materiais.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "material_id",
            "sequencia_movimentacao",
            name="uq_estoque_movimentacao_linhagem",
        ),
    )
    op.create_index(
        "ix_estoque_movimentacoes_material_id",
        "estoque_movimentacoes",
        ["material_id"],
    )
    op.create_index(
        "ix_estoque_movimentacoes_data_movimento",
        "estoque_movimentacoes",
        ["data_movimento"],
    )
    op.create_index(
        "ix_estoque_movimentacoes_tipo_movimento",
        "estoque_movimentacoes",
        ["tipo_movimento"],
    )
    op.create_index(
        "ix_estoque_movimentacoes_data_tipo",
        "estoque_movimentacoes",
        ["data_movimento", "tipo_movimento"],
    )
    op.create_index(
        "ix_estoque_movimentacoes_unidade_gestora",
        "estoque_movimentacoes",
        ["unidade_gestora"],
    )
    op.create_index(
        "ix_estoque_movimentacoes_almoxarifado",
        "estoque_movimentacoes",
        ["almoxarifado"],
    )
    op.create_index(
        "ix_estoque_movimentacoes_localizacao",
        "estoque_movimentacoes",
        ["localizacao"],
    )
    op.create_index(
        "ix_estoque_movimentacoes_classificacao",
        "estoque_movimentacoes",
        ["classificacao"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_estoque_movimentacoes_classificacao",
        table_name="estoque_movimentacoes",
    )
    op.drop_index(
        "ix_estoque_movimentacoes_localizacao",
        table_name="estoque_movimentacoes",
    )
    op.drop_index(
        "ix_estoque_movimentacoes_almoxarifado",
        table_name="estoque_movimentacoes",
    )
    op.drop_index(
        "ix_estoque_movimentacoes_unidade_gestora",
        table_name="estoque_movimentacoes",
    )
    op.drop_index(
        "ix_estoque_movimentacoes_data_tipo",
        table_name="estoque_movimentacoes",
    )
    op.drop_index(
        "ix_estoque_movimentacoes_tipo_movimento",
        table_name="estoque_movimentacoes",
    )
    op.drop_index(
        "ix_estoque_movimentacoes_data_movimento",
        table_name="estoque_movimentacoes",
    )
    op.drop_index(
        "ix_estoque_movimentacoes_material_id",
        table_name="estoque_movimentacoes",
    )
    op.drop_table("estoque_movimentacoes")

    op.drop_index(
        "ix_estoque_materiais_unidade_medida",
        table_name="estoque_materiais",
    )
    op.drop_index(
        "ix_estoque_materiais_origem_periodo",
        table_name="estoque_materiais",
    )
    op.drop_index(
        "ix_estoque_materiais_exercicio_material",
        table_name="estoque_materiais",
    )
    op.drop_index(
        "ix_estoque_materiais_periodo_fim",
        table_name="estoque_materiais",
    )
    op.drop_index(
        "ix_estoque_materiais_exercicio",
        table_name="estoque_materiais",
    )
    op.drop_index(
        "ix_estoque_materiais_origem",
        table_name="estoque_materiais",
    )
    op.drop_index(
        "ix_estoque_materiais_arquivo_origem",
        table_name="estoque_materiais",
    )
    op.drop_table("estoque_materiais")
