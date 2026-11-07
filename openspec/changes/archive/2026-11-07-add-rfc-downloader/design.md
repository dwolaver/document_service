# Design

## Context

This is the project's first component (see proposal.md - Why). The repo is a flat Python
3.14 project: an empty [`query.py`](../../../query.py) at the root and a `venv` that
already includes `requests`, `httpx`, `pydantic`, and `pytest`. There is no package
structure yet. The canonical RFC source serves classic plaintext at
`https://www.rfc-editor.org/rfc/rfc<number>.txt` as `text/plain`, returns a real HTTP 404
for unknown numbers, and sends a `Content-Length` header. RFC headers identify the
document differently across eras (`Request for Comments: 9110` vs. `RFC: 791`), and some
modern RFCs begin with a UTF-8 BOM.

## Goals / Non-Goals

**Goals:**
- A single, testable entry point `download_rfc(rfc_number, directory) -> bool`.
- Never leave a partial, wrong, or corrupt file at the destination path.
- Idempotent re-runs and clear console diagnostics on failure.

**Non-Goals:**
- Parsing, chunking, or indexing RFC content (that is the later Q&A ingestion work).
- Supporting non-plaintext formats, alternate mirrors, or ret/ caching policy beyond the
  skip-if-present behavior.
- Creating the destination directory or managing its lifecycle.

## Decisions

- **Canonical source + plaintext URL**: Use `https://www.rfc-editor.org/rfc/rfc<n>.txt`.
  It is authoritative, stable, and already plaintext — ideal for later ingestion.
  Alternatives (ietf.org mirror, `.xml`/`.html`/`.pdf`) add parsing or a second source of
  truth for no current benefit.

- **HTTP client = `requests`**: Already in the venv and sufficient for a single blocking
  GET with a timeout. `httpx` is also present but adds no value for this synchronous,
  single-request use. Use an explicit connect/read timeout so network hangs fail fast.

- **Atomic write via temp file in the destination directory**: Write bytes to a temporary
  file created *inside* `directory` (e.g. via `tempfile.NamedTemporaryFile(dir=directory,
  delete=False)` or a `.rfc<n>.txt.<rand>.tmp` sibling), `flush()` + `os.fsync()`, then
  `os.replace(tmp, final)`. `os.replace` is atomic only within one filesystem, so the temp
  file must share the destination's filesystem — placing it in the destination directory
  guarantees that. A temp in `/tmp` would silently degrade to a non-atomic copy across
  devices. Always remove the temp file on any failure path.

- **Verification before rename**: Check status == 200, non-empty body, received bytes ==
  `Content-Length` when the header is present, and that the requested number appears in the
  header. Match the number with a regex tolerant of both `Request for Comments:\s*<n>` and
  `RFC:\s*<n>`, after stripping a leading BOM, scanning only the document's head rather
  than the whole body. No per-file checksum is published by the source, so byte-level
  integrity relies on `Content-Length`; this is intentionally adjustable later.

- **Idempotency by presence check**: If `rfc<number>.txt` exists, return `True` without
  downloading. A plain existence check is enough because the atomic write guarantees any
  existing file is a previously completed, verified download.

- **Missing directory fails fast**: The caller owns the directory; if it is absent, print
  an error and return `False` rather than creating it. This keeps the component's
  responsibility narrow and surfaces caller mistakes.

- **Integer-only `rfc_number` greater than 0**: Accept only an `int` whose value is
  greater than 0. Any other type, or an integer not greater than 0 (`0`, negatives), is
  rejected with a console message and a `False` return — no string parsing or prefix
  stripping. This keeps the input contract minimal; broader flexibility can be added later
  if a real need appears. The integer is used directly in the URL and filename
  (`rfc9110.txt`).

- **Module layout**: Implement as a top-level module `rfc_downloader.py` with pytest tests
  in `tests/test_rfc_downloader.py`, matching the current flat structure. Promote to a
  package later if the service grows.

## Risks / Trade-offs

- **No cryptographic integrity check** → `Content-Length` + header identity catch
  truncation and wrong-document cases; the verification stack is deliberately swappable if
  stronger guarantees are needed.
- **Source HTML/format drift or BOM variations** → Header matching tolerates both eras and
  a leading BOM; tests cover a modern and a classic RFC header shape.
- **Stale/partial file predating atomic writes** → Not a concern for a greenfield
  component; all writes go through the atomic path, so any present file is complete.
- **Network variability** → Explicit timeouts and catch-all error handling convert hangs
  and transient errors into a `False` return with diagnostics rather than an exception.

## Open Questions

- Default HTTP timeout values and whether to add bounded retries — safely tunable later
  without changing the specs, the approach, or the task breakdown.
