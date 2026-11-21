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
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

from rfc_qa import paths
from rfc_qa.chunk import Chunk
from rfc_qa.cli import report_error
from rfc_qa.errors import (
    ConfigError,
    IndexUnavailableError,
    ModelResponseError,
    ModelUnavailableError,
    RfcQaError,
)
from rfc_qa.generation.answer_generator import (
    NOT_FOUND_ANSWER,
    GenerationResult,
    ModelSettings,
    generate_answer,
)
from rfc_qa.retrieval.keyword_index import read_metadata, search

# When set and not empty, replaces the configured llm.base_url.
OLLAMA_BASE_URL_ENV = "OLLAMA_BASE_URL"

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
    retrieval_ms: int | None = None
    model_load_ms: int | None = None
    generation_ms: int | None = None
    prompt_tokens: int | None = None
    answer_tokens: int | None = None
    cold_start: bool = False


@dataclass
class QueryResponse:
    """Structured result of a query.

    ``found`` is ``None`` on failure. On success it says whether the indexed RFCs answered the
    question, and ``citations`` is non-empty only when they did.
    """

    success: bool
    answer: str | None = None
    found: bool | None = None
    citations: list[Citation] = field(default_factory=list)
    timings: Timings | None = None
    error_string: str | None = None
    error_code: QueryErrorCode | None = None


@dataclass(frozen=True)
class QueryConfig:
    retrieval_limit: int
    model: ModelSettings


def _positive_integer(value: object, name: str) -> int:
    # bool is a subclass of int but is not a valid value here.
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ConfigError("Config {n} must be a positive integer, got {v!r}.".format(n=name, v=value))
    return value


def _positive_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ConfigError("Config {n} must be a positive number, got {v!r}.".format(n=name, v=value))
    return value


def _non_empty_string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError("Config {n} must be a non-empty string, got {v!r}.".format(n=name, v=value))
    return value


def _section(data: dict[str, Any], name: str) -> dict[str, Any]:
    section = data.get(name)
    if not isinstance(section, dict):
        raise ConfigError("Config {n} must be an object, got {v!r}.".format(n=name, v=section))
    return section


def load_query_config(path: paths.ConfigFile) -> QueryConfig:
    """Return the validated configuration, raising :class:`~rfc_qa.errors.ConfigError` if it's invalid.

    ``OLLAMA_BASE_URL``, when set and not empty, replaces ``llm.base_url``. The file must still give
    a valid ``llm.base_url``, so that it stays complete on its own.
    """
    try:
        with paths.as_traversable(path).open(encoding="utf-8") as config_file:
            data = json.load(config_file)
    except (OSError, ValueError) as exc:
        raise ConfigError("Failed to read {p!r}: {e}".format(p=str(path), e=exc)) from exc
    if not isinstance(data, dict):
        raise ConfigError("Config {p!r} must be a JSON object.".format(p=str(path)))

    retrieval = _section(data, "retrieval")
    llm = _section(data, "llm")
    base_url = _non_empty_string(llm.get("base_url"), "llm.base_url")
    base_url = os.environ.get(OLLAMA_BASE_URL_ENV) or base_url
    return QueryConfig(
        retrieval_limit=_positive_integer(retrieval.get("limit"), "retrieval.limit"),
        model=ModelSettings(
            model=_non_empty_string(llm.get("model"), "llm.model"),
            base_url=base_url,
            num_ctx=_positive_integer(llm.get("num_ctx"), "llm.num_ctx"),
            max_answer_tokens=_positive_integer(llm.get("max_answer_tokens"), "llm.max_answer_tokens"),
            timeout_seconds=_positive_number(llm.get("timeout_seconds"), "llm.timeout_seconds"),
        ),
    )


def _elapsed_ms(start: float) -> int:
    return int(round((time.perf_counter() - start) * 1000))


class _Clock:
    """Wall-clock timings for one query, combined with the model's own durations."""

    def __init__(self) -> None:
        self.start = time.perf_counter()
        self.retrieval_ms: int | None = None

    def timings(self, generation: GenerationResult | None = None) -> Timings:
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


def _failure(code: QueryErrorCode, message: str, timings: Timings | None = None) -> QueryResponse:
    return QueryResponse(success=False, error_code=code, error_string=message, timings=timings)


def _not_found(timings: Timings) -> QueryResponse:
    return QueryResponse(success=True, answer=NOT_FOUND_ANSWER, found=False, timings=timings)


def _chunk_token_target(index_path: str) -> int:
    """Return the chunk token target the index was built with, raising if it doesn't record one."""
    value = read_metadata(index_path).get("target_chunk_tokens")
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise IndexUnavailableError(
            "The index at {p!r} doesn't record a usable target_chunk_tokens. "
            "Rebuild it with `rfc-ingest`.".format(p=index_path)
        ) from exc


def _budget_error(config: QueryConfig, chunk_tokens: int) -> str | None:
    needed = config.retrieval_limit * chunk_tokens + PROMPT_ALLOWANCE_TOKENS + config.model.max_answer_tokens
    if needed <= config.model.num_ctx:
        return None
    return (
        "Config doesn't fit the context window: {l} passages x {c} tokens + {p} for the prompt + {a} "
        "for the answer is {n} tokens, more than llm.num_ctx ({x})."
    ).format(
        l=config.retrieval_limit,
        c=chunk_tokens,
        p=PROMPT_ALLOWANCE_TOKENS,
        a=config.model.max_answer_tokens,
        n=needed,
        x=config.model.num_ctx,
    )


def _citation(chunk: Chunk) -> Citation:
    return Citation(
        chunk.chunk_id, chunk.rfc_number, chunk.rfc_title, chunk.section_number, chunk.section_title
    )


def _retrieve(clock: _Clock, index_path: str, user_query: str, limit: int) -> list[Chunk]:
    start = time.perf_counter()
    try:
        return [result.chunk for result in search(index_path, user_query, limit)]
    finally:
        clock.retrieval_ms = _elapsed_ms(start)


def _answer(user_query: str, config: QueryConfig, index_path: str) -> QueryResponse:
    clock = _Clock()
    try:
        budget_error = _budget_error(config, _chunk_token_target(index_path))
        if budget_error is not None:
            return _failure(QueryErrorCode.CONFIG_INVALID, budget_error, clock.timings())
        chunks = _retrieve(clock, index_path, user_query, config.retrieval_limit)
        if not chunks:
            return _not_found(clock.timings())
        generation = generate_answer(user_query, chunks, config.model)
    except IndexUnavailableError as exc:
        return _failure(QueryErrorCode.INDEX_UNAVAILABLE, str(exc), clock.timings())
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


def query(user_query: str, *, config_dir: str | None = None, data_dir: str | None = None) -> QueryResponse:
    """Answer a natural-language query about RFCs.

    The query configuration is read from ``config_dir`` if given, then from the directory named by
    ``RFC_QA_CONFIG_DIR``, then from the defaults installed with the package. The index is
    ``index.db`` in ``data_dir`` if given, then in the directory named by ``RFC_QA_DATA_DIR``, then in
    the user's data directory for rfc-qa, such as ``~/.local/share/rfc-qa`` on Linux.

    Returns a :class:`QueryResponse`. Expected failures, such as an empty query, invalid
    configuration, a missing index or an unavailable model, are reported through the response
    rather than raised. A query that isn't a ``str`` is a bug in the caller and raises
    :class:`TypeError`.
    """
    if not isinstance(user_query, str):
        raise TypeError("Query must be a str, got {t}.".format(t=type(user_query).__name__))
    if not user_query.strip():
        return _failure(
            QueryErrorCode.INVALID_QUERY,
            "Query must be a non-empty string with at least one non-whitespace token.",
        )
    try:
        directory = paths.resolve_config_dir(config_dir, explicit_source="config_dir argument")
        config = load_query_config(directory.file(paths.QUERY_CONFIG_FILE))
    except ConfigError as exc:
        return _failure(QueryErrorCode.CONFIG_INVALID, str(exc))
    selected_data_dir = paths.resolve_data_dir(data_dir, explicit_source="data_dir argument")
    index_path = selected_data_dir.file(paths.INDEX_FILE)
    return _answer(user_query, config, index_path)


def _print_success(response: QueryResponse) -> None:
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
    if timings is not None and timings.cold_start and timings.model_load_ms is not None:
        print()
        print(
            "Note: the model was loaded for this query, which took {s:.1f} seconds.".format(
                s=timings.model_load_ms / 1000
            )
        )


def main(argv: Sequence[str] | None = None) -> int:
    """Console entry point: print the answer or error and return an exit code."""
    parser = argparse.ArgumentParser(description="Ask a question about RFCs.")
    parser.add_argument("query", help="The natural-language query to answer.")
    parser.add_argument(
        "--config-dir",
        help="Directory holding {q}. Defaults to ${e}, then the packaged defaults.".format(
            q=paths.QUERY_CONFIG_FILE, e=paths.CONFIG_DIR_ENV
        ),
    )
    parser.add_argument(
        "--data-dir",
        help="Directory holding {i}. Defaults to ${e}, then the user data directory ({d}).".format(
            i=paths.INDEX_FILE, e=paths.DATA_DIR_ENV, d=paths.default_data_dir()
        ),
    )
    args = parser.parse_args(argv)

    # Resolved here, not in query(), so an error names the flag the user typed.
    try:
        config_dir = paths.resolve_config_dir(args.config_dir)
        data_dir = paths.resolve_data_dir(args.data_dir)
    except RfcQaError as exc:
        return report_error(exc)

    # The packaged defaults have no path to pass on, and query() selects them the same way.
    selected_config_dir = None if config_dir.is_packaged else str(config_dir.location)
    response = query(args.query, config_dir=selected_config_dir, data_dir=data_dir.path)
    if response.success:
        _print_success(response)
        return 0

    return report_error(response.error_string)


if __name__ == "__main__":
    sys.exit(main())
