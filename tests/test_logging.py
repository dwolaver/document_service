import argparse
import logging
import subprocess
import sys

import pytest

import rfc_qa
from rfc_qa import cli


def test_package_logger_has_only_a_null_handler():
    handlers = logging.getLogger(rfc_qa.__name__).handlers
    assert [type(handler) for handler in handlers] == [logging.NullHandler]


def _warn_without_configuration(code):
    """Run ``code`` in a fresh interpreter, then log a warning from a library logger."""
    script = code + "\nimport logging\nlogging.getLogger('rfc_qa.paths').warning('a library warning')\n"
    return subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=True)


def test_unconfigured_program_sees_no_records():
    result = _warn_without_configuration("import rfc_qa")
    assert (result.stdout, result.stderr) == ("", "")


def test_without_the_null_handler_the_warning_would_show():
    # Shows that the test above depends on the handler: Python's last resort prints the warning.
    result = _warn_without_configuration("")
    assert result.stderr == "a library warning\n"


def test_configured_program_receives_debug_records(caplog):
    caplog.set_level(logging.DEBUG, logger="rfc_qa")
    logging.getLogger("rfc_qa.paths").debug("detail %s", 1)
    assert [(r.name, r.levelno, r.getMessage()) for r in caplog.records] == [
        ("rfc_qa.paths", logging.DEBUG, "detail 1")
    ]


# --- Commands' -v ---


def _cli_handlers():
    return [h for h in logging.getLogger("rfc_qa").handlers if not isinstance(h, logging.NullHandler)]


def test_verbose_argument_counts():
    parser = argparse.ArgumentParser()
    cli.add_verbose_argument(parser)
    assert [parser.parse_args(args).verbose for args in ([], ["-v"], ["-vv"], ["--verbose", "-v"])] == [
        0,
        1,
        2,
        2,
    ]


def test_verbosity_0_changes_nothing():
    logger = logging.getLogger("rfc_qa")
    level = logger.level
    cli.configure_logging(0)
    assert _cli_handlers() == []
    assert logger.level == level


@pytest.mark.parametrize("verbosity, level", [(1, logging.INFO), (2, logging.DEBUG), (3, logging.DEBUG)])
def test_verbosity_sets_the_level(verbosity, level):
    cli.configure_logging(verbosity)
    assert logging.getLogger("rfc_qa").level == level
    assert len(_cli_handlers()) == 1


def test_a_second_call_replaces_the_handler():
    cli.configure_logging(1)
    first = _cli_handlers()
    cli.configure_logging(2)
    assert len(_cli_handlers()) == 1
    assert _cli_handlers() != first


def test_root_logger_is_unchanged():
    root = logging.getLogger()
    before = (root.level, list(root.handlers))
    cli.configure_logging(2)
    assert (root.level, list(root.handlers)) == before


def test_records_are_written_to_stderr_as_one_line(capsys):
    cli.configure_logging(2)
    logging.getLogger("rfc_qa.paths").debug("Data directory %r (from %s)", "/srv/data", "default")
    logging.getLogger("urllib3.connectionpool").debug("not ours")
    captured = capsys.readouterr()
    assert captured.err == "DEBUG rfc_qa.paths: Data directory '/srv/data' (from default)\n"
    assert captured.out == ""
