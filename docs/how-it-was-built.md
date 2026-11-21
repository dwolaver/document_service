# How this was built

[Back to README](../README.md)

I didn't write the code in this repository. AI coding assistants wrote it, along with the tests and
the OpenSpec proposals, designs, task lists and specs:

- GitHub Copilot wrote the first two components, the RFC downloader and the query interface. I
  already used Copilot in my professional work.
- I then switched to Claude, Anthropic's AI model, in Claude Code, to gain experience with it. Claude
  wrote everything since, including `ARCHITECTURE.md`. It also proposed options and their
  trade-offs, ran the measurements the designs rely on, and pointed out problems it found along the
  way.

My part was to direct the work and to decide what was accepted:

- I set the goals, the scope and the order of the roadmap.
- I reviewed every proposal, design and task list before implementation started, and every resulting
  spec before it was archived, and asked for changes where they didn't match what I wanted.
- I reviewed every pull request and merged each one myself. Branch rules require a pull request for
  every change to `main`.

These decisions were mine, and they shaped the result:

- **A narrow input from the start.** The first RFC downloader specification accepted either an
  integer or a string such as `"RFC 9110"`, `"9110"`, `"0002"` or `"RFC2"`. Before any code was
  written, I narrowed it to one positive integer, the RFC number. That removed string parsing, prefix
  and zero handling from the design, and the number goes straight into the URL and the filename.
- **Never using a partial download.** I asked for the RFC downloader to check each download before
  keeping it and to write files atomically. It rejects an empty body, a body shorter than its
  `Content-Length`, or text that doesn't identify itself as the requested RFC. Then it writes to a
  temporary file and renames it into place. Ingestion reuses any RFC file already in the data directory, so an
  interrupted download never leaves a broken file to be indexed later.
- **The problem worth solving.** I scoped the corpus to HTTP, TLS and TCP, and chose status-aware
  retrieval as the goal, so that answers don't rely on RFCs that have been replaced. That's why the
  corpus deliberately includes obsolete RFCs alongside the ones that replaced them.
- **Building it by hand.** I chose to write the pipeline without a RAG framework, and to run
  open-weight models locally with Ollama, so that each part can be seen and understood.
- **Two entry points.** The split of the system into an offline ingestion step, `rfc-ingest`, and a
  query step, `rfc-query`, came out of my planning discussions with the agents. Separating them means
  the slow work of downloading, parsing and indexing RFCs happens once, and each question works from
  the finished index.
- **Challenging the database choice.** During planning I asked for SQLite to be weighed against
  ChromaDB, and whether the database should sit behind an interface that could be swapped later. The
  comparison was tested rather than assumed. Local Chroma had no BM25 ranking, so SQLite FTS5 stayed.
  Callers reach search through two functions, so the backend can change without touching them, and a
  formal interface waits until a second backend shows what shape it needs.
- **Values tied to the models and the corpus.** Early designs hard-coded values that were only true
  for the current LLM, embedding model and corpus. I judged that short-sighted, because changing any
  of them would mean refactoring. The design was changed so that those values follow what they depend
  on, in configuration. Chunk size comes from the embedding model's token limit and a
  characters-per-token ratio measured on this corpus, and the index records the settings that built
  it. The LLM's context window and answer length are set with the model, and a query that wouldn't
  fit is refused before the model is called.
- **How answers behave.** I decided that when the RFCs don't answer a question, the result is a
  successful "not found" answer, not an error. I chose short passage labels for citations after
  comparing the trade-offs. I also asked for slow first answers, while the model loads, to be flagged,
  so that they won't skew later performance measurements.
- **Compatibility after release.** I decided that error code values could be reused before the first
  release, and must be retired rather than reused after it.
- **The review process.** I asked for every change to go through a pull request, and decided that a
  change is archived on its branch before it merges, so that the code, spec and archive land as one
  commit. Early on, I merged a pull request before archiving its change. Rather than rely on
  remembering next time, I judged that the order should be enforced, and asked for a required check
  that fails until the change is archived, with a label for genuine exceptions.
- **ARCHITECTURE.md.** The idea of a definitive architecture document, and the method for producing
  it, were mine. The source code is the ground truth, not the plans. The file goes from a high-level
  overview down to the interfaces, and is generated once and then updated, with every claim checked
  against the code. I decided that updating it is part of each release, not an OpenSpec change,
  because it describes the code as released rather than proposing anything.
- **A pinned model.** I set the goal that one model, pinned in the skill, produces the file, and that
  a run refuses to go ahead on any other. Switching models should be a deliberate decision that gets
  a more thorough review. Claude Code skills can't yet refuse to run on the wrong model, so I asked
  for a small script to enforce it, with comments saying it can be removed once they can.
- **Key decisions to revisit.** I asked for a table of key decisions, each with the assumption that
  could make it wrong, so that they can be reviewed as things change. Only I mark a decision as
  reviewed, and I reviewed and marked all 15 for v0.1.0.

The record is public. The proposals and designs in [openspec/changes/archive/](../openspec/changes/archive/)
show each decision with its reasons and the alternatives that were rejected, and the
[pull requests](https://github.com/dwolaver/document_service/pulls?q=is%3Apr) show the reviews.
