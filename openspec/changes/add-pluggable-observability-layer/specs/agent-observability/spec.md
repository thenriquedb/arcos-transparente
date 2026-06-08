## ADDED Requirements

### Requirement: Chatbot runtime uses a pluggable observability provider
The chatbot runtime MUST resolve observability through a runtime-owned provider interface rather than coupling core orchestration code directly to LangSmith APIs. It MUST support a no-op provider when observability is disabled and a LangSmith-backed provider when LangSmith observability is enabled.

#### Scenario: Disabled observability uses the no-op provider
- **WHEN** observability is disabled or no observability provider is configured
- **THEN** the chatbot runtime uses a no-op observability provider
- **AND** allowed and blocked queries continue to execute with the same functional behavior as an uninstrumented runtime

#### Scenario: LangSmith mode uses a provider adapter
- **WHEN** observability is enabled with the `langsmith` provider and the required provider settings are present
- **THEN** the chatbot runtime constructs a LangSmith-backed observability adapter through the shared provider boundary
- **AND** the rest of the runtime depends only on the shared observability contract rather than LangSmith-specific calls at each orchestration site

### Requirement: Query lifecycle stages are observable end to end
The chatbot runtime MUST emit observability events or spans for the main lifecycle stages of a user query, including deterministic policy outcome, hybrid selection outcome, agent/backend execution, tool execution, and final success or failure.

#### Scenario: Blocked query records guardrail outcome without agent execution
- **WHEN** a user query is blocked by deterministic policy before tool selection or agent invocation
- **THEN** observability records the blocked request outcome and policy category
- **AND** it does not record a downstream agent-execution stage for that request

#### Scenario: Allowed query records selection and execution stages
- **WHEN** a user query passes policy checks and executes through the chatbot runtime
- **THEN** observability records the request lifecycle with correlation identifiers for the chat request or session
- **AND** it records the hybrid selection outcome, including fallback reason codes when fallback occurs
- **AND** it records the executed public tool names and backend completion outcome

#### Scenario: Tool failure records a failure stage
- **WHEN** a selected tool or backend execution raises an error during a chatbot request
- **THEN** observability records a failure stage for the affected request or tool execution
- **AND** the runtime still follows its existing user-facing error handling path

### Requirement: Observability payloads use a sanitized runtime event model
The system MUST export observability data through an allowlisted runtime event model so provider adapters receive only approved request, decision, tool, and error metadata.

#### Scenario: Observability metadata omits secrets
- **WHEN** the runtime emits observability data for a request
- **THEN** the exported payload includes only allowlisted metadata such as session identifiers, tool names, policy categories, selection reason codes, and execution status
- **AND** it does not include provider credentials, raw environment secrets, or arbitrary runtime objects

#### Scenario: Provider adapters receive provider-neutral event data
- **WHEN** the runtime emits an observability event for a request stage
- **THEN** the shared event model is translated to provider-specific metadata inside the active adapter
- **AND** runtime orchestration modules do not need to change their event shape when a different observability provider is added later
