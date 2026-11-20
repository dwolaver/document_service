# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: Resolve configuration and data from the repository root`
- TO: `### Requirement: Resolve data from the repository root`

## MODIFIED Requirements

### Requirement: Resolve data from the repository root

The default data directory and index path SHALL resolve from the repository root, whatever the
working directory. Relative paths given in configuration SHALL also resolve from the repository root,
whichever configuration directory is in use.

#### Scenario: Command run from another directory

- **WHEN** `rfc-query` is run from a directory other than the repository root
- **THEN** it reads the index from `data/` at the repository root

#### Scenario: Ingestion defaults

- **WHEN** `rfc-ingest` is run without options
- **THEN** it writes the downloaded RFCs and the index to `data/` at the repository root

#### Scenario: Relative index path with another configuration directory

- **WHEN** the configuration directory is outside the repository and its query configuration gives a relative `index_path`
- **THEN** the index path resolves from the repository root, not from the configuration directory

## ADDED Requirements

### Requirement: Read configuration from a configuration directory

The corpus manifest (`corpus.json`), the ingestion configuration (`ingest.json`) and the query
configuration (`query.json`) SHALL be read from one configuration directory. By default this
is `config/` at the repository root, whatever the working directory. No configuration file SHALL
remain at the repository root.

#### Scenario: Default configuration from another directory

- **WHEN** `rfc-query` or `rfc-ingest` is run from a directory other than the repository root, with no override
- **THEN** it reads its configuration files from `config/` at the repository root

#### Scenario: No configuration at the root

- **WHEN** the repository root is listed
- **THEN** it contains no `corpus.json`, `ingest_config.json` or `query_config.json`

### Requirement: Select the configuration directory

The configuration directory SHALL be chosen in this order: the `--config-dir` flag of `rfc-ingest`
or `rfc-query`, then the `RFC_QA_CONFIG_DIR` environment variable, then the default. A relative
directory given by the flag or the variable SHALL resolve from the working directory. An empty
variable SHALL count as unset.

#### Scenario: Environment variable

- **WHEN** `RFC_QA_CONFIG_DIR` names a directory and no flag is given
- **THEN** the command reads its configuration files from that directory

#### Scenario: Flag over environment variable

- **WHEN** both `--config-dir` and `RFC_QA_CONFIG_DIR` are given, naming different directories
- **THEN** the command reads its configuration files from the directory the flag names

#### Scenario: Relative directory

- **WHEN** `--config-dir staging` is given in a working directory that contains `staging/`
- **THEN** the command reads its configuration files from that `staging/` directory

#### Scenario: Empty variable

- **WHEN** `RFC_QA_CONFIG_DIR` is set to an empty string and no flag is given
- **THEN** the command reads its configuration files from the default directory

#### Scenario: Programmatic query

- **WHEN** the programmatic query entry point is called with a configuration directory
- **THEN** it reads the query configuration from that directory, ahead of `RFC_QA_CONFIG_DIR` and the default

### Requirement: Override one ingestion file

`rfc-ingest` SHALL accept `--corpus` and `--config` flags naming a single manifest or ingestion
configuration file. A file flag SHALL take precedence over the configuration directory for that file
only.

#### Scenario: Corpus flag with a configuration directory

- **WHEN** `rfc-ingest` is run with `--config-dir` naming one directory and `--corpus` naming a file elsewhere
- **THEN** it reads the manifest from the `--corpus` file and the ingestion configuration from the configuration directory

### Requirement: Report a missing configuration directory

When the selected configuration directory doesn't exist, the command or query SHALL fail before doing
any work. The message SHALL name the directory and whether it came from the flag, the environment
variable or the default.

#### Scenario: Missing directory from the environment

- **WHEN** `RFC_QA_CONFIG_DIR` names a directory that doesn't exist
- **THEN** `rfc-ingest` exits non-zero with a message naming the directory and `RFC_QA_CONFIG_DIR`, without downloading anything

#### Scenario: Missing directory for a query

- **WHEN** a query runs with a configuration directory that doesn't exist
- **THEN** the response is a failure with the configuration error code, naming the directory and where it was set
