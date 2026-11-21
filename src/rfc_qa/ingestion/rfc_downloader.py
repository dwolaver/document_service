"""Download IETF RFCs by number, verify them, and store them atomically on disk."""

import contextlib
import logging
import os
import re
import tempfile
from collections.abc import Mapping

import requests

from rfc_qa.errors import DownloadError

logger = logging.getLogger(__name__)

# (connect timeout, read timeout) in seconds.
HTTP_TIMEOUT = (10, 30)

# Request uncompressed content so a declared Content-Length, when present,
# refers to the same bytes we receive and verify.
_REQUEST_HEADERS = {"Accept-Encoding": "identity"}

# Only the document head is scanned for the identifying RFC number.
_HEADER_SCAN_BYTES = 4096


def _rfc_url(number: int) -> str:
    """Return the address of RFC ``number``'s classic plaintext at the RFC Editor."""
    return f"https://www.rfc-editor.org/rfc/rfc{number}.txt"


def _check_rfc_number(rfc_number: object) -> None:
    """Raise for an RFC number that isn't a positive ``int``, which is a bug in the caller."""
    message = f"Invalid RFC number {rfc_number!r}: expected an integer greater than 0."
    # bool is a subclass of int but is not a valid RFC number.
    if not isinstance(rfc_number, int) or isinstance(rfc_number, bool):
        raise TypeError(message)
    if rfc_number <= 0:
        raise ValueError(message)


def _header_identifies_rfc(content: bytes, rfc_number: int) -> bool:
    head = content[:_HEADER_SCAN_BYTES].decode("utf-8", errors="replace").lstrip("\ufeff")
    patterns = (
        rf"Request for Comments:\s*{rfc_number}\b",
        rf"RFC:\s*{rfc_number}\b",
    )
    return any(re.search(pattern, head) for pattern in patterns)


def _verify(content: bytes, headers: Mapping[str, str], rfc_number: int) -> None:
    """Raise :class:`DownloadError` naming the first check ``content`` fails."""
    if not content:
        raise DownloadError(f"RFC {rfc_number}: empty response body.")

    declared_length = headers.get("Content-Length")
    if declared_length is not None:
        try:
            expected: int | None = int(declared_length)
        except TypeError, ValueError:
            expected = None
        if expected is not None and expected != len(content):
            raise DownloadError(
                f"RFC {rfc_number}: truncated download (Content-Length {expected}, received {len(content)})."
            )

    if not _header_identifies_rfc(content, rfc_number):
        raise DownloadError(f"RFC {rfc_number}: document header does not identify the requested RFC.")


def _atomic_write(content: bytes, directory: str, dest_path: str, rfc_number: int) -> None:
    """Store ``content`` at ``dest_path`` through a temporary file, so the path is never partial."""
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=f".rfc{rfc_number}.", suffix=".tmp")
    except OSError as exc:
        raise DownloadError(f"RFC {rfc_number}: failed to store file: {exc}") from exc
    try:
        with os.fdopen(tmp_fd, "wb") as tmp_file:
            tmp_file.write(content)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        os.replace(tmp_path, dest_path)
    except OSError as exc:
        with contextlib.suppress(OSError):
            os.remove(tmp_path)
        raise DownloadError(f"RFC {rfc_number}: failed to store file: {exc}") from exc


def download_rfc(rfc_number: int, directory: str) -> str:
    """Download RFC ``rfc_number`` into ``directory`` and return the path of ``rfc<number>.txt``.

    When the file is already there, it's returned without a download. Raises :class:`TypeError` for
    a number that isn't an ``int`` and :class:`ValueError` for one below 1, and
    :class:`~rfc_qa.errors.DownloadError` for any other failure, leaving no file behind.
    """
    _check_rfc_number(rfc_number)

    if not os.path.isdir(directory):
        raise DownloadError(f"RFC {rfc_number}: destination directory does not exist: {directory!r}")

    dest_path = os.path.join(directory, f"rfc{rfc_number}.txt")
    if os.path.exists(dest_path):
        logger.debug("RFC %d is already stored at %r", rfc_number, dest_path)
        return dest_path

    url = _rfc_url(rfc_number)
    logger.info("Downloading RFC %d from %s", rfc_number, url)
    try:
        response = requests.get(url, headers=_REQUEST_HEADERS, timeout=HTTP_TIMEOUT)
    except requests.RequestException as exc:
        raise DownloadError(f"RFC {rfc_number}: download failed: {exc}") from exc

    if response.status_code != 200:
        raise DownloadError(f"RFC {rfc_number}: unexpected HTTP status {response.status_code}.")

    content = response.content
    _verify(content, response.headers, rfc_number)
    _atomic_write(content, directory, dest_path, rfc_number)
    logger.debug("Stored %d bytes of RFC %d at %r", len(content), rfc_number, dest_path)
    return dest_path
