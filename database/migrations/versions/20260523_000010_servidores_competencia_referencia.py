"""servidores usam competencia_referencia em vez de data_admissao

Revision ID: 20260523_000010
Revises: 20260522_000009
Create Date: 2026-05-23 00:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260523_000010"
down_revision = "20260522_000009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index(
        "ix_servidores_secretaria_cargo_data_admissao",
        table_name="servidores",
    )
    op.drop_index("ix_servidores_data_admissao", table_name="servidores")

    with op.batch_alter_table("servidores") as batch_op:
        batch_op.drop_constraint(
            "uq_servidor_nome_cargo_sec_data_admissao",
            type_="unique",
        )
        batch_op.alter_column(
            "data_admissao",
            new_column_name="competencia_referencia",
            existing_type=sa.Date(),
            existing_nullable=False,
        )
        batch_op.create_unique_constraint(
            "uq_servidor_nome_cargo_sec_comp_ref",
            ["nome", "cargo", "secretaria", "competencia_referencia"],
        )

    op.create_index(
        "ix_servidores_competencia_referencia",
        "servidores",
        ["competencia_referencia"],
    )
    op.create_index(
        "ix_servidores_secretaria_cargo_comp_ref",
        "servidores",
        ["secretaria", "cargo", "competencia_referencia"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_servidores_secretaria_cargo_comp_ref",
        table_name="servidores",
    )
    op.drop_index(
        "ix_servidores_competencia_referencia",
        table_name="servidores",
    )

    with op.batch_alter_table("servidores") as batch_op:
        batch_op.drop_constraint(
            "uq_servidor_nome_cargo_sec_comp_ref",
            type_="unique",
        )
        batch_op.alter_column(
            "competencia_referencia",
            new_column_name="data_admissao",
            existing_type=sa.Date(),
            existing_nullable=False,
        )
        batch_op.create_unique_constraint(
            "uq_servidor_nome_cargo_sec_data_admissao",
            ["nome", "cargo", "secretaria", "data_admissao"],
        )

    op.create_index("ix_servidores_data_admissao", "servidores", ["data_admissao"])
    op.create_index(
        "ix_servidores_secretaria_cargo_data_admissao",
        "servidores",
        ["secretaria", "cargo", "data_admissao"],
    )
