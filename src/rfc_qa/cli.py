"""What the commands share: reporting an error, and showing the library's log records on request."""

import argparse
import logging
import sys

_PACKAGE_LOGGER = "rfc_qa"
_FORMAT = "%(levelname)s %(name)s: %(message)s"

# The handler configure_logging() attached, so a later call replaces it instead of adding another.
_handler: logging.Handler | None = None


def report_error(message: object) -> int:
    """Print ``message`` as one line to standard error and return the exit status 1."""
    print(message, file=sys.stderr)
    return 1


def add_verbose_argument(parser: argparse.ArgumentParser) -> None:
    """Add ``-v``/``--verbose``, which can be repeated, to a command's arguments."""
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Show progress on standard error. Repeat (-vv) to show details too.",
    )


def configure_logging(verbosity: int) -> None:
    """Show the library's records on standard error: ``INFO`` for 1, and ``DEBUG`` for 2 or more.

    With 0 nothing is changed, so the command's output is only its result. Only the ``rfc_qa``
    logger is configured, so other libraries' records stay hidden.
    """
    global _handler
    if verbosity <= 0:
        return
    logger = logging.getLogger(_PACKAGE_LOGGER)
    if _handler is not None:
        logger.removeHandler(_handler)
    _handler = logging.StreamHandler(sys.stderr)
    _handler.setFormatter(logging.Formatter(_FORMAT))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO if verbosity == 1 else logging.DEBUG)
