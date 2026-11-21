"""What the commands share: reporting an error to the user."""

import sys


def report_error(message: object) -> int:
    """Print ``message`` as one line to standard error and return the exit status 1."""
    print(message, file=sys.stderr)
    return 1
