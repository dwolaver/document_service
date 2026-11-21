"""Build and search the keyword index. All SQL in the project stays in this module."""

import argparse
import logging
import os
import pathlib
import re
import sqlite3
import sys
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from rfc_qa import paths
from rfc_qa.chunk import Chunk
from rfc_qa.cli import add_verbose_argument, configure_logging, report_error
from rfc_qa.errors import IndexBuildError, IndexUnavailableError, RfcQaError

logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 5

# BM25 weight of a match in each FTS column, so section titles count more than body text.
_TITLE_WEIGHT = 10.0
_TEXT_WEIGHT = 1.0
_EXCERPT_CHARS = 160

_SCHEMA = """
CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE chunks (
    id INTEGER PRIMARY KEY,
    chunk_id TEXT NOT NULL UNIQUE,
    rfc_number INTEGER NOT NULL,
    rfc_title TEXT NOT NULL,
    family TEXT NOT NULL,
    section_number TEXT NOT NULL,
    section_title TEXT NOT NULL,
    text TEXT NOT NULL
);
CREATE VIRTUAL TABLE chunks_fts USING fts5(
    section_title,
    text,
    content='chunks',
    content_rowid='id',
    tokenize='porter unicode61'
);
"""

_SEARCH_SQL = """
SELECT c.chunk_id, c.rfc_number, c.rfc_title, c.family, c.section_number, c.section_title, c.text,
       bm25(chunks_fts, ?, ?) AS rank
FROM chunks_fts
JOIN chunks AS c ON c.id = chunks_fts.rowid
WHERE chunks_fts MATCH ?
ORDER BY rank, c.chunk_id
LIMIT ?
"""


@dataclass(frozen=True)
class SearchResult:
    """A matching chunk and its relevance. A higher ``score`` is a better match."""

    chunk: Chunk
    score: float


def _write_index(path: str, chunks: Iterable[Chunk], metadata: Mapping[str, object]) -> None:
    connection = sqlite3.connect(path)
    try:
        # The file is only moved into place once complete, so a journal adds nothing.
        connection.execute("PRAGMA journal_mode=OFF")
        connection.executescript(_SCHEMA)
        connection.executemany(
            "INSERT INTO metadata (key, value) VALUES (?, ?)",
            [(key, str(value)) for key, value in sorted(metadata.items())],
        )
        connection.executemany(
            "INSERT INTO chunks (chunk_id, rfc_number, rfc_title, family, section_number,"
            " section_title, text) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (c.chunk_id, c.rfc_number, c.rfc_title, c.family, c.section_number, c.section_title, c.text)
                for c in chunks
            ],
        )
        connection.execute("INSERT INTO chunks_fts (chunks_fts) VALUES ('rebuild')")
        connection.commit()
    finally:
        connection.close()


def build_index(chunks: Iterable[Chunk], metadata: Mapping[str, object], path: str) -> None:
    """Write ``chunks`` and ``metadata`` to a new index at ``path``, replacing it atomically.

    Raises :class:`~rfc_qa.errors.IndexBuildError` on failure, leaving any existing index
    unchanged and no temporary file behind.
    """
    chunks = list(chunks)
    logger.info("Writing %d chunks to the index at %r", len(chunks), path)
    tmp_path: str | None = None
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=os.path.dirname(os.path.abspath(path)), prefix=".index.", suffix=".tmp"
        )
        os.close(tmp_fd)
        _write_index(tmp_path, chunks, metadata)
        os.replace(tmp_path, path)
    except (OSError, sqlite3.Error) as exc:
        if tmp_path is not None and os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise IndexBuildError(f"Failed to build index {path!r}: {exc}") from exc


def _unreadable(action: str, path: str, exc: sqlite3.Error) -> IndexUnavailableError:
    return IndexUnavailableError(f"Failed to {action} index {path!r}: {exc}. Rebuild it with rfc-ingest.")


def _connect_read_only(path: str) -> sqlite3.Connection:
    """Open an existing index. SQLite would otherwise create an empty file at a missing path."""
    if not os.path.isfile(path):
        raise IndexUnavailableError(f"Index not found: {path!r}. Run rfc-ingest to build it.")
    uri = pathlib.Path(path).resolve().as_uri() + "?mode=ro"
    try:
        return sqlite3.connect(uri, uri=True)
    except sqlite3.Error as exc:
        raise _unreadable("open", path, exc) from exc


def read_metadata(path: str) -> dict[str, str]:
    """Return the index's build configuration as a dict.

    Raises :class:`~rfc_qa.errors.IndexUnavailableError` if the index is missing or can't be read.
    """
    connection = _connect_read_only(path)
    try:
        return dict(connection.execute("SELECT key, value FROM metadata"))
    except sqlite3.Error as exc:
        raise _unreadable("read", path, exc) from exc
    finally:
        connection.close()


def _to_match_expression(query_text: str) -> str:
    """Quote each token, so that user text can't be read as FTS query syntax."""
    tokens = re.findall(r"\w+", query_text)
    return " OR ".join(f'"{token}"' for token in tokens)


def search(path: str, query_text: str, limit: int = DEFAULT_LIMIT) -> list[SearchResult]:
    """Return up to ``limit`` chunks matching ``query_text``, best first.

    Returns an empty list when nothing matches. Raises :class:`~rfc_qa.errors.IndexUnavailableError`
    if the index is missing or can't be read.
    """
    connection = _connect_read_only(path)
    try:
        expression = _to_match_expression(query_text)
        results: list[SearchResult] = []
        if expression and limit > 0:
            rows = connection.execute(_SEARCH_SQL, (_TITLE_WEIGHT, _TEXT_WEIGHT, expression, limit))
            # bm25() is more negative for better matches.
            results = [SearchResult(Chunk(*row[:7]), -row[7]) for row in rows]
    except sqlite3.Error as exc:
        raise _unreadable("search", path, exc) from exc
    finally:
        connection.close()
    logger.debug("Searched %r for %r (limit %d): %d results", path, query_text, limit, len(results))
    return results


def _excerpt(text: str) -> str:
    flattened = " ".join(text.split())
    if len(flattened) <= _EXCERPT_CHARS:
        return flattened
    return flattened[:_EXCERPT_CHARS].rstrip() + "..."


def main(argv: Sequence[str] | None = None) -> int:
    """Console entry point: print matching chunks and return an exit code."""
    default_data_dir = paths.default_data_dir()
    parser = argparse.ArgumentParser(description="Search the RFC keyword index.")
    parser.add_argument("query", help="The search text.")
    parser.add_argument(
        "--data-dir",
        help=f"Directory holding {paths.INDEX_FILE}. Defaults to ${paths.DATA_DIR_ENV}, then the user data "
        f"directory ({default_data_dir}).",
    )
    parser.add_argument("--index", help="Path to the index file, instead of the one in the data directory.")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="Maximum results.")
    add_verbose_argument(parser)
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    index_path = args.index
    if index_path is None:
        index_path = paths.resolve_data_dir(args.data_dir).file(paths.INDEX_FILE)
    try:
        results = search(index_path, args.query, args.limit)
    except RfcQaError as exc:
        return report_error(exc)
    for result in results:
        chunk = result.chunk
        print(
            f"{chunk.chunk_id}  RFC {chunk.rfc_number} section {chunk.section_number}: {chunk.section_title}"
        )
        print("    " + _excerpt(chunk.text))
    if not results:
        print("No matches.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
