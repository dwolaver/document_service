import os

import pytest

import keyword_index
from chunker import Chunk
from keyword_index import build_index, main, read_metadata, search

METADATA = {"embedding_model_name": "nomic-embed-text", "max_chunk_chars": 2970}


def _chunk(number, section, title, text):
    return Chunk(
        "rfc{n}-s{s}-p0".format(n=number, s=section), number, "RFC {n}".format(n=number), "tcp",
        section, title, text,
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
    assert build_index(CHUNKS, METADATA, path) is True
    return path


def _ids(results):
    return [result.chunk.chunk_id for result in results]


# --- Building (task 4.1) ---

def test_build_writes_a_complete_index(index_path):
    assert len(search(index_path, "handshake", 10)) == 2
    assert search(index_path, "econnreset")[0].chunk == CHUNKS[3]


def test_index_records_its_configuration(index_path):
    assert read_metadata(index_path) == {
        "embedding_model_name": "nomic-embed-text",
        "max_chunk_chars": "2970",
    }


def test_build_replaces_an_existing_index(index_path):
    assert build_index(CHUNKS[:1], METADATA, index_path) is True
    assert search(index_path, "econnreset") == []


def test_failed_build_leaves_existing_index_and_no_temporary_file(index_path, tmp_path, capsys):
    before = open(index_path, "rb").read()
    duplicate = [CHUNKS[0], CHUNKS[0]]
    assert build_index(duplicate, METADATA, index_path) is False
    assert open(index_path, "rb").read() == before
    assert os.listdir(tmp_path) == ["index.db"]
    assert "Failed to build index" in capsys.readouterr().err


def test_build_in_missing_directory_reports_a_failure(tmp_path, capsys):
    assert build_index(CHUNKS, METADATA, str(tmp_path / "missing" / "index.db")) is False
    assert "Failed to build index" in capsys.readouterr().err


# --- Searching (task 4.2) ---

def test_exact_term_returns_its_chunk_first(index_path):
    assert _ids(search(index_path, "ECONNRESET"))[0] == "rfc9110-s1-p0"


def test_results_carry_metadata_and_scores(index_path):
    result = search(index_path, "handshake")[0]
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
    assert build_index(chunks, METADATA, path) is True
    assert _ids(search(path, "congestion"))[0] == "rfc2-s1-p0"


def test_limit(index_path):
    assert len(search(index_path, "the handshake field index", 2)) == 2


def test_zero_limit_returns_nothing(index_path):
    assert search(index_path, "handshake", 0) == []


@pytest.mark.parametrize(
    "query",
    ['Content-Length', '"HTTP/2', 'handshake"', "a AND", "NOT", "(unbalanced", "col:umn", "*", "^x",
     "NEAR(a b)", "it's", "--", "chunks_fts"],
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


def test_missing_index_reports_and_does_not_create_it(tmp_path, capsys):
    path = str(tmp_path / "missing.db")
    assert search(path, "handshake") is None
    assert not os.path.exists(path)
    assert "Index not found" in capsys.readouterr().err


def test_corrupt_index_reports_a_diagnostic(tmp_path, capsys):
    path = tmp_path / "index.db"
    path.write_bytes(b"this is not a database at all, but it is long enough to be read")
    assert search(str(path), "handshake") is None
    assert "Failed to search index" in capsys.readouterr().err


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


def test_cli_missing_index_is_non_zero(tmp_path, capsys):
    assert main(["handshake", "--index", str(tmp_path / "missing.db")]) != 0
    assert "Index not found" in capsys.readouterr().err


def test_long_excerpts_are_shortened():
    assert keyword_index._excerpt("word " * 100).endswith("...")
