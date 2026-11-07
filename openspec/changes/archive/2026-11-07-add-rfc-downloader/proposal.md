# Proposal

## Why

The Document Q&A Service needs source documents before it can answer anything, and
IETF RFCs are the first corpus we want to ingest. We need a reliable way to fetch a
given RFC by number and land a complete, correct copy on disk — without leaving
partial or wrong files behind when a download fails or is interrupted.

## What Changes

- Add an RFC downloader component exposing `download_rfc(rfc_number, directory) -> bool`.
- Fetch the classic plaintext of an RFC from `https://www.rfc-editor.org/rfc/rfc<number>.txt`.
- Verify the response before storing it: HTTP 200, non-empty body, declared
  `Content-Length` matches bytes received, and the requested RFC number appears in the
  document header (tolerant of modern `Request for Comments: N` and classic `RFC: N`
  headers, plus a possible UTF-8 BOM).
- Store the verified document as `rfc<number>.txt` using an atomic write: download to a
  temporary file in the destination directory, fsync, then `os.replace` onto the final
  name, cleaning up the temp file on any failure.
- Idempotency: if `rfc<number>.txt` already exists, skip the download and return `True`.
- If the destination directory does not exist, fail and return `False` (the caller owns
  the directory).
- On any failure, print diagnostic detail to the console and return `False`.

## Capabilities

### New Capabilities
- `rfc-downloader`: Fetching an RFC by number from the canonical source, verifying its
  integrity and identity, and storing it on disk atomically and idempotently.

### Modified Capabilities
<!-- None: this is the project's first capability. -->

## Impact

- New module implementing the downloader (target layout decided in design.md).
- New runtime dependency on an HTTP client (`requests`, already present in the venv).
- Network egress to `rfc-editor.org`.
- No existing code or APIs are modified; this is additive.
