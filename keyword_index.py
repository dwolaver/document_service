"""Build and search the keyword index. All SQL in the project stays in this module."""

import argparse
import os
import pathlib
import re
import sqlite3
import sys
import tempfile
from dataclasses import dataclass

from chunker import Chunk

DEFAULT_INDEX_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "index.db")
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


def _log_error(message):
    print(message, file=sys.stderr)


def _write_index(path, chunks, metadata):
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
                (c.chunk_id, c.rfc_number, c.rfc_title, c.family, c.section_number,
                 c.section_title, c.text)
                for c in chunks
            ],
        )
        connection.execute("INSERT INTO chunks_fts (chunks_fts) VALUES ('rebuild')")
        connection.commit()
    finally:
        connection.close()


def build_index(chunks, metadata, path):
    """Write ``chunks`` and ``metadata`` to a new index at ``path``, replacing it atomically.

    Returns ``True`` on success. On failure it returns ``False`` after printing a diagnostic,
    leaving any existing index unchanged and no temporary file behind.
    """
    tmp_path = None
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=os.path.dirname(os.path.abspath(path)), prefix=".index.", suffix=".tmp"
        )
        os.close(tmp_fd)
        _write_index(tmp_path, chunks, metadata)
        os.replace(tmp_path, path)
        return True
    except (OSError, sqlite3.Error) as exc:
        _log_error("Failed to build index {p!r}: {e}".format(p=path, e=exc))
        if tmp_path is not None and os.path.exists(tmp_path):
            os.remove(tmp_path)
        return False


def _connect_read_only(path):
    """Open an existing index. SQLite would otherwise create an empty file at a missing path."""
    if not os.path.isfile(path):
        _log_error("Index not found: {p!r}. Run ingest.py to build it.".format(p=path))
        return None
    uri = pathlib.Path(path).resolve().as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


def read_metadata(path):
    """Return the index's build configuration as a dict, or ``None`` if it can't be read."""
    connection = _connect_read_only(path)
    if connection is None:
        return None
    try:
        return dict(connection.execute("SELECT key, value FROM metadata"))
    except sqlite3.Error as exc:
        _log_error("Failed to read index {p!r}: {e}".format(p=path, e=exc))
        return None
    finally:
        connection.close()


def _to_match_expression(query_text):
    """Quote each token, so that user text can't be read as FTS query syntax."""
    tokens = re.findall(r"\w+", query_text)
    return " OR ".join('"{t}"'.format(t=token) for token in tokens)


def search(path, query_text, limit=DEFAULT_LIMIT):
    """Return up to ``limit`` chunks matching ``query_text``, best first.

    Returns an empty list when nothing matches, and ``None`` after printing a diagnostic when the
    index can't be read.
    """
    connection = _connect_read_only(path)
    if connection is None:
        return None
    try:
        expression = _to_match_expression(query_text)
        if not expression or limit <= 0:
            return []
        rows = connection.execute(_SEARCH_SQL, (_TITLE_WEIGHT, _TEXT_WEIGHT, expression, limit))
        # bm25() is more negative for better matches.
        return [SearchResult(Chunk(*row[:7]), -row[7]) for row in rows]
    except sqlite3.Error as exc:
        _log_error("Failed to search index {p!r}: {e}".format(p=path, e=exc))
        return None
    finally:
        connection.close()


def _excerpt(text):
    flattened = " ".join(text.split())
    if len(flattened) <= _EXCERPT_CHARS:
        return flattened
    return flattened[:_EXCERPT_CHARS].rstrip() + "..."


def main(argv=None):
    """Console entry point: print matching chunks and return an exit code."""
    parser = argparse.ArgumentParser(description="Search the RFC keyword index.")
    parser.add_argument("query", help="The search text.")
    parser.add_argument("--index", default=DEFAULT_INDEX_PATH, help="Path to the index file.")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="Maximum results.")
    args = parser.parse_args(argv)

    results = search(args.index, args.query, args.limit)
    if results is None:
        return 1
    for result in results:
        chunk = result.chunk
        print(
            "{id}  RFC {rfc} section {section}: {title}".format(
                id=chunk.chunk_id,
                rfc=chunk.rfc_number,
                section=chunk.section_number,
                title=chunk.section_title,
            )
        )
        print("    " + _excerpt(chunk.text))
    if not results:
        print("No matches.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
