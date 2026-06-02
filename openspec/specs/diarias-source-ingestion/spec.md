# diarias-source-ingestion Specification

## Purpose
TBD - created by archiving change extend-diarias-ingestion-and-agent-tools. Update Purpose after archive.
## Requirements
### Requirement: Supported `diarias` source files are discovered by the standard ingestion flow
The system MUST detect every approved dedicated `diarias` CSV source profile from the configured data directories and include those files in the normal local ingestion pipeline.

#### Scenario: Dedicated `diarias` file is picked up during ingestion
- **WHEN** an operator places a file that matches a supported `diarias` source profile under the configured transparency data tree and runs the relevant ingestion flow
- **THEN** the pipeline includes that file in the discovered inputs for import
- **AND** the file is processed as supported `diarias` data instead of being ignored

#### Scenario: Unknown `diarias`-like CSV layout is not guessed silently
- **WHEN** the pipeline encounters a CSV file in the expected `diarias` area that does not match any approved `diarias` source profile or required header contract
- **THEN** the system does not import it as if it were a known `diarias` layout
- **AND** the outcome is a predictable skip or failure path rather than a silent best-effort parse

### Requirement: Imported `diarias` records are stored with travel-specific fields in the local SQL database
The system MUST normalize supported `diarias` CSV records into the local SQL transparency database, preserving the canonical payment fields and the travel-specific attributes required for public querying.

#### Scenario: Valid `diarias` record becomes a persisted SQL row
- **WHEN** a supported `diarias` CSV file contains a valid row with the required identifying and payment fields
- **THEN** the ingestion flow persists that record in the local SQL database with normalized text, date, and numeric values
- **AND** the stored record remains available for later public tool queries

#### Scenario: Travel-specific attributes are preserved during import
- **WHEN** a supported `diarias` CSV row includes travel-specific fields such as destination, trip dates, quantity of daily allowances, unit value, objective, or total value
- **THEN** the ingestion flow stores those supported attributes in the canonical SQL model
- **AND** those values remain queryable after import without re-reading the source CSV

### Requirement: Re-importing the same supported `diarias` source is idempotent by source lineage
The system MUST allow supported `diarias` files to be re-imported without duplicating the same source lineage, while refreshing persisted values when the source payload changed.

#### Scenario: Re-import updates an existing `diarias` record
- **WHEN** the ingestion flow processes a supported `diarias` row whose file-plus-row identity already exists in the local SQL database
- **THEN** the system updates the existing stored record when imported values changed
- **AND** it does not create a duplicate persisted row for that same source lineage

#### Scenario: Re-import leaves unchanged `diarias` records stable
- **WHEN** the ingestion flow reprocesses a supported `diarias` source row and the normalized payload did not change
- **THEN** the previously stored SQL row remains the authoritative record for that lineage
- **AND** the re-import does not create duplicate records or drift in the stored values

