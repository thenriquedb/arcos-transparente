"""frotas detalhadas com relacoes

Revision ID: 20260521_000003
Revises: 20260521_000002
Create Date: 2026-05-21 00:55:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260521_000003"
down_revision = "20260521_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "frota_veiculos",
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
        sa.Column("codigo_veiculo", sa.String(length=40), nullable=False),
        sa.Column("placa_patrimonio", sa.String(length=20), nullable=True),
        sa.Column("placa_veiculo", sa.String(length=20), nullable=True),
        sa.Column("descricao_material", sa.String(length=120), nullable=True),
        sa.Column("unidade_gestora", sa.String(length=255), nullable=True),
        sa.Column("tipo_veiculo", sa.String(length=80), nullable=True),
        sa.Column("marca", sa.String(length=80), nullable=True),
        sa.Column("modelo", sa.String(length=120), nullable=True),
        sa.Column("data_aquisicao", sa.DateTime(timezone=False), nullable=True),
        sa.Column("localizacao", sa.String(length=255), nullable=True),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("ano_fabricacao", sa.Integer(), nullable=True),
        sa.Column("situacao_veiculo", sa.String(length=60), nullable=True),
        sa.Column("situacao_veiculo_patrimonio", sa.String(length=60), nullable=True),
        sa.Column("estado_conservacao", sa.String(length=60), nullable=True),
        sa.Column("renavam", sa.String(length=30), nullable=True),
        sa.Column("chassi", sa.String(length=40), nullable=True),
        sa.Column("ano_modelo", sa.Integer(), nullable=True),
        sa.Column("qtd_passageiros", sa.Integer(), nullable=True),
        sa.Column("marcador_atual", sa.Numeric(15, 2), nullable=True),
        sa.Column("unidade_medida", sa.String(length=20), nullable=True),
        sa.Column("fornecedor", sa.String(length=255), nullable=True),
        sa.Column("cor_predominante", sa.String(length=40), nullable=True),
        sa.Column("valor_atual", sa.Numeric(15, 2), nullable=True),
        sa.UniqueConstraint(
            "codigo_veiculo", "placa_veiculo", name="uq_frota_codigo_placa"
        ),
    )
    op.create_index(
        "ix_frota_veiculos_codigo_veiculo", "frota_veiculos", ["codigo_veiculo"]
    )
    op.create_index(
        "ix_frota_veiculos_placa_patrimonio", "frota_veiculos", ["placa_patrimonio"]
    )
    op.create_index(
        "ix_frota_veiculos_placa_veiculo", "frota_veiculos", ["placa_veiculo"]
    )
    op.create_index(
        "ix_frota_veiculos_unidade_gestora", "frota_veiculos", ["unidade_gestora"]
    )
    op.create_index(
        "ix_frota_veiculos_tipo_veiculo", "frota_veiculos", ["tipo_veiculo"]
    )
    op.create_index(
        "ix_frota_veiculos_data_aquisicao", "frota_veiculos", ["data_aquisicao"]
    )
    op.create_index(
        "ix_frota_veiculos_situacao_veiculo", "frota_veiculos", ["situacao_veiculo"]
    )
    op.create_index("ix_frota_veiculos_renavam", "frota_veiculos", ["renavam"])
    op.create_index("ix_frota_veiculos_chassi", "frota_veiculos", ["chassi"])
    op.create_index("ix_frota_veiculos_fornecedor", "frota_veiculos", ["fornecedor"])

    op.create_table(
        "frota_despesas",
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
            "veiculo_id",
            sa.Integer(),
            sa.ForeignKey("frota_veiculos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("descricao_evento", sa.Text(), nullable=True),
        sa.Column("quantidade_lancamento", sa.Numeric(15, 4), nullable=True),
        sa.Column("valor_lancamento", sa.Numeric(15, 4), nullable=True),
        sa.Column("data_evento", sa.Date(), nullable=True),
        sa.Column("tp_despesa", sa.String(length=20), nullable=True),
        sa.Column("tipo_despesa", sa.String(length=80), nullable=True),
        sa.Column("total_despesa", sa.Numeric(15, 4), nullable=True),
        sa.UniqueConstraint(
            "veiculo_id",
            "descricao_evento",
            "data_evento",
            "valor_lancamento",
            name="uq_frota_despesa_evento",
        ),
    )
    op.create_index("ix_frota_despesas_veiculo_id", "frota_despesas", ["veiculo_id"])
    op.create_index("ix_frota_despesas_data_evento", "frota_despesas", ["data_evento"])
    op.create_index(
        "ix_frota_despesas_tipo_despesa", "frota_despesas", ["tipo_despesa"]
    )


def downgrade() -> None:
    op.drop_index("ix_frota_despesas_tipo_despesa", table_name="frota_despesas")
    op.drop_index("ix_frota_despesas_data_evento", table_name="frota_despesas")
    op.drop_index("ix_frota_despesas_veiculo_id", table_name="frota_despesas")
    op.drop_table("frota_despesas")

    op.drop_index("ix_frota_veiculos_fornecedor", table_name="frota_veiculos")
    op.drop_index("ix_frota_veiculos_chassi", table_name="frota_veiculos")
    op.drop_index("ix_frota_veiculos_renavam", table_name="frota_veiculos")
    op.drop_index("ix_frota_veiculos_situacao_veiculo", table_name="frota_veiculos")
    op.drop_index("ix_frota_veiculos_data_aquisicao", table_name="frota_veiculos")
    op.drop_index("ix_frota_veiculos_tipo_veiculo", table_name="frota_veiculos")
    op.drop_index("ix_frota_veiculos_unidade_gestora", table_name="frota_veiculos")
    op.drop_index("ix_frota_veiculos_placa_veiculo", table_name="frota_veiculos")
    op.drop_index("ix_frota_veiculos_placa_patrimonio", table_name="frota_veiculos")
    op.drop_index("ix_frota_veiculos_codigo_veiculo", table_name="frota_veiculos")
    op.drop_table("frota_veiculos")
