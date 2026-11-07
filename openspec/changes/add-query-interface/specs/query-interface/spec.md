# Spec Delta

## Purpose

Provides the service's main entry point for submitting a natural-language query about RFCs
and receiving a structured response, so the project can be exercised and unit-tested while
the answer-producing RAG workflow is built incrementally.

## ADDED Requirements

### Requirement: Accept a query through the programmatic API

The service SHALL expose a programmatic entry point that accepts a single user query and
returns a structured response object describing the outcome. The entry point SHALL return a
response rather than raising for expected failure conditions.

#### Scenario: Query returns a structured response

- **WHEN** the entry point is called with a value
- **THEN** it returns a response object carrying a success flag and, depending on the outcome, an answer, an integer enumeration error code, and a human-readable error string

### Requirement: Validate the query input

The service SHALL require the query to be a string containing at least one non-whitespace
token. A query that is not a string, is empty, or contains only whitespace SHALL be rejected
as a failure identified by the `INVALID_QUERY` error code, without attempting to answer it.

#### Scenario: Non-string query

- **WHEN** the query is not a string (for example `None` or a number)
- **THEN** the response has `success` false and the `INVALID_QUERY` error code

#### Scenario: Empty or whitespace-only query

- **WHEN** the query is an empty string or contains only whitespace
- **THEN** the response has `success` false and the `INVALID_QUERY` error code

### Requirement: Report that answering is not yet implemented

Until the answer-producing workflow exists, the service SHALL respond to a valid query with a
failure response identified by the `NOT_IMPLEMENTED` error code, carrying a human-readable error
string that the RAG workflow is still in progress and no answer.

#### Scenario: Valid query while the workflow is unavailable

- **WHEN** a valid query is submitted and the answer-producing workflow is not yet implemented
- **THEN** the response has `success` false, the `NOT_IMPLEMENTED` error code, an error string indicating the RAG workflow is in progress, and no answer

### Requirement: Provide a console entry point

The service SHALL provide a command-line wrapper that accepts a single query argument, invokes
the programmatic entry point, and reports the outcome to the console. On success it SHALL print
the answer to standard output and exit with a zero status; on failure it SHALL print the error
string to standard error and exit with a non-zero status.

#### Scenario: Successful query from the console

- **WHEN** the console wrapper is run with a query that produces a successful response
- **THEN** it prints the answer to standard output and exits with status zero

#### Scenario: Failed query from the console

- **WHEN** the console wrapper is run with a query that produces a failure response
- **THEN** it prints the error string to standard error and exits with a non-zero status
