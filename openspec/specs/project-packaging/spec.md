# project-packaging Specification

## Purpose

Defines how the service's code is organized into a package with one subpackage per stage, how the
project is installed, which commands it provides, and where those commands find configuration and
data.

## Requirements

### Requirement: Organize the service into stage subpackages

The service code SHALL live in a single package, `rfc_qa`, with one subpackage each for
ingestion, retrieval and generation. Code shared by several stages, and the query interface that
combines retrieval and generation, SHALL live at the package top level. No service module SHALL
remain at the repository root.

#### Scenario: Stages importable from their subpackages

- **WHEN** code imports the ingestion, retrieval or generation functionality
- **THEN** it imports it from `rfc_qa.ingestion`, `rfc_qa.retrieval` or `rfc_qa.generation` respectively

#### Scenario: Query interface at the package top level

- **WHEN** code imports the programmatic query entry point
- **THEN** it imports it from `rfc_qa.query`

#### Scenario: No service modules at the root

- **WHEN** the repository root is listed
- **THEN** it contains no Python modules of the service, only configuration, documentation, the package, tests and release scripts

### Requirement: Provide installed commands

Installing the project from the repository SHALL provide three commands: `rfc-ingest` builds the
index, `rfc-query` answers a question, and `rfc-search` searches the index by keyword. Each command
SHALL accept the same arguments, print the same output and exit with the same status as the
command line it replaces.

#### Scenario: Commands available after install

- **WHEN** the project is installed from the repository in editable mode
- **THEN** `rfc-ingest`, `rfc-query` and `rfc-search` are available on the environment's path

#### Scenario: Behavior unchanged

- **WHEN** `rfc-query` is run with a question
- **THEN** it prints the answer, its sources and any cold-start note, and exits with the same status, as running the query module directly did before this change

### Requirement: Run the commands as modules

Each command SHALL also be runnable as a Python module from the repository root without installing
the project, for example `python -m rfc_qa.query`.

#### Scenario: Module run from the repository root

- **WHEN** `python -m rfc_qa.ingestion.ingest` is run from the repository root without the project installed
- **THEN** it behaves the same as `rfc-ingest`

### Requirement: Resolve configuration and data from the repository root

Default paths to the corpus manifest, the ingestion and query configuration, the data directory and
the index SHALL resolve from the repository root, whatever the working directory. Relative paths
given in configuration SHALL also resolve from the repository root.

#### Scenario: Command run from another directory

- **WHEN** `rfc-query` is run from a directory other than the repository root
- **THEN** it reads `query_config.json` and the index from the repository root

#### Scenario: Ingestion defaults

- **WHEN** `rfc-ingest` is run without options
- **THEN** it reads `corpus.json` and `ingest_config.json` from the repository root and writes to `data/` there

### Requirement: Name the ingestion command in guidance

Messages that tell the user to build the index SHALL name the `rfc-ingest` command.

#### Scenario: Index missing

- **WHEN** a query or search fails because the index doesn't exist or can't be read
- **THEN** the error message tells the user to run `rfc-ingest`
