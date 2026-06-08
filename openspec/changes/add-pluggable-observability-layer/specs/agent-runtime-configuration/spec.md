## ADDED Requirements

### Requirement: Chatbot bootstrap supports environment-defined observability settings
The chatbot runtime MUST load observability enablement and provider selection from environment variables loaded through the project's `.env` workflow. It MUST keep observability optional by default, but it MUST validate provider-specific settings when observability is explicitly enabled.

#### Scenario: Unconfigured observability falls back to no-op
- **WHEN** `OBSERVABILITY_ENABLED` is unset or false and no observability provider is explicitly selected
- **THEN** the chatbot bootstrap configures the runtime with the no-op observability provider
- **AND** the chatbot remains usable without any LangSmith credentials

#### Scenario: Bootstrap accepts configured LangSmith observability
- **WHEN** the environment defines `OBSERVABILITY_ENABLED=true`, `OBSERVABILITY_PROVIDER=langsmith`, and the required LangSmith settings
- **THEN** the chatbot bootstrap configures the runtime with the LangSmith observability provider
- **AND** the runtime records `langsmith` as the selected observability provider

#### Scenario: Missing LangSmith setting is rejected when observability is enabled
- **WHEN** `OBSERVABILITY_ENABLED=true` and `OBSERVABILITY_PROVIDER=langsmith` but a required LangSmith setting such as `LANGSMITH_API_KEY` is missing or blank
- **THEN** the bootstrap fails fast with a clear validation error naming the missing setting
- **AND** it does not silently downgrade to no-op observability

#### Scenario: Unsupported observability provider is rejected explicitly
- **WHEN** `OBSERVABILITY_ENABLED=true` and `OBSERVABILITY_PROVIDER` is set to an unsupported provider value
- **THEN** the bootstrap fails fast with a clear unsupported-provider error
- **AND** the error identifies the supported observability providers for the current phase

## MODIFIED Requirements

### Requirement: Repository documents the canonical agent env contract
The repository MUST provide a checked-in environment example and onboarding documentation that describe the same agent and observability configuration contracts enforced by the chatbot runtime.

#### Scenario: Example env file includes agent and observability bootstrap settings
- **WHEN** a contributor opens the root `.env.example`
- **THEN** the file includes the documented chatbot settings for `LLM_PROVIDER`, `OPENAI_MODEL`, and `OPENAI_API_KEY`
- **AND** it includes the canonical observability settings for enablement, provider selection, and provider-specific LangSmith configuration
- **AND** it includes any existing core project environment entries needed for local setup

#### Scenario: README points developers to the env workflow for tracing
- **WHEN** a contributor follows the agent setup section in `README.md`
- **THEN** the README instructs them to create `.env` from the example file or equivalent values
- **AND** it documents the canonical provider, model, and API-key variable names expected by the chatbot runtime
- **AND** it documents how observability is enabled, which observability provider values are supported, and which LangSmith settings are required when tracing is enabled
- **AND** it states that OpenAI is the only supported LLM provider in the current phase
