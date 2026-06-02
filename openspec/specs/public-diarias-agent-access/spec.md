# public-diarias-agent-access Specification

## Purpose
TBD - created by archiving change extend-diarias-ingestion-and-agent-tools. Update Purpose after archive.
## Requirements
### Requirement: Public `diarias` tools expose imported travel-allowance records from SQL
The system MUST expose imported `diarias` data through dedicated public SQL tools for lookup and aggregation, rather than relying only on generic `despesas` text filtering.

#### Scenario: Lookup tool returns imported `diarias` records with travel fields
- **WHEN** imported `diarias` records in the local SQL database match supported lookup filters such as year, origin, beneficiary, destination, trip period, or travel objective
- **THEN** the public lookup capability returns the matching `diarias` records from SQL
- **AND** the response can include the supported travel-specific fields exposed by the public contract

#### Scenario: Aggregation tool summarizes imported `diarias` data
- **WHEN** imported `diarias` records in the local SQL database match an aggregation query for totals, counts, or rankings
- **THEN** the public aggregation capability computes the requested result from the persisted SQL data
- **AND** the result reflects the dedicated `diarias` contract rather than a generic expense-text fallback

### Requirement: The citizen-facing agent uses the dedicated `diarias` tool path for structured per-diem questions
The chatbot MUST treat supported questions about travel allowances as an in-scope SQL transparency domain and answer them through the public `diarias` tools backed by the local database.

#### Scenario: User asks for individual `diarias` records
- **WHEN** a user asks for specific `diarias` entries or travel details such as destination, beneficiary, trip dates, or objective
- **THEN** the agent keeps the request inside the supported public-data scope
- **AND** it answers through the dedicated `diarias` lookup capability instead of generic free-form reasoning

#### Scenario: User asks for totals or rankings over `diarias`
- **WHEN** a user asks for total spending, counts, or rankings about `diarias`
- **THEN** the agent keeps the request inside the supported public-data scope
- **AND** it answers through the dedicated `diarias` aggregation capability as the SQL source of truth

### Requirement: Dedicated `diarias` tools remain auditable within the public tool registry
The public tool registry, routing layer, and prompt contracts MUST keep the supported `diarias` tools discoverable to the citizen-facing agent so structured per-diem answers come from local SQL data.

#### Scenario: Public tool set includes the dedicated `diarias` capabilities
- **WHEN** the citizen-facing agent is initialized with the public tool registry
- **THEN** the supported dedicated `diarias` lookup and aggregation capabilities are available in the public tool set
- **AND** they remain tagged and documented as part of the public transparency domain

#### Scenario: `Diarias` questions prefer dedicated tools over generic expense fallbacks
- **WHEN** the user asks a structured question that clearly targets `diarias`
- **THEN** the routing and prompt contracts prefer the dedicated `diarias` tool path
- **AND** the answer does not depend solely on generic `despesas` description matching when a dedicated `diarias` capability is available

