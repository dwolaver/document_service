"""The errors the library raises for failures the user, the configuration or the environment cause.

Every one is an :class:`RfcQaError`, so a caller can catch them all in one place, or one subclass
for one kind of failure. ``str()`` of an error is a message ready to show as it is. A mistake in the
calling code, such as an argument of the wrong type, raises the built-in :class:`TypeError` or
:class:`ValueError` instead, which ``except RfcQaError`` doesn't catch.
"""


class RfcQaError(Exception):
    """A failure the user or the environment caused, with a message ready to show."""


class ConfigError(RfcQaError):
    """A configuration directory is missing, or a configuration file can't be read or is invalid."""


class DownloadError(RfcQaError):
    """An RFC couldn't be downloaded, verified or stored."""


class IngestError(RfcQaError):
    """The corpus couldn't be turned into chunks."""


class IndexUnavailableError(RfcQaError):
    """The index is missing or can't be read."""


class IndexBuildError(RfcQaError):
    """The index couldn't be written."""


class ModelUnavailableError(RfcQaError):
    """The model service couldn't produce a response, with a message saying how to fix it."""


class ModelResponseError(RfcQaError):
    """The model service responded, but its output can't be used."""
