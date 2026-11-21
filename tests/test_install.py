"""A regular install from a built wheel, run with no checkout nearby.

These tests build a wheel, install it with its dependencies into a fresh virtual environment, and
run the commands from an empty directory. They need PyPI, for the build backend and the
dependencies, but no document source or model. They're skipped unless RFC_QA_INSTALL_TESTS=1.
"""

import json
import os
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.conftest import REPO_ROOT

pytestmark = [
    pytest.mark.install,
    pytest.mark.skipif(
        os.environ.get("RFC_QA_INSTALL_TESTS") != "1",
        reason="set RFC_QA_INSTALL_TESTS=1 to build and install a wheel (needs PyPI)",
    ),
    pytest.mark.skipif(sys.platform == "win32", reason="runs the commands from the venv's bin/"),
]

CONFIG_FILES = ("corpus.toml", "ingest.toml", "query.toml")
FIXTURE_RFC = os.path.join(REPO_ROOT, "tests", "ingestion", "fixtures", "paginated.txt")
# Nothing listens here, so a model running on the developer's machine doesn't answer.
UNREACHABLE_OLLAMA = "http://127.0.0.1:9"


@dataclass
class Install:
    wheel: Path
    venv: Path
    work: Path
    data_home: Path
    env: dict[str, str]

    def run(self, command: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(self.venv / "bin" / command), *args],
            cwd=self.work,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=300,
        )


def _copy_sources(destination: Path) -> None:
    """Copy only what the build reads, so nothing left in the checkout can end up in the wheel."""
    destination.mkdir()
    for name in ("pyproject.toml", "README.md", "LICENSE"):
        shutil.copy(os.path.join(REPO_ROOT, name), destination / name)
    shutil.copytree(
        os.path.join(REPO_ROOT, "src"),
        destination / "src",
        ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"),
    )


def _clean_environment(home: Path, data_home: Path) -> dict[str, str]:
    env = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith("RFC_QA_") and name not in ("PYTHONPATH", "VIRTUAL_ENV")
    }
    env.update(HOME=str(home), XDG_DATA_HOME=str(data_home), OLLAMA_BASE_URL=UNREACHABLE_OLLAMA)
    return env


@pytest.fixture(scope="module")
def install(tmp_path_factory: pytest.TempPathFactory) -> Install:
    root = tmp_path_factory.mktemp("install")
    _copy_sources(root / "source")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--quiet",
            "--no-deps",
            "-w",
            str(root / "dist"),
            str(root / "source"),
        ],
        check=True,
    )
    (wheel,) = (root / "dist").glob("*.whl")
    venv = root / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    subprocess.run([str(venv / "bin" / "python"), "-m", "pip", "install", "--quiet", str(wheel)], check=True)
    for name in ("work", "home", "data-home"):
        (root / name).mkdir()
    env = _clean_environment(root / "home", root / "data-home")
    return Install(wheel, venv, root / "work", root / "data-home", env)


def test_wheel_holds_the_package_and_its_configuration(install):
    with zipfile.ZipFile(install.wheel) as wheel:
        names = wheel.namelist()
    assert all(name.startswith(("rfc_qa/", "rfc_qa-")) for name in names), names
    for name in CONFIG_FILES:
        assert "rfc_qa/config/" + name in names
    assert [name for name in names if name.endswith(".json")] == []


def test_package_is_imported_from_the_environment(install):
    result = install.run("python", "-c", "import rfc_qa; print(rfc_qa.__file__)")
    assert result.returncode == 0, result.stderr
    assert Path(result.stdout.strip()).is_relative_to(install.venv)


def test_default_data_directory_is_the_user_data_directory(install):
    result = install.run("python", "-c", "from rfc_qa import paths; print(paths.default_data_dir())")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(install.data_home / "rfc-qa")


def _seed_corpus(install: Install) -> int:
    """Save the fixture RFC under every number in the packaged corpus, so nothing is downloaded."""
    script = (
        "import json, tomllib; from importlib.resources import files; "
        "print(json.dumps([e['number'] for e in tomllib.loads("
        "(files('rfc_qa') / 'config' / 'corpus.toml').read_text(encoding='utf-8'))['rfcs']]))"
    )
    result = install.run("python", "-c", script)
    assert result.returncode == 0, result.stderr
    numbers = json.loads(result.stdout)
    rfcs = install.data_home / "rfc-qa" / "rfcs"
    rfcs.mkdir(parents=True)
    for number in numbers:
        shutil.copy(FIXTURE_RFC, rfcs / f"rfc{number}.txt")
    return len(numbers)


def test_commands_run_with_the_packaged_defaults(install):
    count = _seed_corpus(install)

    ingested = install.run("rfc-ingest")
    assert ingested.returncode == 0, ingested.stderr
    assert f"Indexed {count} RFCs" in ingested.stdout
    assert (install.data_home / "rfc-qa" / "index.db").is_file()

    searched = install.run("rfc-search", "Hypertext Transfer Protocol")
    assert searched.returncode == 0, searched.stderr
    assert "RFC " in searched.stdout

    # The configuration and the index are both found, so the query only fails at the model.
    asked = install.run("rfc-query", "What is the Hypertext Transfer Protocol?")
    assert asked.returncode == 1
    assert f"Can't reach Ollama at {UNREACHABLE_OLLAMA}" in asked.stderr
    assert list(install.work.iterdir()) == []
