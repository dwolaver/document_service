import os

import pytest

from rfc_qa import paths
from rfc_qa.paths import (
    CONFIG_DIR_ENV,
    DATA_DIR_ENV,
    ConfigDirError,
    SelectedDir,
    resolve_config_dir,
    resolve_data_dir,
)


@pytest.fixture
def dirs(tmp_path):
    flag, env = tmp_path / "flag", tmp_path / "env"
    flag.mkdir()
    env.mkdir()
    return str(flag), str(env)


def test_default_is_config_at_the_repository_root():
    assert paths.DEFAULT_CONFIG_DIR == os.path.join(paths.REPO_ROOT, "config")
    assert resolve_config_dir() == SelectedDir(paths.DEFAULT_CONFIG_DIR, "default")


def test_environment_over_default(dirs, monkeypatch):
    monkeypatch.setenv(CONFIG_DIR_ENV, dirs[1])
    assert resolve_config_dir() == SelectedDir(dirs[1], CONFIG_DIR_ENV)


def test_explicit_over_environment(dirs, monkeypatch):
    monkeypatch.setenv(CONFIG_DIR_ENV, dirs[1])
    assert resolve_config_dir(dirs[0]) == SelectedDir(dirs[0], "--config-dir")


def test_explicit_source_label(dirs):
    assert resolve_config_dir(dirs[0], "config_dir argument").source == "config_dir argument"


def test_empty_environment_counts_as_unset(monkeypatch):
    monkeypatch.setenv(CONFIG_DIR_ENV, "")
    assert resolve_config_dir() == SelectedDir(paths.DEFAULT_CONFIG_DIR, "default")


def test_relative_explicit_resolves_from_the_working_directory(tmp_path, monkeypatch):
    (tmp_path / "staging").mkdir()
    monkeypatch.chdir(tmp_path)
    assert resolve_config_dir("staging").path == str(tmp_path / "staging")


def test_relative_environment_resolves_from_the_working_directory(tmp_path, monkeypatch):
    (tmp_path / "staging").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(CONFIG_DIR_ENV, "staging")
    assert resolve_config_dir().path == str(tmp_path / "staging")


@pytest.mark.parametrize("use_env, source", [(False, "--config-dir"), (True, CONFIG_DIR_ENV)])
def test_missing_directory_names_path_and_source(tmp_path, monkeypatch, use_env, source):
    missing = str(tmp_path / "missing")
    if use_env:
        monkeypatch.setenv(CONFIG_DIR_ENV, missing)
    with pytest.raises(ConfigDirError) as excinfo:
        resolve_config_dir(None if use_env else missing)
    assert missing in str(excinfo.value)
    assert "(from {s})".format(s=source) in str(excinfo.value)


def test_config_dir_error_is_a_value_error():
    assert issubclass(ConfigDirError, ValueError)


# --- Data directory ---


def test_data_default_is_data_at_the_repository_root():
    assert paths.DEFAULT_DATA_DIR == os.path.join(paths.REPO_ROOT, "data")
    assert resolve_data_dir() == SelectedDir(paths.DEFAULT_DATA_DIR, "default")


def test_data_environment_over_default(dirs, monkeypatch):
    monkeypatch.setenv(DATA_DIR_ENV, dirs[1])
    assert resolve_data_dir() == SelectedDir(dirs[1], DATA_DIR_ENV)


def test_data_explicit_over_environment(dirs, monkeypatch):
    monkeypatch.setenv(DATA_DIR_ENV, dirs[1])
    assert resolve_data_dir(dirs[0]) == SelectedDir(dirs[0], "--data-dir")
    assert resolve_data_dir(dirs[0], "data_dir argument").source == "data_dir argument"


def test_data_empty_environment_counts_as_unset(monkeypatch):
    monkeypatch.setenv(DATA_DIR_ENV, "")
    assert resolve_data_dir() == SelectedDir(paths.DEFAULT_DATA_DIR, "default")


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
    assert data_dir.file(paths.INDEX_FILE) == os.path.join(paths.REPO_ROOT, "data", "index.db")
    assert data_dir.file(paths.RFCS_FOLDER) == os.path.join(paths.REPO_ROOT, "data", "rfcs")
