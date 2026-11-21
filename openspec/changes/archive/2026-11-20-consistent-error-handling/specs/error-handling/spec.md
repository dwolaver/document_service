## Purpose

Defines how the library reports failures to its callers, how a caller's own mistakes are reported, and
how the commands turn errors into a message and an exit status, so that failures are caught in one
place and shown once.

## ADDED Requirements

### Requirement: Raise one family of errors for expected failures

Library code SHALL report a failure caused by the user, the configuration or the environment by
raising an exception derived from `RfcQaError`, which callers import from `rfc_qa.errors`. Each
failure kind SHALL have its own subclass, so a caller can handle one kind without matching messages.
When another exception caused the failure, it SHALL be chained as the cause.

#### Scenario: Catch every expected failure

- **WHEN** a caller wraps a library call in `except RfcQaError`
- **THEN** a missing configuration directory, an invalid configuration file, a failed download, a missing or unreadable index, a failed index build and an unavailable or misbehaving model are all caught

#### Scenario: Catch one kind of failure

- **WHEN** a caller catches only the subclass for a missing or unreadable index
- **THEN** a configuration error isn't caught by that handler

#### Scenario: Underlying cause kept

- **WHEN** a failure is caused by an operating system, network or database error
- **THEN** the raised error's `__cause__` is that original exception

### Requirement: Give each error a message ready to show

The message of an `RfcQaError` SHALL be a complete sentence a user can act on, naming what failed, such
as the file, directory, RFC number or address. `str()` of the error SHALL be that message, with no
prefix to add and no traceback needed.

#### Scenario: Message names what failed

- **WHEN** a download of an RFC fails
- **THEN** the error's message names the RFC number and the reason

#### Scenario: Message shown as it is

- **WHEN** a command reports an `RfcQaError`
- **THEN** the line on standard error is exactly `str()` of the error

### Requirement: Never print from library code

Library code SHALL NOT write to standard output or standard error. Only the command entry points SHALL
print.

#### Scenario: Failure inside the library

- **WHEN** a library function fails, for example a search of a missing index or a failed download
- **THEN** nothing is written to standard output or standard error, and the caller receives the raised error

#### Scenario: Query failure

- **WHEN** `query()` returns a failure response
- **THEN** nothing has been written to standard output or standard error

### Requirement: Report caller bugs with built-in exceptions

When a caller passes an argument of the wrong type to a public function that checks its arguments,
the function SHALL raise `TypeError`. For a value outside the allowed range it SHALL raise
`ValueError`. Neither SHALL be an `RfcQaError`, so a handler for expected failures doesn't hide a bug.

#### Scenario: Wrong type

- **WHEN** a public function that checks its arguments receives a value of the wrong type
- **THEN** it raises `TypeError`, and `except RfcQaError` doesn't catch it

#### Scenario: Value out of range

- **WHEN** a public function that checks its arguments receives a value of the right type outside the allowed range
- **THEN** it raises `ValueError`, and `except RfcQaError` doesn't catch it

### Requirement: Report errors once from the commands

`rfc-ingest`, `rfc-search` and `rfc-query` SHALL catch `RfcQaError`, print its message once as one line
to standard error, write nothing to standard output for that failure, and exit with status 1. A failure
response from `query()` SHALL be reported the same way. The commands SHALL NOT catch other exceptions,
so that a bug shows its traceback. Argument errors from the command-line parser SHALL keep the parser's
usage message and its exit status 2.

#### Scenario: Expected failure in a command

- **WHEN** a command fails with an `RfcQaError`, such as a missing index for `rfc-search`
- **THEN** standard error holds exactly one line, the error's message, and the exit status is 1

#### Scenario: Missing index for a query

- **WHEN** `rfc-query` runs and the index doesn't exist
- **THEN** the message naming the index path and `rfc-ingest` is printed once, not twice

#### Scenario: Bug in a command

- **WHEN** an exception that isn't an `RfcQaError` escapes a command
- **THEN** the command doesn't catch it, so Python prints the traceback and exits non-zero

#### Scenario: Bad command-line arguments

- **WHEN** a command is run with an unknown option
- **THEN** it prints the parser's usage message and exits with status 2
