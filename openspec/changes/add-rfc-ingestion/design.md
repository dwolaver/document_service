# Design

## Context

See proposal.md - Why. Requirements are in specs/rfc-ingestion/spec.md.

The project is a flat layout of Python 3.14 modules with module-level functions, small dataclasses
for results, and errors sent to stderr through a `_log_error` helper. `download_rfc(number,
directory)` stores `rfc<number>.txt`, skips files it already has, and requires the directory to
exist. CI runs offline, and tests must stay that way.

Sampling 12 real RFCs, from RFC 793 in 1981 through RFC 9846, showed the layouts the parser has to handle:

| Layout | Examples | Page breaks | Headings |
|---|---|---|---|
| Early | 793 | Form feeds, running headers with the date | Top level centered and uppercase; others at the margin |
| Hierarchical | 1122, 1323 | Form feeds | Indented by depth, often one or two spaces after the number |
| Paginated | 2616, 5681, 8446 | Form feeds, `RFC n ... date` headers | At the margin; 2616 uses `13.1.1 Title` with no trailing period |
| Unpaginated | 9110, 9293, 9846 | None | At the margin; UTF-8 text is possible |

Other measurements from that sample:

- The median section is 1,000 to 1,700 characters, so most sections fit in one chunk. The largest
  real sections reach about 43,000 characters.
- `nomic-embed-text` reports a 2,048-token limit. Four overlapping excerpts of RFC 9110 measured
  between 2.7 and 4.7 characters per token. That is a rough starting point rather than a corpus
  figure, so this change measures it properly.
- By default Ollama truncates over-long input with no error. With `truncate: false` it returns an
  error instead.
- Unnumbered back matter is a real trap. Without handling it, a 24,505-character "section B.9" in
  RFC 9110 is mostly its Index, and reference lists can dominate results.
- SQLite FTS5 with BM25 ranking works in the project's Python build.

## Goals / Non-Goals

**Goals:**
- A parser whose behavior on each layout is pinned down by tests, not guessed.
- An index that is one file, so that it can be copied into a Docker image at step 5.
- Chunk IDs that later citation checking can rely on.

**Non-Goals:**
- Perfect structure inside sections. Unnumbered subheadings, such as the event names in RFC 793
  section 3.9, stay as text.
- Semantic chunking or chunk overlap. These can be evaluated against the golden set later.
- Reflowing text. Line layout is preserved, because figures depend on it.
- Incremental index updates. The corpus is small and rarely changes, so ingestion always does a
  full rebuild.

## Decisions

- **Four focused modules**: `rfc_parser.py` turns text into sections, `chunker.py` turns sections
  into chunks, `keyword_index.py` builds and searches the index, and `ingest.py` is the entry point
  that connects them. Each step can be tested alone, and each maps to one RAG concept for a reader
  of the repository. A single large `ingest.py` was rejected because tests would have to go through
  the entire pipeline to check one heading rule.

- **`corpus.json` holds number, family and title**: A manifest is easy to review and needs no parser.
  Titles come from the manifest rather than the document because RFC cover pages vary too much:
  RFC 793's title sits among funding details. Status isn't stored yet, because status-aware retrieval
  is planned for step 3 and it will need its own source of truth.

- **The corpus is 59 RFCs, checked against the RFC Editor's index**:

  | Family | Current or still relevant | Obsolete |
  |---|---|---|
  | HTTP (24) | 9110, 9111, 9112, 9113, 9114, 9204, 7541, 9651, 9457, 6265, 6455, 7838, 8288, 5789, 6585 | 2616, 7230, 7231, 7232, 7233, 7234, 7235, 7540, 2818 |
  | TLS (17) | 9846, 9325, 9525, 8996, 6066, 7301, 5280, 9147 | 8446, 8422, 5246, 4346, 2246, 5077, 6961, 7525, 6125 |
  | TCP (18) | 9293, 5681, 6298, 7323, 2018, 1122, 7413, 8985, 6582, 3168, 9438, 5961 | 793, 6528, 8312, 2581, 2988, 1323 |

  RFC 8446 is deliberately listed as obsolete: the index shows that RFC 9846 replaced it, which is
  also a realistic trap, because many readers still treat 8446 as current. QUIC itself stays out of
  scope, even though HTTP/3 depends on it.

- **Page handling by line pattern**: Footers end in `[Page n]`, and headers match the `RFC n ...
  date` pattern or the early-era form. Blank lines around a removed break are dropped, so a
  paragraph that crosses pages stays together. If a real paragraph end falls on a break, two
  paragraphs join, which is harmless for keyword search. Pattern matching is limited to lines next
  to form feeds where one exists, so that body text isn't removed by accident.

- **Heading detection uses order as well as shape**: A line must look like a heading, and its number
  must come after the previous heading in section order. The order check is what rejects a numbered
  list restarting at `1.`, including the indented lists in RFC 793, without needing a rule for each
  era. It requires an increase of at most two at the top level, so an RFC that skips a number still
  parses, but `9.` can't follow section 3. Dotted leader lines and everything before the end of the
  table of contents are never headings. Appendices sort after numeric sections.

  Testing all 59 RFCs showed that order alone isn't enough, because wrapped body text can look like
  a heading: `6.1 of [RFC7231])` in RFC 7234 blocked 30 real sections. So titles must also start
  with a capital or a digit, unless they are subsections at the margin, where lowercase field names
  like `max-age` are real headings. An RFC with subsection headings at the margin is also treated
  as never having indented ones, because layout is consistent within a document. Indented headings
  must sit at exactly three spaces per level.

- **Unnumbered headings are matched against a fixed list**: `Abstract`, `Status of This Memo`,
  `Copyright Notice`, `Table of Contents`, `Acknowledgments` and spelling variants, `Contributors`,
  `Authors' Addresses` and `Author's Address`, `Index`, and others found by scanning the corpus, such
  as `Intellectual Property`. RFCs 2818, 2246, 1122 and 1323 also have an unnumbered `Security
  Considerations`, which is kept as a section numbered `security`. Headings are matched at the
  margin or centered. Matching is case-insensitive. A title list is simple to read and easy to
  extend when ingestion reveals a new variant.

- **Excluding by section title**: References, acknowledgments and author details are dropped, but
  `Security Considerations` and `IANA Considerations` stay. Security sections matter for TLS
  questions, and change history sections answer "what changed from RFC 2616?".

- **Chunk limits live in `ingest_config.json`**: Chunk size was first planned as a fixed 3,000
  characters, but that number mixed two separate things. The file keeps them apart:

  ```json
  {
    "embedding_model": { "name": "nomic-embed-text", "max_tokens": 2048 },
    "chars_per_token": 1.6,
    "target_chunk_tokens": 1100
  }
  ```

  - `embedding_model.max_tokens` is the hard ceiling, set by the embedding model.
  - `target_chunk_tokens` is a retrieval quality choice inside that ceiling, to be tuned against
    the golden set. It starts well below the ceiling, because most sections already fit and the
    task prefix also uses tokens.
  - `chars_per_token` belongs to the pair of this corpus and this model's tokenizer, so it sits
    beside the model name rather than with the corpus. Changing either one means measuring it
    again.

  Ingestion calculates the maximum chunk size in characters as `target_chunk_tokens` x
  `chars_per_token`. It fails if the target exceeds
  `max_tokens`. Keeping the limit in characters means ingestion, tests and CI don't need Ollama. A
  separate file keeps model settings out of the RFC list in `corpus.json`. Reading the limit from
  Ollama at ingestion time was rejected, because it would make Ollama a build dependency in this
  change, before anything is embedded.

- **Measure the ratio across the whole corpus**: One measurement during implementation counts tokens
  for every chunk through Ollama and sets `chars_per_token` from the lowest result, rounded down,
  so that the estimate errs towards smaller chunks. An average would allow dense chunks to overrun.

  The measurement covered all chunks with the task prefix included. The median was 4.8 characters
  per token, but dense ASCII tables reached 1.67, far below the 2.7 starting estimate, so
  `chars_per_token` is now 1.6 and the maximum chunk size is 1,760 characters. Chunks under 200
  characters were left out, because their ratio mostly reflects the prefix: `None.` measures 1.0.
  After the rebuild there are 5,261 chunks, up from 3,994 at 2.7, and the largest is 1,074 tokens.
  At 2.7 the largest was 1,731 tokens and 34 chunks exceeded the target, though none reached the
  2,048-token ceiling.

- **The index records its configuration**: A `metadata` table stores the values above and the derived
  maximum. That shows which settings built a given index, and lets step 3 detect an index built for
  a different model.

- **The LLM does not set chunk size**: Swapping the LLM changes how many chunks fit in a prompt, not
  how they are cut. `add-answer-generation` owns that budget, which covers chunks retrieved x chunk
  tokens + prompt + answer, within the `num_ctx` it sets for the model in use.

- **Step 3 verifies these values**: When embeddings arrive, step 3 should check `max_tokens` against
  what Ollama reports for the model, and pass `truncate: false`. A wrong estimate then fails loudly
  instead of silently losing text, which is why the ratio only has to be good enough here.

- **Split at paragraphs, then lines, and no overlap**: Paragraphs are packed greedily up to the
  maximum. An oversized paragraph or figure splits between lines. Overlap adds duplicate text, which
  is the near-duplicate problem this project is trying to reduce, and it can be added later if the
  golden set shows a need.

- **Chunk IDs look like `rfc9110-s15.5.1-p0`**: They are readable in logs and citations, and they are
  stable because they derive from the document. `p` is the position in the section. If an RFC
  repeats a section number, a counter suffix keeps IDs unique. The `abstract` section uses the same
  form.

- **SQLite FTS5 for keyword search**: One file, BM25 ranking built in, and no new dependency. A
  hand-written BM25 would teach the formula,
  but the agreed lesson of this project is chunking and retrieval behavior rather than inverted
  indexes, and an FTS5 ranking is easy to replace behind one function. `rank_bm25` was rejected
  because it needs a dependency and has to load everything into memory on every process start.

  Chroma was also rejected for this change. Its local mode has no BM25: on chromadb 1.5.9 and Python
  3.14, creating a BM25 sparse index failed with `Sparse vector indexing is not enabled in local`,
  and only an unranked `$contains` document filter was available. It would also add about 85
  packages and 488 MB, and this change doesn't store vectors, which is where Chroma is strongest.

- **The retrieval boundary is two functions**: Callers use only `build_index(chunks, config, path)`
  and `search(path, query_text, limit)`. SQL stays inside `keyword_index.py`, and results come back
  as plain dataclasses rather than database rows. The boundary is at retrieval rather than the
  database, because keyword, vector and hybrid search take different inputs and return different
  scores, so a generic database interface wouldn't fit them. A formal interface class is deferred
  until a second backend exists at step 3, when its real shape will be known.

- **Search details**: The FTS table has `section_title` and `text` columns, and BM25 column weights
  favor the title. The `porter unicode61` tokenizer stems common words, and it keeps identifiers
  like `ECONNRESET` whole. User text is never passed as FTS syntax: it is split into tokens, each
  token is quoted, and they are joined with `OR`. That is what makes any input safe.

- **Atomic build**: The index is written to a temporary file in the same directory, then moved into
  place with `os.replace`, as the downloader does for RFCs. The build always starts from an empty
  database.

- **Ingestion validates everything before writing**: It loads the manifest, makes sure all RFCs are
  stored, parses them all, and fails on the first problem with the RFC named. The index file is
  only opened once every RFC has produced chunks, so failure is cheap and leaves no partial output.

- **`data/` is generated and git-ignored**: `data/rfcs/` holds downloads and `data/index.db` holds
  the index. Keeping them out of git keeps the repository small, and the build can reproduce them
  from `corpus.json`. Step 5 runs ingestion while building the Docker image.

- **Tests use short fixtures**: Each layout gets a small excerpt in `tests/fixtures/`, so tests run
  offline in CI. Full-corpus quality is checked by running ingestion during implementation.

## Risks / Trade-offs

- [A heading rule misfires on an RFC that wasn't sampled] → The full-corpus task inspects section
  counts and the largest sections for all 59 RFCs. Any new layout gets a fixture before its fix.
- [A false heading with a large number, such as a date or `1000 bytes`, blocks real headings after
  it through the order check] → Requires a capitalized title and a limit on title length, and the
  full-corpus check compares headings with each RFC's table of contents where one exists.
- [Pattern matching removes a body line that looks like a page header] → Patterns are strict, and
  they apply only around page breaks.
- [Chunks that lack their heading text might rank poorly] → The section title is indexed in its own
  weighted column.
- [`chars_per_token` goes stale when the model or corpus changes] → It sits beside the model name
  and has a recorded meaning, and step 3's `truncate: false` turns a stale value into a clear error.
- [The ratio is measured on chunks that it also helped size] → The measurement is repeated after the
  rebuild, and the check that matters is the largest chunk's real token count against the target.
- [`porter` stemming merges terms that differ in an RFC] → Accepted for now, and measurable with the
  golden set at step 2.
- [FTS5 is missing from another Python build] → It's confirmed locally, and tests in CI fail clearly
  if it's absent there. Step 5 will rely on the same check.
- [rfc-editor.org is unavailable] → Only the first ingestion needs it. Downloaded files are reused.

## Migration Plan

This change only adds files, so there is nothing to migrate. To roll back, revert the pull request
and delete the local `data/` directory.

## Open Questions

- Which vector store to use at step 3. Chroma, `sqlite-vec` and plain NumPy are the candidates, to be
  compared on the corpus. Exact search should be fast enough at this size, so an approximate index
  isn't required. Local Chroma would mean running hybrid search across two stores, with rank fusion
  in project code. This doesn't affect this change, because it stores no vectors.
