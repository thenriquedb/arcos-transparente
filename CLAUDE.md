# Arcos Transparente

Citizen-facing transparency chatbot over ingested municipal public data. See `CONTEXT.md` for the project's domain language and `docs/` for architecture notes.

## Agent skills

### Issue tracker

Issues are tracked as GitHub issues in `thenriquedb/arcos-transparente` via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
