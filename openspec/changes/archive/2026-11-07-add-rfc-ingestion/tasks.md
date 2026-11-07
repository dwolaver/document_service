# Tasks

## 1. Corpus manifest

- [x] 1.1 Add `corpus.json` with the 59 RFCs from design.md, each with number, family and title; verify every number and title against the RFC Editor's index, and that RFCs 793, 9293, 2616, 9110, 8446 and 9846 are present
- [x] 1.2 Add manifest loading and validation to `ingest.py`, rejecting malformed data, unknown families and duplicate numbers with a diagnostic; verify unit tests cover a valid manifest and each rejection, and that the real `corpus.json` loads
- [x] 1.3 Add `ingest_config.json` with the starting values from design.md, and loading in `ingest.py` that derives the maximum chunk size; verify unit tests cover the derived value, a target above `max_tokens`, and missing, non-numeric and non-positive values

## 2. RFC parsing

- [x] 2.1 Add short layout fixtures to `tests/fixtures/` for the early, hierarchical, paginated and unpaginated layouts, each including a table of contents, a body list that restarts its numbering, and back matter; verify they are small plain-text excerpts that tests can load offline
- [x] 2.2 Implement page furniture removal in `rfc_parser.py`; verify unit tests show no `[Page N]` footers, running headers or form feeds remain, a paragraph crossing a page break stays adjacent, and unpaginated text is unchanged
- [x] 2.3 Implement section detection for all four layouts and appendices, with number normalization, table of contents skipping and the section-order check; verify unit tests cover every heading scenario in the spec, and that table of contents lines and restarted lists create no sections
- [x] 2.4 Implement unnumbered front and back matter handling, including the `abstract` section and excluded section titles; verify unit tests show back matter never attaches to the last numbered section, boilerplate and references are excluded, and security considerations remain

## 3. Chunking

- [x] 3.1 Implement `chunker.py` taking the maximum chunk size as a parameter, splitting oversized sections at paragraphs and then lines; verify unit tests cover a section that fits, an oversized section, an oversized paragraph, an empty section, and that joined chunks reproduce the section text in order
- [x] 3.2 Add chunk IDs and metadata, including the suffix for repeated section numbers; verify unit tests show IDs are unique, stable across runs, and that an ASCII figure keeps its indentation

## 4. Keyword index and search

- [x] 4.1 Implement index building in `keyword_index.py`, using SQLite FTS5 and writing through a temporary file with an atomic replace; store the build configuration in a metadata table; verify unit tests show a complete index is written, its metadata matches the configuration, a failed build leaves an existing index unchanged, and no temporary file remains
- [x] 4.2 Implement `search(index_path, query_text, limit)` with quoted query tokens and a higher weight for section titles; verify unit tests cover exact terms, title ranking, the limit, punctuation and FTS operators, no matches, and a missing index
- [x] 4.3 Add a small command-line search to `keyword_index.py`, printing each result's chunk ID, RFC, section and an excerpt; verify it prints results for a fixture index and exits non-zero when the index is missing

## 5. Ingestion command

- [x] 5.1 Implement the `ingest.py` pipeline and `main(argv=None) -> int`, creating `data/rfcs/`, downloading only missing RFCs through `download_rfc`, and writing `data/index.db`; verify unit tests with a patched downloader cover success, skipping stored RFCs, a failed download, an RFC with no chunks, and the printed summary
- [x] 5.2 Add `data/` to `.gitignore`; verify `git check-ignore data/index.db` matches
- [x] 5.3 Document ingestion, search and `ingest_config.json` in the README, and remove the corpus question from the open questions; verify the documented commands run as written

## 6. Full-corpus verification

- [x] 6.1 Run ingestion on all 59 RFCs; verify it succeeds, every RFC has chunks, and no chunk exceeds the derived maximum
- [x] 6.2 For every RFC, compare detected section numbers with its table of contents where one exists, and review the largest and smallest sections; add a fixture and fix for any new layout problem, and verify detected sections match or that each remaining difference is explained
- [x] 6.3 After the section fixes, count tokens for every chunk with Ollama using `truncate: false`, set `chars_per_token` from the lowest ratio rounded down, rebuild, and record the result in design.md; verify after the rebuild that the largest chunk is within `target_chunk_tokens` and `max_tokens`
- [x] 6.4 Confirm no chunk contains page furniture, and none comes from an excluded section; verify by scanning all chunks in the index for footers, form feeds and excluded titles
- [x] 6.5 Run ingestion twice and compare chunk IDs and text; verify they are identical, and that the second run makes no downloads
- [x] 6.6 Search for `three-way handshake`, `Content-Length`, `SACK` and `session ticket`, and for `ECONNRESET`, which appears in no corpus RFC and so correctly returns nothing; verify results are relevant, and that the handshake results include both RFC 793 and RFC 9293, which is the obsolete-RFC conflict step 2 will measure
- [x] 6.7 Run the full test suite offline; verify all tests pass with the existing network test still skipped

## Workflow follow-up

- Open a pull request from `add-rfc-ingestion` and confirm the `test` check passes, which also confirms FTS5 works in CI.
- The repository owner reviews the code. Any changes are made on this branch, in the active change, and the `test` check must pass again.
- After review is complete, archive the change on this branch as the last step. The change is then considered complete.
- The repository owner squash merges the pull request once the `test` check still passes after the archive, so that the code, spec and archive land as one commit on `main`.
- Propose `add-answer-generation`, which is the next part of step 1.
