import json
import logging
import os
import pathlib
import shutil
import tomllib

import pytest

from rfc_qa import paths
from rfc_qa.errors import ConfigError, DownloadError, IndexBuildError, IngestError
from rfc_qa.ingestion import ingest
from rfc_qa.ingestion.ingest import (
    IngestSummary,
    load_config,
    load_corpus,
    main,
    run_ingestion,
)
from rfc_qa.retrieval.keyword_index import read_metadata, search
from tests.conftest import split_stderr, write_toml

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")

ENTRIES = [
    {"number": 793, "family": "tcp", "title": "Transmission Control Protocol"},
    {"number": 9110, "family": "http", "title": "HTTP Semantics"},
]
CONFIG = {
    "embedding_model": {"name": "nomic-embed-text", "max_tokens": 2048},
    "chars_per_token": 2.7,
    "target_chunk_tokens": 1100,
}


def _corpus(tmp_path, rfcs):
    return load_corpus(write_toml(tmp_path / "corpus.toml", {"rfcs": rfcs}))


def _config(tmp_path, data):
    return load_config(write_toml(tmp_path / "config.toml", data))


def _modified_config(**changes):
    return {**CONFIG, **changes}


# --- Manifest (tasks 1.1 and 1.2) ---


def test_valid_manifest(tmp_path):
    entries = _corpus(tmp_path, ENTRIES)
    assert [(e.number, e.family) for e in entries] == [(793, "tcp"), (9110, "http")]
    assert entries[0].title == "Transmission Control Protocol"


def test_duplicate_rfc_is_rejected(tmp_path):
    with pytest.raises(ConfigError, match="RFC 793 more than once"):
        _corpus(tmp_path, [ENTRIES[0], ENTRIES[0]])


def test_unknown_family_is_rejected(tmp_path):
    with pytest.raises(ConfigError, match="unknown family"):
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
    with pytest.raises(ConfigError):
        _corpus(tmp_path, [entry])


@pytest.mark.parametrize("data", [{}, {"rfcs": []}, {"rfcs": "793"}])
def test_malformed_manifest_is_rejected(tmp_path, data):
    with pytest.raises(ConfigError):
        load_corpus(write_toml(tmp_path / "corpus.toml", data))


def test_invalid_toml_names_the_file_line_and_column(tmp_path):
    path = tmp_path / "corpus.toml"
    path.write_text('rfcs = [\n    { number = 793, family = "tcp" title = "TCP" },\n]\n', encoding="utf-8")
    with pytest.raises(ConfigError) as excinfo:
        load_corpus(str(path))
    message = str(excinfo.value)
    assert message.startswith(f"Failed to read {str(path)!r}: ")
    assert message.endswith("Unclosed inline table (at line 2, column 36)")
    assert isinstance(excinfo.value.__cause__, tomllib.TOMLDecodeError)


def test_json_corpus_is_rejected(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"rfcs": ENTRIES}), encoding="utf-8")
    with pytest.raises(ConfigError, match=r"^Failed to read .*manifest\.json.*\(at line 1, column 1\)$"):
        load_corpus(str(path))


def test_missing_manifest_is_rejected(tmp_path):
    with pytest.raises(ConfigError, match="Failed to read"):
        load_corpus(str(tmp_path / "missing.toml"))


def test_real_corpus_loads_and_has_the_obsolete_pairs():
    entries = load_corpus(paths.packaged_config_dir() / "corpus.toml")
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
    with pytest.raises(ConfigError, match=r"\(3000\) exceeds .* \(2048\)"):
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
    with pytest.raises(ConfigError, match="Config"):
        _config(tmp_path, _modified_config(**changes))


@pytest.mark.parametrize("key", ["chars_per_token", "target_chunk_tokens", "embedding_model"])
def test_missing_config_value_is_rejected(tmp_path, key):
    data = {k: v for k, v in CONFIG.items() if k != key}
    with pytest.raises(ConfigError, match="Config"):
        _config(tmp_path, data)


def test_real_config_loads():
    config = load_config(paths.packaged_config_dir() / "ingest.toml")
    assert config.embedding_model_name == "nomic-embed-text"
    assert config.max_chunk_chars > 0


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
        path = pathlib.Path(directory) / f"rfc{number}.txt"
        _copy_fixture(name, path)
        return str(path)

    monkeypatch.setattr(ingest, "download_rfc", fake_download)
    return {
        "corpus": write_toml(tmp_path / "corpus.toml", {"rfcs": ENTRIES}),
        "config": write_toml(tmp_path / "config.toml", CONFIG),
        "data_dir": str(data_dir),
        "index": str(data_dir / "index.db"),
        "downloads": downloads,
    }


def _run(workspace):
    return run_ingestion(workspace["corpus"], workspace["config"], workspace["data_dir"])


def _main_args(workspace):
    return [
        "--corpus",
        workspace["corpus"],
        "--config",
        workspace["config"],
        "--data-dir",
        workspace["data_dir"],
    ]


def test_success_builds_an_index_from_every_rfc(workspace):
    summary = _run(workspace)
    assert summary.rfc_count == 2
    assert summary.chunk_count > 2
    results = search(workspace["index"], "introduction protocol", 50)
    assert results is not None
    rfcs = {r.chunk.rfc_number for r in results}
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
    assert metadata is not None
    assert metadata["embedding_model_name"] == "nomic-embed-text"
    assert metadata["embedding_max_tokens"] == "2048"
    assert metadata["chars_per_token"] == "2.7"
    assert metadata["target_chunk_tokens"] == "1100"
    assert metadata["max_chunk_chars"] == "2970"


def test_chunks_respect_the_configured_maximum(workspace, tmp_path):
    workspace["config"] = write_toml(
        tmp_path / "config.toml", _modified_config(chars_per_token=1, target_chunk_tokens=60)
    )
    assert _run(workspace).largest_chunk_chars <= 60


def test_summary_is_printed(workspace, capsys):
    assert main(_main_args(workspace)) == 0
    output = capsys.readouterr().out
    assert "Indexed 2 RFCs into" in output
    assert "Largest chunk:" in output


def _failing_download(number, directory):
    raise DownloadError(f"RFC {number}: unexpected HTTP status 503.")


def test_failed_download_prints_its_reason_once(workspace, monkeypatch, capsys):
    monkeypatch.setattr(ingest, "download_rfc", _failing_download)
    assert main(_main_args(workspace)) == 1
    assert capsys.readouterr() == ("", "RFC 793: unexpected HTTP status 503.\n")
    assert not os.path.exists(workspace["index"])


def test_failed_download_propagates_from_run_ingestion(workspace, monkeypatch):
    monkeypatch.setattr(ingest, "download_rfc", _failing_download)
    with pytest.raises(DownloadError, match="RFC 793"):
        _run(workspace)


def test_unreadable_rfc_names_the_rfc(workspace, monkeypatch, capsys):
    _run(workspace)
    os.remove(workspace["index"])
    capsys.readouterr()
    error = PermissionError(13, "Permission denied")
    real_open = open

    def fake_open(path, *args, **kwargs):
        if str(path).endswith("rfc9110.txt"):
            raise error
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", fake_open)
    with pytest.raises(IngestError, match=r"^RFC 9110: failed to read ") as excinfo:
        _run(workspace)
    assert excinfo.value.__cause__ is error
    assert not os.path.exists(workspace["index"])

    assert main(_main_args(workspace)) == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert err.count("\n") == 1
    assert err.startswith("RFC 9110: failed to read ")
    assert "Permission denied" in err
    assert not os.path.exists(workspace["index"])


def test_failed_index_build_prints_once(workspace, monkeypatch, capsys):
    def fail_build(chunks, metadata, path):
        raise IndexBuildError(f"Failed to build index {path!r}: disk full")

    monkeypatch.setattr(ingest, "build_index", fail_build)
    assert main(_main_args(workspace)) == 1
    assert capsys.readouterr() == (
        "",
        f"Failed to build index {workspace['index']!r}: disk full\n",
    )


def test_rfc_with_no_chunks_names_the_rfc(workspace, capsys):
    rfc_dir = os.path.join(workspace["data_dir"], "rfcs")
    os.makedirs(rfc_dir)
    for number in (793, 9110):
        with open(os.path.join(rfc_dir, f"rfc{number}.txt"), "w") as rfc_file:
            rfc_file.write("no structure here\n")
    assert main(_main_args(workspace)) == 1
    assert capsys.readouterr() == ("", "RFC 793: produced no chunks.\n")
    assert not os.path.exists(workspace["index"])


def test_failed_run_keeps_the_earlier_index(workspace, monkeypatch):
    _run(workspace)
    before = pathlib.Path(workspace["index"]).read_bytes()
    os.remove(os.path.join(workspace["data_dir"], "rfcs", "rfc793.txt"))
    monkeypatch.setattr(ingest, "download_rfc", _failing_download)
    assert main(_main_args(workspace)) == 1
    assert pathlib.Path(workspace["index"]).read_bytes() == before
    assert sorted(os.listdir(workspace["data_dir"])) == ["index.db", "rfcs"]


def test_invalid_manifest_fails_before_downloading(workspace, tmp_path, capsys):
    workspace["corpus"] = write_toml(tmp_path / "corpus.toml", {"rfcs": [ENTRIES[0], ENTRIES[0]]})
    with pytest.raises(ConfigError, match="RFC 793 more than once"):
        _run(workspace)
    assert workspace["downloads"] == []
    assert not os.path.exists(workspace["index"])


def test_json_corpus_flag_fails_before_downloading(workspace, tmp_path, capsys):
    corpus = tmp_path / "corpus.json"
    corpus.write_text(json.dumps({"rfcs": ENTRIES}), encoding="utf-8")
    workspace["corpus"] = str(corpus)
    assert main(_main_args(workspace)) == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert err.startswith(f"Failed to read {str(corpus)!r}: ")
    assert err.count("\n") == 1
    assert workspace["downloads"] == []
    assert not os.path.exists(workspace["index"])


def test_invalid_config_fails_before_writing_an_index(workspace, tmp_path, capsys):
    workspace["config"] = write_toml(tmp_path / "config.toml", _modified_config(target_chunk_tokens=9999))
    assert main(_main_args(workspace)) != 0
    assert "exceeds" in capsys.readouterr().err
    assert workspace["downloads"] == []
    assert not os.path.exists(workspace["index"])


# --- Configuration directory ---


@pytest.fixture
def ingestion_inputs(monkeypatch):
    """Replace run_ingestion, recording the manifest and configuration paths it's given."""
    calls = []

    def fake_run(corpus_path, config_path, data_dir):
        calls.append((str(corpus_path), str(config_path)))
        return IngestSummary(1, 1, 1)

    monkeypatch.setattr(ingest, "run_ingestion", fake_run)
    return calls


def _config_dir(path):
    path.mkdir()
    return str(path)


def test_defaults_read_from_the_packaged_configuration(ingestion_inputs, tmp_path):
    assert main(["--data-dir", str(tmp_path)]) == 0
    assert ingestion_inputs == [
        (
            str(paths.packaged_config_dir() / "corpus.toml"),
            str(paths.packaged_config_dir() / "ingest.toml"),
        )
    ]


def test_environment_selects_the_config_directory(ingestion_inputs, tmp_path, monkeypatch):
    directory = _config_dir(tmp_path / "env")
    monkeypatch.setenv(paths.CONFIG_DIR_ENV, directory)
    assert main(["--data-dir", str(tmp_path)]) == 0
    assert ingestion_inputs == [
        (os.path.join(directory, "corpus.toml"), os.path.join(directory, "ingest.toml"))
    ]


def test_flag_selects_the_config_directory_over_the_environment(ingestion_inputs, tmp_path, monkeypatch):
    directory = _config_dir(tmp_path / "flag")
    monkeypatch.setenv(paths.CONFIG_DIR_ENV, _config_dir(tmp_path / "env"))
    assert main(["--config-dir", directory, "--data-dir", str(tmp_path)]) == 0
    assert ingestion_inputs == [
        (os.path.join(directory, "corpus.toml"), os.path.join(directory, "ingest.toml"))
    ]


def test_corpus_flag_with_a_config_directory(ingestion_inputs, tmp_path):
    directory = _config_dir(tmp_path / "flag")
    corpus = str(tmp_path / "elsewhere.toml")
    assert main(["--config-dir", directory, "--corpus", corpus, "--data-dir", str(tmp_path)]) == 0
    assert ingestion_inputs == [(corpus, os.path.join(directory, "ingest.toml"))]


@pytest.mark.parametrize(("use_env", "source"), [(False, "--config-dir"), (True, "RFC_QA_CONFIG_DIR")])
def test_missing_config_directory_fails_before_downloading(workspace, monkeypatch, capsys, use_env, source):
    missing = os.path.join(workspace["data_dir"], "missing")
    args = ["--data-dir", workspace["data_dir"]]
    if use_env:
        monkeypatch.setenv(paths.CONFIG_DIR_ENV, missing)
    else:
        args += ["--config-dir", missing]
    assert main(args) == 1
    err = capsys.readouterr().err
    assert missing in err
    assert f"(from {source})" in err
    assert workspace["downloads"] == []
    assert not os.path.exists(workspace["index"])


def test_selected_directory_without_a_corpus_does_not_use_the_packaged_copy(workspace, capsys):
    directory = os.path.join(workspace["data_dir"], "partial")
    os.makedirs(directory)
    shutil.copy(workspace["config"], os.path.join(directory, "ingest.toml"))
    assert main(["--config-dir", directory, "--data-dir", workspace["data_dir"]]) == 1
    assert os.path.join(directory, "corpus.toml") in capsys.readouterr().err
    assert workspace["downloads"] == []
    assert not os.path.exists(workspace["index"])


def test_missing_config_directory_is_ignored_when_both_files_are_given(workspace, monkeypatch):
    monkeypatch.setenv(paths.CONFIG_DIR_ENV, os.path.join(workspace["data_dir"], "missing"))
    assert main(_main_args(workspace)) == 0


# --- Data directory ---


@pytest.fixture
def ingestion_data_dirs(monkeypatch):
    """Replace run_ingestion, recording the data directory it's given."""
    data_dirs = []

    def fake_run(corpus_path, config_path, data_dir):
        data_dirs.append(data_dir)
        return IngestSummary(1, 1, 1)

    monkeypatch.setattr(ingest, "run_ingestion", fake_run)
    return data_dirs


def test_data_directory_defaults_to_the_user_data_directory(ingestion_data_dirs):
    assert main([]) == 0
    assert ingestion_data_dirs == [paths.default_data_dir()]


def test_environment_selects_the_data_directory(ingestion_data_dirs, tmp_path, monkeypatch):
    monkeypatch.setenv(paths.DATA_DIR_ENV, str(tmp_path / "env"))
    assert main([]) == 0
    assert ingestion_data_dirs == [str(tmp_path / "env")]


def test_flag_selects_the_data_directory_over_the_environment(ingestion_data_dirs, tmp_path, monkeypatch):
    monkeypatch.setenv(paths.DATA_DIR_ENV, str(tmp_path / "env"))
    assert main(["--data-dir", str(tmp_path / "flag")]) == 0
    assert ingestion_data_dirs == [str(tmp_path / "flag")]


def test_missing_data_directory_is_created(workspace, tmp_path, monkeypatch):
    data_dir = tmp_path / "new" / "data"
    monkeypatch.setenv(paths.DATA_DIR_ENV, str(data_dir))
    assert main(["--corpus", workspace["corpus"], "--config", workspace["config"]]) == 0
    assert sorted(os.listdir(data_dir)) == ["index.db", "rfcs"]


# --- Logging ---


def test_ingestion_is_logged(workspace, caplog):
    caplog.set_level(logging.DEBUG, logger="rfc_qa")
    summary = _run(workspace)
    records = [(r.levelno, r.getMessage()) for r in caplog.records if r.name == "rfc_qa.ingestion.ingest"]
    assert records[0] == (logging.INFO, f"2 RFCs in the manifest {workspace['corpus']!r}")
    assert records[-1] == (logging.INFO, f"Chunked 2 RFCs into {summary.chunk_count} chunks")
    per_rfc = [message for level, message in records[1:-1]]
    assert [message.split(":")[0] for message in per_rfc] == ["RFC 793", "RFC 9110"]
    assert all(level == logging.DEBUG for level, _ in records[1:-1])
    chunk_counts = [int(message.split(", ")[1].split()[0]) for message in per_rfc]
    assert sum(chunk_counts) == summary.chunk_count


def test_failed_ingestion_is_raised_not_logged(workspace, monkeypatch, caplog):
    caplog.set_level(logging.DEBUG, logger="rfc_qa")
    monkeypatch.setattr(ingest, "download_rfc", _failing_download)
    with pytest.raises(DownloadError) as excinfo:
        _run(workspace)
    assert all(str(excinfo.value) not in record.getMessage() for record in caplog.records)


# --- -v ---


def test_ingest_is_quiet_without_v(workspace, capsys):
    assert main(_main_args(workspace)) == 0
    assert capsys.readouterr().err == ""


def test_ingest_v_shows_progress_on_stderr_only(workspace, capsys):
    assert main(_main_args(workspace)) == 0
    quiet_out = capsys.readouterr().out
    os.remove(workspace["index"])
    assert main([*_main_args(workspace), "-v"]) == 0
    captured = capsys.readouterr()
    assert captured.out == quiet_out
    levels, other = split_stderr(captured.err)
    assert other == []
    assert set(levels) == {"INFO"}
    assert "Writing" in captured.err
    assert workspace["index"] in captured.err


def test_ingest_vv_adds_detail(workspace, capsys):
    assert main([*_main_args(workspace), "-vv"]) == 0
    levels, other = split_stderr(capsys.readouterr().err)
    assert other == []
    assert {"INFO", "DEBUG"} <= set(levels)


def test_ingest_v_failure_ends_with_the_error_once(workspace, monkeypatch, capsys):
    monkeypatch.setattr(ingest, "download_rfc", _failing_download)
    assert main([*_main_args(workspace), "-v"]) == 1
    captured = capsys.readouterr()
    levels, other = split_stderr(captured.err)
    assert levels
    assert other == ["RFC 793: unexpected HTTP status 503."]
    assert captured.err.endswith("RFC 793: unexpected HTTP status 503.\n")
    assert captured.err.count("unexpected HTTP status 503") == 1
    assert captured.out == ""
