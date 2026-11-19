"""Download IETF RFCs by number, verify them, and store them atomically on disk."""

import os
import re
import sys
import tempfile

import requests

RFC_URL_TEMPLATE = "https://www.rfc-editor.org/rfc/rfc{number}.txt"

# (connect timeout, read timeout) in seconds.
HTTP_TIMEOUT = (10, 30)

# Request uncompressed content so a declared Content-Length, when present,
# refers to the same bytes we receive and verify.
_REQUEST_HEADERS = {"Accept-Encoding": "identity"}

# Only the document head is scanned for the identifying RFC number.
_HEADER_SCAN_BYTES = 4096


def _log_error(message):
    print(message, file=sys.stderr)


def _is_valid_rfc_number(rfc_number):
    # bool is a subclass of int but is not a valid RFC number.
    return isinstance(rfc_number, int) and not isinstance(rfc_number, bool) and rfc_number > 0


def _header_identifies_rfc(content, rfc_number):
    head = content[:_HEADER_SCAN_BYTES].decode("utf-8", errors="replace").lstrip("\ufeff")
    patterns = (
        r"Request for Comments:\s*{n}\b".format(n=rfc_number),
        r"RFC:\s*{n}\b".format(n=rfc_number),
    )
    return any(re.search(pattern, head) for pattern in patterns)


def _verify(content, headers, rfc_number):
    if not content:
        _log_error("RFC {n}: empty response body.".format(n=rfc_number))
        return False

    declared_length = headers.get("Content-Length")
    if declared_length is not None:
        try:
            expected = int(declared_length)
        except (TypeError, ValueError):
            expected = None
        if expected is not None and expected != len(content):
            _log_error(
                "RFC {n}: truncated download (Content-Length {d}, received {r}).".format(
                    n=rfc_number, d=expected, r=len(content)
                )
            )
            return False

    if not _header_identifies_rfc(content, rfc_number):
        _log_error("RFC {n}: document header does not identify the requested RFC.".format(n=rfc_number))
        return False

    return True


def _atomic_write(content, directory, dest_path, rfc_number):
    tmp_fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".rfc{n}.".format(n=rfc_number), suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "wb") as tmp_file:
            tmp_file.write(content)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        os.replace(tmp_path, dest_path)
        return True
    except OSError as exc:
        _log_error("RFC {n}: failed to store file: {e}".format(n=rfc_number, e=exc))
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        return False


def download_rfc(rfc_number, directory):
    """Download RFC ``rfc_number`` into ``directory`` as ``rfc<number>.txt``.

    Returns ``True`` on success (including when the file already exists) and
    ``False`` on any failure, printing diagnostic detail to the console.
    """
    if not _is_valid_rfc_number(rfc_number):
        _log_error("Invalid RFC number {r!r}: expected an integer greater than 0.".format(r=rfc_number))
        return False

    if not os.path.isdir(directory):
        _log_error("Destination directory does not exist: {d!r}".format(d=directory))
        return False

    dest_path = os.path.join(directory, "rfc{n}.txt".format(n=rfc_number))
    if os.path.exists(dest_path):
        return True

    url = RFC_URL_TEMPLATE.format(number=rfc_number)
    try:
        response = requests.get(url, headers=_REQUEST_HEADERS, timeout=HTTP_TIMEOUT)
    except requests.RequestException as exc:
        _log_error("RFC {n}: download failed: {e}".format(n=rfc_number, e=exc))
        return False

    if response.status_code != 200:
        _log_error("RFC {n}: unexpected HTTP status {s}.".format(n=rfc_number, s=response.status_code))
        return False

    content = response.content
    if not _verify(content, response.headers, rfc_number):
        return False

    return _atomic_write(content, directory, dest_path, rfc_number)
