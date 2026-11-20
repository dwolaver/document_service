## ADDED Requirements

### Requirement: Verify a regular install outside the checkout

The automated checks SHALL build a wheel from the proposed change, install it as a regular install
into a fresh environment, and run `rfc-ingest`, `rfc-search` and `rfc-query` from a directory outside
the repository, without selecting a configuration or data directory. They SHALL fail when a command
can't run without the checkout. This check SHALL NOT need network access to document sources or a
model.

#### Scenario: Package data missing from the wheel

- **WHEN** a packaged configuration file is left out of the built wheel
- **THEN** the automated checks report failure

#### Scenario: Code reads the checkout

- **WHEN** a command's default refers to a file in the repository instead of the installed package or the user data directory
- **THEN** the automated checks report failure

#### Scenario: Commands work from a regular install

- **WHEN** the installed commands build an index from RFC files already in the data directory, search it, and run a query with no model reachable
- **THEN** ingestion and search succeed, the query fails with the model-unavailable error rather than a configuration or missing-index error, and the automated checks report success
