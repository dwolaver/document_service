# Proposal

## Why

The downloader can fetch one RFC, and `query.py` can accept a question, but nothing turns RFC text
into something searchable. This change builds the offline half of the RAG pipeline, so the next
change can retrieve real passages and cite them. It comes first because it can be built and
checked by reading the chunks, with no LLM involved.

RFCs are not generic documents. Page furniture, section numbering and layout differ by era, so
retrieval quality and section-level citations depend on parsing them properly.

## What Changes

- Add a corpus manifest listing 59 RFCs across the HTTP, TLS and TCP families, including
  obsolete RFCs alongside their replacements. Each entry records the RFC number, family and title.
- Add RFC-aware parsing that removes page furniture and splits a document into numbered sections
  across the layouts found in the corpus.
- Exclude sections with little retrieval value, such as boilerplate, tables of contents,
  references and author details.
- Add a small ingestion configuration that records the embedding model's token limit, the target
  chunk size in tokens, and the characters-per-token ratio for this corpus and tokenizer. Trying
  another embedding model becomes a configuration change rather than a code change.
- Add section-based chunking, with the size limit derived from that configuration. A section stays
  whole when it fits the limit, and larger sections split on paragraph boundaries. Every chunk has
  a stable ID and records its RFC, family, section number and title, so that citations can point
  to it.
- Add a keyword index stored in a single file, and a keyword search function that the next change
  will build on. A small command-line search makes the results easy to inspect.
- Add an ingestion command that downloads missing RFCs, then builds the index atomically and
  deterministically. A failure in any RFC fails the run and leaves any existing index untouched.
  The index records the configuration that built it.
- Document the commands in the README and resolve the roadmap's open question about the corpus.

Out of scope: wiring search into `query()`, the LLM, embeddings, labeling RFC status and
status-aware retrieval, and the golden question set. Each belongs to a later roadmap step.

## Capabilities

### New Capabilities
- `rfc-ingestion`: Turns the curated RFC corpus into a searchable, citable index, including the
  corpus definition, parsing, chunking, index build, and keyword search.

### Modified Capabilities
<!-- None: rfc-downloader is reused as it is, and query-interface is unchanged by this change. -->

## Impact

- New: `corpus.json`, `ingest_config.json`, `rfc_parser.py`, `chunker.py`, `keyword_index.py`, `ingest.py`, their tests,
  and small test fixtures.
- Updated: `README.md` and `.gitignore`. The new `data/` directory holds downloaded RFCs and the
  generated index, and it is not committed.
- No new dependencies. The index uses the SQLite module in Python's standard library.
- Requires network access to rfc-editor.org the first time ingestion runs. Tests and CI remain
  offline.
- Ingestion, tests and CI do not require Ollama. Measuring the characters-per-token ratio during
  this change does, once, because Ollama reports the real token counts.
