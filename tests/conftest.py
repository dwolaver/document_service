import os

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
def _isolated_default_data_dir(tmp_path_factory, monkeypatch):
    """Point the default data directory at a temporary one, so no test reads or writes the real one."""
    directory = str(tmp_path_factory.mktemp("default-data") / "rfc-qa")
    monkeypatch.setattr(paths, "default_data_dir", lambda: directory)
    return directory


@pytest.fixture
def real_default_data_dir(monkeypatch):
    """Restore the real default lookup, for tests that only compare its paths and never write there."""
    monkeypatch.setattr(paths, "default_data_dir", REAL_DEFAULT_DATA_DIR)
