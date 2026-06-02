## ADDED Requirements

### Requirement: Public `passagens` tools expose imported passagens records from SQL
The system MUST expose imported `passagens` data through dedicated public SQL tools for lookup and aggregation, rather than relying only on generic `despesas` text filtering.

#### Scenario: Lookup tool returns imported `passagens` records with supported fields
- **WHEN** imported `passagens` records in the local SQL database match supported lookup filters such as year, origin, beneficiary, report period, or category
- **THEN** the public lookup capability returns the matching `passagens` records from SQL
- **AND** the response includes only the supported source-backed fields exposed by the public contract

#### Scenario: Aggregation tool summarizes imported `passagens` data
- **WHEN** imported `passagens` records in the local SQL database match an aggregation query for totals, counts, or rankings
- **THEN** the public aggregation capability computes the requested result from the persisted SQL data
- **AND** the result reflects the dedicated `passagens` contract rather than a generic expense-text fallback

### Requirement: The citizen-facing agent uses the dedicated `passagens` tool path for structured travel-fare questions
The chatbot MUST treat supported questions about `passagens` and locomotion spending as an in-scope SQL transparency domain and answer them through the public `passagens` tools backed by the local database.

#### Scenario: User asks for individual `passagens` records
- **WHEN** a user asks for specific `passagens` entries or beneficiary/payment details
- **THEN** the agent keeps the request inside the supported public-data scope
- **AND** it answers through the dedicated `passagens` lookup capability instead of generic free-form reasoning

#### Scenario: User asks for totals or rankings over `passagens`
- **WHEN** a user asks for total spending, counts, or rankings about `passagens`
- **THEN** the agent keeps the request inside the supported public-data scope
- **AND** it answers through the dedicated `passagens` aggregation capability as the SQL source of truth

### Requirement: Dedicated `passagens` tools remain auditable within the public tool registry
The public tool registry, routing layer, and prompt contracts MUST keep the supported `passagens` tools discoverable to the citizen-facing agent so structured passagens answers come from local SQL data.

#### Scenario: Public tool set includes the dedicated `passagens` capabilities
- **WHEN** the citizen-facing agent is initialized with the public tool registry
- **THEN** the supported dedicated `passagens` lookup and aggregation capabilities are available in the public tool set
- **AND** they remain tagged and documented as part of the public transparency domain

#### Scenario: `Passagens` questions prefer dedicated tools over generic expense fallbacks
- **WHEN** the user asks a structured question that clearly targets `passagens`
- **THEN** the routing and prompt contracts prefer the dedicated `passagens` tool path
- **AND** the answer does not depend solely on generic `despesas` description matching when a dedicated `passagens` capability is available
