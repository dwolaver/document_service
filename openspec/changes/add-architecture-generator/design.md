# Design

## Context

See proposal.md - Why. The decisions below were made during exploration, before
`add-answer-generation`. Check them against the code when this change resumes.

The repository has no `ARCHITECTURE.md`, no tags and no releases. `main` requires a pull request,
with `test` and `archive-check` as required checks. Project skills live in `.claude/skills/`. The
`.github/skills/` copies exist for Copilot, which this change doesn't target.

Modules use leading underscores for private helpers, which gives a usable line between internal
interfaces and implementation details. `rfc_parser.py` alone has 17 private functions.

The Claude Code documentation was reviewed in November 2026 for how skills handle models:

- A skill's `model` frontmatter applies for the current turn and isn't saved to settings.
- A model blocked by `availableModels` is ignored, and the skill runs on the session model. No notice
  is documented, so the skill fails open.
- Behavior for an unavailable model isn't documented for skills.
- No hook, environment variable or shell step documents a way to read a skill's model during a run.
  There is no `$CLAUDE_MODEL` variable.
- Headless JSON output reports the model actually used, in the `modelUsage` field of the result.

Parts of this came from summaries of long pages, so confirm them before relying on them.

## Goals / Non-Goals

**Goals:**
- A file that's accurate at each release, with the source code as the source of truth.
- A run that's rejected unless the pinned model produced it.
- Key decisions whose assumptions are reviewed at every release.

**Non-Goals:**
- Running in CI, which would need a model there and works against the owner reviewing every change.
- Documenting every function. Private helpers are left out.
- Describing planned work. The README's roadmap covers that.
- Making or reversing decisions. Reversals go through OpenSpec.

## Decisions

- **A Claude Code skill in `.claude/skills/update-architecture/`**: Only Claude Code is targeted, so
  there's one copy to maintain. A GitHub Action was rejected for the reasons in Non-Goals.

- **Use the diff to focus, and the code to verify**:

  ```
  No file:   read code --> write everything --> verify
  Exists:    read diff --> find affected sections --> rewrite them --> verify
  ```

  Verification checks that every named file, function, parameter and diagram step still exists, on
  every run. Following only the diff would let one early mistake survive indefinitely. Deleting the
  file gives a clean rebuild.

- **The header records what produced the file**:

  ```
  Generated from commit 3b64fbc by claude-opus-5-5, for release v0.1.0.
  ```

  The commit is the starting point for the next update. `git log -- ARCHITECTURE.md` was rejected,
  because a small manual fix would move that starting point and skip real changes. Tags were rejected
  because none exist yet.

- **File structure runs from high level to detail**: High-level architecture, then workflows with
  diagrams, then public interfaces, then internal interfaces, then key decisions.

- **Three tiers for interfaces**:

  | Tier | Includes | Examples today |
  |---|---|---|
  | Public | What outside users and callers rely on | `query()`, `QueryResponse`, the command lines, `corpus.json`, `ingest_config.json` |
  | Internal | Non-underscore functions that connect modules | `parse_rfc`, `chunk_sections`, `build_index`, `search`, `Chunk` |
  | Left out | Underscore functions | `_is_plausible_title` |

- **Mermaid diagrams**: GitHub renders them, and they change cleanly in diffs. Three to start with: the
  system overview, the ingestion flow and a query sequence.

- **Describe only what exists**: The README keeps the roadmap, and its approach section and diagram
  shrink to a link to this file.

- **Key decisions record their assumptions**: Each row has the decision, why it was made, the assumption
  to revisit, its status, when it was last reviewed, and its source. For example:

  | Decision | Why | Assumption to revisit | Status | Last reviewed | Source |
  |---|---|---|---|---|---|
  | SQLite FTS5 for keyword search | One file, no dependencies | Local Chroma still lacks BM25, as of chromadb 1.5.9 | Current | v0.1.0 | `add-rfc-ingestion` design |
  | `chars_per_token` is 1.6 | Worst case measured across the corpus | Same corpus and embedding model, and dense tables justify smaller chunks for everything | Current | v0.1.0 | `add-rfc-ingestion` design |
  | Terminal script enforces the model | Skills fail open on a blocked model | Skills still can't refuse on a mismatch | Current | v0.1.0 | `add-architecture-generator` design |

  The list stays at roughly 10 to 15 decisions: those that are expensive to reverse or rest on something
  that can expire. The "why" comes from the archived designs, because code can't supply it. The code
  still wins on what exists.

- **The generator flags, and the owner decides**: Each run checks whether the code still reflects each
  decision, and whether the release touched its assumption. It can set `Review needed` with a reason,
  and it can add a decision. Only the owner can set `Current` or update `Last reviewed`, so that an LLM
  doesn't approve its own assumptions. Assumptions that can't be checked from the code, such as
  whether Chroma has gained local BM25, are listed as questions on every run.

- **The key decisions section is preserved**: It holds review notes that aren't in the code, so even a
  full regeneration carries it over unchanged. This is the one exception to generating from code. When
  a review overturns a decision, the reversal goes through an OpenSpec change, and the row becomes
  `Superseded` with a link. Superseded rows stay.

- **Pin the full model ID, starting with `claude-opus-5-5`**: An alias like `opus` moves to a newer
  model without anyone deciding to. Changing the ID is a one-line edit that shows up in a pull request.

- **`scripts/update-architecture.sh` enforces the model**:

  ```
  read the pinned model from SKILL.md
    --> claude -p "/update-architecture" --model <pinned> --output-format json
    --> check modelUsage
          matches: keep ARCHITECTURE.md for review
          anything else, or any error: restore the file, exit non-zero
  ```

  The skill's own `model` field can't refuse, as described in Context. A slash command inside a session
  was rejected for this reason: it would be more convenient, but it could only self-report. This is a
  refusal after the run, so it rejects a result rather than preventing a run. That's acceptable for
  something run rarely. Reading the model from `SKILL.md` keeps one place to change it.

  The script's header comment must explain this rationale, link the Claude Code documentation, and
  state clearly that the script can be removed in favor of the skill alone once a model mismatch can
  refuse to run.

- **The skill also checks its own model first**: Its first step tells the model to stop if it isn't the
  pinned one. This catches most mismatches early, but it's self-reporting, so it doesn't replace the
  script.

- **A model switch takes a stricter path**: If the model in the file's header differs from the pinned
  one, the skill ignores the diff, regenerates everything except key decisions, and lists what changed
  in meaning. The owner then validates the file in more detail than a normal update.

- **Release flow**: Create a branch, run the script, open a pull request, the owner reviews and merges,
  then tag the release.

- **The tooling follows OpenSpec, and its output doesn't**: `archive-check` applies to this change as
  normal, and later `ARCHITECTURE.md` updates pass it because they don't touch active changes.

## Risks / Trade-offs

- [`modelUsage` lists a small helper model as well] → Tested when this change resumes. The check would
  then confirm which model did the main work, rather than requiring exactly one entry.
- [A configured fallback model swaps models mid-run] → The script's check rejects the result, and no
  fallback should be configured for this run.
- [The script restores `ARCHITECTURE.md` over wanted local edits] → It refuses to start if the file has
  uncommitted changes.
- [The documented behavior changes] → The key decisions table carries this as an assumption, so it's
  reviewed at every release.
- [Generated text sounds right but is wrong] → Verification covers named items, and the owner reviews
  the meaning in the pull request.
- [Headless mode needs permission for the tools the skill uses] → Tested when this change resumes, with
  access limited to what the skill needs.

## Open Questions

- The version scheme and what defines a release. `v0.1.0` once step 1 gives a working RAG answer is the
  likely first release.

## To Test When Resuming

- Whether a bad or unavailable model name makes `claude -p --model` fail cleanly.
- Whether `modelUsage` can list more than one model for a run, and what a mismatch looks like.
- Whether a slash command runs in headless mode as planned, and which permissions it needs.
- Whether the documentation findings in Context are still current.
