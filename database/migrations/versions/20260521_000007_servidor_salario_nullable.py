"""servidor salario nullable

Revision ID: 20260521_000007
Revises: 20260521_000006
Create Date: 2026-05-21 20:50:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260521_000007"
down_revision = "20260521_000006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("servidores") as batch_op:
        batch_op.alter_column("salario_base", existing_type=sa.Numeric(15, 2), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("servidores") as batch_op:
        batch_op.alter_column("salario_base", existing_type=sa.Numeric(15, 2), nullable=False)
