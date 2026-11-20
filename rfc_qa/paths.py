"""Locations of the configuration and generated data.

The repository root is the directory above this package, so the paths hold whatever the working
directory. Configuration is read from one directory, which defaults to ``config/`` at the root
and can be overridden by a flag or ``RFC_QA_CONFIG_DIR``. Generated data (downloaded RFCs and the
index) lives in one data directory, which defaults to ``data/`` at the root and can be overridden
by a flag or ``RFC_QA_DATA_DIR``.

Only editable installs (``pip install -e .``) are supported: a regular install would copy the
package into site-packages, away from the configuration and data in the checkout.
"""

import os
from dataclasses import dataclass

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_CONFIG_DIR = os.path.join(REPO_ROOT, "config")
CONFIG_DIR_ENV = "RFC_QA_CONFIG_DIR"
CORPUS_FILE = "corpus.json"
INGEST_CONFIG_FILE = "ingest.json"
QUERY_CONFIG_FILE = "query.json"


DEFAULT_DATA_DIR = os.path.join(REPO_ROOT, "data")
DATA_DIR_ENV = "RFC_QA_DATA_DIR"
RFCS_FOLDER = "rfcs"
INDEX_FILE = "index.db"


class ConfigDirError(ValueError):
    """The selected configuration directory doesn't exist, with a message naming it and its source."""


@dataclass(frozen=True)
class SelectedDir:
    """A directory and where it was chosen: a flag, an argument, the environment or the default."""

    path: str
    source: str

    def file(self, name: str) -> str:
        return os.path.join(self.path, name)


def _select_dir(explicit: str | None, explicit_source: str, env: str, default: str) -> SelectedDir:
    """Apply the precedence: ``explicit``, then ``env`` if it's set and not empty, then ``default``.

    A relative explicit or environment path resolves from the working directory.
    """
    if explicit:
        return SelectedDir(os.path.abspath(explicit), explicit_source)
    if os.environ.get(env):
        return SelectedDir(os.path.abspath(os.environ[env]), env)
    return SelectedDir(default, "default")


def resolve_config_dir(explicit: str | None = None, explicit_source: str = "--config-dir") -> SelectedDir:
    """Return the configuration directory to use, raising :class:`ConfigDirError` if it's missing.

    The order is ``explicit``, then ``RFC_QA_CONFIG_DIR`` if it's set and not empty, then the
    default.
    """
    config_dir = _select_dir(explicit, explicit_source, CONFIG_DIR_ENV, DEFAULT_CONFIG_DIR)
    if not os.path.isdir(config_dir.path):
        raise ConfigDirError(
            "Configuration directory {p!r} (from {s}) doesn't exist.".format(
                p=config_dir.path, s=config_dir.source
            )
        )
    return config_dir


def resolve_data_dir(explicit: str | None = None, explicit_source: str = "--data-dir") -> SelectedDir:
    """Return the data directory to use, which holds ``rfcs/`` and ``index.db``.

    The order is ``explicit``, then ``RFC_QA_DATA_DIR`` if it's set and not empty, then the
    default. The directory isn't required to exist: ingestion creates it, and a query or search
    reports the missing index.
    """
    return _select_dir(explicit, explicit_source, DATA_DIR_ENV, DEFAULT_DATA_DIR)
