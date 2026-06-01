## Context

The current XML ingestion flow is inconsistent about how source files are decoded. `LicitacoesParser` already forces `iso-8859-1`, `QuadroPessoalParser` reads text with `ISO-8859-1`, `FrotasParser` re-reads content as `cp1252`, and several other parsers delegate directly to `ET.parse(filepath)`. That means two XML files with the same byte content can be interpreted differently depending on which parser handles them.

The code also has no single boundary that guarantees persisted strings are free of invalid control characters. Most parsers assemble Python dictionaries and trust downstream validation, while `SQLLoader` currently normalizes numeric/date types but passes strings through unchanged. Contracts are even more exposed because `_load_contratos` writes payloads and nested child rows without going through `SQLLoader`.

This change needs to unify XML decoding and make database-safe text persistence an invariant of the ingestion pipeline, not a best effort inside individual parsers.

## Goals / Non-Goals

**Goals:**
- Ensure XML ingestion reads source files with `ISO-8859-1` consistently across parser entrypoints.
- Remove invalid database characters from XML-derived text before any record is persisted.
- Cover both regular loader-based persistence and custom contract-loading paths.
- Preserve the current record shapes and business mapping logic while improving input safety.
- Add regression coverage for representative parser, pipeline, and persistence edge cases.

**Non-Goals:**
- Reworking field mappings, schema definitions, or business validation rules unrelated to encoding and text safety.
- Expanding support for multiple source encodings beyond the explicitly requested `ISO-8859-1` contract.
- Preserving byte-for-byte raw XML when it contains characters that violate the new storage safety rules.
- Solving unrelated malformed XML structure issues beyond what is necessary to decode and sanitize text safely.

## Decisions

### 1. Introduce a shared XML input helper for ingestion parsers

Add an ingestion-local helper module for XML parsing utilities, scoped to `ingestion/parsers/xml/`, that:
- reads file bytes,
- decodes them as `ISO-8859-1`,
- strips characters that are invalid for persisted text and unsafe for XML parsing,
- builds the `ElementTree` root or returns sanitized text for regex/block-based parsers.

Rationale:
- The behavior should be consistent for all XML parsers without duplicating file I/O logic.
- This is an ingestion concern, so a local shared module is a better fit than a top-level generic utility.

Alternatives considered:
- Keep using `ET.parse(filepath)` and rely on XML declarations: rejected because current sources already require manual `ISO-8859-1` handling in multiple places.
- Let each parser choose its own decoding strategy: rejected because it preserves the inconsistency the user wants removed.
- Standardize on `cp1252`: rejected because the requested contract is explicitly `ISO-8859-1`.

### 2. Sanitize text at the persistence boundary as a second line of defense

Add a recursive text-sanitization helper that removes invalid control characters from strings inside dictionaries, lists, and raw XML snapshots. Apply it:
- before parser payloads are handed to model constructors or DB models when practical,
- inside `SQLLoader._normalize_and_validate` for all string-backed columns,
- inside the custom `_load_contratos` path before writing `Contrato` and child-row fields.

Rationale:
- Parser-level sanitization improves consistency, but a DB-boundary guarantee is what actually enforces “no invalid characters stored in the database.”
- Contracts bypass the generic loader, so the guarantee must cover both persistence paths.

Alternatives considered:
- Sanitize only inside parsers: rejected because a missed field or future parser could still leak unsafe text.
- Sanitize only inside the loader: rejected because parser-specific fields like `xml_original` and malformed source fragments benefit from earlier cleanup before validation and serialization.

### 3. Define “invalid characters” as control characters excluded from safe persisted text

The sanitization rule will remove control characters that do not belong in normal persisted text, especially NUL and other non-printable control codes, while preserving common whitespace that users expect (`\\n`, `\\r`, `\\t`) and valid Latin characters produced by `ISO-8859-1` decoding.

Rationale:
- The primary failure mode is polluted text fields or DB driver/storage issues caused by control bytes, not accented Latin characters.
- Preserving expected whitespace minimizes behavioral drift in audit fields and free-text descriptions.

Alternatives considered:
- Normalize or transliterate accented characters: rejected because the request is about safe storage, not lossy normalization.
- Replace invalid characters with placeholders: rejected because silent replacement introduces content that never existed in the source and complicates downstream search.

### 4. Preserve current parser outputs while centralizing decode-and-parse behavior

Each XML parser will keep its existing field extraction and Pydantic validation logic. The implementation will change only how source XML/text is obtained and how string values are sanitized before persistence.

Rationale:
- This isolates the change to encoding and storage safety.
- It reduces regression risk in a pipeline that already has source-specific business mapping logic.

Alternatives considered:
- Refactor all parsers into a shared base class in the same change: rejected because it mixes structural refactor with a behavioral safety fix.

### 5. Add regression tests at parser and pipeline boundaries

Coverage will include:
- parser tests proving `ISO-8859-1` decoding works consistently for representative XML files,
- sanitization tests proving invalid control characters are removed from ordinary fields and `xml_original`,
- pipeline/loader tests proving persisted records no longer contain invalid characters even when input payloads do.

Rationale:
- The requirement is a behavior guarantee, so tests need to assert the invariant where data enters and where it is stored.

Alternatives considered:
- Unit-test only the shared helper: rejected because the most important guarantee is integration behavior across ingestion and persistence.

## Risks / Trade-offs

- [Risk] Forcing `ISO-8859-1` may change the interpreted text for files that previously depended on XML declaration handling or `cp1252` quirks. -> Mitigation: cover representative fixtures and call out `cp1252` removal explicitly in review and tests.
- [Risk] Sanitization could strip characters that a downstream consumer expected to see verbatim in `xml_original`. -> Mitigation: scope removal to invalid control characters only and preserve normal whitespace plus valid Latin text.
- [Risk] Applying sanitization in both parser and persistence layers can create duplicate logic or confusion. -> Mitigation: centralize the logic in one shared helper and call it from both layers rather than duplicating regexes.
- [Risk] Nested child collections in contracts may still bypass the guarantee if only top-level payloads are cleaned. -> Mitigation: use recursive sanitization for dict/list payloads and add nested contract coverage.

## Migration Plan

1. Add shared XML reader/sanitizer helpers under the ingestion XML parser area.
2. Update XML parsers to obtain roots or raw text through the shared `ISO-8859-1` path.
3. Add recursive payload sanitization at the persistence boundary in `SQLLoader` and the custom contract loader path.
4. Update or add regression tests for representative parsers, `xml_original`, and persisted records with invalid control characters.
5. Document the new ingestion contract for future XML parser additions.

Rollback strategy:
- Revert the shared helper adoption and persistence-boundary sanitization if the change causes unacceptable text regressions.
- Because the change is internal to ingestion, rollback is limited to code and test reversion without external API migration.

## Open Questions

- Should the same sanitization helper be reused later by non-XML ingestion sources, or stay explicitly scoped to XML-driven persistence for now?
