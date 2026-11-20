"""Build the RFC search index from the corpus manifest.

This is the offline half of the RAG pipeline: it downloads any missing RFCs, parses and chunks
them, then builds the index. A problem with any RFC fails the whole run, so the index is complete
or left unchanged.
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass

from rfc_qa import paths
from rfc_qa.ingestion.chunker import chunk_sections
from rfc_qa.ingestion.rfc_downloader import download_rfc
from rfc_qa.ingestion.rfc_parser import parse_rfc
from rfc_qa.retrieval.keyword_index import build_index

FAMILIES = ("http", "tls", "tcp")


class IngestError(Exception):
    """A problem that stops ingestion, with a message ready to show."""


@dataclass(frozen=True)
class CorpusEntry:
    number: int
    family: str
    title: str


@dataclass(frozen=True)
class IngestConfig:
    embedding_model_name: str
    embedding_max_tokens: int
    chars_per_token: float
    target_chunk_tokens: int

    @property
    def max_chunk_chars(self):
        """The chunk size limit in characters, derived from the token target."""
        return int(self.target_chunk_tokens * self.chars_per_token)

    def as_metadata(self):
        return {
            "embedding_model_name": self.embedding_model_name,
            "embedding_max_tokens": self.embedding_max_tokens,
            "chars_per_token": self.chars_per_token,
            "target_chunk_tokens": self.target_chunk_tokens,
            "max_chunk_chars": self.max_chunk_chars,
        }


@dataclass(frozen=True)
class IngestSummary:
    rfc_count: int
    chunk_count: int
    largest_chunk_chars: int


def _log_error(message):
    print(message, file=sys.stderr)


def _load_json(path):
    try:
        with open(path, encoding="utf-8") as json_file:
            return json.load(json_file)
    except (OSError, ValueError) as exc:
        raise IngestError("Failed to read {p!r}: {e}".format(p=path, e=exc)) from exc


def _is_integer(value):
    # bool is a subclass of int but is not a valid number here.
    return isinstance(value, int) and not isinstance(value, bool)


def _parse_corpus_entry(entry):
    if not isinstance(entry, dict):
        raise IngestError("Corpus entry is not an object: {e!r}".format(e=entry))
    number, family, title = entry.get("number"), entry.get("family"), entry.get("title")
    if not _is_integer(number) or number <= 0:
        raise IngestError("Corpus entry has an invalid RFC number: {e!r}".format(e=entry))
    if family not in FAMILIES:
        raise IngestError("Corpus entry has an unknown family: {e!r}".format(e=entry))
    if not isinstance(title, str) or not title.strip():
        raise IngestError("Corpus entry has an invalid title: {e!r}".format(e=entry))
    return CorpusEntry(number, family, title)


def load_corpus(path):
    """Return the validated manifest entries, raising :class:`IngestError` if it's invalid."""
    data = _load_json(path)
    rfcs = data.get("rfcs") if isinstance(data, dict) else None
    if not isinstance(rfcs, list) or not rfcs:
        raise IngestError("Corpus {p!r} must have a non-empty 'rfcs' list.".format(p=path))
    entries = [_parse_corpus_entry(entry) for entry in rfcs]
    seen = set()
    for entry in entries:
        if entry.number in seen:
            raise IngestError("Corpus lists RFC {n} more than once.".format(n=entry.number))
        seen.add(entry.number)
    return entries


def _positive_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise IngestError("Config {n} must be a positive number, got {v!r}.".format(n=name, v=value))
    return value


def _positive_integer(value, name):
    if not _is_integer(value) or value <= 0:
        raise IngestError("Config {n} must be a positive integer, got {v!r}.".format(n=name, v=value))
    return value


def load_config(path):
    """Return the validated configuration, raising :class:`IngestError` if it's invalid."""
    data = _load_json(path)
    if not isinstance(data, dict):
        raise IngestError("Config {p!r} must be a JSON object.".format(p=path))
    model = data.get("embedding_model")
    if not isinstance(model, dict):
        raise IngestError("Config embedding_model must be an object, got {v!r}.".format(v=model))
    name = model.get("name")
    if not isinstance(name, str) or not name.strip():
        raise IngestError("Config embedding_model.name must be a name, got {v!r}.".format(v=name))
    max_tokens = _positive_integer(model.get("max_tokens"), "embedding_model.max_tokens")
    chars_per_token = _positive_number(data.get("chars_per_token"), "chars_per_token")
    target = _positive_integer(data.get("target_chunk_tokens"), "target_chunk_tokens")
    if target > max_tokens:
        raise IngestError(
            "Config target_chunk_tokens ({t}) exceeds embedding_model.max_tokens ({m}).".format(
                t=target, m=max_tokens
            )
        )
    config = IngestConfig(name, max_tokens, chars_per_token, target)
    if config.max_chunk_chars < 1:
        raise IngestError("Config produces an empty chunk size limit.")
    return config


def _rfc_path(rfc_dir, number):
    return os.path.join(rfc_dir, "rfc{n}.txt".format(n=number))


def _ensure_downloaded(entries, rfc_dir):
    os.makedirs(rfc_dir, exist_ok=True)
    for entry in entries:
        if not os.path.exists(_rfc_path(rfc_dir, entry.number)):
            if not download_rfc(entry.number, rfc_dir):
                raise IngestError("RFC {n}: download failed.".format(n=entry.number))


def _chunk_rfc(entry, rfc_dir, max_chunk_chars):
    with open(_rfc_path(rfc_dir, entry.number), encoding="utf-8", errors="replace") as rfc_file:
        sections = parse_rfc(rfc_file.read())
    chunks = chunk_sections(sections, entry.number, entry.title, entry.family, max_chunk_chars)
    if not chunks:
        raise IngestError("RFC {n}: produced no chunks.".format(n=entry.number))
    return chunks


def run_ingestion(corpus_path, config_path, data_dir):
    """Build the index, returning an :class:`IngestSummary` or raising :class:`IngestError`."""
    entries = load_corpus(corpus_path)
    config = load_config(config_path)
    rfc_dir = os.path.join(data_dir, paths.RFCS_FOLDER)
    _ensure_downloaded(entries, rfc_dir)

    chunks = []
    for entry in entries:
        chunks.extend(_chunk_rfc(entry, rfc_dir, config.max_chunk_chars))

    if not build_index(chunks, config.as_metadata(), os.path.join(data_dir, paths.INDEX_FILE)):
        raise IngestError("Index build failed.")
    return IngestSummary(len(entries), len(chunks), max(len(chunk.text) for chunk in chunks))


def _input_paths(args):
    """Return the manifest and configuration paths, taking from the configuration directory only
    the files no flag names, so the directory is resolved only when it's used."""
    corpus_path, config_path = args.corpus, args.config
    if corpus_path is None or config_path is None:
        config_dir = paths.resolve_config_dir(args.config_dir)
        if corpus_path is None:
            corpus_path = config_dir.file(paths.CORPUS_FILE)
        if config_path is None:
            config_path = config_dir.file(paths.INGEST_CONFIG_FILE)
    return corpus_path, config_path


def main(argv=None):
    """Console entry point: build the index, print a summary and return an exit code."""
    parser = argparse.ArgumentParser(description="Build the RFC search index.")
    parser.add_argument(
        "--config-dir",
        help="Directory holding {c} and {i}. Defaults to ${e}, then config/ at the repository "
        "root.".format(c=paths.CORPUS_FILE, i=paths.INGEST_CONFIG_FILE, e=paths.CONFIG_DIR_ENV),
    )
    parser.add_argument(
        "--corpus",
        help="Path to the corpus manifest, instead of the one in the configuration directory.",
    )
    parser.add_argument(
        "--config",
        help="Path to the ingestion configuration, instead of the one in the configuration directory.",
    )
    parser.add_argument(
        "--data-dir",
        help="Directory for the downloaded RFCs and the index. Defaults to ${e}, then data/ at the "
        "repository root.".format(e=paths.DATA_DIR_ENV),
    )
    args = parser.parse_args(argv)

    try:
        corpus_path, config_path = _input_paths(args)
        data_dir = paths.resolve_data_dir(args.data_dir)
        summary = run_ingestion(corpus_path, config_path, data_dir.path)
    except (IngestError, paths.ConfigDirError) as exc:
        _log_error(str(exc))
        return 1

    print(
        "Indexed {r} RFCs into {c} chunks. Largest chunk: {l} characters.".format(
            r=summary.rfc_count, c=summary.chunk_count, l=summary.largest_chunk_chars
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
