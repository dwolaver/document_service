import os
import sys
from pathlib import Path

import platformdirs
import pytest

import rfc_qa
from rfc_qa import paths
from rfc_qa.errors import ConfigError
from rfc_qa.paths import (
    CONFIG_DIR_ENV,
    DATA_DIR_ENV,
    PACKAGED_CONFIG_SOURCE,
    ConfigDir,
    SelectedDir,
    packaged_config_dir,
    resolve_config_dir,
    resolve_data_dir,
)
from tests.conftest import REAL_DEFAULT_DATA_DIR


@pytest.fixture
def dirs(tmp_path):
    flag, env = tmp_path / "flag", tmp_path / "env"
    flag.mkdir()
    env.mkdir()
    return str(flag), str(env)


def test_packaged_defaults_are_in_the_imported_package():
    package_dir = os.path.dirname(os.path.abspath(rfc_qa.__file__))
    assert str(packaged_config_dir()) == os.path.join(package_dir, "config")
    for name in (paths.CORPUS_FILE, paths.INGEST_CONFIG_FILE, paths.QUERY_CONFIG_FILE):
        assert packaged_config_dir().joinpath(name).is_file()


def test_default_is_the_packaged_configuration():
    config_dir = resolve_config_dir()
    assert config_dir == ConfigDir(packaged_config_dir(), PACKAGED_CONFIG_SOURCE)
    assert config_dir.is_packaged
    assert str(config_dir.file(paths.QUERY_CONFIG_FILE)) == str(packaged_config_dir() / "query.json")


def test_environment_over_default(dirs, monkeypatch):
    monkeypatch.setenv(CONFIG_DIR_ENV, dirs[1])
    assert resolve_config_dir() == ConfigDir(Path(dirs[1]), CONFIG_DIR_ENV)
    assert not resolve_config_dir().is_packaged


def test_explicit_over_environment(dirs, monkeypatch):
    monkeypatch.setenv(CONFIG_DIR_ENV, dirs[1])
    assert resolve_config_dir(dirs[0]) == ConfigDir(Path(dirs[0]), "--config-dir")


def test_explicit_source_label(dirs):
    assert resolve_config_dir(dirs[0], "config_dir argument").source == "config_dir argument"


def test_empty_environment_counts_as_unset(monkeypatch):
    monkeypatch.setenv(CONFIG_DIR_ENV, "")
    assert resolve_config_dir().is_packaged


def test_relative_explicit_resolves_from_the_working_directory(tmp_path, monkeypatch):
    (tmp_path / "staging").mkdir()
    monkeypatch.chdir(tmp_path)
    assert resolve_config_dir("staging").location == tmp_path / "staging"


def test_relative_environment_resolves_from_the_working_directory(tmp_path, monkeypatch):
    (tmp_path / "staging").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(CONFIG_DIR_ENV, "staging")
    assert resolve_config_dir().location == tmp_path / "staging"


@pytest.mark.parametrize("use_env, source", [(False, "--config-dir"), (True, CONFIG_DIR_ENV)])
def test_missing_directory_names_path_and_source(tmp_path, monkeypatch, use_env, source):
    missing = str(tmp_path / "missing")
    if use_env:
        monkeypatch.setenv(CONFIG_DIR_ENV, missing)
    with pytest.raises(ConfigError) as excinfo:
        resolve_config_dir(None if use_env else missing)
    assert missing in str(excinfo.value)
    assert "(from {s})".format(s=source) in str(excinfo.value)


def test_missing_directory_is_not_a_value_error(tmp_path):
    # A caller's `except ValueError` is for its own bugs, so it mustn't catch a missing directory.
    with pytest.raises(ConfigError) as excinfo:
        resolve_config_dir(str(tmp_path / "missing"))
    assert not isinstance(excinfo.value, ValueError)


# --- Data directory ---


@pytest.mark.usefixtures("real_default_data_dir")
def test_data_default_is_the_user_data_directory():
    expected = platformdirs.user_data_dir("rfc-qa", appauthor=False)
    assert paths.default_data_dir() == expected
    assert resolve_data_dir() == SelectedDir(expected, "default")


@pytest.mark.skipif(sys.platform != "linux", reason="XDG_DATA_HOME is the Linux setting")
@pytest.mark.usefixtures("real_default_data_dir")
def test_data_default_follows_xdg_data_home(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert resolve_data_dir().path == str(tmp_path / "rfc-qa")
    assert not os.path.exists(tmp_path / "rfc-qa")


def test_tests_use_a_temporary_default_data_directory(_isolated_default_data_dir):
    assert resolve_data_dir() == SelectedDir(_isolated_default_data_dir, "default")
    assert _isolated_default_data_dir != REAL_DEFAULT_DATA_DIR()


def test_data_environment_over_default(dirs, monkeypatch):
    monkeypatch.setenv(DATA_DIR_ENV, dirs[1])
    assert resolve_data_dir() == SelectedDir(dirs[1], DATA_DIR_ENV)


def test_data_explicit_over_environment(dirs, monkeypatch):
    monkeypatch.setenv(DATA_DIR_ENV, dirs[1])
    assert resolve_data_dir(dirs[0]) == SelectedDir(dirs[0], "--data-dir")
    assert resolve_data_dir(dirs[0], "data_dir argument").source == "data_dir argument"


def test_data_empty_environment_counts_as_unset(monkeypatch):
    monkeypatch.setenv(DATA_DIR_ENV, "")
    assert resolve_data_dir() == SelectedDir(paths.default_data_dir(), "default")


def test_data_relative_paths_resolve_from_the_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert resolve_data_dir("scratch").path == str(tmp_path / "scratch")
    monkeypatch.setenv(DATA_DIR_ENV, "other")
    assert resolve_data_dir().path == str(tmp_path / "other")


def test_missing_data_directory_is_returned_not_raised(tmp_path):
    missing = str(tmp_path / "missing")
    assert resolve_data_dir(missing) == SelectedDir(missing, "--data-dir")
    assert not os.path.exists(missing)


def test_data_files_are_named_in_the_data_directory():
    data_dir = resolve_data_dir()
    assert data_dir.file(paths.INDEX_FILE) == os.path.join(paths.default_data_dir(), "index.db")
    assert data_dir.file(paths.RFCS_FOLDER) == os.path.join(paths.default_data_dir(), "rfcs")
