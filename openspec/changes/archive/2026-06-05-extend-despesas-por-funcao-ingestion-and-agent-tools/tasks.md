## 1. `despesas-por-funcao` Source Ingestion

- [x] 1.1 Extend file discovery to recognize the supported `data/xml/despesas/despesas-por-funcao/*.csv` profile and add a parser/schema flow for its metadata and function rows.
- [x] 1.2 Normalize the report header, period, unit, localized monetary values, and function names into SQL-ready records while skipping `Totais` and other synthetic export rows.
- [x] 1.3 Add parser-level fixtures and regression tests for a valid report, an unsupported layout, and summary-row handling.

## 2. Dedicated SQL Persistence

- [x] 2.1 Add the SQLAlchemy model and Alembic migration for a dedicated `despesas_por_funcao` table with the supported metrics, source-lineage fields, unique contract, and useful indexes.
- [x] 2.2 Integrate the ingestion load path so imported report rows upsert idempotently into `despesas_por_funcao` and preserve report metadata plus supported values.
- [x] 2.3 Add pipeline/database regression tests proving the new table is populated correctly and remains stable across re-imports.

## 3. Public `despesas-por-funcao` Tools

- [x] 3.1 Implement `consultar_despesas_por_funcao` with supported filters, projected fields, pagination metadata, and source-backed response semantics.
- [x] 3.2 Implement `agregar_despesas_por_funcao` with supported totals, counts, rankings, and grouping behavior over the persisted report rows.
- [x] 3.3 Register the new tools in the public tool registry and add SQL-backed unit tests for lookup and aggregation behavior.

## 4. Agent Integration And Documentation

- [x] 4.1 Update routing, docstrings, and prompt/tool guidance so explicit function-report questions prefer `despesas-por-funcao` over `planejamento` and generic `despesas`.
- [x] 4.2 Update database/import documentation to describe the new table and its boundary against existing planning and expense domains.
- [x] 4.3 Add router/chatbot regression tests covering representative `despesas-por-funcao` questions answered through the dedicated SQL tools.
