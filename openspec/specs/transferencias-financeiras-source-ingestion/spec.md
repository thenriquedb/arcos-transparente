# transferencias-financeiras-source-ingestion Specification

## Purpose
TBD - created by archiving change extend-transferencias-financeiras-ingestion-and-agent-tools. Update Purpose after archive.
## Requirements
### Requirement: Supported `transferencias-financeiras` files are discovered by the standard ingestion flow
The system MUST detect supported files under `data/xml/transferencias-financeiras/` and include them in the normal local ingestion workflow using source-specific parsing contracts.

#### Scenario: Recebimentos XML is discovered for import
- **WHEN** an operator places a supported `recebimentos-YYYY.xml` file under the `transferencias-financeiras` directory and runs the relevant ingestion flow
- **THEN** the pipeline includes that XML file in the import inputs for the `transferencias-financeiras` domain
- **AND** the file is parsed as transfer-movement data rather than ignored

#### Scenario: Emendas CSV is discovered for import
- **WHEN** an operator places a supported `emendas-parlamentares-YYYY.csv` file under the `transferencias-financeiras` directory and runs the relevant ingestion flow
- **THEN** the pipeline includes that CSV file in the import inputs for the same domain
- **AND** the file is parsed with the approved emenda-parlamentar contract rather than treated as a generic CSV

### Requirement: Transfer-movement XML records are stored in a dedicated SQL table for this domain
The system MUST normalize supported transfer-movement XML records into a dedicated SQL table for financial-transfer movements, preserving the movement-specific public fields needed for later querying.

#### Scenario: Valid XML movement becomes a persisted transfer record
- **WHEN** a supported `recebimentos` XML file contains a valid `TransferenciaFinanceira` entry
- **THEN** the ingestion flow persists the movement in the dedicated transfer-movement SQL table
- **AND** the stored record preserves supported fields such as identification, conceding unit, receiving unit, purpose, funding source, movement date, movement type, programmed amount, and movement amount

#### Scenario: Re-import of the same XML lineage is idempotent
- **WHEN** the ingestion flow reprocesses a supported transfer-movement XML entry whose stable source lineage already exists in SQL
- **THEN** the system updates the stored record when normalized values changed
- **AND** it does not create a duplicate persisted row for that same movement lineage

### Requirement: Parliamentary-amendment CSV rows are stored in a separate dedicated SQL table
The system MUST normalize supported parliamentary-amendment CSV rows into their own dedicated SQL table, separate from both transfer-movement records and existing revenue/expense tables.

#### Scenario: Valid emenda CSV row becomes a persisted amendment record
- **WHEN** a supported `emendas-parlamentares` CSV file contains a valid data row
- **THEN** the ingestion flow persists that row in the dedicated parliamentary-amendment SQL table
- **AND** the stored record preserves supported public fields such as exercise, year-number identifier, author, object, amendment type, function, and normalized value

#### Scenario: Unsupported or malformed emenda layout is not guessed silently
- **WHEN** the ingestion flow encounters a CSV in the expected directory that does not match the approved emenda-parlamentar header/layout contract
- **THEN** the system does not import it as if it were a supported amendment file
- **AND** the outcome is a predictable skip or failure path instead of a silent best-effort parse

### Requirement: The domain does not overload unrelated revenue or expense tables
The system MUST keep imported `transferencias-financeiras` data in dedicated tables for this domain instead of coercing the records into existing `receitas` or `despesas` persistence contracts.

#### Scenario: Import preserves domain-specific semantics
- **WHEN** supported XML and CSV records from `transferencias-financeiras` are imported
- **THEN** they are stored in domain-specific SQL tables designed for those sources
- **AND** the import does not require flattening them into existing revenue or expense schemas that lose source meaning

