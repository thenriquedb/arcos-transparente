"""adiciona tabelas de transferencias financeiras e emendas parlamentares

Revision ID: 20260602_000017
Revises: 20260601_000016
Create Date: 2026-06-02 20:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260602_000017"
down_revision = "20260601_000016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transferencias_financeiras_movimentos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
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
        sa.Column("sequencia_origem", sa.Integer(), nullable=False),
        sa.Column("exercicio", sa.Integer(), nullable=False),
        sa.Column("identificacao", sa.String(length=40), nullable=True),
        sa.Column("unidade_gestora_concessora", sa.String(length=255), nullable=True),
        sa.Column("unidade_gestora_recebedora", sa.String(length=255), nullable=True),
        sa.Column("finalidade", sa.Text(), nullable=True),
        sa.Column("fonte_recurso", sa.Text(), nullable=True),
        sa.Column("detalhamento_fonte", sa.Text(), nullable=True),
        sa.Column("programacao_inicial", sa.Numeric(15, 2), nullable=True),
        sa.Column("data_movimento", sa.Date(), nullable=False),
        sa.Column("tipo_movimento", sa.String(length=120), nullable=True),
        sa.Column("valor_movimento", sa.Numeric(15, 2), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "arquivo_origem",
            "sequencia_origem",
            name="uq_transf_fin_mov_arquivo_seq",
        ),
    )
    op.create_index(
        "ix_transferencias_financeiras_movimentos_arquivo_origem",
        "transferencias_financeiras_movimentos",
        ["arquivo_origem"],
    )
    op.create_index(
        "ix_transferencias_financeiras_movimentos_data_movimento",
        "transferencias_financeiras_movimentos",
        ["data_movimento"],
    )
    op.create_index(
        "ix_transferencias_financeiras_movimentos_exercicio",
        "transferencias_financeiras_movimentos",
        ["exercicio"],
    )
    op.create_index(
        "ix_transferencias_financeiras_movimentos_identificacao",
        "transferencias_financeiras_movimentos",
        ["identificacao"],
    )
    op.create_index(
        "ix_transferencias_financeiras_movimentos_tipo_movimento",
        "transferencias_financeiras_movimentos",
        ["tipo_movimento"],
    )
    op.create_index(
        "ix_transferencias_financeiras_movimentos_unidade_gestora_concessora",
        "transferencias_financeiras_movimentos",
        ["unidade_gestora_concessora"],
    )
    op.create_index(
        "ix_transferencias_financeiras_movimentos_unidade_gestora_recebedora",
        "transferencias_financeiras_movimentos",
        ["unidade_gestora_recebedora"],
    )

    op.create_table(
        "emendas_parlamentares",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
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
        sa.Column("sequencia_origem", sa.Integer(), nullable=False),
        sa.Column("exercicio_consulta", sa.Integer(), nullable=False),
        sa.Column("ano", sa.Integer(), nullable=False),
        sa.Column("ano_numero", sa.String(length=40), nullable=False),
        sa.Column("autor", sa.String(length=255), nullable=True),
        sa.Column("objeto", sa.Text(), nullable=True),
        sa.Column("tipo_emenda", sa.String(length=255), nullable=True),
        sa.Column("funcao", sa.String(length=120), nullable=True),
        sa.Column("valor", sa.Numeric(15, 2), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "arquivo_origem",
            "sequencia_origem",
            name="uq_emenda_parl_arquivo_seq",
        ),
    )
    op.create_index(
        "ix_emendas_parlamentares_ano",
        "emendas_parlamentares",
        ["ano"],
    )
    op.create_index(
        "ix_emendas_parlamentares_ano_numero",
        "emendas_parlamentares",
        ["ano_numero"],
    )
    op.create_index(
        "ix_emendas_parlamentares_arquivo_origem",
        "emendas_parlamentares",
        ["arquivo_origem"],
    )
    op.create_index(
        "ix_emendas_parlamentares_autor",
        "emendas_parlamentares",
        ["autor"],
    )
    op.create_index(
        "ix_emendas_parlamentares_exercicio_consulta",
        "emendas_parlamentares",
        ["exercicio_consulta"],
    )
    op.create_index(
        "ix_emendas_parlamentares_funcao",
        "emendas_parlamentares",
        ["funcao"],
    )
    op.create_index(
        "ix_emendas_parlamentares_tipo_emenda",
        "emendas_parlamentares",
        ["tipo_emenda"],
    )


def downgrade() -> None:
    op.drop_index("ix_emendas_parlamentares_tipo_emenda", table_name="emendas_parlamentares")
    op.drop_index("ix_emendas_parlamentares_funcao", table_name="emendas_parlamentares")
    op.drop_index(
        "ix_emendas_parlamentares_exercicio_consulta",
        table_name="emendas_parlamentares",
    )
    op.drop_index("ix_emendas_parlamentares_autor", table_name="emendas_parlamentares")
    op.drop_index(
        "ix_emendas_parlamentares_arquivo_origem",
        table_name="emendas_parlamentares",
    )
    op.drop_index("ix_emendas_parlamentares_ano_numero", table_name="emendas_parlamentares")
    op.drop_index("ix_emendas_parlamentares_ano", table_name="emendas_parlamentares")
    op.drop_table("emendas_parlamentares")

    op.drop_index(
        "ix_transferencias_financeiras_movimentos_unidade_gestora_recebedora",
        table_name="transferencias_financeiras_movimentos",
    )
    op.drop_index(
        "ix_transferencias_financeiras_movimentos_unidade_gestora_concessora",
        table_name="transferencias_financeiras_movimentos",
    )
    op.drop_index(
        "ix_transferencias_financeiras_movimentos_tipo_movimento",
        table_name="transferencias_financeiras_movimentos",
    )
    op.drop_index(
        "ix_transferencias_financeiras_movimentos_identificacao",
        table_name="transferencias_financeiras_movimentos",
    )
    op.drop_index(
        "ix_transferencias_financeiras_movimentos_exercicio",
        table_name="transferencias_financeiras_movimentos",
    )
    op.drop_index(
        "ix_transferencias_financeiras_movimentos_data_movimento",
        table_name="transferencias_financeiras_movimentos",
    )
    op.drop_index(
        "ix_transferencias_financeiras_movimentos_arquivo_origem",
        table_name="transferencias_financeiras_movimentos",
    )
    op.drop_table("transferencias_financeiras_movimentos")
