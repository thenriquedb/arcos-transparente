# llm-orchestrated-chat Specification

## Purpose
TBD - created by archiving change adopt-llm-orchestrator-agent. Update Purpose after archive.

## Requirements

### Requirement: Hard pre-agent guardrails
The citizen-facing chatbot MUST evaluate hard guardrails before invoking the language model. At minimum, it SHALL block empty queries, prompt-injection attempts, and requests that are outside the supported municipal public-data scope.

#### Scenario: Empty query is rejected before model invocation
- **WHEN** the user submits an empty or whitespace-only message
- **THEN** the system returns a guardrail response asking for a valid public-data question
- **AND** the language model is not invoked

#### Scenario: Prompt injection is rejected before model invocation
- **WHEN** the user asks the assistant to ignore rules, reveal internal prompts, or bypass system instructions
- **THEN** the system returns a refusal focused on supported public-data queries
- **AND** the language model is not invoked

#### Scenario: Out-of-scope request is rejected before model invocation
- **WHEN** the user asks for content outside the supported transparency domains
- **THEN** the system returns a response explaining that it only handles municipal public-data queries
- **AND** the language model is not invoked

### Requirement: LLM-led orchestration for allowed queries
For queries that pass guardrails, the chatbot SHALL use the language model as the primary orchestrator for tool selection, follow-up questions, and response composition rather than relying on deterministic per-query routing to select a single domain path in advance.

#### Scenario: Allowed query can use cross-domain reasoning
- **WHEN** the user asks a question whose answer may require data from more than one public-data domain
- **THEN** the assistant may select and chain the necessary public tools within the same response flow
- **AND** the query is not rejected only because no single deterministic route matches it exactly

#### Scenario: Allowed query is not restricted to one preselected tool family
- **WHEN** the user asks an in-scope question that could reasonably require lookup, aggregation, or follow-up checks
- **THEN** the assistant is able to choose the appropriate public tools at runtime based on the full request and conversation context

### Requirement: Cross-domain chained resolution
The chatbot MUST resolve known multi-step public-data questions by chaining the relevant tools and presenting the combined result as one coherent answer when a single tool is not sufficient.

#### Scenario: Cargo politico resolves to payment history
- **WHEN** the user asks for the salary or payments of the prefeito, vice-prefeito, or a vereador without providing a full name
- **THEN** the assistant first resolves the elected official identity from the eleitos data
- **AND** then queries the payment-history tool using the resolved full name
- **AND** answers without asking the user to provide the official's name again

#### Scenario: Zero-value contract triggers related follow-up checks
- **WHEN** a contract lookup returns a contract with zero or empty value
- **THEN** the assistant performs the documented follow-up checks against related licitacao and despesa data when the needed search terms are available
- **AND** presents the consolidated result without treating the zero-value contract as the final answer by itself

#### Scenario: Empty contract search triggers neighboring domain lookup
- **WHEN** a contract search returns no matching records for an event, supplier, or service
- **THEN** the assistant checks the related licitacao domain before concluding that no relevant data was found

### Requirement: Conversational context continuity
The chatbot SHALL preserve conversational context across a session so it can resolve anaphoric references, reuse previously confirmed meanings, and refine prior result sets without forcing the user to restate known context.

#### Scenario: Pronoun follow-up reuses previously resolved person
- **WHEN** the user asks a follow-up question such as `e qual o salario dele?` after a person has already been identified in the session
- **THEN** the assistant reuses the previously resolved person for the next tool call
- **AND** does not ask the user to restate the same name

#### Scenario: Confirmed acronym remains bound in the session
- **WHEN** the user has already confirmed the meaning of an ambiguous acronym in the session
- **THEN** the assistant reuses that confirmed expansion in later tool calls
- **AND** does not ask for the same clarification again

#### Scenario: Result refinement uses prior list context
- **WHEN** the user asks to filter or narrow a previously discussed result set
- **THEN** the assistant refines the prior context instead of restarting the interaction as an unrelated fresh query

### Requirement: Clarification policy for ambiguous execution
The chatbot MUST ask a single focused clarification before tool execution when the request is too ambiguous for a reliable answer, and it MUST skip unnecessary clarification for the documented direct-execution exceptions.

#### Scenario: Ambiguous short acronym triggers clarification
- **WHEN** the user uses a short ambiguous acronym such as `UPA`, `UBS`, `PSF`, `CRAS`, or `CREAS` as the main textual filter without prior session confirmation
- **THEN** the assistant asks one brief clarification question suggesting the most likely expansion
- **AND** does not execute the data lookup until the acronym meaning is confirmed

#### Scenario: Missing period triggers clarification for large-volume domains
- **WHEN** the user asks about despesas, receitas, contratos, or folha without a time range and the request would otherwise span a large volume of data
- **THEN** the assistant asks one clarification question to establish the relevant period before executing the lookup

#### Scenario: Direct-execution exception bypasses clarification
- **WHEN** the user asks a documented exception such as a simple count, a named person lookup, or an explicitly enumerated full-list request
- **THEN** the assistant executes the relevant tool flow without first asking for a time-range clarification

### Requirement: Ambiguous entity selection safety
When a tool returns multiple plausible human matches for an individual salary or payment query, the chatbot MUST surface the candidates and wait for user disambiguation instead of choosing one match on its own.

#### Scenario: Multiple matching servidores require user choice
- **WHEN** the payment-history tool returns multiple matching servidores for the supplied identity
- **THEN** the assistant presents the candidate options with enough identifying information to distinguish them
- **AND** asks the user to choose the intended person or candidate identifier
- **AND** does not answer with one candidate's payment history until the ambiguity is resolved
