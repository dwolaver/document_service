# Tasks

## 1. Scaffolding

- [x] 1.1 Create `rfc_downloader.py` with a `download_rfc(rfc_number, directory) -> bool` stub and `tests/` package; verify `pytest` collects an empty/placeholder test for `tests/test_rfc_downloader.py`
- [x] 1.2 Record `requests` as a project dependency (add `requirements.txt` pinned to the installed version) and verify `pip install -r requirements.txt` succeeds in the venv

## 2. Input handling and directory guard

- [x] 2.1 Accept only an integer `rfc_number` greater than 0 and reject any other type or out-of-range value with a console message and `False`; verify unit tests cover a valid int (`9110`) and rejection of non-integer inputs (e.g. `"791"`, `None`) and integers not greater than 0 (e.g. `0`, `-5`)
- [x] 2.2 Return `False` with a console message when the destination directory does not exist, without creating it; verify a unit test asserts no directory is created and `False` is returned

## 3. Idempotent skip

- [x] 3.1 Return `True` without any network call when `rfc<number>.txt` already exists in the directory; verify a unit test (HTTP layer patched to fail if called) confirms the skip path returns `True`

## 4. Fetch and verify

- [x] 4.1 Fetch the plaintext from `https://www.rfc-editor.org/rfc/rfc<number>.txt` with an explicit timeout, converting network errors/timeouts to a `False` return with a console message; verify a unit test simulating a network error returns `False`
- [x] 4.2 Reject non-200 responses (e.g. 404) without storing a file; verify a unit test with a mocked 404 returns `False`
- [x] 4.3 Implement content verification (non-empty body, received bytes match `Content-Length` when present, requested number present in header via a BOM-tolerant regex matching both `Request for Comments: <n>` and `RFC: <n>`); verify unit tests cover a modern header, a classic header, a truncated body, and a wrong-number header
- [x] 4.4 Add a focused integration test (network-gated/skippable) that downloads a known real RFC and asserts verification passes

## 5. Atomic storage

- [x] 5.1 Write verified bytes to a temporary file inside the destination directory, `flush` + `os.fsync`, then `os.replace` onto `rfc<number>.txt`; verify a unit test confirms the final file contains the full expected bytes and is created via replace
- [x] 5.2 Remove the temporary file on every failure path (verification failure and write/replace error) and return `False` with a console message; verify unit tests assert no `.tmp` artifacts remain after an induced verification failure and an induced write failure

## 6. End-to-end verification

- [x] 6.1 Add an end-to-end test using a mocked HTTP layer that exercises success, skip-existing, missing-directory, non-200, and verification-failure paths, asserting the correct boolean and on-disk state for each; verify the full `pytest` suite passes
