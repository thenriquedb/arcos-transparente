## 1. Estoques Source Ingestion

- [x] 1.1 Add the dedicated `estoques` import type to the CLI and pipeline discovery flow, including explicit support for `data/xml/administracao/estoques/estoque-*.xml`.
- [x] 1.2 Implement the `estoques` XML parser/schema normalization flow for material summaries, report period/origin extraction, and nested daily movement rows.
- [x] 1.3 Add parser fixtures and regression tests covering a supported `estoques` file, an auxiliary/unsupported layout, a summary-only material, and a material with multiple daily movements.

## 2. Dedicated SQL Persistence

- [x] 2.1 Add the SQLAlchemy models and Alembic migration for `estoque_materiais` and `estoque_movimentacoes` with source-lineage constraints and useful indexes.
- [x] 2.2 Implement the custom pipeline load path that upserts stock materials and refreshes their related movement rows idempotently on re-import.
- [x] 2.3 Add pipeline/database regression tests proving `estoques` imports persist summaries and movements correctly and remain stable across re-imports.

## 3. Public Estoques Tools

- [x] 3.1 Implement `consultar_estoques` with supported material-balance filters, projected fields, pagination metadata, and source-backed response semantics.
- [x] 3.2 Implement `agregar_estoques` with supported totals, counts, and rankings over summary metrics such as entradas, saidas, and saldo.
- [x] 3.3 Implement `consultar_movimentacoes_de_estoque` with supported movement-history filters for material, date range, movement type, unidade gestora, almoxarifado, localizacao, and classificacao.
- [x] 3.4 Register the new public `estoques` tools and add SQL-backed unit tests for summary lookup, aggregation, and movement-history behavior.

## 4. Agent Integration And Documentation

- [x] 4.1 Update routing keywords, route rules, and tool guidance so stock, warehouse, balance, and movement questions prefer the dedicated `estoques` domain over adjacent domains.
- [x] 4.2 Update database/import documentation and operational surfaces such as CLI help or status reporting to describe the new `estoques` import type and SQL tables.
- [x] 4.3 Add router/chatbot regression tests covering representative saldo de material and movimentacao de estoque questions answered through the dedicated SQL tools.
