import json
import logging
import os
import re
from typing import ClassVar

import pytest

from rfc_qa import paths, query
from rfc_qa.chunk import Chunk
from rfc_qa.errors import (
    ConfigError,
    DownloadError,
    IndexUnavailableError,
    ModelResponseError,
    ModelUnavailableError,
)
from rfc_qa.generation import answer_generator
from rfc_qa.query import QueryErrorCode, QueryResponse, Timings, load_query_config, main
from rfc_qa.query import query as run_query
from rfc_qa.retrieval.keyword_index import build_index
from tests.conftest import split_stderr, write_toml

CONFIG = {
    "retrieval": {"limit": 3},
    "llm": {
        "model": "llama3.2",
        "base_url": "http://localhost:11434",
        "num_ctx": 8192,
        "max_answer_tokens": 512,
        "timeout_seconds": 120,
    },
}
CHUNKS = [
    Chunk(
        "rfc9110-s15.5.5-p0",
        9110,
        "HTTP Semantics",
        "http",
        "15.5.5",
        "404 Not Found",
        "The 404 status code indicates the server did not find the resource.",
    ),
    Chunk(
        "rfc9293-s3.5-p0",
        9293,
        "TCP",
        "tcp",
        "3.5",
        "Establishing a Connection",
        "The three-way handshake establishes a connection.",
    ),
]


def _write_config(tmp_path, data, monkeypatch):
    """Write ``query.toml`` to ``tmp_path`` and select it through the environment variable."""
    path = write_toml(tmp_path / "query.toml", data)
    monkeypatch.setenv(paths.CONFIG_DIR_ENV, str(tmp_path))
    return path


def _with(**changes):
    data = json.loads(json.dumps(CONFIG))
    for dotted, value in changes.items():
        section, _, key = dotted.rpartition("__")
        target = data[section] if section else data
        if value is _MISSING:
            target.pop(key)
        else:
            target[key] = value
    return data


_MISSING = object()


def _data_dir(path, metadata=None):
    """Build a fixture index as ``index.db`` in a new data directory at ``path``."""
    path.mkdir()
    metadata = {"target_chunk_tokens": 1100} if metadata is None else metadata
    build_index(CHUNKS, metadata, str(path / "index.db"))
    return str(path)


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """A data directory holding the fixture index, selected through the environment variable."""
    directory = _data_dir(tmp_path / "data")
    monkeypatch.setenv(paths.DATA_DIR_ENV, directory)
    return directory


@pytest.fixture
def setup(tmp_path, monkeypatch, data_dir):
    """A fixture index and config, with the model replaced by ``setup.result`` or ``setup.error``."""

    class Setup:
        calls: ClassVar[list[tuple[str, list[str], object]]] = []
        error = None
        result = answer_generator.GenerationResult(
            found=True,
            answer="Not found means 404.",
            cited=[CHUNKS[0]],
            model_load_ms=2,
            generation_ms=48,
            prompt_tokens=1200,
            answer_tokens=49,
        )

    def fake_generate(question, chunks, settings):
        Setup.calls.append((question, [c.chunk_id for c in chunks], settings))
        if Setup.error is not None:
            raise Setup.error
        return Setup.result

    Setup.calls = []
    monkeypatch.setattr(query, "generate_answer", fake_generate)
    _write_config(tmp_path, CONFIG, monkeypatch)
    return Setup


# --- Configuration (task 1.1) ---


def test_real_config_loads():
    config = load_query_config(paths.packaged_config_dir() / "query.toml")
    assert config.model.model == "llama3.2"
    assert config.retrieval_limit == 5


def _spy_on_config_path(monkeypatch):
    """Record the configuration path a query reads, stopping the query there."""
    read = []

    def fake_load(path):
        read.append(path)
        raise ConfigError("stop")

    monkeypatch.setattr(query, "load_query_config", fake_load)
    return read


def test_default_config_is_the_packaged_configuration(monkeypatch):
    read = _spy_on_config_path(monkeypatch)
    run_query("What does 404 mean?")
    assert [str(path) for path in read] == [str(paths.packaged_config_dir() / "query.toml")]


def test_config_dir_argument_over_environment(tmp_path, monkeypatch):
    (tmp_path / "argument").mkdir()
    (tmp_path / "env").mkdir()
    monkeypatch.setenv(paths.CONFIG_DIR_ENV, str(tmp_path / "env"))
    read = _spy_on_config_path(monkeypatch)
    run_query("What does 404 mean?", config_dir=str(tmp_path / "argument"))
    assert [str(path) for path in read] == [str(tmp_path / "argument" / "query.toml")]


def test_environment_over_default(tmp_path, monkeypatch):
    monkeypatch.setenv(paths.CONFIG_DIR_ENV, str(tmp_path))
    read = _spy_on_config_path(monkeypatch)
    run_query("What does 404 mean?")
    assert [str(path) for path in read] == [str(tmp_path / "query.toml")]


@pytest.mark.parametrize(("use_env", "source"), [(False, "config_dir argument"), (True, "RFC_QA_CONFIG_DIR")])
def test_missing_config_dir_is_a_config_error(tmp_path, monkeypatch, use_env, source):
    missing = str(tmp_path / "missing")
    if use_env:
        monkeypatch.setenv(paths.CONFIG_DIR_ENV, missing)
        response = run_query("What does 404 mean?")
    else:
        response = run_query("What does 404 mean?", config_dir=missing)
    assert (response.success, response.error_code) == (False, QueryErrorCode.CONFIG_INVALID)
    assert response.error_string is not None
    assert missing in response.error_string
    assert source in response.error_string


def test_selected_directory_without_query_config_does_not_use_the_packaged_copy(tmp_path):
    response = run_query("What does 404 mean?", config_dir=str(tmp_path))
    assert (response.success, response.error_code) == (False, QueryErrorCode.CONFIG_INVALID)
    assert response.error_string is not None
    assert str(tmp_path / "query.toml") in response.error_string


def _spy_on_index_path(monkeypatch):
    """Record the index path a query is answered from, stopping the query there."""
    used = []
    monkeypatch.setattr(query, "_answer", lambda user_query, config, index_path: used.append(index_path))
    return used


def test_default_data_directory(tmp_path, monkeypatch):
    _write_config(tmp_path, CONFIG, monkeypatch)
    used = _spy_on_index_path(monkeypatch)
    run_query("What does 404 mean?")
    assert used == [os.path.join(paths.default_data_dir(), "index.db")]


def test_data_directory_from_the_environment(tmp_path, monkeypatch):
    _write_config(tmp_path, CONFIG, monkeypatch)
    monkeypatch.setenv(paths.DATA_DIR_ENV, str(tmp_path / "env"))
    used = _spy_on_index_path(monkeypatch)
    run_query("What does 404 mean?")
    assert used == [str(tmp_path / "env" / "index.db")]


def test_data_dir_argument_over_environment(tmp_path, monkeypatch):
    _write_config(tmp_path, CONFIG, monkeypatch)
    monkeypatch.setenv(paths.DATA_DIR_ENV, str(tmp_path / "env"))
    used = _spy_on_index_path(monkeypatch)
    run_query("What does 404 mean?", data_dir=str(tmp_path / "argument"))
    assert used == [str(tmp_path / "argument" / "index.db")]


@pytest.mark.parametrize(
    ("changes", "name"),
    [
        ({"retrieval__limit": 0}, "retrieval.limit"),
        ({"retrieval__limit": "5"}, "retrieval.limit"),
        ({"retrieval__limit": True}, "retrieval.limit"),
        ({"llm__model": _MISSING}, "llm.model"),
        ({"llm__base_url": 3}, "llm.base_url"),
        ({"llm__num_ctx": -1}, "llm.num_ctx"),
        ({"llm__num_ctx": 8192.5}, "llm.num_ctx"),
        ({"llm__max_answer_tokens": None}, "llm.max_answer_tokens"),
        ({"llm__timeout_seconds": 0}, "llm.timeout_seconds"),
        ({"llm__timeout_seconds": "120"}, "llm.timeout_seconds"),
        ({"llm": _MISSING}, "llm"),
        ({"retrieval": [5]}, "retrieval"),
    ],
)
def test_invalid_config_names_the_value(tmp_path, monkeypatch, changes, name):
    _write_config(tmp_path, _with(**changes), monkeypatch)
    response = run_query("What does 404 mean?")
    assert (response.success, response.error_code) == (False, QueryErrorCode.CONFIG_INVALID)
    assert response.error_string is not None
    assert name in response.error_string


def test_ollama_base_url_overrides_the_configured_address(tmp_path, monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434")
    config = load_query_config(_write_config(tmp_path, CONFIG, monkeypatch))
    assert config.model.base_url == "http://ollama:11434"


@pytest.mark.parametrize("value", [None, ""])
def test_unset_or_empty_ollama_base_url_keeps_the_configured_address(tmp_path, monkeypatch, value):
    if value is not None:
        monkeypatch.setenv("OLLAMA_BASE_URL", value)
    config = load_query_config(_write_config(tmp_path, CONFIG, monkeypatch))
    assert config.model.base_url == "http://localhost:11434"


def test_ollama_base_url_does_not_replace_a_missing_configured_address(tmp_path, monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434")
    _write_config(tmp_path, _with(llm__base_url=_MISSING), monkeypatch)
    response = run_query("What does 404 mean?")
    assert (response.success, response.error_code) == (False, QueryErrorCode.CONFIG_INVALID)
    assert response.error_string is not None
    assert "llm.base_url" in response.error_string


def test_ollama_base_url_reaches_the_model(setup, monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434")
    run_query("What does a 404 status code mean?")
    assert setup.calls[0][2].base_url == "http://ollama:11434"


def test_unreadable_config(tmp_path, monkeypatch):
    (tmp_path / "query.toml").write_text("{oops", encoding="utf-8")
    monkeypatch.setenv(paths.CONFIG_DIR_ENV, str(tmp_path))
    assert run_query("What does 404 mean?").error_code is QueryErrorCode.CONFIG_INVALID


# --- Response shape (task 1.2) ---


def test_response_defaults():
    response = QueryResponse(success=True, answer="hi")
    assert (response.found, response.citations, response.timings) == (None, [], None)
    assert (response.error_string, response.error_code) == (None, None)


def test_error_code_numbers():
    assert {code.name: int(code) for code in QueryErrorCode} == {
        "INVALID_QUERY": 1,
        "INDEX_UNAVAILABLE": 2,
        "MODEL_UNAVAILABLE": 3,
        "MODEL_INVALID_RESPONSE": 4,
        "CONFIG_INVALID": 5,
    }


def test_timings_defaults():
    assert Timings(total_ms=5) == Timings(5, None, None, None, None, None, False)


# --- Input validation ---


@pytest.mark.parametrize("bad", ["", "   ", "\t\n"])
def test_empty_queries_rejected(setup, bad):
    response = run_query(bad)
    assert (response.success, response.error_code) == (False, QueryErrorCode.INVALID_QUERY)
    assert response.error_string
    assert (response.answer, response.timings) == (None, None)
    assert setup.calls == []


@pytest.mark.parametrize(("bad", "name"), [(None, "NoneType"), (123, "int"), (b"404", "bytes")])
def test_non_string_query_is_a_type_error(monkeypatch, bad, name):
    def must_not_read(*args, **kwargs):
        raise AssertionError("read before the query was checked")

    monkeypatch.setattr(paths, "resolve_config_dir", must_not_read)
    monkeypatch.setattr(query, "read_metadata", must_not_read)
    # A wrong type is the point: query() must reject it at runtime.
    with pytest.raises(TypeError, match=f"^Query must be a str, got {name}\\.$"):
        run_query(bad)


# --- Pipeline (task 3.1) ---


def test_answered_query(setup):
    response = run_query("What does a 404 status code mean?")
    assert (response.success, response.found, response.error_code) == (True, True, None)
    assert response.answer == "Not found means 404."
    assert [c.chunk_id for c in response.citations] == ["rfc9110-s15.5.5-p0"]
    citation = response.citations[0]
    assert (citation.rfc_number, citation.rfc_title) == (9110, "HTTP Semantics")
    assert (citation.section_number, citation.section_title) == ("15.5.5", "404 Not Found")


def test_retrieved_chunks_and_settings_reach_the_model(setup):
    run_query("What does a 404 status code mean?")
    question, chunk_ids, settings = setup.calls[0]
    assert question == "What does a 404 status code mean?"
    assert chunk_ids[0] == "rfc9110-s15.5.5-p0"
    assert len(chunk_ids) <= 3
    assert settings.model == "llama3.2"


def test_nothing_retrieved_is_not_found_without_a_model_call(setup):
    response = run_query("zzzzqqqq")
    assert (response.success, response.found, response.citations) == (True, False, [])
    assert response.answer == answer_generator.NOT_FOUND_ANSWER
    assert setup.calls == []


def test_model_not_found_is_a_successful_not_found(setup):
    setup.result = answer_generator.GenerationResult(found=False, answer=None, model_load_ms=2)
    response = run_query("What does a 404 status code mean?")
    assert (response.success, response.found, response.citations) == (True, False, [])
    assert response.answer == answer_generator.NOT_FOUND_ANSWER


def test_missing_index(tmp_path, monkeypatch, setup):
    missing = tmp_path / "missing"
    monkeypatch.setenv(paths.DATA_DIR_ENV, str(missing))
    response = run_query("What does a 404 status code mean?")
    assert (response.success, response.error_code) == (False, QueryErrorCode.INDEX_UNAVAILABLE)
    assert response.error_string is not None
    assert str(missing / "index.db") in response.error_string
    assert "rfc-ingest" in response.error_string
    assert not missing.exists()
    assert setup.calls == []


@pytest.mark.parametrize("metadata", [{}, {"target_chunk_tokens": "many"}])
def test_index_without_a_usable_chunk_token_target(tmp_path, monkeypatch, setup, metadata):
    data_dir = _data_dir(tmp_path / "old", metadata=metadata)
    monkeypatch.setenv(paths.DATA_DIR_ENV, data_dir)
    response = run_query("What does 404 mean?")
    assert response.error_code is QueryErrorCode.INDEX_UNAVAILABLE
    index = os.path.join(data_dir, "index.db")
    assert response.error_string == (
        f"The index at {index!r} doesn't record a usable target_chunk_tokens. Rebuild it with `rfc-ingest`."
    )
    assert setup.calls == []


def test_unreadable_index(tmp_path, monkeypatch, setup):
    data_dir = tmp_path / "corrupt"
    data_dir.mkdir()
    (data_dir / "index.db").write_bytes(b"this is not a database at all, but it is long enough to be read")
    monkeypatch.setenv(paths.DATA_DIR_ENV, str(data_dir))
    response = run_query("What does 404 mean?")
    assert (response.success, response.error_code) == (False, QueryErrorCode.INDEX_UNAVAILABLE)
    assert response.error_string is not None
    assert str(data_dir / "index.db") in response.error_string
    assert "rfc-ingest" in response.error_string
    assert setup.calls == []


def test_search_failure_is_index_unavailable_with_retrieval_timing(monkeypatch, setup):
    def broken_search(path, text, limit):
        raise IndexUnavailableError(f"Failed to search index {path!r}: disk I/O error.")

    monkeypatch.setattr(query, "search", broken_search)
    response = run_query("What does 404 mean?")
    assert response.error_code is QueryErrorCode.INDEX_UNAVAILABLE
    assert response.error_string is not None
    assert "disk I/O error" in response.error_string
    assert response.timings is not None
    assert response.timings.retrieval_ms is not None


def _fail_with_config(tmp_path, monkeypatch):
    _write_config(tmp_path, _with(llm__num_ctx=0), monkeypatch)


def _fail_with_budget(tmp_path, monkeypatch):
    _write_config(tmp_path, _with(llm__num_ctx=4096), monkeypatch)


def _fail_with_index(tmp_path, monkeypatch):
    monkeypatch.setenv(paths.DATA_DIR_ENV, str(tmp_path / "missing"))


@pytest.mark.parametrize(
    ("cause", "error", "code"),
    [
        (_fail_with_config, None, QueryErrorCode.CONFIG_INVALID),
        (_fail_with_budget, None, QueryErrorCode.CONFIG_INVALID),
        (_fail_with_index, None, QueryErrorCode.INDEX_UNAVAILABLE),
        (None, ModelUnavailableError("Start Ollama"), QueryErrorCode.MODEL_UNAVAILABLE),
        (None, ModelResponseError("bad output"), QueryErrorCode.MODEL_INVALID_RESPONSE),
    ],
)
def test_failure_response_keeps_its_code_and_prints_nothing(
    tmp_path, monkeypatch, capsys, setup, cause, error, code
):
    if cause is not None:
        cause(tmp_path, monkeypatch)
    setup.error = error
    capsys.readouterr()
    response = run_query("What does a 404 status code mean?")
    assert (response.success, response.error_code) == (False, code)
    assert response.error_string
    assert capsys.readouterr() == ("", "")


def test_unexpected_rfc_qa_error_is_not_reported_under_a_code(monkeypatch, setup):
    setup.error = DownloadError("can't happen in a query")
    with pytest.raises(DownloadError):
        run_query("What does a 404 status code mean?")


def test_budget_that_does_not_fit_fails_before_the_model(tmp_path, monkeypatch, setup):
    _write_config(tmp_path, _with(llm__num_ctx=4096), monkeypatch)
    response = run_query("What does a 404 status code mean?")
    assert (response.success, response.error_code) == (False, QueryErrorCode.CONFIG_INVALID)
    assert response.error_string is not None
    assert "4324 tokens" in response.error_string
    assert setup.calls == []


def test_budget_that_fits_exactly(tmp_path, monkeypatch, setup):
    _write_config(tmp_path, _with(llm__num_ctx=3 * 1100 + 512 + 512), monkeypatch)
    assert run_query("What does a 404 status code mean?").success is True


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (ModelUnavailableError("Start Ollama"), QueryErrorCode.MODEL_UNAVAILABLE),
        (ModelResponseError("bad output"), QueryErrorCode.MODEL_INVALID_RESPONSE),
    ],
)
def test_model_failures(setup, error, code):
    setup.error = error
    response = run_query("What does a 404 status code mean?")
    assert (response.success, response.error_code, response.found) == (False, code, None)
    assert response.error_string == str(error)


def test_model_body_that_is_not_a_json_object_is_an_invalid_response(tmp_path, monkeypatch, data_dir):
    class ListResponse:
        status_code = 200

        def json(self):
            return ["not", "an", "object"]

    monkeypatch.setattr(answer_generator, "_post_chat", lambda url, body, timeout: ListResponse())
    _write_config(tmp_path, CONFIG, monkeypatch)
    response = run_query("What does a 404 status code mean?")
    assert (response.success, response.error_code) == (False, QueryErrorCode.MODEL_INVALID_RESPONSE)
    assert response.error_string is not None
    assert "isn't a JSON object" in response.error_string


# --- Timings (task 3.2) ---


def test_warm_call_timings(setup):
    timings = run_query("What does a 404 status code mean?").timings
    assert timings is not None
    assert timings.retrieval_ms is not None
    assert timings.total_ms >= timings.retrieval_ms >= 0
    assert (timings.model_load_ms, timings.generation_ms) == (2, 48)
    assert (timings.prompt_tokens, timings.answer_tokens) == (1200, 49)
    assert timings.cold_start is False


@pytest.mark.parametrize(("load_ms", "cold"), [(499, False), (500, True), (4852, True)])
def test_cold_start_threshold(setup, load_ms, cold):
    setup.result = answer_generator.GenerationResult(
        found=True, answer="a", cited=[CHUNKS[0]], model_load_ms=load_ms
    )
    timings = run_query("What does a 404 status code mean?").timings
    assert timings is not None
    assert timings.cold_start is cold


def test_no_model_call_timings(setup):
    timings = run_query("zzzzqqqq").timings
    assert timings is not None
    assert timings.retrieval_ms is not None
    assert (timings.model_load_ms, timings.generation_ms, timings.prompt_tokens, timings.answer_tokens) == (
        None,
    ) * 4
    assert timings.cold_start is False


def test_model_failure_still_reports_timings(setup):
    setup.error = ModelUnavailableError("timed out")
    timings = run_query("What does a 404 status code mean?").timings
    assert timings is not None
    assert timings.retrieval_ms is not None
    assert timings.total_ms >= timings.retrieval_ms
    assert timings.model_load_ms is None


# --- Console (task 3.3) ---


def test_main_prints_answer_and_citations(setup, capsys):
    assert main(["What does a 404 status code mean?"]) == 0
    captured = capsys.readouterr()
    assert captured.out.splitlines()[0] == "Not found means 404."
    assert "Sources:" in captured.out
    assert "RFC 9110 section 15.5.5: 404 Not Found (rfc9110-s15.5.5-p0)" in captured.out
    assert "loaded" not in captured.out
    assert captured.err == ""


def test_main_prints_a_cold_start_note(setup, capsys):
    setup.result = answer_generator.GenerationResult(
        found=True, answer="a", cited=[CHUNKS[0]], model_load_ms=4852
    )
    assert main(["What does a 404 status code mean?"]) == 0
    assert "the model was loaded for this query, which took 4.9 seconds" in capsys.readouterr().out


def test_main_not_found_exits_zero(setup, capsys):
    assert main(["zzzzqqqq"]) == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == answer_generator.NOT_FOUND_ANSWER
    assert captured.err == ""


def test_main_failure_routes_to_stderr_nonzero(setup, capsys):
    setup.error = ModelUnavailableError("Can't reach Ollama. Start Ollama.")
    assert main(["What does a 404 status code mean?"]) != 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Start Ollama" in captured.err


def test_main_invalid_query_argument(capsys):
    assert main([""]) != 0
    captured = capsys.readouterr()
    assert captured.err.strip()
    assert captured.out == ""


def test_main_success_without_timings(monkeypatch, capsys):
    monkeypatch.setattr(
        query, "query", lambda q, config_dir, data_dir: QueryResponse(success=True, answer="the answer")
    )
    assert main(["anything"]) == 0
    assert capsys.readouterr().out.strip() == "the answer"


def test_main_config_dir_flag_selects_the_directory(setup, tmp_path):
    flag_dir = tmp_path / "flag"
    flag_dir.mkdir()
    data = _with(llm__model="other")
    write_toml(flag_dir / "query.toml", data)
    assert main(["What does a 404 status code mean?", "--config-dir", str(flag_dir)]) == 0
    assert setup.calls[0][2].model == "other"


def test_main_missing_config_dir_names_the_flag(tmp_path, capsys):
    missing = str(tmp_path / "missing")
    assert main(["What does 404 mean?", "--config-dir", missing]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert missing in captured.err
    assert "(from --config-dir)" in captured.err


def test_main_data_dir_flag_selects_the_index(setup, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv(paths.DATA_DIR_ENV, str(tmp_path / "missing"))
    flag_dir = _data_dir(tmp_path / "flag")
    assert main(["What does a 404 status code mean?", "--data-dir", flag_dir]) == 0
    assert "Not found means 404." in capsys.readouterr().out


def test_main_data_dir_without_an_index_prints_once(setup, tmp_path, capsys):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert main(["What does a 404 status code mean?", "--data-dir", str(empty)]) == 1
    index = str(empty / "index.db")
    assert capsys.readouterr() == (
        "",
        f"Index not found: {index!r}. Run rfc-ingest to build it.\n",
    )


def test_main_failure_response_is_one_stderr_line(setup, capsys):
    setup.error = ModelUnavailableError("Can't reach Ollama. Start Ollama.")
    assert main(["What does a 404 status code mean?"]) == 1
    assert capsys.readouterr() == ("", "Can't reach Ollama. Start Ollama.\n")


def test_main_unknown_option_exits_2_with_usage(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--bogus", "x"])
    assert excinfo.value.code == 2
    assert "usage:" in capsys.readouterr().err


def test_main_does_not_catch_a_bug(monkeypatch):
    def broken(*args, **kwargs):
        raise KeyError("bug")

    monkeypatch.setattr(query, "query", broken)
    with pytest.raises(KeyError):
        main(["anything"])


# --- Real model (task 4.1) ---


@pytest.mark.ollama
@pytest.mark.skipif(
    os.environ.get("OLLAMA_TESTS") != "1",
    reason="set OLLAMA_TESTS=1 to run tests against the real model and index",
)
def test_real_model_answers_a_corpus_question():
    response = run_query("What does a 404 status code mean?")
    assert response.success is True, response.error_string
    assert response.found is True
    assert {c.rfc_number for c in response.citations} & {9110, 7231, 2616}
    assert response.timings is not None
    assert response.timings.prompt_tokens is not None
    assert response.timings.prompt_tokens > 0


# --- Logging ---


def _query_records(caplog, level=None):
    return [
        r.getMessage()
        for r in caplog.records
        if r.name == "rfc_qa.query" and (level is None or r.levelno == level)
    ]


def test_answered_query_is_logged(setup, caplog):
    caplog.set_level(logging.DEBUG, logger="rfc_qa")
    run_query("What does a 404 status code mean?")
    progress = _query_records(caplog, logging.INFO)
    assert len(progress) == 2
    assert re.fullmatch(r"Retrieved 2 passages in \d+ ms", progress[0])
    assert re.fullmatch(r"The model answered in \d+ ms, citing 1 of 2 passages", progress[1])


def test_not_found_by_the_model_is_logged(setup, caplog):
    caplog.set_level(logging.INFO, logger="rfc_qa")
    setup.result = answer_generator.GenerationResult(found=False, answer=None, model_load_ms=2)
    run_query("What does a 404 status code mean?")
    assert re.fullmatch(r"The model found no answer in the passages, in \d+ ms", _query_records(caplog)[-1])


def test_nothing_retrieved_is_logged_without_a_model_record(setup, caplog):
    caplog.set_level(logging.INFO, logger="rfc_qa")
    run_query("zzzzqqqq")
    progress = _query_records(caplog)
    assert len(progress) == 1
    assert re.fullmatch(r"Retrieved 0 passages in \d+ ms", progress[0])


def test_query_detail_is_logged(setup, tmp_path, data_dir, caplog):
    caplog.set_level(logging.DEBUG, logger="rfc_qa")
    run_query("What does a 404 status code mean?")
    detail = _query_records(caplog, logging.DEBUG)
    assert f"Query configuration {str(tmp_path / 'query.toml')!r}" in detail
    assert f"Index {os.path.join(data_dir, 'index.db')!r}" in detail
    assert "Context budget: 4324 of 8192 tokens (llm.num_ctx)" in detail


def test_query_failure_is_returned_not_logged(tmp_path, monkeypatch, setup, caplog):
    caplog.set_level(logging.DEBUG, logger="rfc_qa")
    monkeypatch.setenv(paths.DATA_DIR_ENV, str(tmp_path / "missing"))
    response = run_query("What does 404 mean?")
    assert response.error_string
    assert all(response.error_string not in record.getMessage() for record in caplog.records)


# --- -v ---


def test_main_is_quiet_without_v(setup, capsys):
    assert main(["What does a 404 status code mean?"]) == 0
    assert capsys.readouterr().err == ""


def test_main_v_shows_progress_on_stderr_only(setup, capsys):
    assert main(["What does a 404 status code mean?"]) == 0
    quiet_out = capsys.readouterr().out
    assert main(["What does a 404 status code mean?", "-v"]) == 0
    captured = capsys.readouterr()
    assert captured.out == quiet_out
    levels, other = split_stderr(captured.err)
    assert other == []
    assert levels == ["INFO", "INFO"]
    assert "Retrieved 2 passages" in captured.err
    assert "The model answered" in captured.err


def test_main_vv_adds_detail(setup, capsys):
    assert main(["What does a 404 status code mean?", "-vv"]) == 0
    captured = capsys.readouterr()
    levels, other = split_stderr(captured.err)
    assert other == []
    assert {"INFO", "DEBUG"} <= set(levels)
    assert "DEBUG rfc_qa.paths: Configuration directory" in captured.err


def test_main_v_failure_ends_with_the_error_once(setup, capsys):
    setup.error = ModelUnavailableError("Can't reach Ollama. Start Ollama.")
    assert main(["What does a 404 status code mean?", "-v"]) == 1
    captured = capsys.readouterr()
    levels, other = split_stderr(captured.err)
    assert levels == ["INFO"]
    assert other == ["Can't reach Ollama. Start Ollama."]
    assert captured.err.endswith("Can't reach Ollama. Start Ollama.\n")
    assert captured.out == ""
