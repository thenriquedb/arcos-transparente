"""importa dados faltantes de xml

Revision ID: 20260526_000014
Revises: 20260525_000013
Create Date: 2026-05-26 10:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260526_000014"
down_revision = "20260525_000013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patrimonios",
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
        sa.Column("unidade_gestora", sa.String(length=255), nullable=False),
        sa.Column("placa", sa.String(length=40), nullable=False),
        sa.Column("situacao_bem", sa.String(length=80), nullable=True),
        sa.Column("comandatario", sa.String(length=255), nullable=True),
        sa.Column("classificacao", sa.String(length=80), nullable=True),
        sa.Column("descricao_item", sa.Text(), nullable=False),
        sa.Column("tipo_ingresso", sa.String(length=80), nullable=True),
        sa.Column("data_aquisicao", sa.Date(), nullable=True),
        sa.Column("data_baixa", sa.Date(), nullable=True),
        sa.Column("localizacao", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=80), nullable=True),
        sa.Column("valor_ingresso", sa.Numeric(15, 2), nullable=True),
        sa.Column("valor_atualizado", sa.Numeric(15, 2), nullable=True),
        sa.UniqueConstraint(
            "unidade_gestora",
            "placa",
            name="uq_patrimonio_unidade_placa",
        ),
    )
    op.create_index("ix_patrimonios_unidade_gestora", "patrimonios", ["unidade_gestora"])
    op.create_index("ix_patrimonios_placa", "patrimonios", ["placa"])
    op.create_index("ix_patrimonios_situacao_bem", "patrimonios", ["situacao_bem"])
    op.create_index("ix_patrimonios_tipo_ingresso", "patrimonios", ["tipo_ingresso"])
    op.create_index("ix_patrimonios_data_aquisicao", "patrimonios", ["data_aquisicao"])
    op.create_index("ix_patrimonios_data_baixa", "patrimonios", ["data_baixa"])
    op.create_index("ix_patrimonios_localizacao", "patrimonios", ["localizacao"])
    op.create_index("ix_patrimonios_status", "patrimonios", ["status"])
    op.create_index(
        "ix_patrimonios_localizacao_status",
        "patrimonios",
        ["localizacao", "status"],
    )
    op.create_index("ix_patrimonios_classificacao", "patrimonios", ["classificacao"])

    op.create_table(
        "quadro_pessoal",
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
        sa.Column("competencia_referencia", sa.Date(), nullable=False),
        sa.Column("regime_contratacao", sa.String(length=120), nullable=False),
        sa.Column("vagas_criadas", sa.Integer(), nullable=True),
        sa.Column("vagas_preenchidas", sa.Integer(), nullable=True),
        sa.UniqueConstraint(
            "origem",
            "competencia_referencia",
            "regime_contratacao",
            name="uq_quadro_pessoal_origem_comp_regime",
        ),
    )
    op.create_index("ix_quadro_pessoal_origem", "quadro_pessoal", ["origem"])
    op.create_index(
        "ix_quadro_pessoal_competencia_referencia",
        "quadro_pessoal",
        ["competencia_referencia"],
    )
    op.create_index(
        "ix_quadro_pessoal_regime_contratacao",
        "quadro_pessoal",
        ["regime_contratacao"],
    )
    op.create_index(
        "ix_quadro_pessoal_origem_competencia",
        "quadro_pessoal",
        ["origem", "competencia_referencia"],
    )

    op.create_table(
        "despesa_documentos",
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
        sa.Column("tipo_origem", sa.String(length=40), nullable=False),
        sa.Column("arquivo_origem", sa.String(length=255), nullable=False),
        sa.Column("sequencia_origem", sa.Integer(), nullable=False),
        sa.Column("origem", sa.String(length=80), nullable=False),
        sa.Column("exercicio", sa.Integer(), nullable=False),
        sa.Column("unidade_gestora", sa.String(length=255), nullable=False),
        sa.Column("orgao", sa.String(length=255), nullable=True),
        sa.Column("unidade", sa.String(length=255), nullable=True),
        sa.Column("departamento", sa.String(length=255), nullable=True),
        sa.Column("funcao", sa.String(length=120), nullable=True),
        sa.Column("subfuncao", sa.String(length=160), nullable=True),
        sa.Column("programa", sa.String(length=255), nullable=True),
        sa.Column("tipo_acao", sa.String(length=80), nullable=True),
        sa.Column("descricao_acao", sa.Text(), nullable=True),
        sa.Column("fonte_recurso_identificacao", sa.String(length=40), nullable=True),
        sa.Column("fonte_recurso_descricao", sa.Text(), nullable=True),
        sa.Column("esfera_administrativa", sa.String(length=80), nullable=True),
        sa.Column("modalidade_aplicacao_identificacao", sa.String(length=40), nullable=True),
        sa.Column("modalidade_aplicacao_descricao", sa.Text(), nullable=True),
        sa.Column("categoria_economica_identificacao", sa.String(length=40), nullable=True),
        sa.Column("categoria_economica_descricao", sa.Text(), nullable=True),
        sa.Column("grupo_despesa_identificacao", sa.String(length=40), nullable=True),
        sa.Column("grupo_despesa_descricao", sa.Text(), nullable=True),
        sa.Column("elemento_despesa_identificacao", sa.String(length=40), nullable=True),
        sa.Column("elemento_despesa_descricao", sa.Text(), nullable=True),
        sa.Column("desdobramento_despesa_identificacao", sa.String(length=40), nullable=True),
        sa.Column("desdobramento_despesa_descricao", sa.Text(), nullable=True),
        sa.Column("conta_extra_identificacao", sa.String(length=40), nullable=True),
        sa.Column("conta_extra_descricao", sa.Text(), nullable=True),
        sa.Column("numero_documento", sa.String(length=50), nullable=False),
        sa.Column("data_documento", sa.Date(), nullable=False),
        sa.Column("categoria_documento", sa.String(length=80), nullable=True),
        sa.Column("credor", sa.String(length=255), nullable=True),
        sa.Column("cpf_cnpj", sa.String(length=80), nullable=True),
        sa.Column("modalidade_licitacao", sa.String(length=120), nullable=True),
        sa.Column("numero_licitacao", sa.String(length=80), nullable=True),
        sa.Column("ano_licitacao", sa.Integer(), nullable=True),
        sa.Column("data_homologacao", sa.Date(), nullable=True),
        sa.Column("processo_compra", sa.String(length=80), nullable=True),
        sa.Column("numero_contrato", sa.String(length=80), nullable=True),
        sa.Column("numero_convenio", sa.String(length=80), nullable=True),
        sa.Column("valor_documento", sa.Numeric(15, 2), nullable=True),
        sa.Column("valor_empenhado", sa.Numeric(15, 2), nullable=True),
        sa.Column("valor_liquidacao", sa.Numeric(15, 2), nullable=True),
        sa.Column("valor_liquidado", sa.Numeric(15, 2), nullable=True),
        sa.Column("valor_pago", sa.Numeric(15, 2), nullable=True),
        sa.Column("valor_anulado", sa.Numeric(15, 2), nullable=True),
        sa.Column("objetivo_viagem", sa.Text(), nullable=True),
        sa.Column("legislacao_associada", sa.Text(), nullable=True),
        sa.Column("ato_legal", sa.Text(), nullable=True),
        sa.Column("destino", sa.String(length=255), nullable=True),
        sa.Column("data_inicial_viagem", sa.Date(), nullable=True),
        sa.Column("data_final_viagem", sa.Date(), nullable=True),
        sa.Column("quantidade_dias_diarias", sa.Numeric(15, 4), nullable=True),
        sa.Column("valor_diaria", sa.Numeric(15, 2), nullable=True),
        sa.Column("valor_total", sa.Numeric(15, 2), nullable=True),
        sa.UniqueConstraint(
            "tipo_origem",
            "arquivo_origem",
            "sequencia_origem",
            name="uq_despesa_documento_base",
        ),
    )
    op.create_index("ix_despesa_documentos_tipo_origem", "despesa_documentos", ["tipo_origem"])
    op.create_index("ix_despesa_documentos_arquivo_origem", "despesa_documentos", ["arquivo_origem"])
    op.create_index("ix_despesa_documentos_origem", "despesa_documentos", ["origem"])
    op.create_index("ix_despesa_documentos_exercicio", "despesa_documentos", ["exercicio"])
    op.create_index(
        "ix_despesa_documentos_unidade_gestora",
        "despesa_documentos",
        ["unidade_gestora"],
    )
    op.create_index(
        "ix_despesa_documentos_numero_documento",
        "despesa_documentos",
        ["numero_documento"],
    )
    op.create_index("ix_despesa_documentos_data_documento", "despesa_documentos", ["data_documento"])
    op.create_index(
        "ix_despesa_documentos_tipo_exercicio",
        "despesa_documentos",
        ["tipo_origem", "exercicio"],
    )
    op.create_index("ix_despesa_documentos_data", "despesa_documentos", ["data_documento"])
    op.create_index("ix_despesa_documentos_credor", "despesa_documentos", ["credor"])
    op.create_index("ix_despesa_documentos_funcao", "despesa_documentos", ["funcao"])
    op.create_index(
        "ix_despesa_documentos_numero_contrato",
        "despesa_documentos",
        ["numero_contrato"],
    )
    op.create_index(
        "ix_despesa_documentos_conta_extra",
        "despesa_documentos",
        ["conta_extra_identificacao"],
    )

    op.create_table(
        "despesa_documento_itens",
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
        sa.Column("documento_id", sa.Integer(), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column("numero_item", sa.String(length=40), nullable=True),
        sa.Column("descricao_item", sa.Text(), nullable=True),
        sa.Column("quantidade", sa.Numeric(15, 4), nullable=True),
        sa.Column("valor_unitario", sa.Numeric(15, 2), nullable=True),
        sa.Column("valor_total", sa.Numeric(15, 2), nullable=True),
        sa.ForeignKeyConstraint(["documento_id"], ["despesa_documentos.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "documento_id",
            "ordem",
            name="uq_despesa_documento_item_ordem",
        ),
    )
    op.create_index(
        "ix_despesa_documento_itens_documento_id",
        "despesa_documento_itens",
        ["documento_id"],
    )

    op.create_table(
        "despesa_documentos_comprobatorios",
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
        sa.Column("documento_id", sa.Integer(), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column("data_liquidacao", sa.Date(), nullable=True),
        sa.Column("codigo_tipo_documento", sa.String(length=40), nullable=True),
        sa.Column("descricao_tipo_documento", sa.String(length=120), nullable=True),
        sa.Column("numero_documento", sa.String(length=80), nullable=True),
        sa.Column("serie_modelo_nota_fiscal", sa.String(length=80), nullable=True),
        sa.Column("descricao_serie", sa.String(length=80), nullable=True),
        sa.Column("chave_acesso", sa.Text(), nullable=True),
        sa.Column("data_emissao_documento", sa.Date(), nullable=True),
        sa.Column("valor_documento", sa.Numeric(15, 2), nullable=True),
        sa.Column("numero_empenho", sa.String(length=80), nullable=True),
        sa.Column("codigo_unidade_gestora", sa.String(length=40), nullable=True),
        sa.Column("numero_sequencia", sa.String(length=80), nullable=True),
        sa.ForeignKeyConstraint(["documento_id"], ["despesa_documentos.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "documento_id",
            "ordem",
            name="uq_despesa_documento_comprobatorio_ordem",
        ),
    )
    op.create_index(
        "ix_despesa_documentos_comprobatorios_documento_id",
        "despesa_documentos_comprobatorios",
        ["documento_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_despesa_documentos_comprobatorios_documento_id",
        table_name="despesa_documentos_comprobatorios",
    )
    op.drop_table("despesa_documentos_comprobatorios")
    op.drop_index(
        "ix_despesa_documento_itens_documento_id",
        table_name="despesa_documento_itens",
    )
    op.drop_table("despesa_documento_itens")

    op.drop_index("ix_despesa_documentos_conta_extra", table_name="despesa_documentos")
    op.drop_index("ix_despesa_documentos_numero_contrato", table_name="despesa_documentos")
    op.drop_index("ix_despesa_documentos_funcao", table_name="despesa_documentos")
    op.drop_index("ix_despesa_documentos_credor", table_name="despesa_documentos")
    op.drop_index("ix_despesa_documentos_data", table_name="despesa_documentos")
    op.drop_index("ix_despesa_documentos_tipo_exercicio", table_name="despesa_documentos")
    op.drop_index("ix_despesa_documentos_data_documento", table_name="despesa_documentos")
    op.drop_index("ix_despesa_documentos_numero_documento", table_name="despesa_documentos")
    op.drop_index("ix_despesa_documentos_unidade_gestora", table_name="despesa_documentos")
    op.drop_index("ix_despesa_documentos_exercicio", table_name="despesa_documentos")
    op.drop_index("ix_despesa_documentos_origem", table_name="despesa_documentos")
    op.drop_index("ix_despesa_documentos_tipo_origem", table_name="despesa_documentos")
    op.drop_index("ix_despesa_documentos_arquivo_origem", table_name="despesa_documentos")
    op.drop_table("despesa_documentos")

    op.drop_index("ix_quadro_pessoal_origem_competencia", table_name="quadro_pessoal")
    op.drop_index("ix_quadro_pessoal_regime_contratacao", table_name="quadro_pessoal")
    op.drop_index(
        "ix_quadro_pessoal_competencia_referencia",
        table_name="quadro_pessoal",
    )
    op.drop_index("ix_quadro_pessoal_origem", table_name="quadro_pessoal")
    op.drop_table("quadro_pessoal")

    op.drop_index("ix_patrimonios_classificacao", table_name="patrimonios")
    op.drop_index("ix_patrimonios_localizacao_status", table_name="patrimonios")
    op.drop_index("ix_patrimonios_status", table_name="patrimonios")
    op.drop_index("ix_patrimonios_localizacao", table_name="patrimonios")
    op.drop_index("ix_patrimonios_data_baixa", table_name="patrimonios")
    op.drop_index("ix_patrimonios_data_aquisicao", table_name="patrimonios")
    op.drop_index("ix_patrimonios_tipo_ingresso", table_name="patrimonios")
    op.drop_index("ix_patrimonios_situacao_bem", table_name="patrimonios")
    op.drop_index("ix_patrimonios_placa", table_name="patrimonios")
    op.drop_index("ix_patrimonios_unidade_gestora", table_name="patrimonios")
    op.drop_table("patrimonios")
