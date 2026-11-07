"""Top-level query interface for the Document Q&A Service.

This is the service's main entry point. ``query`` is the real programmatic API;
``main`` is a thin console wrapper. The answer-producing RAG workflow does not
exist yet, so a valid query currently returns a ``NOT_IMPLEMENTED`` failure.
"""

import argparse
import sys
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


class QueryErrorCode(IntEnum):
    """Enumerated failure kinds carried by a :class:`QueryResponse`."""

    INVALID_QUERY = 1
    NOT_IMPLEMENTED = 2


@dataclass
class QueryResponse:
    """Structured result of a query.

    Grows over time with evaluation details (sources, latency, scores, ...).
    """

    success: bool
    answer: Optional[str] = None
    error_string: Optional[str] = None
    error_code: Optional[QueryErrorCode] = None


_NOT_IMPLEMENTED_MESSAGE = "The RAG workflow is still in progress; querying is not yet implemented."


def _log_error(message):
    print(message, file=sys.stderr)


def _is_valid_query(user_query):
    return isinstance(user_query, str) and bool(user_query.strip())


def query(user_query):
    """Answer a natural-language query about RFCs.

    Returns a :class:`QueryResponse`. Expected failures (invalid input, missing
    workflow) are reported through the response rather than raised.
    """
    if not _is_valid_query(user_query):
        return QueryResponse(
            success=False,
            error_code=QueryErrorCode.INVALID_QUERY,
            error_string="Query must be a non-empty string with at least one non-whitespace token.",
        )

    # The RAG workflow will replace this branch, returning success=True with an answer.
    return QueryResponse(
        success=False,
        error_code=QueryErrorCode.NOT_IMPLEMENTED,
        error_string=_NOT_IMPLEMENTED_MESSAGE,
    )


def main(argv=None):
    """Console entry point: print the answer or error and return an exit code."""
    parser = argparse.ArgumentParser(description="Ask a question about RFCs.")
    parser.add_argument("query", help="The natural-language query to answer.")
    args = parser.parse_args(argv)

    response = query(args.query)
    if response.success:
        print(response.answer)
        return 0

    _log_error(response.error_string)
    return 1


if __name__ == "__main__":
    sys.exit(main())
