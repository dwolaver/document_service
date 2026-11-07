# Proposal

## Why

The Document Q&A Service has an ingestion path (the RFC downloader) but no entry point for
asking questions. We need the service's main user-facing interface in place now — even as a
stub — so the project can be unit-tested as it grows and the eventual RAG workflow can slot
in behind a stable signature.

## What Changes

- Add a top-level query interface in [`query.py`](../../../query.py) exposing
  `query(user_query: str) -> QueryResponse` as the service's main programmatic API.
- Introduce a plain `dataclass` `QueryResponse` carrying `success`, `answer`, `error_code`,
  and `error_string`, where `error_code` is an integer enumeration value identifying the
  failure kind and `error_string` is a human-readable description; the response is designed to
  grow with evaluation details over time.
- Validate input like the downloader does: the query must be a `str` containing at least one
  non-whitespace token; otherwise return a failure response with the `INVALID_QUERY` error
  code.
- Until the RAG workflow exists, a valid query returns a failure response with the
  `NOT_IMPLEMENTED` error code and an `error_string` stating the RAG workflow is still in
  progress.
- Add a thin CLI wrapper (`main`) that takes a single positional query argument, prints the
  answer to stdout on success and the error to stderr on failure, and exits `0` on success or
  non-zero on failure.

## Capabilities

### New Capabilities
- `query-interface`: The service's main entry point for submitting a natural-language RFC
  query and receiving a structured response, including input validation and the console
  wrapper.

### Modified Capabilities
<!-- None: the RFC-downloader capability is unaffected. -->

## Impact

- Implements the currently-empty `query.py` module.
- No new runtime dependencies (plain `dataclass`, standard library CLI).
- No changes to the existing `rfc-downloader` capability or its code.
- Establishes the API seam that the future RAG retrieval/answer workflow will fill in.
