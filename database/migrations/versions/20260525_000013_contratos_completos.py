"""expande contratos com campos completos e tabelas filhas

Revision ID: 20260525_000013
Revises: 20260525_000012
Create Date: 2026-05-25 02:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260525_000013"
down_revision = "20260525_000012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "contratos",
        sa.Column("numero_licitatorio", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "contratos",
        sa.Column("numero_instrumento", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "contratos",
        sa.Column("tipo_instrumento_contratual", sa.String(length=60), nullable=True),
    )
    op.add_column(
        "contratos",
        sa.Column("possui_aditivo", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "contratos",
        sa.Column("xml_original", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_contratos_numero_licitatorio",
        "contratos",
        ["numero_licitatorio"],
    )
    op.create_index(
        "ix_contratos_numero_instrumento",
        "contratos",
        ["numero_instrumento"],
    )
    op.create_index(
        "ix_contratos_numero_licitatorio_data_inicio",
        "contratos",
        ["numero_licitatorio", "data_inicio"],
    )

    op.create_table(
        "contrato_despesas_orcamentarias",
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
        sa.Column("contrato_id", sa.Integer(), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column("unidade_gestora", sa.String(length=120), nullable=True),
        sa.Column("exercicio", sa.Integer(), nullable=True),
        sa.Column("orgao", sa.String(length=255), nullable=True),
        sa.Column("unidade", sa.String(length=255), nullable=True),
        sa.Column("departamento", sa.String(length=255), nullable=True),
        sa.Column("fonte_recurso", sa.Text(), nullable=True),
        sa.Column("natureza_despesa_rubrica", sa.String(length=40), nullable=True),
        sa.Column("descricao_despesa", sa.Text(), nullable=True),
        sa.Column("valor_despesa", sa.Numeric(15, 2), nullable=True),
        sa.ForeignKeyConstraint(["contrato_id"], ["contratos.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "contrato_id",
            "ordem",
            name="uq_contrato_despesa_ordem",
        ),
    )
    op.create_index(
        "ix_contrato_despesas_orcamentarias_contrato_id",
        "contrato_despesas_orcamentarias",
        ["contrato_id"],
    )
    op.create_index(
        "ix_contrato_despesas_orcamentarias_exercicio",
        "contrato_despesas_orcamentarias",
        ["exercicio"],
    )
    op.create_index(
        "ix_contrato_despesas_orcamentarias_natureza_despesa_rubrica",
        "contrato_despesas_orcamentarias",
        ["natureza_despesa_rubrica"],
    )
    op.create_index(
        "ix_contrato_despesa_classificacao",
        "contrato_despesas_orcamentarias",
        ["descricao_despesa", "natureza_despesa_rubrica"],
    )

    op.create_table(
        "contrato_itens_adquiridos",
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
        sa.Column("contrato_id", sa.Integer(), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column("unidade_gestora", sa.String(length=120), nullable=True),
        sa.Column("numero_lote", sa.String(length=30), nullable=True),
        sa.Column("numero_item", sa.String(length=30), nullable=True),
        sa.Column("identificacao", sa.Text(), nullable=True),
        sa.Column("quantidade", sa.Numeric(15, 4), nullable=True),
        sa.Column("valor_unitario", sa.Numeric(15, 2), nullable=True),
        sa.Column("valor_total", sa.Numeric(15, 2), nullable=True),
        sa.ForeignKeyConstraint(["contrato_id"], ["contratos.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "contrato_id",
            "ordem",
            name="uq_contrato_item_ordem",
        ),
    )
    op.create_index(
        "ix_contrato_itens_adquiridos_contrato_id",
        "contrato_itens_adquiridos",
        ["contrato_id"],
    )
    op.create_index(
        "ix_contrato_item_lote_item",
        "contrato_itens_adquiridos",
        ["numero_lote", "numero_item"],
    )


def downgrade() -> None:
    op.drop_index("ix_contrato_item_lote_item", table_name="contrato_itens_adquiridos")
    op.drop_index(
        "ix_contrato_itens_adquiridos_contrato_id",
        table_name="contrato_itens_adquiridos",
    )
    op.drop_table("contrato_itens_adquiridos")

    op.drop_index(
        "ix_contrato_despesa_classificacao",
        table_name="contrato_despesas_orcamentarias",
    )
    op.drop_index(
        "ix_contrato_despesas_orcamentarias_natureza_despesa_rubrica",
        table_name="contrato_despesas_orcamentarias",
    )
    op.drop_index(
        "ix_contrato_despesas_orcamentarias_exercicio",
        table_name="contrato_despesas_orcamentarias",
    )
    op.drop_index(
        "ix_contrato_despesas_orcamentarias_contrato_id",
        table_name="contrato_despesas_orcamentarias",
    )
    op.drop_table("contrato_despesas_orcamentarias")

    op.drop_index(
        "ix_contratos_numero_licitatorio_data_inicio",
        table_name="contratos",
    )
    op.drop_index("ix_contratos_numero_instrumento", table_name="contratos")
    op.drop_index("ix_contratos_numero_licitatorio", table_name="contratos")
    op.drop_column("contratos", "possui_aditivo")
    op.drop_column("contratos", "xml_original")
    op.drop_column("contratos", "tipo_instrumento_contratual")
    op.drop_column("contratos", "numero_instrumento")
    op.drop_column("contratos", "numero_licitatorio")
