# project-packaging Specification

## Purpose

Defines how the service's code is organized into a package with one subpackage per stage, how the
project is installed, which commands it provides, and where those commands find configuration and
data.

## Requirements

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
- **THEN** it contains no Python modules of the service, no package directory and no configuration directory, only the source directory, documentation, tests and release scripts

#### Scenario: Package in the source directory

- **WHEN** the `src/` directory at the repository root is listed
- **THEN** it contains the `rfc_qa` package, and the import paths are the same as before the package moved there

### Requirement: Provide installed commands

Installing the project, in editable mode or as a regular install, SHALL provide three commands:
`rfc-ingest` builds the index, `rfc-query` answers a question, and `rfc-search` searches the index
by keyword. Each command SHALL accept the same arguments, print the same output and exit with the
same status as the command line it replaces.

#### Scenario: Commands available after install

- **WHEN** the project is installed from the repository in editable mode, or installed from a built wheel
- **THEN** `rfc-ingest`, `rfc-query` and `rfc-search` are available on the environment's path

#### Scenario: Behavior unchanged

- **WHEN** `rfc-query` is run with a question
- **THEN** it prints the answer, its sources and any cold-start note, and exits with the same status, as running the query module directly did before this change

### Requirement: Run the commands as modules

Each command SHALL also be runnable as a Python module once the project is installed, from any
directory, for example `python -m rfc_qa.query`. The package SHALL only be importable as installed,
so an uninstalled checkout is never run by accident.

#### Scenario: Module run from the repository root

- **WHEN** `python -m rfc_qa.ingestion.ingest` is run from the repository root with the project installed
- **THEN** it behaves the same as `rfc-ingest`

#### Scenario: Module run from another directory

- **WHEN** `python -m rfc_qa.query` is run from a directory other than the repository root with the project installed
- **THEN** it behaves the same as `rfc-query`, including reading the packaged configuration and the user data directory by default

#### Scenario: Uninstalled checkout

- **WHEN** `python -m rfc_qa.query` is run from the repository root in an environment where the project isn't installed
- **THEN** Python reports that `rfc_qa` can't be found, instead of running the code in the checkout

### Requirement: Keep generated data in one data directory

Downloaded RFCs and the index SHALL live in one data directory: the RFCs in its `rfcs/` folder and
the index in its `index.db` file. Every command SHALL find the index there, so the index a query reads
is the one ingestion built in the same data directory. By default the data directory is the user's
data directory for `rfc-qa` on their platform, such as `~/.local/share/rfc-qa` on Linux, whatever the
working directory. The query configuration SHALL NOT give the index location.

#### Scenario: Command run from another directory

- **WHEN** `rfc-query` is run from any directory, with no override
- **THEN** it reads the index from the user data directory

#### Scenario: Ingestion defaults

- **WHEN** `rfc-ingest` is run without options
- **THEN** it writes the downloaded RFCs and the index to the user data directory, creating it if needed

#### Scenario: Relative index path with another configuration directory

- **WHEN** the configuration directory is outside the repository
- **THEN** the query reads the index from the selected data directory, not from a path relative to the configuration directory, the working directory or the repository

#### Scenario: Build and query agree

- **WHEN** `rfc-ingest` builds an index in a data directory, and `rfc-query` and `rfc-search` are run with the same data directory
- **THEN** both read the index that `rfc-ingest` built

#### Scenario: Data directory that doesn't exist

- **WHEN** the selected data directory doesn't exist
- **THEN** `rfc-ingest` creates it, and `rfc-query` and `rfc-search` report a missing index that names the index path and tells the user to run `rfc-ingest`

#### Scenario: Platform data directory followed

- **WHEN** the platform's setting for the user data location is changed, such as `XDG_DATA_HOME` on Linux, and no override is given
- **THEN** the default data directory is `rfc-qa` under that location

### Requirement: Name the ingestion command in guidance

Messages that tell the user to build the index SHALL name the `rfc-ingest` command.

#### Scenario: Index missing

- **WHEN** a query or search fails because the index doesn't exist or can't be read
- **THEN** the error message tells the user to run `rfc-ingest`

### Requirement: Read configuration from a configuration directory

The corpus manifest (`corpus.json`), the ingestion configuration (`ingest.json`) and the query
configuration (`query.json`) SHALL be read from one configuration directory. By default this is the
set of configuration files installed with the package, whatever the working directory. No
configuration file or configuration directory SHALL remain at the repository root.

#### Scenario: Default configuration from another directory

- **WHEN** `rfc-query` or `rfc-ingest` is run from any directory, with no override
- **THEN** it reads its configuration files from the ones installed with the package

#### Scenario: No configuration at the root

- **WHEN** the repository root is listed
- **THEN** it contains no `config/` directory, and no `corpus.json`, `ingest_config.json` or `query_config.json`

#### Scenario: Selected directory missing a file

- **WHEN** the selected configuration directory exists but doesn't contain a file the command reads
- **THEN** the command fails with a message naming that file, and doesn't fall back to the packaged copy

#### Scenario: Packaged defaults in an editable install

- **WHEN** the project is installed in editable mode and a packaged configuration file is edited in the checkout
- **THEN** the next command run with no override reads the edited file

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

### Requirement: Run from a regular install

A regular install of the project, from a built wheel or a source directory, SHALL provide working
commands without the repository being present. The package SHALL NOT read any file from the
repository checkout. Its defaults SHALL come from the installed package and the user's data
directory.

#### Scenario: Wheel installed with no checkout

- **WHEN** a wheel built from the repository is installed into a fresh environment, and `rfc-ingest`, `rfc-search` and `rfc-query` are run from a directory unrelated to the repository, with no overrides
- **THEN** each command reads its configuration from the installed package and its data from the user data directory, and behaves as it does in an editable install
