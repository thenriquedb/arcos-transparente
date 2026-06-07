## Why

The chatbot runtime still mixes hard-coded agent defaults with partially documented environment variables, which makes local setup fragile and lets the README drift away from the real runtime contract. We need one explicit `.env`-driven configuration path for provider, model, and API key so contributors can configure the agent without reading source code.

## What Changes

- Move the chatbot's provider, model, and API-key selection to a documented environment-variable contract loaded from `.env`.
- Consolidate the runtime around canonical agent configuration variables instead of relying on scattered aliases and hard-coded model defaults.
- Add a root `.env.example` that shows the required and optional agent settings alongside the existing project environment variables.
- Update the README and related setup docs so the documented agent configuration matches the runtime behavior.

## Capabilities

### New Capabilities
- `agent-runtime-configuration`: Define the required environment-based contract for configuring the chatbot provider, model, and credentials, including setup documentation and example env scaffolding.

### Modified Capabilities
- None.

## Impact

- Affected code: `agents/chatbot/agent.py` and any shared configuration helpers introduced for agent bootstrap.
- Affected docs: `README.md`, `.env.example`, and any setup docs that currently document incomplete or outdated agent configuration.
- Operational impact: local and deployed environments will need to provide the documented agent env vars consistently through `.env` or equivalent environment injection.
