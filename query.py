"""Top-level query interface for the Document Q&A Service.

This is the service's main entry point. ``query`` is the programmatic API, and ``main`` is a thin
console wrapper. A query retrieves RFC passages from the keyword index, asks the local model to
answer from them, and returns the answer with checked citations and timings.
"""

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Optional

from answer_generator import (
    NOT_FOUND_ANSWER,
    ModelResponseError,
    ModelSettings,
    ModelUnavailableError,
    generate_answer,
)
from keyword_index import read_metadata, search

_ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(_ROOT, "query_config.json")

# Tokens reserved for the instructions, passage labels and the question.
PROMPT_ALLOWANCE_TOKENS = 512
# A model load at least this long means Ollama had to load the model for this query.
COLD_START_THRESHOLD_MS = 500


class QueryErrorCode(IntEnum):
    """Enumerated failure kinds carried by a :class:`QueryResponse`.

    Values may be renumbered until the first release. After that, a removed value is retired and not
    reused.
    """

    INVALID_QUERY = 1
    INDEX_UNAVAILABLE = 2
    MODEL_UNAVAILABLE = 3
    MODEL_INVALID_RESPONSE = 4
    CONFIG_INVALID = 5


@dataclass(frozen=True)
class Citation:
    """An RFC section an answer was drawn from."""

    chunk_id: str
    rfc_number: int
    rfc_title: str
    section_number: str
    section_title: str


@dataclass(frozen=True)
class Timings:
    """Where a query's time went. Model fields are ``None`` when the model wasn't called."""

    total_ms: int
    retrieval_ms: Optional[int] = None
    model_load_ms: Optional[int] = None
    generation_ms: Optional[int] = None
    prompt_tokens: Optional[int] = None
    answer_tokens: Optional[int] = None
    cold_start: bool = False


@dataclass
class QueryResponse:
    """Structured result of a query.

    ``found`` is ``None`` on failure. On success it says whether the indexed RFCs answered the
    question, and ``citations`` is non-empty only when they did.
    """

    success: bool
    answer: Optional[str] = None
    found: Optional[bool] = None
    citations: List[Citation] = field(default_factory=list)
    timings: Optional[Timings] = None
    error_string: Optional[str] = None
    error_code: Optional[QueryErrorCode] = None


class QueryConfigError(Exception):
    """An invalid query configuration, with a message naming the value."""


@dataclass(frozen=True)
class QueryConfig:
    index_path: str
    retrieval_limit: int
    model: ModelSettings


def _log_error(message):
    print(message, file=sys.stderr)


def _is_valid_query(user_query):
    return isinstance(user_query, str) and bool(user_query.strip())


def _positive_integer(value, name):
    # bool is a subclass of int but is not a valid value here.
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise QueryConfigError("Config {n} must be a positive integer, got {v!r}.".format(n=name, v=value))
    return value


def _positive_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise QueryConfigError("Config {n} must be a positive number, got {v!r}.".format(n=name, v=value))
    return value


def _non_empty_string(value, name):
    if not isinstance(value, str) or not value.strip():
        raise QueryConfigError("Config {n} must be a non-empty string, got {v!r}.".format(n=name, v=value))
    return value


def _section(data, name):
    section = data.get(name)
    if not isinstance(section, dict):
        raise QueryConfigError("Config {n} must be an object, got {v!r}.".format(n=name, v=section))
    return section


def load_query_config(path):
    """Return the validated configuration, raising :class:`QueryConfigError` if it's invalid."""
    try:
        with open(path, encoding="utf-8") as config_file:
            data = json.load(config_file)
    except (OSError, ValueError) as exc:
        raise QueryConfigError("Failed to read {p!r}: {e}".format(p=path, e=exc)) from exc
    if not isinstance(data, dict):
        raise QueryConfigError("Config {p!r} must be a JSON object.".format(p=path))

    index_path = _non_empty_string(data.get("index_path"), "index_path")
    retrieval = _section(data, "retrieval")
    llm = _section(data, "llm")
    return QueryConfig(
        index_path=os.path.join(_ROOT, index_path),
        retrieval_limit=_positive_integer(retrieval.get("limit"), "retrieval.limit"),
        model=ModelSettings(
            model=_non_empty_string(llm.get("model"), "llm.model"),
            base_url=_non_empty_string(llm.get("base_url"), "llm.base_url"),
            num_ctx=_positive_integer(llm.get("num_ctx"), "llm.num_ctx"),
            max_answer_tokens=_positive_integer(llm.get("max_answer_tokens"), "llm.max_answer_tokens"),
            timeout_seconds=_positive_number(llm.get("timeout_seconds"), "llm.timeout_seconds"),
        ),
    )


def _elapsed_ms(start):
    return int(round((time.perf_counter() - start) * 1000))


class _Clock:
    """Wall-clock timings for one query, combined with the model's own durations."""

    def __init__(self):
        self.start = time.perf_counter()
        self.retrieval_ms = None

    def timings(self, generation=None):
        if generation is None:
            return Timings(_elapsed_ms(self.start), self.retrieval_ms)
        load_ms = generation.model_load_ms
        return Timings(
            total_ms=_elapsed_ms(self.start),
            retrieval_ms=self.retrieval_ms,
            model_load_ms=load_ms,
            generation_ms=generation.generation_ms,
            prompt_tokens=generation.prompt_tokens,
            answer_tokens=generation.answer_tokens,
            cold_start=load_ms is not None and load_ms >= COLD_START_THRESHOLD_MS,
        )


def _failure(code, message, timings=None):
    return QueryResponse(success=False, error_code=code, error_string=message, timings=timings)


def _not_found(timings):
    return QueryResponse(success=True, answer=NOT_FOUND_ANSWER, found=False, timings=timings)


def _chunk_token_target(index_path):
    """Return the index's chunk token target, or ``None`` if the index can't provide it."""
    metadata = read_metadata(index_path)
    try:
        return int(metadata["target_chunk_tokens"])
    except (TypeError, KeyError, ValueError):
        return None


def _budget_error(config, chunk_tokens):
    needed = config.retrieval_limit * chunk_tokens + PROMPT_ALLOWANCE_TOKENS + config.model.max_answer_tokens
    if needed <= config.model.num_ctx:
        return None
    return (
        "Config doesn't fit the context window: {l} passages x {c} tokens + {p} for the prompt + {a} "
        "for the answer is {n} tokens, more than llm.num_ctx ({x})."
    ).format(
        l=config.retrieval_limit, c=chunk_tokens, p=PROMPT_ALLOWANCE_TOKENS,
        a=config.model.max_answer_tokens, n=needed, x=config.model.num_ctx,
    )


def _citation(chunk):
    return Citation(
        chunk.chunk_id, chunk.rfc_number, chunk.rfc_title, chunk.section_number, chunk.section_title
    )


def _answer(user_query, config):
    clock = _Clock()

    chunk_tokens = _chunk_token_target(config.index_path)
    if chunk_tokens is None:
        return _failure(
            QueryErrorCode.INDEX_UNAVAILABLE,
            "The index at {p!r} can't be read. Build it with `python ingest.py`.".format(p=config.index_path),
            clock.timings(),
        )
    budget_error = _budget_error(config, chunk_tokens)
    if budget_error is not None:
        return _failure(QueryErrorCode.CONFIG_INVALID, budget_error, clock.timings())

    retrieval_start = time.perf_counter()
    results = search(config.index_path, user_query, config.retrieval_limit)
    clock.retrieval_ms = _elapsed_ms(retrieval_start)
    if results is None:
        return _failure(
            QueryErrorCode.INDEX_UNAVAILABLE,
            "The index at {p!r} can't be searched.".format(p=config.index_path),
            clock.timings(),
        )
    if not results:
        return _not_found(clock.timings())

    chunks = [result.chunk for result in results]
    try:
        generation = generate_answer(user_query, chunks, config.model)
    except ModelUnavailableError as exc:
        return _failure(QueryErrorCode.MODEL_UNAVAILABLE, str(exc), clock.timings())
    except ModelResponseError as exc:
        return _failure(QueryErrorCode.MODEL_INVALID_RESPONSE, str(exc), clock.timings())

    timings = clock.timings(generation)
    if not generation.found:
        return _not_found(timings)
    return QueryResponse(
        success=True,
        answer=generation.answer,
        found=True,
        citations=[_citation(chunk) for chunk in generation.cited],
        timings=timings,
    )


def query(user_query):
    """Answer a natural-language query about RFCs.

    Returns a :class:`QueryResponse`. Expected failures, such as invalid input, a missing index or an
    unavailable model, are reported through the response rather than raised.
    """
    if not _is_valid_query(user_query):
        return _failure(
            QueryErrorCode.INVALID_QUERY,
            "Query must be a non-empty string with at least one non-whitespace token.",
        )
    try:
        config = load_query_config(CONFIG_PATH)
    except QueryConfigError as exc:
        return _failure(QueryErrorCode.CONFIG_INVALID, str(exc))
    return _answer(user_query, config)


def _print_success(response):
    print(response.answer)
    if response.citations:
        print()
        print("Sources:")
        for citation in response.citations:
            print(
                "  RFC {rfc} section {section}: {title} ({id})".format(
                    rfc=citation.rfc_number,
                    section=citation.section_number,
                    title=citation.section_title,
                    id=citation.chunk_id,
                )
            )
    timings = response.timings
    if timings is not None and timings.cold_start:
        print()
        print("Note: the model was loaded for this query, which took {s:.1f} seconds.".format(
            s=timings.model_load_ms / 1000
        ))


def main(argv=None):
    """Console entry point: print the answer or error and return an exit code."""
    parser = argparse.ArgumentParser(description="Ask a question about RFCs.")
    parser.add_argument("query", help="The natural-language query to answer.")
    args = parser.parse_args(argv)

    response = query(args.query)
    if response.success:
        _print_success(response)
        return 0

    _log_error(response.error_string)
    return 1


if __name__ == "__main__":
    sys.exit(main())
