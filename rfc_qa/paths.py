"""Locations of the configuration and generated data.

The repository root is the directory above this package, so the paths hold whatever the working
directory. Generated data lives at the root. Configuration is read from one directory, which
defaults to ``config/`` at the root and can be overridden by a flag or ``RFC_QA_CONFIG_DIR``.

Only editable installs (``pip install -e .``) are supported: a regular install would copy the
package into site-packages, away from the configuration and data in the checkout.
"""

import os
from dataclasses import dataclass

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")
INDEX_PATH = os.path.join(DATA_DIR, "index.db")

DEFAULT_CONFIG_DIR = os.path.join(REPO_ROOT, "config")
CONFIG_DIR_ENV = "RFC_QA_CONFIG_DIR"
CORPUS_FILE = "corpus.json"
INGEST_CONFIG_FILE = "ingest.json"
QUERY_CONFIG_FILE = "query.json"


class ConfigDirError(ValueError):
    """The selected configuration directory doesn't exist, with a message naming it and its source."""


@dataclass(frozen=True)
class ConfigDir:
    """A configuration directory and where it was chosen: a flag, the environment or the default."""

    path: str
    source: str

    def file(self, name):
        return os.path.join(self.path, name)


def resolve_config_dir(explicit=None, explicit_source="--config-dir"):
    """Return the configuration directory to use, raising :class:`ConfigDirError` if it's missing.

    The order is ``explicit``, then ``RFC_QA_CONFIG_DIR`` if it's set and not empty, then the
    default. A relative explicit or environment path resolves from the working directory.
    """
    if explicit:
        config_dir = ConfigDir(os.path.abspath(explicit), explicit_source)
    elif os.environ.get(CONFIG_DIR_ENV):
        config_dir = ConfigDir(os.path.abspath(os.environ[CONFIG_DIR_ENV]), CONFIG_DIR_ENV)
    else:
        config_dir = ConfigDir(DEFAULT_CONFIG_DIR, "default")
    if not os.path.isdir(config_dir.path):
        raise ConfigDirError(
            "Configuration directory {p!r} (from {s}) doesn't exist.".format(
                p=config_dir.path, s=config_dir.source
            )
        )
    return config_dir
