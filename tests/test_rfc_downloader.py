import os

import pytest

import rfc_downloader
from rfc_downloader import download_rfc


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
    calls = {"count": 0}

    def fake_get(url, **kwargs):
        calls["count"] += 1
        if exc is not None:
            raise exc
        return response

    monkeypatch.setattr(rfc_downloader.requests, "get", fake_get)
    return calls


def _fail_if_called(monkeypatch):
    def fake_get(url, **kwargs):
        raise AssertionError("network call should not happen")

    monkeypatch.setattr(rfc_downloader.requests, "get", fake_get)


# --- Input validation (task 2.1) ---

def test_rejects_non_integer_and_out_of_range(monkeypatch, tmp_path):
    _fail_if_called(monkeypatch)
    for bad in ["791", None, 0, -5, True, 9110.0]:
        assert download_rfc(bad, str(tmp_path)) is False


def test_accepts_valid_integer(monkeypatch, tmp_path):
    _patch_get(monkeypatch, FakeResponse(200, MODERN_BODY, {"Content-Length": str(len(MODERN_BODY))}))
    assert download_rfc(9110, str(tmp_path)) is True
    assert (tmp_path / "rfc9110.txt").read_bytes() == MODERN_BODY


# --- Missing directory (task 2.2) ---

def test_missing_directory_returns_false_and_not_created(monkeypatch, tmp_path):
    _fail_if_called(monkeypatch)
    missing = tmp_path / "does_not_exist"
    assert download_rfc(9110, str(missing)) is False
    assert not missing.exists()


# --- Idempotent skip (task 3.1) ---

def test_skips_download_when_file_exists(monkeypatch, tmp_path):
    (tmp_path / "rfc9110.txt").write_bytes(b"already here")
    _fail_if_called(monkeypatch)
    assert download_rfc(9110, str(tmp_path)) is True
    assert (tmp_path / "rfc9110.txt").read_bytes() == b"already here"


# --- Fetch errors (tasks 4.1, 4.2) ---

def test_network_error_returns_false(monkeypatch, tmp_path):
    _patch_get(monkeypatch, exc=rfc_downloader.requests.RequestException("boom"))
    assert download_rfc(9110, str(tmp_path)) is False
    assert not (tmp_path / "rfc9110.txt").exists()


def test_non_200_returns_false(monkeypatch, tmp_path):
    _patch_get(monkeypatch, FakeResponse(404, b"404 - Not found"))
    assert download_rfc(99999, str(tmp_path)) is False
    assert not (tmp_path / "rfc99999.txt").exists()


# --- Verification (task 4.3) ---

def test_modern_header_accepted(monkeypatch, tmp_path):
    _patch_get(monkeypatch, FakeResponse(200, MODERN_BODY, {"Content-Length": str(len(MODERN_BODY))}))
    assert download_rfc(9110, str(tmp_path)) is True


def test_classic_header_accepted(monkeypatch, tmp_path):
    _patch_get(monkeypatch, FakeResponse(200, CLASSIC_BODY, {"Content-Length": str(len(CLASSIC_BODY))}))
    assert download_rfc(791, str(tmp_path)) is True


def test_truncated_body_rejected(monkeypatch, tmp_path):
    _patch_get(monkeypatch, FakeResponse(200, MODERN_BODY, {"Content-Length": str(len(MODERN_BODY) + 50)}))
    assert download_rfc(9110, str(tmp_path)) is False
    assert not (tmp_path / "rfc9110.txt").exists()


def test_wrong_number_header_rejected(monkeypatch, tmp_path):
    _patch_get(monkeypatch, FakeResponse(200, MODERN_BODY, {"Content-Length": str(len(MODERN_BODY))}))
    assert download_rfc(9999, str(tmp_path)) is False
    assert not (tmp_path / "rfc9999.txt").exists()


def test_empty_body_rejected(monkeypatch, tmp_path):
    _patch_get(monkeypatch, FakeResponse(200, b"", {}))
    assert download_rfc(9110, str(tmp_path)) is False


def test_verification_passes_without_content_length(monkeypatch, tmp_path):
    _patch_get(monkeypatch, FakeResponse(200, MODERN_BODY, {}))
    assert download_rfc(9110, str(tmp_path)) is True


# --- Atomic storage (tasks 5.1, 5.2) ---

def test_final_file_contains_full_bytes(monkeypatch, tmp_path):
    _patch_get(monkeypatch, FakeResponse(200, MODERN_BODY, {"Content-Length": str(len(MODERN_BODY))}))
    assert download_rfc(9110, str(tmp_path)) is True
    assert (tmp_path / "rfc9110.txt").read_bytes() == MODERN_BODY


def test_no_temp_left_after_verification_failure(monkeypatch, tmp_path):
    _patch_get(monkeypatch, FakeResponse(200, MODERN_BODY, {"Content-Length": str(len(MODERN_BODY) + 50)}))
    assert download_rfc(9110, str(tmp_path)) is False
    assert list(tmp_path.iterdir()) == []


def test_no_temp_left_after_write_failure(monkeypatch, tmp_path):
    _patch_get(monkeypatch, FakeResponse(200, MODERN_BODY, {"Content-Length": str(len(MODERN_BODY))}))

    def boom(src, dst):
        raise OSError("replace failed")

    monkeypatch.setattr(rfc_downloader.os, "replace", boom)
    assert download_rfc(9110, str(tmp_path)) is False
    assert not (tmp_path / "rfc9110.txt").exists()
    assert [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")] == []


# --- End-to-end across paths with a mocked HTTP layer (task 6.1) ---

def test_end_to_end_paths(monkeypatch, tmp_path):
    # success
    _patch_get(monkeypatch, FakeResponse(200, MODERN_BODY, {"Content-Length": str(len(MODERN_BODY))}))
    assert download_rfc(9110, str(tmp_path)) is True
    assert (tmp_path / "rfc9110.txt").exists()

    # skip-existing (no network)
    _fail_if_called(monkeypatch)
    assert download_rfc(9110, str(tmp_path)) is True

    # missing directory
    assert download_rfc(9110, str(tmp_path / "nope")) is False

    # non-200
    _patch_get(monkeypatch, FakeResponse(404, b"404 - Not found"))
    assert download_rfc(99999, str(tmp_path)) is False
    assert not (tmp_path / "rfc99999.txt").exists()

    # verification failure
    _patch_get(monkeypatch, FakeResponse(200, MODERN_BODY, {"Content-Length": str(len(MODERN_BODY))}))
    assert download_rfc(9999, str(tmp_path)) is False
    assert not (tmp_path / "rfc9999.txt").exists()


# --- Network-gated integration (task 4.4) ---

@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("RFC_DOWNLOADER_NETWORK_TESTS") != "1",
    reason="set RFC_DOWNLOADER_NETWORK_TESTS=1 to run network integration tests",
)
def test_real_download_passes_verification(tmp_path):
    assert download_rfc(791, str(tmp_path)) is True
    content = (tmp_path / "rfc791.txt").read_bytes()
    assert content
    assert b"791" in content[:4096]
