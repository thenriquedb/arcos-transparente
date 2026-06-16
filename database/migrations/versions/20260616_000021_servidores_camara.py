"""adiciona tabelas de servidores e salarios da camara municipal

Revision ID: 20260616_000021
Revises: 20260607_000020
Create Date: 2026-06-16 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260616_000021"
down_revision = "20260607_000020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "servidores_camara",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("competencia_referencia", sa.Date(), nullable=False),
        sa.Column("matricula", sa.String(50), nullable=False),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("cargo", sa.String(255), nullable=True),
        sa.Column("lotacao", sa.String(255), nullable=True),
        sa.Column("vinculo", sa.String(120), nullable=True),
        sa.Column("situacao_funcional", sa.String(120), nullable=True),
        sa.Column("data_admissao", sa.Date(), nullable=True),
        sa.Column("salario_base", sa.Numeric(15, 2), nullable=True),
        sa.Column("proventos", sa.Numeric(15, 2), nullable=True),
        sa.Column("vantagens", sa.Numeric(15, 2), nullable=True),
        sa.Column("proventos_totais", sa.Numeric(15, 2), nullable=True),
        sa.Column("descontos", sa.Numeric(15, 2), nullable=True),
        sa.Column("liquido", sa.Numeric(15, 2), nullable=True),
        sa.UniqueConstraint("matricula", "competencia_referencia", name="uq_servidor_camara_matricula_comp"),
    )
    op.create_index("ix_servidores_camara_nome", "servidores_camara", ["nome"])
    op.create_index("ix_servidores_camara_cargo", "servidores_camara", ["cargo"])
    op.create_index("ix_servidores_camara_lotacao", "servidores_camara", ["lotacao"])
    op.create_index("ix_servidores_camara_competencia_referencia", "servidores_camara", ["competencia_referencia"])

    op.create_table(
        "salarios_por_cargo_camara",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("competencia_referencia", sa.Date(), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("descricao", sa.String(255), nullable=False),
        sa.UniqueConstraint("codigo", "competencia_referencia", name="uq_salario_cargo_camara_codigo_comp"),
    )
    op.create_index("ix_salarios_cargo_camara_competencia", "salarios_por_cargo_camara", ["competencia_referencia"])
    op.create_index("ix_salarios_cargo_camara_descricao", "salarios_por_cargo_camara", ["descricao"])


def downgrade() -> None:
    op.drop_index("ix_salarios_cargo_camara_descricao", table_name="salarios_por_cargo_camara")
    op.drop_index("ix_salarios_cargo_camara_competencia", table_name="salarios_por_cargo_camara")
    op.drop_table("salarios_por_cargo_camara")

    op.drop_index("ix_servidores_camara_competencia_referencia", table_name="servidores_camara")
    op.drop_index("ix_servidores_camara_lotacao", table_name="servidores_camara")
    op.drop_index("ix_servidores_camara_cargo", table_name="servidores_camara")
    op.drop_index("ix_servidores_camara_nome", table_name="servidores_camara")
    op.drop_table("servidores_camara")
