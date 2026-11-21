"""Build the RFC search index from the corpus manifest.

This is the offline half of the RAG pipeline: it downloads any missing RFCs, parses and chunks
them, then builds the index. A problem with any RFC fails the whole run, so the index is complete
or left unchanged.
"""

import argparse
import logging
import os
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypeGuard

from rfc_qa import paths
from rfc_qa.chunk import Chunk
from rfc_qa.cli import add_verbose_argument, configure_logging, report_error
from rfc_qa.errors import ConfigError, IngestError, RfcQaError
from rfc_qa.ingestion.chunker import chunk_sections
from rfc_qa.ingestion.rfc_downloader import download_rfc
from rfc_qa.ingestion.rfc_parser import parse_rfc
from rfc_qa.retrieval.keyword_index import build_index

logger = logging.getLogger(__name__)

FAMILIES = ("http", "tls", "tcp")


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
    def max_chunk_chars(self) -> int:
        """The chunk size limit in characters, derived from the token target."""
        return int(self.target_chunk_tokens * self.chars_per_token)

    def as_metadata(self) -> dict[str, object]:
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


def _is_integer(value: object) -> TypeGuard[int]:
    # bool is a subclass of int but is not a valid number here.
    return isinstance(value, int) and not isinstance(value, bool)


def _parse_corpus_entry(entry: object) -> CorpusEntry:
    if not isinstance(entry, dict):
        raise ConfigError(f"Corpus entry is not an object: {entry!r}")
    number, family, title = entry.get("number"), entry.get("family"), entry.get("title")
    if not _is_integer(number) or number <= 0:
        raise ConfigError(f"Corpus entry has an invalid RFC number: {entry!r}")
    if family not in FAMILIES:
        raise ConfigError(f"Corpus entry has an unknown family: {entry!r}")
    if not isinstance(title, str) or not title.strip():
        raise ConfigError(f"Corpus entry has an invalid title: {entry!r}")
    return CorpusEntry(number, family, title)


def load_corpus(path: paths.ConfigFile) -> list[CorpusEntry]:
    """Return the validated manifest entries, raising :class:`~rfc_qa.errors.ConfigError` if it's invalid."""
    rfcs = paths.read_toml(path).get("rfcs")
    if not isinstance(rfcs, list) or not rfcs:
        raise ConfigError(f"Corpus {str(path)!r} must have a non-empty 'rfcs' list.")
    entries = [_parse_corpus_entry(entry) for entry in rfcs]
    seen: set[int] = set()
    for entry in entries:
        if entry.number in seen:
            raise ConfigError(f"Corpus lists RFC {entry.number} more than once.")
        seen.add(entry.number)
    return entries


def _positive_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ConfigError(f"Config {name} must be a positive number, got {value!r}.")
    return value


def _positive_integer(value: object, name: str) -> int:
    if not _is_integer(value) or value <= 0:
        raise ConfigError(f"Config {name} must be a positive integer, got {value!r}.")
    return value


def load_config(path: paths.ConfigFile) -> IngestConfig:
    """Return the validated configuration, raising :class:`~rfc_qa.errors.ConfigError` if it's invalid."""
    data = paths.read_toml(path)
    model = data.get("embedding_model")
    if not isinstance(model, dict):
        raise ConfigError(f"Config embedding_model must be an object, got {model!r}.")
    name = model.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ConfigError(f"Config embedding_model.name must be a name, got {name!r}.")
    max_tokens = _positive_integer(model.get("max_tokens"), "embedding_model.max_tokens")
    chars_per_token = _positive_number(data.get("chars_per_token"), "chars_per_token")
    target = _positive_integer(data.get("target_chunk_tokens"), "target_chunk_tokens")
    if target > max_tokens:
        raise ConfigError(
            f"Config target_chunk_tokens ({target}) exceeds embedding_model.max_tokens ({max_tokens})."
        )
    config = IngestConfig(name, max_tokens, chars_per_token, target)
    if config.max_chunk_chars < 1:
        raise ConfigError("Config produces an empty chunk size limit.")
    return config


def _rfc_path(rfc_dir: str, number: int) -> str:
    return os.path.join(rfc_dir, f"rfc{number}.txt")


def _ensure_downloaded(entries: Sequence[CorpusEntry], rfc_dir: str) -> None:
    os.makedirs(rfc_dir, exist_ok=True)
    for entry in entries:
        if not os.path.exists(_rfc_path(rfc_dir, entry.number)):
            download_rfc(entry.number, rfc_dir)


def _chunk_rfc(entry: CorpusEntry, rfc_dir: str, max_chunk_chars: int) -> list[Chunk]:
    path = _rfc_path(rfc_dir, entry.number)
    try:
        with open(path, encoding="utf-8", errors="replace") as rfc_file:
            text = rfc_file.read()
    except OSError as exc:
        raise IngestError(f"RFC {entry.number}: failed to read {path!r}: {exc}") from exc
    sections = parse_rfc(text)
    chunks = chunk_sections(sections, entry.number, entry.title, entry.family, max_chunk_chars)
    if not chunks:
        raise IngestError(f"RFC {entry.number}: produced no chunks.")
    logger.debug("RFC %d: %d sections, %d chunks", entry.number, len(sections), len(chunks))
    return chunks


def run_ingestion(
    corpus_path: paths.ConfigFile, config_path: paths.ConfigFile, data_dir: str
) -> IngestSummary:
    """Build the index and return an :class:`IngestSummary`.

    Raises :class:`~rfc_qa.errors.ConfigError` for an invalid manifest or configuration,
    :class:`~rfc_qa.errors.DownloadError` for an RFC that can't be downloaded,
    :class:`~rfc_qa.errors.IngestError` for one that can't be read or yields no chunks, and
    :class:`~rfc_qa.errors.IndexBuildError` if the index can't be written.
    """
    entries = load_corpus(corpus_path)
    logger.info("%d RFCs in the manifest %r", len(entries), str(corpus_path))
    config = load_config(config_path)
    rfc_dir = os.path.join(data_dir, paths.RFCS_FOLDER)
    _ensure_downloaded(entries, rfc_dir)

    chunks: list[Chunk] = []
    for entry in entries:
        chunks.extend(_chunk_rfc(entry, rfc_dir, config.max_chunk_chars))
    logger.info("Chunked %d RFCs into %d chunks", len(entries), len(chunks))

    build_index(chunks, config.as_metadata(), os.path.join(data_dir, paths.INDEX_FILE))
    return IngestSummary(len(entries), len(chunks), max(len(chunk.text) for chunk in chunks))


def _input_paths(args: argparse.Namespace) -> tuple[paths.ConfigFile, paths.ConfigFile]:
    """Return the manifest and configuration paths, taking from the configuration directory only
    the files no flag names, so the directory is resolved only when it's used."""
    corpus_path: paths.ConfigFile | None = args.corpus
    config_path: paths.ConfigFile | None = args.config
    if corpus_path is None or config_path is None:
        config_dir = paths.resolve_config_dir(args.config_dir)
        if corpus_path is None:
            corpus_path = config_dir.file(paths.CORPUS_FILE)
        if config_path is None:
            config_path = config_dir.file(paths.INGEST_CONFIG_FILE)
    return corpus_path, config_path


def main(argv: Sequence[str] | None = None) -> int:
    """Console entry point: build the index, print a summary and return an exit code."""
    default_data_dir = paths.default_data_dir()
    parser = argparse.ArgumentParser(description="Build the RFC search index.")
    parser.add_argument(
        "--config-dir",
        help=f"Directory holding {paths.CORPUS_FILE} and {paths.INGEST_CONFIG_FILE}. "
        f"Defaults to ${paths.CONFIG_DIR_ENV}, then the packaged defaults.",
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
        help=f"Directory for the downloaded RFCs and the index. Defaults to ${paths.DATA_DIR_ENV}, then the "
        f"user data directory ({default_data_dir}).",
    )
    add_verbose_argument(parser)
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    try:
        corpus_path, config_path = _input_paths(args)
        data_dir = paths.resolve_data_dir(args.data_dir)
        summary = run_ingestion(corpus_path, config_path, data_dir.path)
    except RfcQaError as exc:
        return report_error(exc)

    print(
        f"Indexed {summary.rfc_count} RFCs into {summary.chunk_count} chunks. "
        f"Largest chunk: {summary.largest_chunk_chars} characters."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
