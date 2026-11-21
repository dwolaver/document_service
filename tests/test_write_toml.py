import tomllib

import pytest

from tests.conftest import write_toml


@pytest.mark.parametrize(
    "data",
    [
        {"retrieval": {"limit": 5}, "llm": {"model": "llama3.2", "timeout_seconds": 1.5}},
        {
            "chars_per_token": 2.7,
            "target_chunk_tokens": 1100,
            "embedding_model": {"name": "x", "max_tokens": 2048},
        },
        {"rfcs": [{"number": 793, "family": "tcp", "title": 'TCP "quoted" / slash'}, "793"]},
        {"rfcs": []},
        {"flag": True, "values": [1, 2.5, "x"]},
    ],
)
def test_round_trips_through_tomllib(tmp_path, data):
    path = write_toml(tmp_path / "x.toml", data)
    with open(path, "rb") as toml_file:
        assert tomllib.load(toml_file) == data


def test_none_values_are_left_out(tmp_path):
    path = write_toml(tmp_path / "x.toml", {"a": None, "b": 1, "c": {"d": None, "e": 2}})
    with open(path, "rb") as toml_file:
        assert tomllib.load(toml_file) == {"b": 1, "c": {"e": 2}}
