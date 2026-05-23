"""licitacoes detalhadas com relacoes

Revision ID: 20260521_000002
Revises: 20260521_000001
Create Date: 2026-05-21 00:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260521_000002"
down_revision = "20260521_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fornecedores",
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
        sa.Column("cnpj_cpf", sa.String(length=18), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.UniqueConstraint("cnpj_cpf", "nome", name="uq_fornecedor_cnpj_nome"),
    )
    op.create_index("ix_fornecedores_cnpj_cpf", "fornecedores", ["cnpj_cpf"])
    op.create_index("ix_fornecedores_nome", "fornecedores", ["nome"])

    op.create_table(
        "vencedores_licitacao",
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
        sa.Column(
            "licitacao_id",
            sa.Integer(),
            sa.ForeignKey("licitacoes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "fornecedor_id",
            sa.Integer(),
            sa.ForeignKey("fornecedores.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("cnpj_cpf", sa.String(length=18), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("validade_proposta", sa.String(length=80), nullable=True),
        sa.UniqueConstraint(
            "licitacao_id", "cnpj_cpf", "nome", name="uq_vencedor_licitacao_doc_nome"
        ),
    )
    op.create_index(
        "ix_vencedores_licitacao_licitacao_id", "vencedores_licitacao", ["licitacao_id"]
    )
    op.create_index(
        "ix_vencedores_licitacao_cnpj_cpf", "vencedores_licitacao", ["cnpj_cpf"]
    )

    op.create_table(
        "instrumentos_contratuais",
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
        sa.Column(
            "licitacao_id",
            sa.Integer(),
            sa.ForeignKey("licitacoes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "fornecedor_id",
            sa.Integer(),
            sa.ForeignKey("fornecedores.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("numero_licitatorio", sa.String(length=50), nullable=True),
        sa.Column("unidade_gestora", sa.String(length=120), nullable=True),
        sa.Column("tipo_instrumento_contratual", sa.String(length=60), nullable=True),
        sa.Column("numero_instrumento", sa.String(length=50), nullable=True),
        sa.Column("tipo_contrato", sa.String(length=80), nullable=True),
        sa.Column("objeto", sa.Text(), nullable=True),
        sa.Column("data_emissao", sa.Date(), nullable=True),
        sa.Column("data_expiracao", sa.Date(), nullable=True),
        sa.Column("possui_aditivo", sa.String(length=20), nullable=True),
        sa.Column("valor_instrumento_contratual", sa.Numeric(15, 2), nullable=True),
        sa.UniqueConstraint(
            "licitacao_id", "numero_instrumento", name="uq_instrumento_licitacao_numero"
        ),
    )
    op.create_index(
        "ix_instrumentos_contratuais_licitacao_id",
        "instrumentos_contratuais",
        ["licitacao_id"],
    )
    op.create_index(
        "ix_instrumentos_contratuais_numero_licitatorio",
        "instrumentos_contratuais",
        ["numero_licitatorio"],
    )
    op.create_index(
        "ix_instrumentos_contratuais_numero_instrumento",
        "instrumentos_contratuais",
        ["numero_instrumento"],
    )
    op.create_index(
        "ix_instrumentos_contratuais_tipo_contrato",
        "instrumentos_contratuais",
        ["tipo_contrato"],
    )
    op.create_index(
        "ix_instrumentos_contratuais_data_emissao",
        "instrumentos_contratuais",
        ["data_emissao"],
    )
    op.create_index(
        "ix_instrumentos_contratuais_data_expiracao",
        "instrumentos_contratuais",
        ["data_expiracao"],
    )

    op.create_table(
        "materias_instrumento",
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
        sa.Column(
            "instrumento_id",
            sa.Integer(),
            sa.ForeignKey("instrumentos_contratuais.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("unidade_gestora", sa.String(length=120), nullable=True),
        sa.Column("numero_lote", sa.String(length=30), nullable=True),
        sa.Column("numero_item", sa.String(length=30), nullable=True),
        sa.Column("identificacao", sa.Text(), nullable=True),
        sa.Column("quantidade", sa.Numeric(15, 4), nullable=True),
        sa.Column("valor_unitario", sa.Numeric(15, 2), nullable=True),
        sa.Column("valor_total", sa.Numeric(15, 2), nullable=True),
        sa.UniqueConstraint(
            "instrumento_id",
            "numero_lote",
            "numero_item",
            name="uq_materia_instrumento_lote_item",
        ),
    )
    op.create_index(
        "ix_materias_instrumento_instrumento_id",
        "materias_instrumento",
        ["instrumento_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_materias_instrumento_instrumento_id", table_name="materias_instrumento"
    )
    op.drop_table("materias_instrumento")

    op.drop_index(
        "ix_instrumentos_contratuais_data_expiracao",
        table_name="instrumentos_contratuais",
    )
    op.drop_index(
        "ix_instrumentos_contratuais_data_emissao",
        table_name="instrumentos_contratuais",
    )
    op.drop_index(
        "ix_instrumentos_contratuais_tipo_contrato",
        table_name="instrumentos_contratuais",
    )
    op.drop_index(
        "ix_instrumentos_contratuais_numero_instrumento",
        table_name="instrumentos_contratuais",
    )
    op.drop_index(
        "ix_instrumentos_contratuais_numero_licitatorio",
        table_name="instrumentos_contratuais",
    )
    op.drop_index(
        "ix_instrumentos_contratuais_licitacao_id",
        table_name="instrumentos_contratuais",
    )
    op.drop_table("instrumentos_contratuais")

    op.drop_index("ix_vencedores_licitacao_cnpj_cpf", table_name="vencedores_licitacao")
    op.drop_index(
        "ix_vencedores_licitacao_licitacao_id", table_name="vencedores_licitacao"
    )
    op.drop_table("vencedores_licitacao")

    op.drop_index("ix_fornecedores_nome", table_name="fornecedores")
    op.drop_index("ix_fornecedores_cnpj_cpf", table_name="fornecedores")
    op.drop_table("fornecedores")
