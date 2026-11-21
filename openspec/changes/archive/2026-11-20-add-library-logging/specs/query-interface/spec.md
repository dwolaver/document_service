## MODIFIED Requirements

### Requirement: Provide a console entry point

The service SHALL provide a command-line wrapper that accepts a single query argument, invokes
the programmatic entry point, and reports the outcome to the console. On success it SHALL print
the answer to standard output, followed by its citations when there are any, and exit with a zero
status; on failure it SHALL print the error string once to standard error and exit with status 1.
With `-v` it SHALL also write the library's log records to standard error, never to standard output.

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
- **THEN** it prints the error string once, as the only output on standard error when run without `-v`, and exits with status 1

#### Scenario: Verbose query

- **WHEN** the console wrapper is run with `-v` and the query succeeds
- **THEN** standard output is the same as without `-v`, and standard error holds the retrieval and answer progress records
