import ast
import pathlib

import pytest

import rfc_qa
from rfc_qa import errors
from rfc_qa.cli import report_error

SUBCLASSES = (
    errors.ConfigError,
    errors.DownloadError,
    errors.IngestError,
    errors.IndexUnavailableError,
    errors.IndexBuildError,
    errors.ModelUnavailableError,
    errors.ModelResponseError,
)


@pytest.mark.parametrize("error_class", SUBCLASSES)
def test_each_error_is_an_rfc_qa_error(error_class):
    assert issubclass(error_class, errors.RfcQaError)


@pytest.mark.parametrize("error_class", (errors.RfcQaError, *SUBCLASSES))
def test_no_error_is_a_caller_bug_exception(error_class):
    assert not issubclass(error_class, (TypeError, ValueError))


@pytest.mark.parametrize("error_class", (errors.RfcQaError, *SUBCLASSES))
def test_str_is_the_message(error_class):
    assert str(error_class("Index not found: '/x/index.db'.")) == "Index not found: '/x/index.db'."


def test_one_kind_is_not_caught_by_another():
    with pytest.raises(errors.ConfigError):
        try:
            raise errors.ConfigError("bad config")
        except errors.IndexUnavailableError:
            pytest.fail("a configuration error was caught as an index error")


def test_report_error_prints_one_line_to_stderr_and_returns_1(capsys):
    assert report_error(errors.DownloadError("RFC 9110: unexpected HTTP status 404.")) == 1
    captured = capsys.readouterr()
    assert captured.err == "RFC 9110: unexpected HTTP status 404.\n"
    assert captured.out == ""


# --- Library code never prints ---

PACKAGE_DIR = pathlib.Path(rfc_qa.__file__).parent

# Modules that are command code throughout, relative to the package.
COMMAND_MODULES = {"cli.py"}

# Functions outside those modules that may write output: every command's ``main``, and the helpers
# that a ``main`` calls to print its success output, by module. A new helper fails the test until
# it's added here on purpose.
OUTPUT_HELPERS = {"query.py": {"_print_success"}}


def _writes_output(node):
    """Whether ``node`` is a call to ``print`` or a use of ``sys.stdout`` or ``sys.stderr``."""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
        return True
    return (
        isinstance(node, ast.Attribute)
        and node.attr in ("stdout", "stderr")
        and isinstance(node.value, ast.Name)
        and node.value.id == "sys"
    )


def _output_outside_command_code(source, module):
    """Return ``(line, function)`` for each place outside the allowed functions that writes output."""
    allowed = {"main"} | OUTPUT_HELPERS.get(module, set())
    found = []

    def visit(node, function):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and function is None:
            function = node.name
        if _writes_output(node) and function not in allowed:
            found.append((node.lineno, function))
        for child in ast.iter_child_nodes(node):
            visit(child, function)

    visit(ast.parse(source), None)
    return found


def _library_modules():
    for path in sorted(PACKAGE_DIR.rglob("*.py")):
        module = path.relative_to(PACKAGE_DIR).as_posix()
        if module not in COMMAND_MODULES:
            yield module, path.read_text(encoding="utf-8")


def test_library_code_never_prints():
    found = {
        module: places
        for module, source in _library_modules()
        if (places := _output_outside_command_code(source, module))
    }
    assert found == {}


def test_every_listed_output_helper_exists():
    for module, helpers in OUTPUT_HELPERS.items():
        tree = ast.parse((PACKAGE_DIR / module).read_text(encoding="utf-8"))
        defined = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
        assert helpers <= defined, module


@pytest.mark.parametrize(
    "source",
    [
        "def search():\n    print('x')\n",
        "import sys\ndef search():\n    sys.stderr.write('x')\n",
        "import sys\ndef search():\n    print('x', file=sys.stdout)\n",
        "print('at import')\n",
        "def main():\n    pass\ndef helper():\n    print('x')\n",
    ],
)
def test_the_check_finds_output(source):
    assert _output_outside_command_code(source, "retrieval/keyword_index.py")


def test_the_check_allows_command_code():
    source = "import sys\ndef main():\n    print('x')\n    def inner():\n        print(file=sys.stderr)\n"
    assert _output_outside_command_code(source, "retrieval/keyword_index.py") == []
    assert _output_outside_command_code("def _print_success():\n    print()\n", "query.py") == []
