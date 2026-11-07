# Design

## Context

See proposal.md - Why. The project is a flat Python 3.14 module layout: an existing
[`rfc_downloader.py`](../../../rfc_downloader.py) and an empty [`query.py`](../../../query.py)
at the root, with `pytest` tests under `tests/`. The downloader establishes conventions this
component should follow: module-level functions (no classes for behavior), strict input
validation, errors sent to `stderr` via a small helper, and a simple return contract. The
answer-producing RAG workflow does not exist yet; this change builds only the entry-point seam.

## Goals / Non-Goals

**Goals:**
- A pure, unit-testable `query()` function that returns a structured result with no I/O.
- A stable response shape that the future RAG workflow fills in without changing the signature.
- A thin CLI for manual, as-you-go testing.

**Non-Goals:**
- Any retrieval, ranking, or LLM/answer generation (the RAG workflow, built later).
- Reading the downloaded RFC corpus or connecting to the downloader.
- Session/state, configuration, or multi-query batch handling.

## Decisions

- **`query.py` as the home, function as the real API**: Implement `query(user_query) ->
  QueryResponse` at module level, matching the downloader's function-first style. The empty,
  well-named `query.py` is the natural location and the documented main entry point.

- **Plain `dataclass` response**: Define `QueryResponse` as a `dataclasses.dataclass` with
  `success: bool`, `answer: Optional[str] = None`, `error_string: Optional[str] = None`,
  `error_code: Optional[QueryErrorCode] = None`. `error_code` is an integer enumeration value
  identifying the failure kind; `error_string` is the human-readable description. A plain
  dataclass (not pydantic) keeps the stub dependency-free and is trivial to extend with
  evaluation fields (sources, latency, scores) later. pydantic was considered but adds nothing
  for an internal result object here.

- **Error codes as an integer enumeration**: Represent failure kinds with a stable, numeric
  `error_code` so unit tests assert on a discrete enumeration value rather than prose, with the
  human-readable detail kept separately in `error_string`. Define `QueryErrorCode` as an
  `enum.IntEnum` with members `INVALID_QUERY` and `NOT_IMPLEMENTED`; `error_code` is `None` on
  success. Alternatives — a free-text error field, or string codes — were rejected because the
  response is explicitly expected to grow for evaluation, where a discrete integer enumeration
  ages better and reads unambiguously.

- **Validation mirrors the downloader**: Reject a non-`str`, empty, or whitespace-only query
  (i.e. `isinstance(str)` and `user_query.strip()` non-empty) as a failure response with
  `error_code=QueryErrorCode.INVALID_QUERY` — never a raised exception for expected bad input.

- **Stub returns a `NOT_IMPLEMENTED` failure**: For a valid query, return
  `QueryResponse(success=False, error_code=QueryErrorCode.NOT_IMPLEMENTED,
  error_string=<RAG-in-progress message>)`. When the RAG workflow lands it replaces this branch,
  setting `success=True` and populating `answer`, with the signature unchanged. A thin internal
  seam (e.g. a private answer-producing function) keeps that future substitution localized.

- **Thin CLI via `main(argv=None) -> int` + argparse**: One positional query argument. On a
  successful response print `answer` to stdout and return `0`; on failure print `error_string`
  to stderr (reusing a downloader-style helper) and return a non-zero code.
  `if __name__ == "__main__": sys.exit(main())`. Passing `argv` makes the CLI unit-testable
  without spawning a process.

## Risks / Trade-offs

- **Everything fails today** → Until RAG exists every valid query returns `not_implemented`, so
  the CLI always exits non-zero. This is intended and gives an immediately testable, stable
  contract; it is not a defect.
- **Response shape churn as evaluation needs grow** → New fields are added with defaults, so
  existing callers and tests keep working; the `success`/`error_code` core stays fixed.
- **CLI/function duplication of outcome handling** → Kept minimal by having `main` only format
  and print what `query()` returns, with no business logic of its own.

## Open Questions

- The concrete set of future `QueryErrorCode` members and evaluation fields — deferred until the
  RAG workflow defines real success and failure modes; it does not affect this stub's specs,
  shape, or tasks.
