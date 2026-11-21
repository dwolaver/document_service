import logging
import os
import tempfile

import pytest
import requests

from rfc_qa.errors import DownloadError, RfcQaError
from rfc_qa.ingestion.rfc_downloader import download_rfc


class FakeResponse:
    def __init__(self, status_code=200, content=b"", headers=None):
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}


MODERN_BODY = (
    b"\xef\xbb\xbf\n\n"
    b"Internet Engineering Task Force (IETF)\n"
    b"Request for Comments: 9110\n"
    b"Category: Standards Track\n\n"
    b"Body of the document.\n"
)

CLASSIC_BODY = b"\n\nRFC:  791\n\nINTERNET PROTOCOL\n\nBody of the document.\n"


def _patch_get(monkeypatch, response=None, exc=None):
    """Replace requests.get, returning the list of URLs it's called with."""
    urls: list[str] = []

    def fake_get(url, **kwargs):
        urls.append(url)
        if exc is not None:
            raise exc
        return response

    monkeypatch.setattr(requests, "get", fake_get)
    return urls


def _fail_if_called(monkeypatch):
    def fake_get(url, **kwargs):
        raise AssertionError("network call should not happen")

    monkeypatch.setattr(requests, "get", fake_get)


def _assert_failed_cleanly(capsys, tmp_path, name):
    """Nothing was stored, no temporary file remains and nothing was printed."""
    assert not (tmp_path / name).exists()
    assert [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")] == []
    assert capsys.readouterr() == ("", "")


# --- Input validation ---


@pytest.mark.parametrize("bad", ["791", None, True, 9110.0])
def test_non_integer_number_is_a_type_error(monkeypatch, tmp_path, capsys, bad):
    _fail_if_called(monkeypatch)
    # A wrong type is the point: download_rfc() must reject it at runtime.
    with pytest.raises(TypeError, match="Invalid RFC number"):
        download_rfc(bad, str(tmp_path))
    assert list(tmp_path.iterdir()) == []
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("bad", [0, -5])
def test_number_below_1_is_a_value_error(monkeypatch, tmp_path, capsys, bad):
    _fail_if_called(monkeypatch)
    with pytest.raises(ValueError, match=f"Invalid RFC number {bad}"):
        download_rfc(bad, str(tmp_path))
    assert list(tmp_path.iterdir()) == []
    assert capsys.readouterr() == ("", "")


def test_caller_bugs_are_not_rfc_qa_errors(monkeypatch, tmp_path):
    _fail_if_called(monkeypatch)
    for bad in ("791", 0):
        with pytest.raises((TypeError, ValueError)) as excinfo:
            download_rfc(bad, str(tmp_path))  # type: ignore[arg-type]
        assert not isinstance(excinfo.value, RfcQaError)


def test_accepts_valid_integer_and_returns_the_path(monkeypatch, tmp_path):
    urls = _patch_get(monkeypatch, FakeResponse(200, MODERN_BODY, {"Content-Length": str(len(MODERN_BODY))}))
    assert download_rfc(9110, str(tmp_path)) == str(tmp_path / "rfc9110.txt")
    assert (tmp_path / "rfc9110.txt").read_bytes() == MODERN_BODY
    assert urls == ["https://www.rfc-editor.org/rfc/rfc9110.txt"]


# --- Missing directory ---


def test_missing_directory_is_a_download_error_and_not_created(monkeypatch, tmp_path, capsys):
    _fail_if_called(monkeypatch)
    missing = tmp_path / "does_not_exist"
    with pytest.raises(
        DownloadError, match=r"RFC 9110: destination directory does not exist: .*does_not_exist"
    ):
        download_rfc(9110, str(missing))
    assert not missing.exists()
    assert capsys.readouterr() == ("", "")


# --- Idempotent skip ---


def test_existing_file_returns_its_path_without_a_request(monkeypatch, tmp_path):
    (tmp_path / "rfc9110.txt").write_bytes(b"already here")
    _fail_if_called(monkeypatch)
    assert download_rfc(9110, str(tmp_path)) == str(tmp_path / "rfc9110.txt")
    assert (tmp_path / "rfc9110.txt").read_bytes() == b"already here"


# --- Fetch errors ---


def test_network_error_is_the_cause(monkeypatch, tmp_path, capsys):
    error = requests.ConnectionError("boom")
    _patch_get(monkeypatch, exc=error)
    with pytest.raises(DownloadError, match="^RFC 9110: download failed: boom$") as excinfo:
        download_rfc(9110, str(tmp_path))
    assert excinfo.value.__cause__ is error
    _assert_failed_cleanly(capsys, tmp_path, "rfc9110.txt")


def test_non_200_names_the_status(monkeypatch, tmp_path, capsys):
    _patch_get(monkeypatch, FakeResponse(404, b"404 - Not found"))
    with pytest.raises(DownloadError, match=r"^RFC 99999: unexpected HTTP status 404\.$"):
        download_rfc(99999, str(tmp_path))
    _assert_failed_cleanly(capsys, tmp_path, "rfc99999.txt")


# --- Verification ---


def test_modern_header_accepted(monkeypatch, tmp_path):
    _patch_get(monkeypatch, FakeResponse(200, MODERN_BODY, {"Content-Length": str(len(MODERN_BODY))}))
    assert download_rfc(9110, str(tmp_path)) == str(tmp_path / "rfc9110.txt")


def test_classic_header_accepted(monkeypatch, tmp_path):
    _patch_get(monkeypatch, FakeResponse(200, CLASSIC_BODY, {"Content-Length": str(len(CLASSIC_BODY))}))
    assert download_rfc(791, str(tmp_path)) == str(tmp_path / "rfc791.txt")


def test_truncated_body_gives_both_sizes(monkeypatch, tmp_path, capsys):
    declared = len(MODERN_BODY) + 50
    _patch_get(monkeypatch, FakeResponse(200, MODERN_BODY, {"Content-Length": str(declared)}))
    with pytest.raises(DownloadError) as excinfo:
        download_rfc(9110, str(tmp_path))
    assert (
        str(excinfo.value)
        == f"RFC 9110: truncated download (Content-Length {declared}, received {len(MODERN_BODY)})."
    )
    assert list(tmp_path.iterdir()) == []
    assert capsys.readouterr() == ("", "")


def test_wrong_number_header_rejected(monkeypatch, tmp_path, capsys):
    _patch_get(monkeypatch, FakeResponse(200, MODERN_BODY, {"Content-Length": str(len(MODERN_BODY))}))
    with pytest.raises(DownloadError, match="^RFC 9999: document header does not identify the requested RFC"):
        download_rfc(9999, str(tmp_path))
    _assert_failed_cleanly(capsys, tmp_path, "rfc9999.txt")


def test_empty_body_rejected(monkeypatch, tmp_path, capsys):
    _patch_get(monkeypatch, FakeResponse(200, b"", {}))
    with pytest.raises(DownloadError, match="^RFC 9110: empty response body"):
        download_rfc(9110, str(tmp_path))
    _assert_failed_cleanly(capsys, tmp_path, "rfc9110.txt")


def test_verification_passes_without_content_length(monkeypatch, tmp_path):
    _patch_get(monkeypatch, FakeResponse(200, MODERN_BODY, {}))
    assert download_rfc(9110, str(tmp_path)) == str(tmp_path / "rfc9110.txt")


# --- Atomic storage ---


def test_final_file_contains_full_bytes(monkeypatch, tmp_path):
    _patch_get(monkeypatch, FakeResponse(200, MODERN_BODY, {"Content-Length": str(len(MODERN_BODY))}))
    download_rfc(9110, str(tmp_path))
    assert (tmp_path / "rfc9110.txt").read_bytes() == MODERN_BODY


def test_write_failure_is_the_cause_and_leaves_no_temp(monkeypatch, tmp_path, capsys):
    _patch_get(monkeypatch, FakeResponse(200, MODERN_BODY, {"Content-Length": str(len(MODERN_BODY))}))
    error = OSError("replace failed")

    def boom(src, dst):
        raise error

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(DownloadError, match="^RFC 9110: failed to store file: replace failed$") as excinfo:
        download_rfc(9110, str(tmp_path))
    assert excinfo.value.__cause__ is error
    _assert_failed_cleanly(capsys, tmp_path, "rfc9110.txt")


def test_unwritable_directory_is_a_download_error(monkeypatch, tmp_path, capsys):
    _patch_get(monkeypatch, FakeResponse(200, MODERN_BODY, {"Content-Length": str(len(MODERN_BODY))}))

    def no_temp_file(**kwargs):
        raise PermissionError("denied")

    monkeypatch.setattr(tempfile, "mkstemp", no_temp_file)
    with pytest.raises(DownloadError, match="^RFC 9110: failed to store file: denied$"):
        download_rfc(9110, str(tmp_path))
    _assert_failed_cleanly(capsys, tmp_path, "rfc9110.txt")


# --- Network-gated integration (task 4.4) ---


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("RFC_DOWNLOADER_NETWORK_TESTS") != "1",
    reason="set RFC_DOWNLOADER_NETWORK_TESTS=1 to run network integration tests",
)
def test_real_download_passes_verification(tmp_path):
    assert download_rfc(791, str(tmp_path)) == str(tmp_path / "rfc791.txt")
    content = (tmp_path / "rfc791.txt").read_bytes()
    assert content
    assert b"791" in content[:4096]


# --- Logging ---


def _records(caplog):
    return [
        (r.levelno, r.getMessage()) for r in caplog.records if r.name == "rfc_qa.ingestion.rfc_downloader"
    ]


def test_download_is_logged(monkeypatch, tmp_path, caplog):
    caplog.set_level(logging.DEBUG, logger="rfc_qa")
    _patch_get(monkeypatch, FakeResponse(200, MODERN_BODY, {"Content-Length": str(len(MODERN_BODY))}))
    path = download_rfc(9110, str(tmp_path))
    assert _records(caplog) == [
        (logging.INFO, "Downloading RFC 9110 from https://www.rfc-editor.org/rfc/rfc9110.txt"),
        (logging.DEBUG, f"Stored {len(MODERN_BODY)} bytes of RFC 9110 at {path!r}"),
    ]


def test_stored_rfc_is_logged_without_a_download(monkeypatch, tmp_path, caplog):
    caplog.set_level(logging.DEBUG, logger="rfc_qa")
    (tmp_path / "rfc9110.txt").write_bytes(b"already here")
    _fail_if_called(monkeypatch)
    path = download_rfc(9110, str(tmp_path))
    assert _records(caplog) == [(logging.DEBUG, f"RFC 9110 is already stored at {path!r}")]


def test_failed_download_is_raised_not_logged(monkeypatch, tmp_path, caplog):
    caplog.set_level(logging.DEBUG, logger="rfc_qa")
    _patch_get(monkeypatch, FakeResponse(404, b"404 - Not found"))
    with pytest.raises(DownloadError) as excinfo:
        download_rfc(9110, str(tmp_path))
    assert _records(caplog) == [
        (logging.INFO, "Downloading RFC 9110 from https://www.rfc-editor.org/rfc/rfc9110.txt")
    ]
    assert all(str(excinfo.value) not in record.getMessage() for record in caplog.records)
