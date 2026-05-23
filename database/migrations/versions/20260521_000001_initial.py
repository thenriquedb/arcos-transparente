"""initial schema

Revision ID: 20260521_000001
Revises:
Create Date: 2026-05-21 00:00:01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260521_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contratos",
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
        sa.Column("numero", sa.String(length=50), nullable=False),
        sa.Column("fornecedor", sa.String(length=255), nullable=False),
        sa.Column("cnpj", sa.String(length=18), nullable=False),
        sa.Column("valor", sa.Numeric(15, 2), nullable=False),
        sa.Column("data_inicio", sa.Date(), nullable=False),
        sa.Column("data_fim", sa.Date(), nullable=True),
        sa.Column("categoria", sa.String(length=100), nullable=False),
        sa.Column("secretaria", sa.String(length=120), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.UniqueConstraint(
            "numero", "data_inicio", name="uq_contrato_numero_data_inicio"
        ),
    )
    op.create_index("ix_contratos_cnpj", "contratos", ["cnpj"])
    op.create_index("ix_contratos_categoria", "contratos", ["categoria"])
    op.create_index("ix_contratos_secretaria", "contratos", ["secretaria"])
    op.create_index("ix_contratos_data_inicio", "contratos", ["data_inicio"])
    op.create_index("ix_contratos_data_fim", "contratos", ["data_fim"])

    op.create_table(
        "licitacoes",
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
        sa.Column("numero", sa.String(length=50), nullable=False),
        sa.Column("modalidade", sa.String(length=100), nullable=False),
        sa.Column("objeto", sa.Text(), nullable=False),
        sa.Column("valor_estimado", sa.Numeric(15, 2), nullable=False),
        sa.Column("data_abertura", sa.Date(), nullable=False),
        sa.Column("situacao", sa.String(length=80), nullable=False),
        sa.Column("secretaria", sa.String(length=120), nullable=False),
        sa.UniqueConstraint(
            "numero", "data_abertura", name="uq_licitacao_numero_data_abertura"
        ),
    )
    op.create_index("ix_licitacoes_modalidade", "licitacoes", ["modalidade"])
    op.create_index("ix_licitacoes_situacao", "licitacoes", ["situacao"])
    op.create_index("ix_licitacoes_secretaria", "licitacoes", ["secretaria"])
    op.create_index("ix_licitacoes_data_abertura", "licitacoes", ["data_abertura"])

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
        sa.Column("salario_base", sa.Numeric(15, 2), nullable=False),
        sa.Column("data_admissao", sa.Date(), nullable=False),
        sa.UniqueConstraint(
            "nome",
            "cargo",
            "data_admissao",
            name="uq_servidor_nome_cargo_data_admissao",
        ),
    )
    op.create_index("ix_servidores_secretaria", "servidores", ["secretaria"])
    op.create_index("ix_servidores_cargo", "servidores", ["cargo"])
    op.create_index("ix_servidores_data_admissao", "servidores", ["data_admissao"])


def downgrade() -> None:
    op.drop_index("ix_servidores_data_admissao", table_name="servidores")
    op.drop_index("ix_servidores_cargo", table_name="servidores")
    op.drop_index("ix_servidores_secretaria", table_name="servidores")
    op.drop_table("servidores")

    op.drop_index("ix_licitacoes_data_abertura", table_name="licitacoes")
    op.drop_index("ix_licitacoes_secretaria", table_name="licitacoes")
    op.drop_index("ix_licitacoes_situacao", table_name="licitacoes")
    op.drop_index("ix_licitacoes_modalidade", table_name="licitacoes")
    op.drop_table("licitacoes")

    op.drop_index("ix_contratos_data_fim", table_name="contratos")
    op.drop_index("ix_contratos_data_inicio", table_name="contratos")
    op.drop_index("ix_contratos_secretaria", table_name="contratos")
    op.drop_index("ix_contratos_categoria", table_name="contratos")
    op.drop_index("ix_contratos_cnpj", table_name="contratos")
    op.drop_table("contratos")
