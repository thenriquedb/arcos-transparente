## Why

The codebase already has a `shared/` area, but many common methods and helper functions still live as local duplicates across ingestion schemas and SQL tool schemas. This duplication makes refactors slower, increases the chance of inconsistent validation behavior, and obscures which helpers are truly generic versus context-specific.

## What Changes

- Extract repeated pure helper functions and normalization methods into dedicated shared folders organized by scope and ownership.
- Standardize where reusable helpers belong:
  - cross-cutting helpers in top-level `shared/`
  - bounded-context helpers in local `shared/` folders near the owning subsystem
- Replace local duplicate implementations with imports from the new shared modules while preserving current external behavior and validation semantics.
- Add regression coverage around representative extracted helpers so the refactor does not silently change parsing, normalization, or metadata behavior.
- Document the folder-placement rules so future utilities are added to the right shared location instead of being copied again.

## Capabilities

### New Capabilities
- `shared-utility-extraction`: Defines how duplicated pure methods and functions are moved into separated shared folders with clear ownership, stable behavior, and consistent reuse across modules.

### Modified Capabilities
- None.

## Impact

- Affected code: `shared/utils/*`, ingestion schema modules, SQL tool schema/filter modules, and any runtime modules updated to consume extracted helpers.
- Affected behavior: text normalization, numeric/date parsing, field-list validation, metadata serialization, and other repeated pure utility behavior.
- Affected docs: contributor-facing guidance about where shared utilities belong.
- Risk areas: behavior drift during extraction, over-generalizing domain-specific helpers, and creating shared modules with unclear boundaries.
