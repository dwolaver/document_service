import json
import os

import pytest

import ingest
from ingest import IngestError, load_config, load_corpus, main, run_ingestion
from keyword_index import read_metadata, search

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ENTRIES = [
    {"number": 793, "family": "tcp", "title": "Transmission Control Protocol"},
    {"number": 9110, "family": "http", "title": "HTTP Semantics"},
]
CONFIG = {
    "embedding_model": {"name": "nomic-embed-text", "max_tokens": 2048},
    "chars_per_token": 2.7,
    "target_chunk_tokens": 1100,
}


def _write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def _corpus(tmp_path, rfcs):
    return load_corpus(_write_json(tmp_path / "corpus.json", {"rfcs": rfcs}))


def _config(tmp_path, data):
    return load_config(_write_json(tmp_path / "config.json", data))


def _modified_config(**changes):
    return {**CONFIG, **changes}


# --- Manifest (tasks 1.1 and 1.2) ---

def test_valid_manifest(tmp_path):
    entries = _corpus(tmp_path, ENTRIES)
    assert [(e.number, e.family) for e in entries] == [(793, "tcp"), (9110, "http")]
    assert entries[0].title == "Transmission Control Protocol"


def test_duplicate_rfc_is_rejected(tmp_path):
    with pytest.raises(IngestError, match="RFC 793 more than once"):
        _corpus(tmp_path, [ENTRIES[0], ENTRIES[0]])


def test_unknown_family_is_rejected(tmp_path):
    with pytest.raises(IngestError, match="unknown family"):
        _corpus(tmp_path, [{"number": 1, "family": "dns", "title": "x"}])


@pytest.mark.parametrize(
    "entry",
    [
        {"number": "793", "family": "tcp", "title": "x"},
        {"number": True, "family": "tcp", "title": "x"},
        {"number": 0, "family": "tcp", "title": "x"},
        {"family": "tcp", "title": "x"},
        {"number": 793, "family": "tcp", "title": ""},
        {"number": 793, "family": "tcp"},
        "793",
    ],
)
def test_malformed_entry_is_rejected(tmp_path, entry):
    with pytest.raises(IngestError):
        _corpus(tmp_path, [entry])


@pytest.mark.parametrize("data", [{}, [], {"rfcs": []}, {"rfcs": "793"}])
def test_malformed_manifest_is_rejected(tmp_path, data):
    with pytest.raises(IngestError):
        load_corpus(_write_json(tmp_path / "corpus.json", data))


def test_invalid_json_is_rejected(tmp_path):
    path = tmp_path / "corpus.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(IngestError, match="Failed to read"):
        load_corpus(str(path))


def test_missing_manifest_is_rejected(tmp_path):
    with pytest.raises(IngestError, match="Failed to read"):
        load_corpus(str(tmp_path / "missing.json"))


def test_real_corpus_loads_and_has_the_obsolete_pairs():
    entries = load_corpus(os.path.join(ROOT, "corpus.json"))
    numbers = {entry.number for entry in entries}
    assert len(entries) == 59
    assert {793, 9293, 2616, 9110, 8446, 9846} <= numbers


# --- Configuration (task 1.3) ---

def test_max_chunk_size_is_derived(tmp_path):
    config = _config(tmp_path, _modified_config(chars_per_token=3, target_chunk_tokens=1000))
    assert config.max_chunk_chars == 3000


def test_fractional_ratio_rounds_down(tmp_path):
    assert _config(tmp_path, CONFIG).max_chunk_chars == 2970


def test_different_model_changes_the_limit_without_code(tmp_path):
    data = {
        "embedding_model": {"name": "other-model", "max_tokens": 512},
        "chars_per_token": 4,
        "target_chunk_tokens": 400,
    }
    config = _config(tmp_path, data)
    assert config.embedding_model_name == "other-model"
    assert config.max_chunk_chars == 1600


def test_target_above_model_limit_reports_both_values(tmp_path):
    with pytest.raises(IngestError, match=r"\(3000\) exceeds .* \(2048\)"):
        _config(tmp_path, _modified_config(target_chunk_tokens=3000))


@pytest.mark.parametrize(
    "changes",
    [
        {"chars_per_token": "2.7"},
        {"chars_per_token": 0},
        {"chars_per_token": -1},
        {"chars_per_token": True},
        {"chars_per_token": None},
        {"target_chunk_tokens": 1100.5},
        {"target_chunk_tokens": 0},
        {"target_chunk_tokens": None},
        {"embedding_model": None},
        {"embedding_model": {"max_tokens": 2048}},
        {"embedding_model": {"name": "x"}},
        {"embedding_model": {"name": "x", "max_tokens": -1}},
        {"embedding_model": {"name": "x", "max_tokens": "2048"}},
    ],
)
def test_invalid_config_is_rejected(tmp_path, changes):
    with pytest.raises(IngestError, match="Config"):
        _config(tmp_path, _modified_config(**changes))


@pytest.mark.parametrize("key", ["chars_per_token", "target_chunk_tokens", "embedding_model"])
def test_missing_config_value_is_rejected(tmp_path, key):
    data = {k: v for k, v in CONFIG.items() if k != key}
    with pytest.raises(IngestError, match="Config"):
        _config(tmp_path, data)


def test_real_config_loads():
    config = load_config(os.path.join(ROOT, "ingest_config.json"))
    assert config.embedding_model_name == "nomic-embed-text"
    assert 0 < config.max_chunk_chars


# --- Pipeline (task 5.1) ---

def _copy_fixture(name, path):
    with open(os.path.join(FIXTURE_DIR, name + ".txt"), encoding="utf-8") as fixture:
        path.write_text(fixture.read(), encoding="utf-8")


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """A corpus of two fixture RFCs, with a fake downloader that records its calls."""
    data_dir = tmp_path / "data"
    downloads = []

    def fake_download(number, directory):
        downloads.append(number)
        name = {793: "early", 9110: "unpaginated"}[number]
        _copy_fixture(name, tmp_path / "data" / "rfcs" / "rfc{n}.txt".format(n=number))
        return True

    monkeypatch.setattr(ingest, "download_rfc", fake_download)
    return {
        "corpus": _write_json(tmp_path / "corpus.json", {"rfcs": ENTRIES}),
        "config": _write_json(tmp_path / "config.json", CONFIG),
        "data_dir": str(data_dir),
        "index": str(data_dir / "index.db"),
        "downloads": downloads,
    }


def _run(workspace):
    return run_ingestion(workspace["corpus"], workspace["config"], workspace["data_dir"])


def _main_args(workspace):
    return ["--corpus", workspace["corpus"], "--config", workspace["config"],
            "--data-dir", workspace["data_dir"]]


def test_success_builds_an_index_from_every_rfc(workspace):
    summary = _run(workspace)
    assert summary.rfc_count == 2
    assert summary.chunk_count > 2
    rfcs = {r.chunk.rfc_number for r in search(workspace["index"], "introduction protocol", 50)}
    assert rfcs == {793, 9110}


def test_storage_directory_is_created(workspace):
    _run(workspace)
    assert os.path.isdir(os.path.join(workspace["data_dir"], "rfcs"))
    assert workspace["downloads"] == [793, 9110]


def test_stored_rfcs_are_not_downloaded_again(workspace):
    _run(workspace)
    workspace["downloads"].clear()
    _run(workspace)
    assert workspace["downloads"] == []


def test_only_missing_rfcs_are_downloaded(workspace):
    _run(workspace)
    os.remove(os.path.join(workspace["data_dir"], "rfcs", "rfc793.txt"))
    workspace["downloads"].clear()
    _run(workspace)
    assert workspace["downloads"] == [793]


def test_two_runs_produce_the_same_chunks(workspace):
    _run(workspace)
    first = search(workspace["index"], "introduction protocol section", 50)
    _run(workspace)
    assert search(workspace["index"], "introduction protocol section", 50) == first


def test_index_records_the_configuration(workspace):
    _run(workspace)
    metadata = read_metadata(workspace["index"])
    assert metadata["embedding_model_name"] == "nomic-embed-text"
    assert metadata["embedding_max_tokens"] == "2048"
    assert metadata["chars_per_token"] == "2.7"
    assert metadata["target_chunk_tokens"] == "1100"
    assert metadata["max_chunk_chars"] == "2970"


def test_chunks_respect_the_configured_maximum(workspace, tmp_path):
    workspace["config"] = _write_json(
        tmp_path / "config.json", _modified_config(chars_per_token=1, target_chunk_tokens=60)
    )
    assert _run(workspace).largest_chunk_chars <= 60


def test_summary_is_printed(workspace, capsys):
    assert main(_main_args(workspace)) == 0
    output = capsys.readouterr().out
    assert "Indexed 2 RFCs into" in output
    assert "Largest chunk:" in output


def test_failed_download_names_the_rfc(workspace, monkeypatch, capsys):
    monkeypatch.setattr(ingest, "download_rfc", lambda number, directory: False)
    assert main(_main_args(workspace)) != 0
    assert "RFC 793: download failed." in capsys.readouterr().err
    assert not os.path.exists(workspace["index"])


def test_rfc_with_no_chunks_names_the_rfc(workspace, capsys):
    rfc_dir = os.path.join(workspace["data_dir"], "rfcs")
    os.makedirs(rfc_dir)
    for number in (793, 9110):
        with open(os.path.join(rfc_dir, "rfc{n}.txt".format(n=number)), "w") as rfc_file:
            rfc_file.write("no structure here\n")
    assert main(_main_args(workspace)) != 0
    assert "RFC 793: produced no chunks." in capsys.readouterr().err
    assert not os.path.exists(workspace["index"])


def test_failed_run_keeps_the_earlier_index(workspace, monkeypatch):
    _run(workspace)
    before = open(workspace["index"], "rb").read()
    os.remove(os.path.join(workspace["data_dir"], "rfcs", "rfc793.txt"))
    monkeypatch.setattr(ingest, "download_rfc", lambda number, directory: False)
    assert main(_main_args(workspace)) != 0
    assert open(workspace["index"], "rb").read() == before
    assert sorted(os.listdir(workspace["data_dir"])) == ["index.db", "rfcs"]


def test_invalid_config_fails_before_writing_an_index(workspace, tmp_path, capsys):
    workspace["config"] = _write_json(
        tmp_path / "config.json", _modified_config(target_chunk_tokens=9999)
    )
    assert main(_main_args(workspace)) != 0
    assert "exceeds" in capsys.readouterr().err
    assert workspace["downloads"] == []
    assert not os.path.exists(workspace["index"])
