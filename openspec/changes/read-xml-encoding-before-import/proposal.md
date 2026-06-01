## Why

The current XML ingestion flow always decodes source files as `ISO-8859-1`, even when the XML declaration advertises a different encoding. That makes imports depend on a hard-coded assumption instead of the source contract and can corrupt accented text or symbols when files arrive with another declared charset.

## What Changes

- Replace the shared XML input contract that forces `ISO-8859-1` with an encoding-aware reader that inspects the XML declaration before decoding parser input.
- Keep the existing sanitization guarantees, but apply them after decoding with the resolved source encoding so stored text remains valid without losing characters from correctly declared files.
- Update parser, pipeline, and documentation expectations to describe the new fallback behavior when the XML declaration is absent or unusable.
- Add regression coverage for declared encodings, missing declarations, and unsupported declarations so imports fail or fall back consistently.

## Capabilities

### New Capabilities
- `xml-encoding-aware-ingestion`: Defines how XML imports resolve source encoding from the XML declaration before parsing and sanitizing payloads.

### Modified Capabilities

## Impact

- Affected code: `ingestion/parsers/xml/shared.py`, XML parser entrypoints under `ingestion/parsers/xml/`, and any ingestion path that currently assumes `ISO-8859-1`.
- Affected behavior: XML decoding, parser input normalization, stored `xml_original` content, and documentation for adding new XML parsers.
- Risk surface: files without declarations or with invalid declarations now need an explicit fallback/error policy instead of silently following the global `ISO-8859-1` default.
