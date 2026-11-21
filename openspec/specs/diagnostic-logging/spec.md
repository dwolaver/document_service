# diagnostic-logging Specification

## Purpose

Defines how the library reports what it is doing, through Python's standard logging, so that a program
embedding it and a user running a command can see its progress and details when they ask for them,
and see nothing when they don't.

## Requirements

### Requirement: Log through the standard logging module

Library code SHALL report what it is doing by emitting records through Python's `logging` module, on
loggers named after their modules under `rfc_qa`. Progress a user would want to follow SHALL be logged
at `INFO`. Detail useful for diagnosing a problem SHALL be logged at `DEBUG`. Log calls SHALL pass
their values as logging arguments rather than formatting the message first.

#### Scenario: Progress at INFO

- **WHEN** ingestion downloads an RFC, chunks the corpus or writes the index, or a query retrieves passages or receives the model's answer
- **THEN** an `INFO` record from an `rfc_qa` logger describes it, naming the RFC, path or count involved

#### Scenario: Detail at DEBUG

- **WHEN** a configuration or data directory is selected, a stored RFC is reused instead of downloaded, a search runs, or the model reports its token counts
- **THEN** a `DEBUG` record from an `rfc_qa` logger gives the value and, for a directory, where it was chosen

#### Scenario: Records filtered by logger

- **WHEN** a program sets the level or handler of the `rfc_qa` logger or one of its children
- **THEN** that setting applies to the library's records and to no other library's

### Requirement: Never configure logging from the library

Library code SHALL NOT add handlers other than a `NullHandler` on the `rfc_qa` logger, set levels, or
call logging's configuration functions. A program that hasn't configured logging SHALL see no log
output from the library at any level. A failure SHALL be raised, not logged.

#### Scenario: Unconfigured program

- **WHEN** a program calls the library without configuring logging, and the call succeeds or fails
- **THEN** nothing is written to standard output or standard error

#### Scenario: Program that configures logging

- **WHEN** a program configures logging with a handler at `DEBUG`
- **THEN** that handler receives the library's `INFO` and `DEBUG` records

#### Scenario: Failure not logged

- **WHEN** a library function raises an `RfcQaError`
- **THEN** no log record repeats the error's message

### Requirement: Show log records on request from the commands

`rfc-ingest`, `rfc-search` and `rfc-query` SHALL accept `-v`/`--verbose`, which may be repeated. Given
once, the command SHALL write the library's `INFO` and higher records to standard error. Given twice
or more, it SHALL also write `DEBUG` records. Each record SHALL be one line giving its level, its
logger and its message. Without the flag, a command SHALL write no log records. Log records SHALL
never be written to standard output.

#### Scenario: Default output

- **WHEN** a command runs without `-v`
- **THEN** standard error is empty when it succeeds and holds only the error's message when it fails with an expected error

#### Scenario: Progress with -v

- **WHEN** `rfc-ingest -v` runs
- **THEN** standard error shows an `INFO` line for each RFC downloaded and for the index being written, and no `DEBUG` line, and standard output holds only the summary

#### Scenario: Detail with -vv

- **WHEN** `rfc-query -vv` runs
- **THEN** standard error also shows `DEBUG` lines, such as the selected directories, and standard output holds only the answer and its sources

#### Scenario: Other libraries' records

- **WHEN** a command runs with `-vv`
- **THEN** records from loggers outside `rfc_qa`, such as the HTTP client's, aren't shown
