"""relacionamentos canonicos e indices compostos

Revision ID: 20260522_000009
Revises: 20260521_000008
Create Date: 2026-05-22 00:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260522_000009"
down_revision = "20260521_000008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("contratos") as batch_op:
        batch_op.add_column(sa.Column("fornecedor_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_contratos_fornecedor_id_fornecedores",
            "fornecedores",
            ["fornecedor_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("folha_servidores") as batch_op:
        batch_op.add_column(sa.Column("servidor_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_folha_servidores_servidor_id_servidores",
            "servidores",
            ["servidor_id"],
            ["id"],
            ondelete="SET NULL",
        )

    _backfill_contratos_fornecedores()
    _backfill_folha_servidores()

    op.create_index("ix_contratos_fornecedor_id", "contratos", ["fornecedor_id"])
    op.create_index(
        "ix_contratos_secretaria_categoria_data_inicio",
        "contratos",
        ["secretaria", "categoria", "data_inicio"],
    )
    op.create_index(
        "ix_licitacoes_secretaria_situacao_data_abertura",
        "licitacoes",
        ["secretaria", "situacao", "data_abertura"],
    )
    op.create_index(
        "ix_instrumentos_contratuais_fornecedor_emissao",
        "instrumentos_contratuais",
        ["fornecedor_id", "data_emissao"],
    )
    op.create_index(
        "ix_vencedores_licitacao_fornecedor_id",
        "vencedores_licitacao",
        ["fornecedor_id"],
    )
    op.create_index(
        "ix_folha_servidores_servidor_id", "folha_servidores", ["servidor_id"]
    )
    op.create_index(
        "ix_folha_pagamentos_ano_mes_lotacao",
        "folha_pagamentos",
        ["competencia_ano", "competencia_mes_num", "lotacao_id"],
    )
    op.create_index(
        "ix_folha_pagamentos_ano_mes_servidor",
        "folha_pagamentos",
        ["competencia_ano", "competencia_mes_num", "servidor_id"],
    )
    op.create_index(
        "ix_servidores_secretaria_cargo_data_admissao",
        "servidores",
        ["secretaria", "cargo", "data_admissao"],
    )
    op.create_index(
        "ix_receita_arrecadacoes_exercicio_mes_natureza_unidade",
        "receita_arrecadacoes",
        ["exercicio", "mes", "natureza_id", "unidade_gestora"],
    )
    op.create_index(
        "ix_receita_lancamentos_exercicio_mes_tipo_tributo",
        "receita_lancamentos",
        ["exercicio", "mes", "tipo_receita", "tributo"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_receita_lancamentos_exercicio_mes_tipo_tributo",
        table_name="receita_lancamentos",
    )
    op.drop_index(
        "ix_receita_arrecadacoes_exercicio_mes_natureza_unidade",
        table_name="receita_arrecadacoes",
    )
    op.drop_index(
        "ix_servidores_secretaria_cargo_data_admissao",
        table_name="servidores",
    )
    op.drop_index(
        "ix_folha_pagamentos_ano_mes_servidor",
        table_name="folha_pagamentos",
    )
    op.drop_index(
        "ix_folha_pagamentos_ano_mes_lotacao",
        table_name="folha_pagamentos",
    )
    op.drop_index("ix_folha_servidores_servidor_id", table_name="folha_servidores")
    op.drop_index(
        "ix_vencedores_licitacao_fornecedor_id",
        table_name="vencedores_licitacao",
    )
    op.drop_index(
        "ix_instrumentos_contratuais_fornecedor_emissao",
        table_name="instrumentos_contratuais",
    )
    op.drop_index(
        "ix_licitacoes_secretaria_situacao_data_abertura",
        table_name="licitacoes",
    )
    op.drop_index(
        "ix_contratos_secretaria_categoria_data_inicio",
        table_name="contratos",
    )
    op.drop_index("ix_contratos_fornecedor_id", table_name="contratos")

    with op.batch_alter_table("folha_servidores") as batch_op:
        batch_op.drop_constraint(
            "fk_folha_servidores_servidor_id_servidores",
            type_="foreignkey",
        )
        batch_op.drop_column("servidor_id")

    with op.batch_alter_table("contratos") as batch_op:
        batch_op.drop_constraint(
            "fk_contratos_fornecedor_id_fornecedores",
            type_="foreignkey",
        )
        batch_op.drop_column("fornecedor_id")


def _backfill_contratos_fornecedores() -> None:
    conn = op.get_bind()
    contratos = sa.table(
        "contratos",
        sa.column("id", sa.Integer()),
        sa.column("fornecedor", sa.String()),
        sa.column("cnpj", sa.String()),
        sa.column("fornecedor_id", sa.Integer()),
    )
    fornecedores = sa.table(
        "fornecedores",
        sa.column("id", sa.Integer()),
        sa.column("cnpj_cpf", sa.String()),
        sa.column("nome", sa.String()),
    )

    fornecedores_existentes = {
        (row.cnpj_cpf, row.nome): row.id
        for row in conn.execute(
            sa.select(
                fornecedores.c.id,
                fornecedores.c.cnpj_cpf,
                fornecedores.c.nome,
            )
        )
    }

    for contrato in conn.execute(
        sa.select(
            contratos.c.id,
            contratos.c.fornecedor,
            contratos.c.cnpj,
        )
    ):
        chave = (contrato.cnpj, contrato.fornecedor)
        fornecedor_id = fornecedores_existentes.get(chave)
        if fornecedor_id is None:
            insert_result = conn.execute(
                fornecedores.insert().values(
                    cnpj_cpf=contrato.cnpj,
                    nome=contrato.fornecedor,
                )
            )
            fornecedor_id = int(insert_result.inserted_primary_key[0])
            fornecedores_existentes[chave] = fornecedor_id

        conn.execute(
            contratos.update()
            .where(contratos.c.id == contrato.id)
            .values(fornecedor_id=fornecedor_id)
        )


def _backfill_folha_servidores() -> None:
    conn = op.get_bind()
    folha_servidores = sa.table(
        "folha_servidores",
        sa.column("id", sa.Integer()),
        sa.column("nome", sa.String()),
        sa.column("servidor_id", sa.Integer()),
    )
    servidores = sa.table(
        "servidores",
        sa.column("id", sa.Integer()),
        sa.column("nome", sa.String()),
    )

    servidores_por_nome: dict[str, list[int]] = {}
    for servidor in conn.execute(sa.select(servidores.c.id, servidores.c.nome)):
        servidores_por_nome.setdefault(servidor.nome, []).append(servidor.id)

    for folha_servidor in conn.execute(
        sa.select(folha_servidores.c.id, folha_servidores.c.nome)
    ):
        candidatos = servidores_por_nome.get(folha_servidor.nome, [])
        if len(candidatos) != 1:
            continue

        conn.execute(
            folha_servidores.update()
            .where(folha_servidores.c.id == folha_servidor.id)
            .values(servidor_id=candidatos[0])
        )
