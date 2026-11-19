"""Locations of the configuration and generated data, which live at the repository root.

The root is the directory above this package, so the paths hold whatever the working directory.
Only editable installs (``pip install -e .``) are supported: a regular install would copy the
package into site-packages, away from the configuration and data in the checkout.
"""

import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS_PATH = os.path.join(REPO_ROOT, "corpus.json")
INGEST_CONFIG_PATH = os.path.join(REPO_ROOT, "ingest_config.json")
QUERY_CONFIG_PATH = os.path.join(REPO_ROOT, "query_config.json")
DATA_DIR = os.path.join(REPO_ROOT, "data")
INDEX_PATH = os.path.join(DATA_DIR, "index.db")
