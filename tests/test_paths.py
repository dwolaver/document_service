import os

import pytest

from rfc_qa import paths
from rfc_qa.paths import CONFIG_DIR_ENV, ConfigDir, ConfigDirError, resolve_config_dir


@pytest.fixture
def dirs(tmp_path):
    flag, env = tmp_path / "flag", tmp_path / "env"
    flag.mkdir()
    env.mkdir()
    return str(flag), str(env)


def test_default_is_config_at_the_repository_root():
    assert paths.DEFAULT_CONFIG_DIR == os.path.join(paths.REPO_ROOT, "config")
    assert resolve_config_dir() == ConfigDir(paths.DEFAULT_CONFIG_DIR, "default")


def test_environment_over_default(dirs, monkeypatch):
    monkeypatch.setenv(CONFIG_DIR_ENV, dirs[1])
    assert resolve_config_dir() == ConfigDir(dirs[1], CONFIG_DIR_ENV)


def test_explicit_over_environment(dirs, monkeypatch):
    monkeypatch.setenv(CONFIG_DIR_ENV, dirs[1])
    assert resolve_config_dir(dirs[0]) == ConfigDir(dirs[0], "--config-dir")


def test_explicit_source_label(dirs):
    assert resolve_config_dir(dirs[0], "config_dir argument").source == "config_dir argument"


def test_empty_environment_counts_as_unset(monkeypatch):
    monkeypatch.setenv(CONFIG_DIR_ENV, "")
    assert resolve_config_dir() == ConfigDir(paths.DEFAULT_CONFIG_DIR, "default")


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
        call = resolve_config_dir
    else:
        call = lambda: resolve_config_dir(missing)
    with pytest.raises(ConfigDirError) as excinfo:
        call()
    assert missing in str(excinfo.value)
    assert "(from {s})".format(s=source) in str(excinfo.value)


def test_config_dir_error_is_a_value_error():
    assert issubclass(ConfigDirError, ValueError)
