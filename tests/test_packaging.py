import importlib
import os
import re
from importlib import metadata

import pytest

from rfc_qa import paths
from tests.conftest import REPO_ROOT

COMMANDS = {
    "rfc-ingest": "rfc_qa.ingestion.ingest:main",
    "rfc-query": "rfc_qa.query:main",
    "rfc-search": "rfc_qa.retrieval.keyword_index:main",
}

# Python files allowed at the repository root. Service code belongs in the rfc_qa package in src/.
ROOT_MODULE_ALLOW_LIST: set[str] = set()


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


def test_repo_root_is_the_repository_root():
    assert os.path.isfile(os.path.join(REPO_ROOT, "pyproject.toml"))
    assert os.path.isdir(os.path.join(REPO_ROOT, "src", "rfc_qa"))


def test_no_configuration_at_the_repository_root():
    names = ("config", "corpus.toml", "ingest.toml", "query.toml")
    earlier = ("corpus.json", "ingest.json", "query.json", "ingest_config.json", "query_config.json")
    for name in names + earlier:
        assert not os.path.exists(os.path.join(REPO_ROOT, name))


# --- Comments in the packaged configuration ---

PACKAGED_CONFIG_FILES = (paths.CORPUS_FILE, paths.INGEST_CONFIG_FILE, paths.QUERY_CONFIG_FILE)
_TABLE = re.compile(r"\[[\w.]+\](\s+#.*)?")
_ASSIGNMENT = re.compile(r"[\w.]+\s*=")
# A comment after a value, on the same line. None of the packaged values contains " #".
_TRAILING_COMMENT = re.compile(r"=.*\s#\s")


def _uncommented(text):
    """Return each table header or setting that isn't described by a comment.

    A table header needs a comment on the line above it. A setting needs one at the end of its own
    line, so a comment block that explains something else can't stand in for it. A setting that
    opens a multi-line array, such as the corpus list, needs a comment on the line above instead,
    and the lines inside the array are exempt. tomllib drops comments, so the file is checked line
    by line.
    """
    lines = text.splitlines()
    missing = []
    depth = 0
    for number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if depth == 0 and (_TABLE.fullmatch(stripped) or _ASSIGNMENT.match(stripped)):
            previous = lines[number - 2].strip() if number > 1 else ""
            if _TABLE.fullmatch(stripped) or stripped.endswith("["):
                described = previous.startswith("#")
            else:
                described = bool(_TRAILING_COMMENT.search(stripped))
            if not described:
                missing.append((number, stripped))
        if not stripped.startswith("#"):
            depth += stripped.count("[") - stripped.count("]")
            if _TABLE.fullmatch(stripped):
                depth = 0
    return missing


@pytest.mark.parametrize("name", PACKAGED_CONFIG_FILES)
def test_every_section_and_setting_has_a_comment(name):
    text = (paths.packaged_config_dir() / name).read_text(encoding="utf-8")
    assert text.startswith("# ")
    assert _uncommented(text) == []


def test_corpus_fields_are_described_above_the_list():
    text = (paths.packaged_config_dir() / paths.CORPUS_FILE).read_text(encoding="utf-8")
    above = text[: text.index("\nrfcs = [")]
    for field in ("number", "family", "title"):
        # A comment line that starts with the field's name and goes on to describe it.
        assert re.search(rf"^#\s+{field}\s+\w", above, re.MULTILINE), field


@pytest.mark.parametrize(
    "text, missing",
    [
        ("# Header\n# Section.\n[a]\n\nx = 1   # Setting.\n", []),
        ("# Header\n\n[a]\nx = 1   # Setting.\n", [(3, "[a]")]),
        ("# Header\n# Section.\n[a]\nx = 1\n", [(4, "x = 1")]),
        ("# Header\n# Section.\n[a]\n# Above isn't enough.\nx = 1\n", [(5, "x = 1")]),
        ("# Header\n# Section.\n[a]\nx = 1   # Setting.\n# Explains x.\ny = 2\n", [(6, "y = 2")]),
        ("# Header\n\n[a]   # Not enough.\nx = 1   # Setting.\n", [(3, "[a]   # Not enough.")]),
        ("# Header\n# List.\nrfcs = [\n    { number = 1 },\n]\nafter = 2\n", [(6, "after = 2")]),
        ("# Header\nrfcs = [\n]\n", []),
        ("# Header\n\nrfcs = [\n]\n", [(3, "rfcs = [")]),
    ],
)
def test_the_comment_check_finds_uncommented_lines(text, missing):
    assert _uncommented(text) == missing


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
