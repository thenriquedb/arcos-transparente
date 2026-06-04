## ADDED Requirements

### Requirement: `folha_servidores` stores the legacy folha snapshot contract without depending on `servidores`
The system MUST persist the legacy snapshot fields used by folha and public salary queries directly on `folha_servidores`, without requiring enrichment through the `servidores` table.

#### Scenario: Existing snapshot rows are preserved in `folha_servidores`
- **WHEN** the migration runs on a database that still has legacy snapshot rows in `servidores`
- **THEN** each legacy snapshot row is copied or transformed into a corresponding `folha_servidores` row
- **AND** the fields `nome`, `cargo`, `secretaria`, `salario_base`, and `competencia_referencia` remain queryable after the migration

#### Scenario: New folha imports maintain snapshot rows in `folha_servidores`
- **WHEN** the ingestion flow imports supported folha de pagamento records for a competence
- **THEN** the pipeline upserts the matching snapshot row in `folha_servidores`
- **AND** the row preserves the legacy public contract for salary, cargo, secretaria, and competence reference

### Requirement: `folha_servidores` is decoupled from `servidores`
The system MUST remove the canonical relationship between `folha_servidores` and `servidores` at the schema, ORM, and ingestion-helper levels.

#### Scenario: Schema no longer carries the canonical foreign key
- **WHEN** the migration finishes
- **THEN** `folha_servidores` no longer has a foreign key column that points to `servidores`
- **AND** the ORM models no longer expose relationship properties that imply canonical enrichment between the two tables

#### Scenario: Folha helpers stop reconciling by canonical servidor link
- **WHEN** the ingestion or folha-query code resolves metadata for a folha servidor
- **THEN** it reads the supported snapshot fields from `folha_servidores` or the linked folha payment rows
- **AND** it does not call reconciliation logic that tries to find a canonical `servidores` row by name, cargo, or secretaria

### Requirement: `folha_pagamentos` remains referentially valid after the migration
The system MUST keep `folha_pagamentos` attached to valid `folha_servidores` rows after the legacy snapshot contract moves out of `servidores`.

#### Scenario: Existing folha pagamento rows are remapped to migrated snapshot rows
- **WHEN** the migration processes an existing database with populated `folha_pagamentos`
- **THEN** each payment row keeps a valid `servidor_id` that resolves to the migrated snapshot representation in `folha_servidores`
- **AND** the migration does not leave dangling folha payment references to removed rows
