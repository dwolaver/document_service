import logging
import os
import sqlite3

import pytest

from rfc_qa import paths
from rfc_qa.chunk import Chunk
from rfc_qa.errors import IndexBuildError, IndexUnavailableError
from rfc_qa.retrieval import keyword_index
from rfc_qa.retrieval.keyword_index import build_index, main, read_metadata, search
from tests.conftest import split_stderr

METADATA = {"embedding_model_name": "nomic-embed-text", "max_chunk_chars": 2970}


def _chunk(number, section, title, text):
    return Chunk(
        f"rfc{number}-s{section}-p0",
        number,
        f"RFC {number}",
        "tcp",
        section,
        title,
        text,
    )


CHUNKS = [
    _chunk(793, "3.4", "Establishing a connection", "The three-way handshake uses SYN segments."),
    _chunk(9293, "3.5", "Establishing a Connection", "The handshake reduces old duplicates."),
    _chunk(9110, "8.6", "Content-Length", "A sender SHOULD NOT send this field in some cases."),
    _chunk(9110, "1", "Introduction", "ECONNRESET appears only in this chunk of the index."),
]


@pytest.fixture
def index_path(tmp_path):
    path = str(tmp_path / "index.db")
    build_index(CHUNKS, METADATA, path)
    return path


def _ids(results):
    return [result.chunk.chunk_id for result in results]


# --- Building (task 4.1) ---


def test_build_writes_a_complete_index(index_path):
    handshake = search(index_path, "handshake", 10)
    assert len(handshake) == 2
    econnreset = search(index_path, "econnreset")
    assert econnreset[0].chunk == CHUNKS[3]


def test_index_records_its_configuration(index_path):
    assert read_metadata(index_path) == {
        "embedding_model_name": "nomic-embed-text",
        "max_chunk_chars": "2970",
    }


def test_build_replaces_an_existing_index(index_path):
    build_index(CHUNKS[:1], METADATA, index_path)
    assert search(index_path, "econnreset") == []


def test_failed_build_leaves_existing_index_and_no_temporary_file(index_path, tmp_path, capsys):
    capsys.readouterr()
    before = open(index_path, "rb").read()
    duplicate = [CHUNKS[0], CHUNKS[0]]
    with pytest.raises(IndexBuildError, match="Failed to build index") as excinfo:
        build_index(duplicate, METADATA, index_path)
    assert index_path in str(excinfo.value)
    assert isinstance(excinfo.value.__cause__, sqlite3.Error)
    assert open(index_path, "rb").read() == before
    assert os.listdir(tmp_path) == ["index.db"]
    assert capsys.readouterr() == ("", "")


def test_build_in_missing_directory_is_an_index_build_error(tmp_path, capsys):
    path = str(tmp_path / "missing" / "index.db")
    with pytest.raises(IndexBuildError, match="Failed to build index") as excinfo:
        build_index(CHUNKS, METADATA, path)
    assert path in str(excinfo.value)
    assert isinstance(excinfo.value.__cause__, OSError)
    assert os.listdir(tmp_path) == []
    assert capsys.readouterr() == ("", "")


# --- Searching (task 4.2) ---


def test_exact_term_returns_its_chunk_first(index_path):
    assert _ids(search(index_path, "ECONNRESET"))[0] == "rfc9110-s1-p0"


def test_results_carry_metadata_and_scores(index_path):
    results = search(index_path, "handshake")
    result = results[0]
    assert result.chunk.rfc_title.startswith("RFC ")
    assert result.chunk.section_title
    assert result.score > 0


def test_stemming_matches_word_forms(index_path):
    assert "rfc793-s3.4-p0" in _ids(search(index_path, "establish"))


def test_title_match_ranks_above_body_match(tmp_path):
    path = str(tmp_path / "index.db")
    filler = "padding words go here to keep both of these chunks the same length"
    chunks = [
        _chunk(1, "1", "Other Topic", "congestion " + filler),
        _chunk(2, "1", "Congestion", "unrelated " + filler),
    ]
    build_index(chunks, METADATA, path)
    assert _ids(search(path, "congestion"))[0] == "rfc2-s1-p0"


def test_limit(index_path):
    results = search(index_path, "the handshake field index", 2)
    assert len(results) == 2


def test_zero_limit_returns_nothing(index_path):
    assert search(index_path, "handshake", 0) == []


@pytest.mark.parametrize(
    "query",
    [
        "Content-Length",
        '"HTTP/2',
        'handshake"',
        "a AND",
        "NOT",
        "(unbalanced",
        "col:umn",
        "*",
        "^x",
        "NEAR(a b)",
        "it's",
        "--",
        "chunks_fts",
    ],
)
def test_query_text_is_never_read_as_syntax(index_path, query):
    assert isinstance(search(index_path, query), list)


def test_operator_words_are_plain_terms(index_path):
    assert _ids(search(index_path, "NOT handshake"))[:1] != []
    assert "rfc9110-s8.6-p0" in _ids(search(index_path, "NOT", 10))


def test_hyphenated_term_finds_the_title(index_path):
    assert _ids(search(index_path, "Content-Length"))[0] == "rfc9110-s8.6-p0"


def test_no_matches_is_empty(index_path):
    assert search(index_path, "zzzzqqqq") == []


def test_query_with_no_tokens_is_empty(index_path):
    assert search(index_path, "!!! ---") == []


@pytest.mark.parametrize("read", [lambda path: search(path, "handshake"), read_metadata])
def test_missing_index_raises_and_is_not_created(tmp_path, capsys, read):
    path = str(tmp_path / "missing.db")
    with pytest.raises(IndexUnavailableError) as excinfo:
        read(path)
    assert str(excinfo.value) == f"Index not found: {path!r}. Run rfc-ingest to build it."
    assert not os.path.exists(path)
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize(
    "read, action",
    [(lambda path: search(path, "handshake"), "search"), (read_metadata, "read")],
)
def test_unreadable_index_raises_with_the_database_error(tmp_path, capsys, read, action):
    path = tmp_path / "index.db"
    content = b"this is not a database at all, but it is long enough to be read"
    path.write_bytes(content)
    with pytest.raises(IndexUnavailableError) as excinfo:
        read(str(path))
    message = str(excinfo.value)
    assert message.startswith(f"Failed to {action} index {str(path)!r}: ")
    assert message.endswith("Rebuild it with rfc-ingest.")
    assert isinstance(excinfo.value.__cause__, sqlite3.Error)
    assert path.read_bytes() == content
    assert os.listdir(tmp_path) == ["index.db"]
    assert capsys.readouterr() == ("", "")


# --- Console search (task 4.3) ---


def test_cli_prints_results(index_path, capsys):
    assert main(["ECONNRESET", "--index", index_path]) == 0
    output = capsys.readouterr().out
    assert "rfc9110-s1-p0" in output
    assert "RFC 9110 section 1: Introduction" in output
    assert "ECONNRESET appears" in output


def test_cli_limit(index_path, capsys):
    assert main(["handshake", "--index", index_path, "--limit", "1"]) == 0
    assert capsys.readouterr().out.count("section") == 1


def test_cli_reports_no_matches(index_path, capsys):
    assert main(["zzzzqqqq", "--index", index_path]) == 0
    assert "No matches." in capsys.readouterr().out


def test_cli_missing_index_prints_one_line_and_exits_1(tmp_path, capsys):
    path = str(tmp_path / "missing.db")
    assert main(["handshake", "--index", path]) == 1
    assert capsys.readouterr() == ("", f"Index not found: {path!r}. Run rfc-ingest to build it.\n")


def test_cli_unreadable_index_prints_one_line_and_exits_1(tmp_path, capsys):
    path = tmp_path / "index.db"
    path.write_bytes(b"this is not a database at all, but it is long enough to be read")
    assert main(["handshake", "--index", str(path)]) == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert err.count("\n") == 1
    assert err.startswith(f"Failed to search index {str(path)!r}: ")


def test_cli_unknown_option_exits_2_with_usage(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--bogus", "x"])
    assert excinfo.value.code == 2
    assert "usage:" in capsys.readouterr().err


def _data_dir_with_index(path):
    path.mkdir()
    build_index(CHUNKS, METADATA, str(path / "index.db"))
    return str(path)


def test_cli_data_dir_flag_finds_its_index(tmp_path, capsys):
    data_dir = _data_dir_with_index(tmp_path / "flag")
    assert main(["ECONNRESET", "--data-dir", data_dir]) == 0
    assert "rfc9110-s1-p0" in capsys.readouterr().out


def test_cli_data_dir_from_the_environment(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv(paths.DATA_DIR_ENV, _data_dir_with_index(tmp_path / "env"))
    assert main(["ECONNRESET"]) == 0
    assert "rfc9110-s1-p0" in capsys.readouterr().out


def test_cli_index_flag_wins_over_the_data_directory(index_path, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv(paths.DATA_DIR_ENV, str(tmp_path / "empty"))
    assert main(["ECONNRESET", "--index", index_path]) == 0
    assert "rfc9110-s1-p0" in capsys.readouterr().out


def test_cli_data_dir_without_an_index(tmp_path, capsys):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert main(["handshake", "--data-dir", str(empty)]) != 0
    assert "Run rfc-ingest" in capsys.readouterr().err
    assert os.listdir(empty) == []


def test_long_excerpts_are_shortened():
    assert keyword_index._excerpt("word " * 100).endswith("...")


# --- Logging ---


def _index_records(caplog):
    return [(r.levelno, r.getMessage()) for r in caplog.records if r.name == "rfc_qa.retrieval.keyword_index"]


def test_build_is_logged(tmp_path, caplog):
    caplog.set_level(logging.DEBUG, logger="rfc_qa")
    path = str(tmp_path / "index.db")
    build_index(iter(CHUNKS), METADATA, path)
    assert _index_records(caplog) == [(logging.INFO, f"Writing 4 chunks to the index at {path!r}")]
    assert len(search(path, "handshake", 10)) == 2


@pytest.mark.parametrize("text, limit, count", [("handshake", 10, 2), ("zzzzqqqq", 5, 0), ("!!!", 5, 0)])
def test_search_is_logged(index_path, caplog, text, limit, count):
    caplog.set_level(logging.DEBUG, logger="rfc_qa")
    search(index_path, text, limit)
    assert _index_records(caplog) == [
        (logging.DEBUG, f"Searched {index_path!r} for {text!r} (limit {limit}): {count} results")
    ]


def test_missing_index_is_raised_not_logged(tmp_path, caplog):
    caplog.set_level(logging.DEBUG, logger="rfc_qa")
    with pytest.raises(IndexUnavailableError) as excinfo:
        search(str(tmp_path / "missing.db"), "handshake")
    assert _index_records(caplog) == []
    assert all(str(excinfo.value) not in record.getMessage() for record in caplog.records)


# --- -v ---


def test_cli_is_quiet_without_v(index_path, capsys):
    assert main(["handshake", "--index", index_path]) == 0
    assert capsys.readouterr().err == ""


def test_cli_v_leaves_output_unchanged_and_shows_no_detail(index_path, capsys):
    assert main(["handshake", "--index", index_path]) == 0
    quiet_out = capsys.readouterr().out
    assert main(["handshake", "--index", index_path, "-v"]) == 0
    captured = capsys.readouterr()
    assert captured.out == quiet_out
    # A search logs only detail, so -v adds nothing.
    assert captured.err == ""


def test_cli_vv_shows_the_search(index_path, capsys):
    assert main(["handshake", "--index", index_path, "-vv"]) == 0
    captured = capsys.readouterr()
    levels, other = split_stderr(captured.err)
    assert other == [] and set(levels) == {"DEBUG"}
    assert f"Searched {index_path!r} for 'handshake' (limit 5): 2 results" in captured.err


def test_cli_vv_failure_ends_with_the_error_once(tmp_path, capsys):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert main(["handshake", "--data-dir", str(empty), "-vv"]) == 1
    captured = capsys.readouterr()
    message = f"Index not found: {str(empty / 'index.db')!r}. Run rfc-ingest to build it."
    levels, other = split_stderr(captured.err)
    assert levels == ["DEBUG"] and other == [message]
    assert captured.err.endswith(message + "\n")
    assert captured.out == ""
