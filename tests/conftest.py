import pytest

# Variables the service reads. Cleared for every test so the developer's shell can't change results;
# a test that needs one sets it itself.
SERVICE_ENVIRONMENT = ("RFC_QA_CONFIG_DIR", "RFC_QA_DATA_DIR", "OLLAMA_BASE_URL")


@pytest.fixture(autouse=True)
def _clear_service_environment(monkeypatch):
    for name in SERVICE_ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)
