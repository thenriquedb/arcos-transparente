"""servidor unique inclui secretaria

Revision ID: 20260521_000008
Revises: 20260521_000007
Create Date: 2026-05-21 21:00:00
"""

from alembic import op

revision = "20260521_000008"
down_revision = "20260521_000007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("servidores") as batch_op:
        batch_op.drop_constraint("uq_servidor_nome_cargo_data_admissao", type_="unique")
        batch_op.create_unique_constraint(
            "uq_servidor_nome_cargo_sec_data_admissao",
            ["nome", "cargo", "secretaria", "data_admissao"],
        )


def downgrade() -> None:
    with op.batch_alter_table("servidores") as batch_op:
        batch_op.drop_constraint(
            "uq_servidor_nome_cargo_sec_data_admissao", type_="unique"
        )
        batch_op.create_unique_constraint(
            "uq_servidor_nome_cargo_data_admissao",
            ["nome", "cargo", "data_admissao"],
        )
