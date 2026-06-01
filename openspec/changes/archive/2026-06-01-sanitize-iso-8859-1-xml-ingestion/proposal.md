## Why

The XML ingestion flow currently mixes decoding strategies: some parsers rely on `ET.parse`, others force `ISO-8859-1`, and one path falls back to `cp1252`. That inconsistency makes imported text depend on the parser entrypoint and increases the risk that malformed control characters or broken bytes end up persisted in the database, especially in audit fields such as `xml_original`.

## What Changes

- Standardize XML file reading so ingestion inputs are decoded as `ISO-8859-1` before parser-specific extraction logic runs.
- Introduce a shared sanitization rule for XML-derived text that removes database-invalid characters before records are validated or persisted.
- Apply the decoding and sanitization flow consistently across all XML parsers, including paths that preserve raw XML fragments for audit or search fallback.
- Add regression coverage for representative `ISO-8859-1` inputs, malformed XML text, and records that previously could carry invalid characters into storage.
- Document the ingestion contract so future XML parsers use the same decode-and-sanitize path by default.

## Capabilities

### New Capabilities
- `xml-ingestion-sanitization`: Defines how XML files are decoded with `ISO-8859-1` and how invalid characters are stripped before XML-derived content is stored in the database.

### Modified Capabilities
- None.

## Impact

- Affected code: `ingestion/parsers/xml/*`, shared ingestion utilities, `ingestion/loaders/sql_loader.py`, and contract-specific persistence paths in `ingestion/pipeline.py`.
- Affected behavior: XML decoding, parser input normalization, `xml_original` preservation, and text persistence safety for all database-backed ingestion entities.
- Affected tests/docs: parser and pipeline regression tests plus ingestion documentation that describes XML import expectations.
- Risk areas: changing effective decoded text for files that previously relied on XML declarations or `cp1252`, over-sanitizing legitimate content, and drifting between parser-level and loader-level guarantees.
