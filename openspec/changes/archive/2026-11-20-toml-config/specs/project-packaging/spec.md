## ADDED Requirements

### Requirement: Write the configuration files in TOML

The corpus manifest, the ingestion configuration and the query configuration SHALL be TOML documents.
A file that isn't valid TOML SHALL be rejected as a configuration error, with a message naming the
file and the line and column of the problem.

#### Scenario: Malformed file

- **WHEN** a configuration file the command reads isn't valid TOML
- **THEN** the command fails with a configuration error naming the file and the line and column of the problem, and reads no other setting from it

#### Scenario: JSON file given

- **WHEN** `--corpus`, `--config` or a configuration directory supplies a file in JSON
- **THEN** the command fails with a configuration error naming the file, rather than reading it

### Requirement: Describe every setting in the configuration files

Each packaged configuration file SHALL begin with a comment saying what it configures and which
command reads it. Each section SHALL have a comment saying what it covers. Each setting SHALL have a
comment giving its meaning and its unit or allowed values, and naming any other setting it has to
agree with. The manifest SHALL describe the fields of an entry once, above the list of RFCs.

#### Scenario: Commented settings

- **WHEN** a packaged configuration file is read
- **THEN** every section and every setting in it has a comment describing it

#### Scenario: Comments don't change the settings

- **WHEN** the comments in a configuration file are edited or removed
- **THEN** the settings read from it are the same

## MODIFIED Requirements

### Requirement: Read configuration from a configuration directory

The corpus manifest (`corpus.toml`), the ingestion configuration (`ingest.toml`) and the query
configuration (`query.toml`) SHALL be read from one configuration directory. By default this is the
set of configuration files installed with the package, whatever the working directory. No
configuration file or configuration directory SHALL remain at the repository root.

#### Scenario: Default configuration from another directory

- **WHEN** `rfc-query` or `rfc-ingest` is run from any directory, with no override
- **THEN** it reads its configuration files from the ones installed with the package

#### Scenario: No configuration at the root

- **WHEN** the repository root is listed
- **THEN** it contains no `config/` directory, and no `corpus.toml`, `ingest.toml` or `query.toml`, nor any of the earlier JSON configuration files

#### Scenario: Selected directory missing a file

- **WHEN** the selected configuration directory exists but doesn't contain a file the command reads
- **THEN** the command fails with a message naming that file, and doesn't fall back to the packaged copy

#### Scenario: Packaged defaults in an editable install

- **WHEN** the project is installed in editable mode and a packaged configuration file is edited in the checkout
- **THEN** the next command run with no override reads the edited file
