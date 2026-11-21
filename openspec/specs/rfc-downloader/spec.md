# rfc-downloader Specification

## Purpose

Fetches an IETF RFC by number from the canonical source, verifies its integrity and
identity, and stores it on disk atomically and idempotently for later ingestion by rfc-qa.

## Requirements

### Requirement: Download RFC by number

The component SHALL accept an integer RFC number and a destination directory and attempt
to retrieve the RFC's classic plaintext from the canonical source
`https://www.rfc-editor.org/rfc/rfc<number>.txt`. An RFC number that is not an integer, or is a
`bool`, SHALL be rejected with `TypeError`, and an integer not greater than 0 with `ValueError`, as
caller bugs. On success it SHALL return the path of the stored `rfc<number>.txt`. Any other failure
SHALL raise `DownloadError` with a message naming the RFC number and the reason.

#### Scenario: Successful download of an existing RFC

- **WHEN** the component is asked to download an existing RFC number into an existing directory that does not already contain it
- **THEN** it retrieves the RFC plaintext, stores it, and returns the path of `rfc<number>.txt`

#### Scenario: Non-integer RFC number

- **WHEN** the provided RFC number is not an integer (for example a string, `None` or `True`)
- **THEN** the component does not attempt a download, stores no file, and raises `TypeError`

#### Scenario: RFC number not greater than 0

- **WHEN** the provided RFC number is an integer that is not greater than 0 (for example `0` or a negative value)
- **THEN** the component does not attempt a download, stores no file, and raises `ValueError`

#### Scenario: RFC number does not exist

- **WHEN** the component is asked to download a number for which the source returns a non-200 status (for example HTTP 404)
- **THEN** it does not store any file and raises `DownloadError` naming the RFC and the status

#### Scenario: Network failure during retrieval

- **WHEN** the retrieval fails due to a network error, timeout, or connection problem
- **THEN** it does not store any file and raises `DownloadError` naming the RFC, with the network error as its cause

### Requirement: Verify downloaded content before storing

The component SHALL verify a retrieved document before storing it: the response status
MUST be 200, the body MUST be non-empty, the received byte count MUST match the declared
`Content-Length` when present, and the requested RFC number MUST appear in the document
header. If any check fails, the component SHALL NOT store the file and SHALL raise
`DownloadError` naming the check that failed.

#### Scenario: Truncated or incomplete body

- **WHEN** the number of bytes received does not match a declared `Content-Length`
- **THEN** the content is rejected, no file is stored, and the component raises `DownloadError` giving the declared and received sizes

#### Scenario: Header identifies a different document

- **WHEN** the retrieved document's header does not reference the requested RFC number
- **THEN** the content is rejected, no file is stored, and the component raises `DownloadError`

#### Scenario: Header styles across RFC eras

- **WHEN** the retrieved document uses the modern header `Request for Comments: <number>`, the classic header `RFC: <number>`, or begins with a UTF-8 byte order mark
- **THEN** the number check accepts the document as identifying the requested RFC

### Requirement: Store the RFC atomically

The component SHALL write the verified document so that the destination file
`rfc<number>.txt` only ever contains complete, verified content. It SHALL download into a
temporary file on the same filesystem as the destination, then move it into place
atomically. A partial or verification-failed download SHALL NOT leave a usable file at the
destination path, and no temporary file SHALL remain after any failure.

#### Scenario: Interruption during write

- **WHEN** the process is terminated while the document is being written
- **THEN** the destination `rfc<number>.txt` is either absent or a previously completed file, never a partially written one

#### Scenario: Temporary file cleanup on failure

- **WHEN** verification or the write fails after a temporary file was created
- **THEN** the temporary file is removed so no leftover temporary files remain in the destination directory

### Requirement: Skip when the RFC already exists

The component SHALL treat the operation as idempotent: when `rfc<number>.txt` already
exists in the destination directory, it SHALL skip the download and return the path of that
file without retrieving the document again.

#### Scenario: File already present

- **WHEN** the destination directory already contains `rfc<number>.txt`
- **THEN** the component performs no download and returns the path of that file

### Requirement: Require an existing destination directory

The component SHALL require the caller to provide an existing destination directory. When
the directory does not exist, it SHALL NOT create it, SHALL NOT store any file, and SHALL
raise `DownloadError` naming the directory.

#### Scenario: Destination directory missing

- **WHEN** the provided destination directory does not exist
- **THEN** the component does not create it, stores no file, and raises `DownloadError` naming the directory
