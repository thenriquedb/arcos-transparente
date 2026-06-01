# xml-ingestion-sanitization Specification

## Purpose
TBD - created by archiving change sanitize-iso-8859-1-xml-ingestion. Update Purpose after archive.
## Requirements
### Requirement: XML ingestion decodes source files as ISO-8859-1
The system SHALL read XML source files using `ISO-8859-1` before parser-specific extraction logic runs, so XML-derived text is interpreted consistently across ingestion parser implementations.

#### Scenario: Accented text is decoded consistently from an ISO-8859-1 XML file
- **WHEN** an ingestion parser processes an XML file whose bytes contain accented Latin characters encoded as `ISO-8859-1`
- **THEN** the extracted text values preserve those characters correctly
- **AND** the result does not depend on whether the parser uses tree traversal or block-based text extraction

#### Scenario: Parser input does not depend on XML declaration-driven decoding
- **WHEN** two XML parser entrypoints process files from the same ingestion source family
- **THEN** both entrypoints obtain their source text through the same `ISO-8859-1` decoding contract
- **AND** they do not rely on parser-specific default file decoding behavior

### Requirement: XML-derived text is sanitized before database storage
The system SHALL remove invalid control characters from XML-derived string content before any record is stored in the database, while preserving normal whitespace and valid Latin text produced by `ISO-8859-1` decoding.

#### Scenario: Invalid control characters are stripped from ordinary text fields
- **WHEN** a parsed XML payload contains invalid control characters in a text field that maps to a database column
- **THEN** the persisted value excludes those invalid characters
- **AND** the remaining visible text content is preserved in order

#### Scenario: Sanitization preserves expected whitespace
- **WHEN** an XML-derived text field contains line breaks, carriage returns, or tabs alongside invalid control characters
- **THEN** the invalid control characters are removed before persistence
- **AND** the permitted whitespace characters remain available in the stored value

### Requirement: Persistence safety applies to all XML ingestion write paths
The no-invalid-characters guarantee SHALL apply to every XML ingestion persistence path, including generic loader-based entities, contract-specific persistence flows, nested child collections, and stored raw XML snapshots such as `xml_original`.

#### Scenario: Generic SQL loader persists sanitized XML-derived values
- **WHEN** an XML parser sends a record with unsafe text content through the generic SQL loader
- **THEN** the loader persists only sanitized string values
- **AND** no invalid characters from the XML payload are stored in the database row

#### Scenario: Custom contract persistence sanitizes nested fields and raw XML snapshots
- **WHEN** the contracts ingestion flow prepares `Contrato`, child collection rows, or `xml_original` content containing invalid characters
- **THEN** each persisted string value is sanitized before insertion or update
- **AND** the database does not retain invalid characters in either top-level or nested contract data

