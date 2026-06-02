# passagens-source-ingestion Specification

## Purpose
TBD - created by archiving change extend-passagens-ingestion-and-agent-tools. Update Purpose after archive.
## Requirements
### Requirement: Supported `passagens` source files are discovered by the standard ingestion flow
The system MUST detect every approved dedicated `passagens` CSV source profile from the configured transparency data directories and include those files in the normal local `despesas` ingestion pipeline.

#### Scenario: Dedicated `passagens` file is picked up during ingestion
- **WHEN** an operator places a file that matches a supported `passagens` source profile under the configured transparency data tree and runs the relevant ingestion flow
- **THEN** the pipeline includes that file in the discovered inputs for import
- **AND** the file is processed as supported `passagens` data instead of being ignored

#### Scenario: Unknown `passagens`-like CSV layout is not guessed silently
- **WHEN** the pipeline encounters a CSV file in the expected `passagens` area that does not match any approved `passagens` source profile or required header contract
- **THEN** the system does not import it as if it were a known `passagens` layout
- **AND** the outcome is a predictable skip or failure path rather than a silent best-effort parse

### Requirement: Imported `passagens` records are stored with source-backed payment and period fields in the local SQL database
The system MUST normalize supported `passagens` CSV records into the local SQL transparency database, preserving the beneficiary identity, origin, report period, category, and canonical monetary fields required for public querying.

#### Scenario: Valid `passagens` row becomes a persisted SQL record
- **WHEN** a supported `passagens` CSV file contains a valid beneficiary/payment row with the required identifying and monetary fields
- **THEN** the ingestion flow persists that row in the local SQL database with normalized text, date, and numeric values
- **AND** the stored record remains available for later public tool queries

#### Scenario: Report metadata is preserved during import
- **WHEN** a supported `passagens` CSV row is imported from a file with source metadata such as exercise, report period, unit, or transfer/category label
- **THEN** the ingestion flow stores the supported metadata in canonical SQL fields alongside the row
- **AND** later queries can use that persisted data without rereading the source CSV

### Requirement: Imported `passagens` data does not fabricate unsupported itinerary fields
The system MUST limit persisted `passagens` attributes to the supported source-backed contract and MUST NOT invent itinerary details that are absent from the imported CSV.

#### Scenario: Consolidated source lacks route or destination fields
- **WHEN** a supported `passagens` CSV row contains only consolidated beneficiary and payment information without route, destination, or ticket identifiers
- **THEN** the persisted SQL record contains only the supported source-backed attributes
- **AND** the import does not fabricate missing itinerary details

### Requirement: Re-importing the same supported `passagens` source is idempotent by source lineage
The system MUST allow supported `passagens` files to be re-imported without duplicating the same source lineage, while refreshing persisted values when the normalized source payload changed.

#### Scenario: Re-import updates an existing `passagens` record
- **WHEN** the ingestion flow processes a supported `passagens` row whose file-plus-row identity already exists in the local SQL database
- **THEN** the system updates the existing stored record when imported values changed
- **AND** it does not create a duplicate persisted row for that same source lineage

#### Scenario: Re-import leaves unchanged `passagens` records stable
- **WHEN** the ingestion flow reprocesses a supported `passagens` source row and the normalized payload did not change
- **THEN** the previously stored SQL row remains the authoritative record for that lineage
- **AND** the re-import does not create duplicate records or drift in the stored values

