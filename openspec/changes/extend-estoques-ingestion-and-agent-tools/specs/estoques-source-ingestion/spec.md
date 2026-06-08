## ADDED Requirements

### Requirement: Supported `estoques` XML files are discovered by the standard ingestion flow
The system MUST detect every approved `estoques` XML source profile under the configured transparency data directories and include those files in the normal local ingestion workflow.

#### Scenario: Dedicated `estoques` file is picked up during ingestion
- **WHEN** an operator places a file that matches a supported `estoques` source profile under `data/xml/administracao/estoques/` and runs the relevant ingestion flow
- **THEN** the pipeline includes that file in the discovered inputs for import
- **AND** the file is processed as supported `estoques` data instead of being ignored

#### Scenario: Unknown or auxiliary `estoques` layout is not guessed silently
- **WHEN** the pipeline encounters an XML file in the expected `estoques` area that does not match the approved source contract for supported `ESTOQUE` data
- **THEN** the system does not import it as if it were a known `estoques` layout
- **AND** the outcome is a predictable skip or failure path rather than a silent best-effort parse

### Requirement: Imported `estoques` materials are stored with summarized balance and nested daily movements in dedicated SQL tables
The system MUST normalize each supported `estoques` material into a dedicated SQL material record and MUST persist any nested daily movements as related SQL movement records with the supported source-backed fields required for public querying.

#### Scenario: Valid material summary becomes a persisted SQL record
- **WHEN** a supported `estoques` XML file contains a valid `MATERIAL` node with the required material identity and summarized period fields
- **THEN** the ingestion flow persists that node as a material record in the dedicated stock summary table
- **AND** the stored record remains queryable later without re-reading the source XML

#### Scenario: Nested daily movement becomes a related persisted movement record
- **WHEN** a supported `MATERIAL` node contains one or more valid nested `MOVIMENTACAODIARIA` rows
- **THEN** the ingestion flow persists each supported movement as a related SQL movement record
- **AND** each movement preserves the supported source-backed fields such as movement date, movement type, unit, warehouse, location, classification, quantity, and values

### Requirement: Materials without daily movement history remain importable without fabricated detail
The system MUST persist supported material summaries even when a `MATERIAL` node has no nested daily movements and MUST NOT invent movement-only detail that is absent from the source.

#### Scenario: Summary-only material is imported without synthetic child movements
- **WHEN** a supported `MATERIAL` node includes summarized balance data but no valid nested daily movement rows
- **THEN** the ingestion flow persists the material summary record
- **AND** no synthetic movement rows are created for that material

### Requirement: Re-importing the same supported `estoques` source is idempotent by source lineage
The system MUST allow supported `estoques` files to be re-imported without duplicating the same material or movement lineage, while refreshing persisted values when the normalized source payload changed.

#### Scenario: Re-import updates an existing material lineage and its related movements
- **WHEN** the ingestion flow processes a supported `estoques` material lineage whose source identity already exists in the local SQL database
- **THEN** the system updates the existing stored material and related movement records when imported values changed
- **AND** it does not create duplicate persisted rows for that same source lineage

#### Scenario: Re-import leaves unchanged `estoques` records stable
- **WHEN** the ingestion flow reprocesses a supported `estoques` source and the normalized material plus movement payload did not change
- **THEN** the previously stored SQL rows remain the authoritative records for that lineage
- **AND** the re-import does not create duplicate records or drift in the stored values
