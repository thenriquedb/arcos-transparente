"""adiciona periodo de referencia para diarias csv

Revision ID: 20260601_000016
Revises: 20260526_000015
Create Date: 2026-06-01 20:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260601_000016"
down_revision = "20260526_000015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "despesa_documentos",
        sa.Column("periodo_referencia_inicio", sa.Date(), nullable=True),
    )
    op.add_column(
        "despesa_documentos",
        sa.Column("periodo_referencia_fim", sa.Date(), nullable=True),
    )
    op.create_index(
        "ix_despesa_documentos_periodo_referencia_inicio",
        "despesa_documentos",
        ["periodo_referencia_inicio"],
    )
    op.create_index(
        "ix_despesa_documentos_periodo_referencia_fim",
        "despesa_documentos",
        ["periodo_referencia_fim"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_despesa_documentos_periodo_referencia_fim",
        table_name="despesa_documentos",
    )
    op.drop_index(
        "ix_despesa_documentos_periodo_referencia_inicio",
        table_name="despesa_documentos",
    )
    op.drop_column("despesa_documentos", "periodo_referencia_fim")
    op.drop_column("despesa_documentos", "periodo_referencia_inicio")
