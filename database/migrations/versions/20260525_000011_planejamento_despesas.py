"""planejamento de despesas

Revision ID: 20260525_000011
Revises: 20260523_000010
Create Date: 2026-05-25 00:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260525_000011"
down_revision = "20260523_000010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "planejamento_despesas",
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
        sa.Column("origem", sa.String(length=80), nullable=False),
        sa.Column("exercicio", sa.Integer(), nullable=False),
        sa.Column("mes", sa.String(length=20), nullable=False),
        sa.Column("mes_num", sa.Integer(), nullable=False),
        sa.Column("unidade_gestora", sa.String(length=255), nullable=False),
        sa.Column("orgao", sa.String(length=255), nullable=True),
        sa.Column("unidade", sa.String(length=255), nullable=True),
        sa.Column("departamento", sa.String(length=255), nullable=True),
        sa.Column("funcao", sa.String(length=120), nullable=False),
        sa.Column("subfuncao", sa.String(length=160), nullable=True),
        sa.Column("programa", sa.String(length=255), nullable=True),
        sa.Column("tipo_acao", sa.String(length=80), nullable=True),
        sa.Column("descricao_acao", sa.Text(), nullable=False),
        sa.Column("fonte_recurso_identificacao", sa.String(length=40), nullable=True),
        sa.Column("fonte_recurso_descricao", sa.Text(), nullable=True),
        sa.Column("esfera_administrativa", sa.String(length=80), nullable=True),
        sa.Column(
            "categoria_economica_identificacao",
            sa.String(length=40),
            nullable=True,
        ),
        sa.Column("categoria_economica_descricao", sa.Text(), nullable=True),
        sa.Column("grupo_despesa_identificacao", sa.String(length=40), nullable=True),
        sa.Column("grupo_despesa_descricao", sa.Text(), nullable=True),
        sa.Column(
            "elemento_despesa_identificacao",
            sa.String(length=40),
            nullable=True,
        ),
        sa.Column("elemento_despesa_descricao", sa.Text(), nullable=True),
        sa.Column(
            "modalidade_aplicacao_identificacao",
            sa.String(length=40),
            nullable=True,
        ),
        sa.Column("modalidade_aplicacao_descricao", sa.Text(), nullable=True),
        sa.Column("dotacao_inicial", sa.Numeric(15, 2), nullable=True),
        sa.Column("creditos_adicionais", sa.Numeric(15, 2), nullable=True),
        sa.Column("dotacao_atualizada", sa.Numeric(15, 2), nullable=True),
        sa.Column("valor_empenhado", sa.Numeric(15, 2), nullable=True),
        sa.Column("valor_liquidacao", sa.Numeric(15, 2), nullable=True),
        sa.Column("valor_liquidado", sa.Numeric(15, 2), nullable=True),
        sa.Column("valor_pago", sa.Numeric(15, 2), nullable=True),
        sa.Column("valor_anulado", sa.Numeric(15, 2), nullable=True),
        sa.UniqueConstraint(
            "origem",
            "exercicio",
            "mes_num",
            "unidade_gestora",
            "orgao",
            "unidade",
            "funcao",
            "subfuncao",
            "programa",
            "tipo_acao",
            "descricao_acao",
            "fonte_recurso_identificacao",
            "categoria_economica_identificacao",
            "grupo_despesa_identificacao",
            "elemento_despesa_identificacao",
            name="uq_planejamento_despesa_base",
        ),
    )
    op.create_index(
        "ix_planejamento_despesas_origem",
        "planejamento_despesas",
        ["origem"],
    )
    op.create_index(
        "ix_planejamento_exercicio_mes_funcao",
        "planejamento_despesas",
        ["exercicio", "mes_num", "funcao"],
    )
    op.create_index(
        "ix_planejamento_programa_acao",
        "planejamento_despesas",
        ["programa", "descricao_acao"],
    )
    op.create_index(
        "ix_planejamento_despesas_subfuncao",
        "planejamento_despesas",
        ["subfuncao"],
    )
    op.create_index(
        "ix_planejamento_despesas_grupo",
        "planejamento_despesas",
        ["grupo_despesa_identificacao"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_planejamento_despesas_grupo",
        table_name="planejamento_despesas",
    )
    op.drop_index(
        "ix_planejamento_despesas_subfuncao",
        table_name="planejamento_despesas",
    )
    op.drop_index(
        "ix_planejamento_programa_acao",
        table_name="planejamento_despesas",
    )
    op.drop_index(
        "ix_planejamento_exercicio_mes_funcao",
        table_name="planejamento_despesas",
    )
    op.drop_index(
        "ix_planejamento_despesas_origem",
        table_name="planejamento_despesas",
    )
    op.drop_table("planejamento_despesas")
