# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: Resolve data from the repository root`
- TO: `### Requirement: Keep generated data in one data directory`

## MODIFIED Requirements

### Requirement: Keep generated data in one data directory

Downloaded RFCs and the index SHALL live in one data directory: the RFCs in its `rfcs/` folder and
the index in its `index.db` file. Every command SHALL find the index there, so the index a query reads
is the one ingestion built in the same data directory. By default the data directory is `data/` at the
repository root, whatever the working directory. The query configuration SHALL NOT give the index
location.

#### Scenario: Command run from another directory

- **WHEN** `rfc-query` is run from a directory other than the repository root, with no override
- **THEN** it reads the index from `data/` at the repository root

#### Scenario: Ingestion defaults

- **WHEN** `rfc-ingest` is run without options
- **THEN** it writes the downloaded RFCs and the index to `data/` at the repository root

#### Scenario: Relative index path with another configuration directory

- **WHEN** the configuration directory is outside the repository and its query configuration still gives a relative `index_path`
- **THEN** the query fails with the configuration error code, saying that the index location comes from the data directory, rather than resolving that path

#### Scenario: Build and query agree

- **WHEN** `rfc-ingest` builds an index in a data directory, and `rfc-query` and `rfc-search` are run with the same data directory
- **THEN** both read the index that `rfc-ingest` built

#### Scenario: Data directory that doesn't exist

- **WHEN** the selected data directory doesn't exist
- **THEN** `rfc-ingest` creates it, and `rfc-query` and `rfc-search` report a missing index that names the index path and tells the user to run `rfc-ingest`

## ADDED Requirements

### Requirement: Select the data directory

The data directory SHALL be chosen in this order: the `--data-dir` flag of `rfc-ingest`, `rfc-query`
or `rfc-search`, then the `RFC_QA_DATA_DIR` environment variable, then the default. A relative
directory given by the flag or the variable SHALL resolve from the working directory. An empty variable
SHALL count as unset.

#### Scenario: Environment variable

- **WHEN** `RFC_QA_DATA_DIR` names a directory and no flag is given
- **THEN** each command uses that directory for the RFCs and the index

#### Scenario: Flag over environment variable

- **WHEN** both `--data-dir` and `RFC_QA_DATA_DIR` are given, naming different directories
- **THEN** the command uses the directory the flag names

#### Scenario: Relative directory

- **WHEN** `--data-dir scratch` is given in a working directory that contains `scratch/`
- **THEN** the command uses that `scratch/` directory

#### Scenario: Empty variable

- **WHEN** `RFC_QA_DATA_DIR` is set to an empty string and no flag is given
- **THEN** the command uses the default data directory

#### Scenario: Programmatic query

- **WHEN** the programmatic query entry point is called with a data directory
- **THEN** it reads the index from that directory, ahead of `RFC_QA_DATA_DIR` and the default

### Requirement: Override the index file for search

`rfc-search` SHALL accept an `--index` flag naming a single index file. It SHALL take precedence over
the data directory.

#### Scenario: Index flag with a data directory

- **WHEN** `rfc-search` is run with `--index` naming a file and `RFC_QA_DATA_DIR` naming a directory
- **THEN** it searches the file `--index` names
