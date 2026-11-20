## MODIFIED Requirements

### Requirement: Organize the service into stage subpackages

The service code SHALL live in a single package, `rfc_qa`, in the `src/` directory at the repository
root, with one subpackage each for ingestion, retrieval and generation. Code shared by several
stages, and the query interface that combines retrieval and generation, SHALL live at the package
top level. No service module SHALL remain at the repository root.

#### Scenario: Stages importable from their subpackages

- **WHEN** code imports the ingestion, retrieval or generation functionality
- **THEN** it imports it from `rfc_qa.ingestion`, `rfc_qa.retrieval` or `rfc_qa.generation` respectively

#### Scenario: Query interface at the package top level

- **WHEN** code imports the programmatic query entry point
- **THEN** it imports it from `rfc_qa.query`

#### Scenario: No service modules at the root

- **WHEN** the repository root is listed
- **THEN** it contains no Python modules of the service and no package directory, only the source directory, the configuration directory, documentation, tests and release scripts

#### Scenario: Package in the source directory

- **WHEN** the `src/` directory at the repository root is listed
- **THEN** it contains the `rfc_qa` package, and the import paths are the same as before the package moved there

### Requirement: Run the commands as modules

Each command SHALL also be runnable as a Python module once the project is installed, from any
directory, for example `python -m rfc_qa.query`. The package SHALL only be importable as installed,
so an uninstalled checkout is never run by accident.

#### Scenario: Module run from the repository root

- **WHEN** `python -m rfc_qa.ingestion.ingest` is run from the repository root with the project installed
- **THEN** it behaves the same as `rfc-ingest`

#### Scenario: Module run from another directory

- **WHEN** `python -m rfc_qa.query` is run from a directory other than the repository root with the project installed
- **THEN** it behaves the same as `rfc-query`, including reading `config/` and `data/` at the repository root by default

#### Scenario: Uninstalled checkout

- **WHEN** `python -m rfc_qa.query` is run from the repository root in an environment where the project isn't installed
- **THEN** Python reports that `rfc_qa` can't be found, instead of running the code in the checkout
