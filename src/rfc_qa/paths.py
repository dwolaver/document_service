"""Locations of the configuration and generated data.

Nothing here refers to the repository checkout, so an editable install and a regular install behave
the same, from any working directory. Configuration is read from one directory, which defaults to
the files installed with the package and can be overridden by a flag or ``RFC_QA_CONFIG_DIR``.
Generated data (downloaded RFCs and the index) lives in one data directory, which defaults to the
user's data directory for rfc-qa and can be overridden by a flag or ``RFC_QA_DATA_DIR``.
"""

import os
from dataclasses import dataclass
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path

import platformdirs

from rfc_qa.errors import ConfigError

CONFIG_DIR_ENV = "RFC_QA_CONFIG_DIR"
CORPUS_FILE = "corpus.json"
INGEST_CONFIG_FILE = "ingest.json"
QUERY_CONFIG_FILE = "query.json"
PACKAGED_CONFIG_SOURCE = "packaged defaults"


APP_NAME = "rfc-qa"
DATA_DIR_ENV = "RFC_QA_DATA_DIR"
RFCS_FOLDER = "rfcs"
INDEX_FILE = "index.db"


@dataclass(frozen=True)
class SelectedDir:
    """A directory on disk and where it was chosen: a flag, an argument, the environment or the default."""

    path: str
    source: str

    def file(self, name: str) -> str:
        return os.path.join(self.path, name)


@dataclass(frozen=True)
class ConfigDir:
    """The configuration directory and where it was chosen.

    ``location`` is the packaged defaults, read with :mod:`importlib.resources`, or a directory on
    disk that a flag, an argument or the environment named.
    """

    location: Traversable
    source: str

    @property
    def is_packaged(self) -> bool:
        return self.source == PACKAGED_CONFIG_SOURCE

    def file(self, name: str) -> Traversable:
        return self.location / name


# A configuration file to read: a path, or a file in a configuration directory.
ConfigFile = str | Traversable


def as_traversable(file: ConfigFile) -> Traversable:
    """Return ``file`` as something to open, turning a path into a :class:`~pathlib.Path`."""
    return Path(file) if isinstance(file, str) else file


def packaged_config_dir() -> Traversable:
    """Return the default configuration installed with the package."""
    return files("rfc_qa") / "config"


def _selected_path(explicit: str | None, explicit_source: str, env: str) -> SelectedDir | None:
    """Apply the precedence ``explicit``, then ``env`` if it's set and not empty, or return ``None``.

    A relative explicit or environment path resolves from the working directory.
    """
    if explicit:
        return SelectedDir(os.path.abspath(explicit), explicit_source)
    if os.environ.get(env):
        return SelectedDir(os.path.abspath(os.environ[env]), env)
    return None


def resolve_config_dir(explicit: str | None = None, explicit_source: str = "--config-dir") -> ConfigDir:
    """Return the configuration directory to use, raising :class:`~rfc_qa.errors.ConfigError` if it's missing.

    The order is ``explicit``, then ``RFC_QA_CONFIG_DIR`` if it's set and not empty, then the
    packaged defaults. A selected directory has to provide every file it's asked for: the packaged
    defaults don't fill gaps.
    """
    selected = _selected_path(explicit, explicit_source, CONFIG_DIR_ENV)
    if selected is None:
        return ConfigDir(packaged_config_dir(), PACKAGED_CONFIG_SOURCE)
    if not os.path.isdir(selected.path):
        raise ConfigError(
            "Configuration directory {p!r} (from {s}) doesn't exist.".format(
                p=selected.path, s=selected.source
            )
        )
    return ConfigDir(Path(selected.path), selected.source)


def default_data_dir() -> str:
    """Return the user's data directory for rfc-qa on this platform, such as ``~/.local/share/rfc-qa``.

    It's looked up on each call, so a change to the environment, such as ``XDG_DATA_HOME``, applies.
    """
    return platformdirs.user_data_dir(APP_NAME, appauthor=False)


def resolve_data_dir(explicit: str | None = None, explicit_source: str = "--data-dir") -> SelectedDir:
    """Return the data directory to use, which holds ``rfcs/`` and ``index.db``.

    The order is ``explicit``, then ``RFC_QA_DATA_DIR`` if it's set and not empty, then the
    default. The directory isn't required to exist: ingestion creates it, and a query or search
    reports the missing index.
    """
    return _selected_path(explicit, explicit_source, DATA_DIR_ENV) or SelectedDir(
        default_data_dir(), "default"
    )
