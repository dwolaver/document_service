## MODIFIED Requirements

### Requirement: Never print from library code

Library code SHALL NOT write to standard output or standard error. It SHALL report what it is doing
only through log records, which reach a stream only through a handler that the calling program or a
command attaches. Only the command entry points SHALL print.

#### Scenario: Failure inside the library

- **WHEN** a library function fails, for example a search of a missing index or a failed download
- **THEN** nothing is written to standard output or standard error, and the caller receives the raised error

#### Scenario: Query failure

- **WHEN** `query()` returns a failure response
- **THEN** nothing has been written to standard output or standard error

#### Scenario: Library activity

- **WHEN** a library function downloads, reads, writes or queries something, and the program hasn't configured logging
- **THEN** nothing is written to standard output or standard error, and the activity is available as log records for a program that configures logging

### Requirement: Report errors once from the commands

`rfc-ingest`, `rfc-search` and `rfc-query` SHALL catch `RfcQaError`, print its message once as one line
to standard error, write nothing to standard output for that failure, and exit with status 1. A failure
response from `query()` SHALL be reported the same way. When `-v` is given, the log records written
before the failure SHALL precede the message on standard error, and none of them SHALL repeat it. The
commands SHALL NOT catch other exceptions, so that a bug shows its traceback. Argument errors from the
command-line parser SHALL keep the parser's usage message and its exit status 2.

#### Scenario: Expected failure in a command

- **WHEN** a command run without `-v` fails with an `RfcQaError`, such as a missing index for `rfc-search`
- **THEN** standard error holds exactly one line, the error's message, and the exit status is 1

#### Scenario: Expected failure with -v

- **WHEN** a command run with `-v` fails with an `RfcQaError`
- **THEN** standard error ends with the error's message as its only unprefixed line, the message appears once, and the exit status is 1

#### Scenario: Missing index for a query

- **WHEN** `rfc-query` runs and the index doesn't exist
- **THEN** the message naming the index path and `rfc-ingest` is printed once, not twice

#### Scenario: Bug in a command

- **WHEN** an exception that isn't an `RfcQaError` escapes a command
- **THEN** the command doesn't catch it, so Python prints the traceback and exits non-zero

#### Scenario: Bad command-line arguments

- **WHEN** a command is run with an unknown option
- **THEN** it prints the parser's usage message and exits with status 2
