## ADDED Requirements

### Requirement: Supported `despesas-por-funcao` source files are discovered by the standard ingestion flow
The system MUST detect every approved `despesas-por-funcao` CSV source profile from the configured transparency data directories and include those files in the normal local ingestion workflow.

#### Scenario: Dedicated `despesas-por-funcao` file is picked up during ingestion
- **WHEN** an operator places a file that matches a supported `despesas-por-funcao` source profile under the configured transparency data tree and runs the relevant ingestion flow
- **THEN** the pipeline includes that file in the discovered inputs for import
- **AND** the file is processed as supported `despesas-por-funcao` data instead of being ignored

#### Scenario: Unknown `despesas-por-funcao` layout is not guessed silently
- **WHEN** the pipeline encounters a CSV file in the expected `despesas-por-funcao` area that does not match the approved header and metadata contract
- **THEN** the system does not import it as if it were a known `despesas-por-funcao` layout
- **AND** the outcome is a predictable skip or failure path rather than a silent best-effort parse

### Requirement: Imported `despesas-por-funcao` rows are stored in a dedicated SQL table with report metadata and function metrics
The system MUST normalize supported `despesas-por-funcao` CSV rows into a dedicated SQL table, preserving the supported report metadata and function-level monetary metrics required for public querying.

#### Scenario: Valid function row becomes a persisted SQL record
- **WHEN** a supported `despesas-por-funcao` CSV file contains a valid function row
- **THEN** the ingestion flow persists that row in the dedicated SQL table with normalized values for `funcao`, report period, unit, and the supported metrics from the source report
- **AND** the stored record remains queryable later without re-reading the source CSV

#### Scenario: Synthetic summary rows are not stored as normal function records
- **WHEN** the source file contains export noise or synthetic rows such as report titles, footer stamps, or `Totais`
- **THEN** the ingestion flow does not persist those lines as ordinary `funcao` records in the dedicated table
- **AND** public totals can still be derived from the stored function rows without double counting

### Requirement: Re-importing the same `despesas-por-funcao` report is idempotent by report identity
The system MUST allow supported `despesas-por-funcao` files to be re-imported without duplicating the same report/function lineage, while refreshing persisted values when the source payload changed.

#### Scenario: Re-import updates an existing function row
- **WHEN** the ingestion flow processes a supported `despesas-por-funcao` row whose report identity already exists in the local SQL database
- **THEN** the system updates the existing stored record when imported values changed
- **AND** it does not create a duplicate persisted row for that same report/function identity

#### Scenario: Re-import leaves unchanged function rows stable
- **WHEN** the ingestion flow reprocesses a supported `despesas-por-funcao` row and the normalized payload did not change
- **THEN** the previously stored SQL row remains the authoritative record for that lineage
- **AND** the re-import does not create duplicate records or drift in the stored values
