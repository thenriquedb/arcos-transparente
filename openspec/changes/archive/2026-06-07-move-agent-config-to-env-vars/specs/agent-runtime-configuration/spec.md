## ADDED Requirements

### Requirement: Chatbot bootstrap uses environment-defined runtime settings
The chatbot bootstrap MUST load its provider, model, and API-key settings from environment variables loaded through the project's `.env` workflow instead of relying on hard-coded runtime defaults.

#### Scenario: Bootstrap uses configured OpenAI runtime values
- **WHEN** the environment defines `LLM_PROVIDER=openai`, a non-empty `OPENAI_MODEL`, and a non-empty `OPENAI_API_KEY`
- **THEN** the chatbot bootstrap creates the LLM client with the configured model
- **AND** the runtime records `openai` as the selected provider

#### Scenario: Missing model is rejected before agent creation
- **WHEN** `OPENAI_MODEL` is missing or blank at chatbot bootstrap time
- **THEN** the bootstrap fails fast with a clear validation error
- **AND** the agent is not created with an implicit fallback model

#### Scenario: Missing API key is rejected before agent creation
- **WHEN** `OPENAI_API_KEY` is missing or blank at chatbot bootstrap time
- **THEN** the bootstrap fails fast with a clear validation error naming `OPENAI_API_KEY`
- **AND** the agent is not created

#### Scenario: Unsupported provider is rejected explicitly
- **WHEN** `LLM_PROVIDER` is set to a provider value other than `openai`
- **THEN** the bootstrap fails fast with a clear unsupported-provider error
- **AND** the error explains that `openai` is the supported provider in the current phase

### Requirement: Repository documents the canonical agent env contract
The repository MUST provide a checked-in environment example and onboarding documentation that describe the same agent configuration contract enforced by the chatbot runtime.

#### Scenario: Example env file includes agent bootstrap settings
- **WHEN** a contributor opens the root `.env.example`
- **THEN** the file includes the documented chatbot settings for `LLM_PROVIDER`, `OPENAI_MODEL`, and `OPENAI_API_KEY`
- **AND** it includes any existing core project environment entries needed for local setup

#### Scenario: README points developers to the example env workflow
- **WHEN** a contributor follows the agent setup section in `README.md`
- **THEN** the README instructs them to create `.env` from the example file or equivalent values
- **AND** it documents the canonical provider, model, and API-key variable names expected by the chatbot runtime
- **AND** it states that OpenAI is the only supported provider in the current phase
