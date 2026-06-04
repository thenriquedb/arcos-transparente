## ADDED Requirements

### Requirement: Supported `servidores` JSON files are discovered by the standard ingestion flow
The system MUST detect the supported `relacao-servidores.json` source under the `servidores` domain and include it in the normal local ingestion workflow.

#### Scenario: The relacao-servidores JSON file is discovered for import
- **WHEN** an operator places `relacao-servidores.json` under `data/xml/servidores/relacao-servidores/` and runs the relevant ingestion flow
- **THEN** the pipeline includes that JSON file in the import inputs for the `servidores` domain
- **AND** the file is parsed with the approved JSON contract instead of the legacy XML snapshot contract

### Requirement: JSON records are stored in a dedicated `servidores` table with full field mapping
The system MUST normalize supported JSON rows into the rebuilt `servidores` table, preserving all supported public fields from the source contract and excluding the legacy folha-only columns that no longer belong to this table.

#### Scenario: Valid JSON row becomes a persisted servidor record
- **WHEN** a supported `relacao-servidores.json` file contains a valid row
- **THEN** the ingestion flow persists that row in the dedicated `servidores` SQL table
- **AND** the stored record preserves the supported mapped fields `source_id`, `competencia_referencia`, `nome`, `cpf`, `matricula`, `cargo_funcao`, `fundamento_legal`, `lotacao`, `situacao_funcional`, `forma_contratacao_investidura`, `data_admissao`, `data_desligamento`, `horario_trabalho`, `carga_horaria`, `local_origem_cedencia`, `local_destino_cedencia`, `onus_pagamento_cedencia`, `data_inicio_cessao`, `data_fim_cessao`, `regime_aposentadoria`, and `vinculo_empregaticio`

#### Scenario: Legacy folha-only fields are not kept on the rebuilt servidores table
- **WHEN** the new `servidores` table is created for the JSON contract
- **THEN** it does not keep legacy snapshot columns whose meaning belongs to `folha_servidores`, such as the old salary-driven folha snapshot contract
- **AND** the table schema reflects only the supported JSON source plus internal persistence metadata

### Requirement: Reimport of the same JSON lineage is idempotent
The system MUST use a stable source-backed identity so reprocessing the same JSON records updates changed values without creating duplicates.

#### Scenario: Re-import updates an existing servidor JSON record
- **WHEN** the ingestion flow reprocesses a JSON row whose stable source identity already exists in SQL
- **THEN** the system updates the stored record when normalized values changed
- **AND** it does not create a duplicate persisted row for that same source lineage

### Requirement: Unsupported or malformed JSON layouts are not guessed silently
The system MUST avoid silently accepting unsupported JSON structures or rows that do not satisfy the approved schema.

#### Scenario: Invalid JSON layout fails predictably
- **WHEN** the ingestion flow encounters a `servidores` JSON payload that is not an array of supported objects or is missing required fields for the contract
- **THEN** the system follows a predictable skip or failure path instead of silently treating it as a valid import
- **AND** valid rows in the same batch, when supported by the parser contract, can still be normalized independently
