## MODIFIED Requirements

### Requirement: Report invalid ingestion inputs as configuration errors

A corpus manifest or ingestion configuration that can't be read, isn't valid TOML or breaks one of its
rules SHALL raise `ConfigError`, with a message naming the file and, where there is one, the value.
A problem with the corpus content during a run, such as an RFC that yields no chunks, SHALL raise
`IngestError`, and so SHALL an RFC file that can't be read.

#### Scenario: Invalid manifest

- **WHEN** ingestion reads a manifest with a duplicate RFC or an unknown family
- **THEN** it raises `ConfigError` naming the problem, before downloading anything

#### Scenario: Unreadable RFC file

- **WHEN** a stored RFC file can't be read
- **THEN** ingestion raises `IngestError` naming the RFC, with the operating system error as its cause, and writes no index

#### Scenario: Manifest that isn't TOML

- **WHEN** ingestion reads a manifest that isn't valid TOML
- **THEN** it raises `ConfigError` naming the file and the line and column of the problem, with the parser's error as its cause, before downloading anything
