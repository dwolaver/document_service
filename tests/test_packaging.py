import importlib
import os
from importlib import metadata

import pytest

from rfc_qa.paths import REPO_ROOT

COMMANDS = {
    "rfc-ingest": "rfc_qa.ingestion.ingest:main",
    "rfc-query": "rfc_qa.query:main",
    "rfc-search": "rfc_qa.retrieval.keyword_index:main",
}

# Python files allowed at the repository root. Service code belongs in the rfc_qa package.
ROOT_MODULE_ALLOW_LIST = set()


def _console_scripts():
    try:
        distribution = metadata.distribution("rfc-qa")
    except metadata.PackageNotFoundError:
        pytest.skip("rfc-qa is not installed; run pip install -r requirements-dev.txt")
    return [ep for ep in distribution.entry_points if ep.group == "console_scripts"]


def test_installed_commands_are_exactly_the_three():
    assert {ep.name: ep.value for ep in _console_scripts()} == COMMANDS


@pytest.mark.parametrize("name", sorted(COMMANDS))
def test_each_command_loads_to_a_callable(name):
    (entry_point,) = [ep for ep in _console_scripts() if ep.name == name]
    assert callable(entry_point.load())


def test_no_service_modules_at_the_repository_root():
    root_modules = {name for name in os.listdir(REPO_ROOT) if name.endswith(".py")}
    assert root_modules <= ROOT_MODULE_ALLOW_LIST


@pytest.mark.parametrize(
    "module",
    [
        "rfc_qa.ingestion.rfc_downloader",
        "rfc_qa.ingestion.rfc_parser",
        "rfc_qa.ingestion.chunker",
        "rfc_qa.ingestion.ingest",
        "rfc_qa.retrieval.keyword_index",
        "rfc_qa.generation.answer_generator",
        "rfc_qa.query",
        "rfc_qa.chunk",
    ],
)
def test_stage_modules_import_from_their_subpackages(module):
    importlib.import_module(module)
