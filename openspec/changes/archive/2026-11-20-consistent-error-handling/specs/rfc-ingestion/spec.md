## ADDED Requirements

### Requirement: Report invalid ingestion inputs as configuration errors

A corpus manifest or ingestion configuration that can't be read, isn't valid JSON or breaks one of its
rules SHALL raise `ConfigError`, with a message naming the file and, where there is one, the value.
A problem with the corpus content during a run, such as an RFC that yields no chunks, SHALL raise
`IngestError`, and so SHALL an RFC file that can't be read.

#### Scenario: Invalid manifest

- **WHEN** ingestion reads a manifest with a duplicate RFC or an unknown family
- **THEN** it raises `ConfigError` naming the problem, before downloading anything

#### Scenario: Unreadable RFC file

- **WHEN** a stored RFC file can't be read
- **THEN** ingestion raises `IngestError` naming the RFC, with the operating system error as its cause, and writes no index

## MODIFIED Requirements

### Requirement: Build the index atomically

Ingestion SHALL write the index so that the index path only ever holds a complete index. When a run
fails, an existing index SHALL remain unchanged and no temporary file SHALL remain. A failure to write
the index SHALL raise `IndexBuildError` naming the index path, with the underlying error as its cause.

#### Scenario: Successful build

- **WHEN** ingestion completes
- **THEN** the index path holds an index containing chunks from every RFC in the manifest

#### Scenario: Build fails

- **WHEN** a run fails after an earlier index exists
- **THEN** the earlier index is unchanged and no temporary file remains

#### Scenario: Index can't be written

- **WHEN** the index can't be written, for example because its directory isn't writable
- **THEN** building raises `IndexBuildError` naming the index path, without printing anything

### Requirement: Fail the whole run on an incomplete corpus

Ingestion SHALL fail, with exit status 1 and a message naming the RFC, when any RFC in the
manifest cannot be downloaded or produces no chunks. It SHALL NOT produce a partial index.

#### Scenario: Download fails

- **WHEN** an RFC in the manifest cannot be downloaded
- **THEN** ingestion exits with status 1 and names that RFC, printing the reason once

#### Scenario: RFC produces no chunks

- **WHEN** a downloaded RFC yields no chunks
- **THEN** ingestion exits with status 1 and names that RFC

### Requirement: Search the index by keyword

The project SHALL provide a keyword search over the index that returns chunks with their metadata,
ranked by relevance and limited to a requested count. Matches in the section title SHALL rank above
equal matches in the body. Search SHALL accept any query text without raising. An index that doesn't
exist or can't be read SHALL raise `IndexUnavailableError`, naming the index path and telling the user
to run `rfc-ingest`.

#### Scenario: Exact term

- **WHEN** a search contains a term that appears in only one chunk
- **THEN** that chunk is returned first

#### Scenario: Title match

- **WHEN** a term appears in one chunk's section title and in another chunk's body with similar frequency
- **THEN** the chunk with the title match ranks higher

#### Scenario: Result limit

- **WHEN** more chunks match than the requested count
- **THEN** only the requested number of chunks is returned

#### Scenario: Query with punctuation

- **WHEN** a search contains punctuation or operators, such as `Content-Length` or `"HTTP/2`
- **THEN** it returns results normally, or no results, and does not raise

#### Scenario: No matches

- **WHEN** no chunk matches the query
- **THEN** an empty result is returned

#### Scenario: Missing index

- **WHEN** a search is run and the index does not exist
- **THEN** it raises `IndexUnavailableError` naming the index path, prints nothing, and does not create an index

#### Scenario: Unreadable index

- **WHEN** the index file exists but isn't a valid index
- **THEN** a search or a read of its build configuration raises `IndexUnavailableError` naming the index path, with the database error as its cause
