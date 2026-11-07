# Spec Delta

## MODIFIED Requirements

### Requirement: Accept a query through the programmatic API

The service SHALL expose a programmatic entry point that accepts a single user query and
returns a structured response object describing the outcome. The entry point SHALL return a
response rather than raising for expected failure conditions.

#### Scenario: Query returns a structured response

- **WHEN** the entry point is called with a value
- **THEN** it returns a response object carrying a success flag and, depending on the outcome, an answer, whether an answer was found, citations, timings, an integer enumeration error code, and a human-readable error string

#### Scenario: Answered query

- **WHEN** a valid query is answered from the indexed RFCs
- **THEN** the response has `success` true, `found` true, the answer, and at least one citation

### Requirement: Provide a console entry point

The service SHALL provide a command-line wrapper that accepts a single query argument, invokes
the programmatic entry point, and reports the outcome to the console. On success it SHALL print
the answer to standard output, followed by its citations when there are any, and exit with a zero
status; on failure it SHALL print the error string to standard error and exit with a non-zero
status.

#### Scenario: Successful query from the console

- **WHEN** the console wrapper is run with a query that produces a successful response
- **THEN** it prints the answer to standard output and exits with status zero

#### Scenario: Citations printed

- **WHEN** a successful response has citations
- **THEN** each citation is printed after the answer with its RFC number, section number, section title and chunk ID

#### Scenario: Cold start noted on the console

- **WHEN** the model had to be loaded for a successful query
- **THEN** a note giving the load time is printed after the answer, so that a slow answer is explained

#### Scenario: Not found from the console

- **WHEN** the console wrapper is run with a query the indexed RFCs don't answer
- **THEN** it prints the not-found message to standard output and exits with status zero

#### Scenario: Failed query from the console

- **WHEN** the console wrapper is run with a query that produces a failure response
- **THEN** it prints the error string to standard error and exits with a non-zero status

## REMOVED Requirements

### Requirement: Report that answering is not yet implemented

**Reason**: The answer-producing workflow now exists, so a valid query is answered or reported as
not found.

**Migration**: Handle `success`, `found` and `citations` on the response. The `NOT_IMPLEMENTED`
error code is no longer returned, and its value, 2, is not reused.
