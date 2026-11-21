import json
import logging
import os
import re

import pytest

from rfc_qa import paths

# The repository checkout that holds these tests. The package itself doesn't know about it.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The real lookup, before the fixture below replaces it.
REAL_DEFAULT_DATA_DIR = paths.default_data_dir

# Variables the service reads. Cleared for every test so the developer's shell can't change results;
# a test that needs one sets it itself.
SERVICE_ENVIRONMENT = ("RFC_QA_CONFIG_DIR", "RFC_QA_DATA_DIR", "OLLAMA_BASE_URL")


@pytest.fixture(autouse=True)
def _clear_service_environment(monkeypatch):
    for name in SERVICE_ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def isolated_default_data_dir(tmp_path_factory, monkeypatch):
    """Point the default data directory at a temporary one, so no test reads or writes the real one."""
    directory = str(tmp_path_factory.mktemp("default-data") / "rfc-qa")
    monkeypatch.setattr(paths, "default_data_dir", lambda: directory)
    return directory


@pytest.fixture
def real_default_data_dir(monkeypatch):
    """Restore the real default lookup, for tests that only compare its paths and never write there."""
    monkeypatch.setattr(paths, "default_data_dir", REAL_DEFAULT_DATA_DIR)


@pytest.fixture(autouse=True)
def _restore_package_logger():
    """Undo any level, handler or propagation change a test or a command makes to the rfc_qa logger."""
    logger = logging.getLogger("rfc_qa")
    saved = (logger.level, list(logger.handlers), logger.propagate)
    yield
    logger.setLevel(saved[0])
    logger.handlers[:] = saved[1]
    logger.propagate = saved[2]


LOG_LINE = re.compile(r"(INFO|DEBUG|WARNING) rfc_qa(\.\w+)*: .+")


def split_stderr(err):
    """Split a command's stderr into its log-record levels and its other lines."""
    levels, other = [], []
    for line in err.splitlines():
        match = LOG_LINE.fullmatch(line)
        if match:
            levels.append(match.group(1))
        else:
            other.append(line)
    return levels, other


def _toml_value(value):
    """Write ``value`` as an inline TOML value: a string, boolean, number, list or inline table."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        # A JSON string is a valid TOML basic string for the values these tests use.
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    if isinstance(value, dict):
        return (
            "{ "
            + ", ".join(f"{key} = {_toml_value(item)}" for key, item in value.items() if item is not None)
            + " }"
        )
    raise TypeError(f"Can't write {value!r} as TOML")


def write_toml(path, data):
    """Write ``data`` to ``path`` as TOML and return the path as a string.

    Each top-level key becomes ``key = <inline value>``, so a nested dict is an inline table. TOML has
    no null, so a ``None`` value is left out, which the loaders report the same way as a missing key.
    """
    lines = [f"{key} = {_toml_value(value)}" for key, value in data.items() if value is not None]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)
