# Design

## Context

- **Current documents:** the root holds only `README.md` (463 lines), `ARCHITECTURE.md` (456 lines)
  and `LICENSE`. There's no `docs/` directory.
- **The README is referenced in three places:**
  - The architecture-docs spec says planned work is left to "the README's roadmap".
  - `.claude/skills/update-architecture/SKILL.md` reads `README.md` only to find the roadmap.
  - `pyproject.toml` sets `readme = "README.md"`, and `tests/test_install.py` copies it into the build.
- **ARCHITECTURE.md is generated** by the `update-architecture` skill, through
  `scripts/update_architecture.py`, at each release.
  - In update mode, the skill keeps the existing text as its base.
  - The file was last generated for v0.1.0, so its text is out of date: it describes modules at the
    root and `corpus.json`. That's expected until the next release.
  - The skill's list of files to read still names `corpus.json`, `ingest.json` and `query.json`,
    which #25 replaced with TOML.
- **History:** the only record of changes is the v0.1.0 GitHub release notes. 18 pull requests have
  merged since then, #9 to #26. Each has an archived OpenSpec change in
  `openspec/changes/archive/`.
- **Private vulnerability reporting** is enabled on the repository.

## Goals / Non-Goals

**Goals:**

- Every paragraph of the current README ends up in exactly one document, apart from the outdated
  notes and the repeated precedence rules, which are removed on purpose.
- The README is short enough to read in two minutes, about 100 lines.
- Links can't silently break, and a new document can't be added without the README listing it.

**Non-Goals:**

- **A release skill.** The procedure has been followed once, before the changelog existed. It's
  written down in `docs/releasing.md` and followed by hand at the next release. A skill, if it's
  still wanted after that, is its own change, with its own spec. It would call
  `scripts/update_architecture.py` rather than repeat it, set `disable-model-invocation`, and stop
  before the merge and the tag.
- **Regenerating ARCHITECTURE.md.** That happens at the next release. This change adds only the
  back-link.
- **Rewriting the content.** Text moves, with edits only to fit its new place: headings, links and
  the opening sentence of a section. The facts stay the same.
- **Checking web links.** The test would need the network, and would fail when an outside site is
  down.
- **The PyPI long description.** The project isn't published, so the relative links in the README
  aren't adjusted for display outside GitHub.

## Decisions

### Where each part of the README goes

| README now | Goes to |
| --- | --- |
| Opening paragraph, Approach | `README.md` |
| How this was built: the first part, on who wrote the code and what the owner directed | `README.md`, shortened, with three or four headline decisions as one-liners |
| How this was built: the full list of decisions and "The record is public" | `docs/how-it-was-built.md` |
| Development: setup, editable install, test variables, ruff, mypy, pre-commit, `.gitleaksignore`, pull requests, CI checks, `archive-check` | `CONTRIBUTING.md` |
| Development: "The repository is public, so a secret … has to be treated as leaked" | `SECURITY.md` |
| Development: reinstalling after the move to `src/` | removed |
| Installing | `README.md` quick start (`pip install .`), and `docs/usage.md` (the wheel) |
| Building the index: `rfc-ingest`, `rfc-search`, the default data directory | `docs/usage.md` |
| Building the index: config directory, the TOML files, chunk settings, copying the config, data directory selection | `docs/configuration.md` |
| Building the index: moving an old `data/` folder | removed |
| Asking a question: `rfc-query`, the example output, cold starts | `docs/usage.md`, and the example output also in the README quick start |
| Asking a question: `query.toml`, `OLLAMA_BASE_URL` | `docs/configuration.md` |
| Asking a question: the directory precedence paragraph | removed, replaced by a link to `docs/configuration.md` |
| Asking a question: `query()` from Python | `docs/library.md` |
| Handling errors: the error classes, `query()`'s responses, the example | `docs/library.md` |
| Handling errors: exit statuses and one-line errors | `docs/usage.md` |
| Seeing what the library is doing: `-v` and `-vv` | `docs/usage.md` |
| Seeing what the library is doing: configuring `logging` from Python | `docs/library.md` |
| Updating ARCHITECTURE.md | `docs/releasing.md` |
| Roadmap: the diagram | `README.md` |
| Roadmap: the diagram, the explanation and the open questions | `docs/roadmap.md` |
| License | `README.md` |

The usage guide covers the commands, and the library guide covers calling the package from Python.
Errors and logging are split between them by who reads them: a person at a terminal, or a program.

Alternative: one `docs/user-guide.md`. It would be easier to write, but it would be another long
file mixing readers, which is the problem the change exists to solve.

### Root files and `docs/`

The root holds the files that GitHub and readers expect there. GitHub links `CONTRIBUTING.md` from
new pull requests and `SECURITY.md` from the Security tab. Readers expect `CHANGELOG.md` and
`ARCHITECTURE.md` at the root. `ARCHITECTURE.md` also stays because the spec, the skill and the
script all name that path. Topic guides go in `docs/`, named by their subject in lowercase.

### The README

In order: the opening paragraph; "How this was built" (short); "Approach"; "Quick start", with four
commands and the example answer; "Roadmap", with the diagram only; "Documentation", a table of each
document and what it covers; "License".

The build story comes second because portfolio reviewers come first. The example answer stays in the
README because it shows what the project does without anyone running it.

### The back-link

Each document's title is followed by a line `[Back to README](README.md)`, or
`[Back to README](../README.md)` in `docs/`. The same wording in every file makes it easy to see and
to test. Links between guides, such as from the usage guide to the configuration guide, are added
where the text refers to another topic.

### The documentation test

`tests/test_docs.py` reads every `*.md` file at the root and in `docs/`. It uses only the standard
library:

- **Links:** it finds inline Markdown links, `[text](target)`, outside fenced code blocks and inline
  code. It skips targets with a scheme, such as `https:` or `mailto:`. Each other target resolves
  from the document's directory and has to exist.
- **Anchors:** when a target has a `#fragment`, the target file's headings are turned into GitHub
  anchors and the fragment must be one of them. A GitHub anchor is the heading in lowercase, with
  punctuation other than `-` and `_` removed and spaces replaced by `-`. A repeated heading gets
  `-1`, `-2` and so on. A fragment on its own refers to the same document.
- **Back-links:** every document other than the README has a link that resolves to `README.md`
  before its first `##` heading.
- **The index:** the README links to every other document found.
- **The changelog:** the first `##` heading in `CHANGELOG.md` is `[Unreleased]`.

Each failure names the document, and for a link, the link itself. The test is parametrized by
document, so each document passes or fails on its own.

Alternative: a link checker such as `lychee` or `markdown-link-check` in CI. Either would be a new
tool to install and pin, and neither checks the back-links or the index.

### The changelog

- **Format:** Keep a Changelog, with Added, Changed and Removed as needed. The newest section comes
  first, and compare links at the bottom point to the GitHub diff for each version.
- **Entries:** one line each, saying what changed for a user or contributor, not how. No PR numbers,
  because an entry is written before its pull request is opened. The compare links lead to the pull
  requests.
- **`[0.1.0]`:** a short summary of the first release, based on its release notes. Under Added: the
  RFC downloader and ingestion, keyword search, answers with checked citations, CI, the archive check
  and `ARCHITECTURE.md`. The archive pull requests are left out.
- **`[Unreleased]`:** the 18 pull requests since v0.1.0, grouped. The grouping below comes from their
  titles, and is checked against each pull request and its archived proposal before it's written:
  - Added: the MIT license; selectable configuration and data directories (#15, #16); ruff, mypy and
    the pre-commit hook (#17); secret scanning (#18); running from a regular install, with the
    install tests (#21); progress logging with `-v` (#24); comments describing every setting (#25).
  - Changed: architecture updates start from the release tag (#9); the `rfc_qa` package and the src
    layout (#11, #20); OpenSpec 2.1 (#12); the test layout and bare `pytest` (#13, #14); strict type
    checking (#19); one family of errors, reported once (#22); the configuration in TOML (#25); the
    lint rules (#23, #26); this change's documents.
  - Removed: the JSON configuration files (#25); `data/` in the repository as the default data
    directory (#16 or #21, whichever made the change); importing the package from the checkout
    without an install (#20).
- **Keeping it current:** a second tasks rule in `openspec/config.yaml` makes each change's task
  list include a task to add its entry under `[Unreleased]`. Because the entry is a tracked task, it
  lands in the same commit as the change, and the owner reviews it with the pull request. This
  change adds its own entry the same way.

Alternative: entries written at release time from the merged pull requests. It's less work per
change, but it turns the release into a summarizing job, which is the reason the CHANGELOG is being
added.

### SECURITY.md

- **Supported versions:** only the latest release gets fixes. The project is pre-1.0 and has one
  release.
- **Reporting:** use the "Report a vulnerability" button on the Security tab, which is GitHub's
  private vulnerability reporting, and don't open a public issue. The policy says this is a personal
  project, so replies are best effort, with no promised response time. No email address is given.
- **Leaked secrets:** the paragraph from the README, plus a link to `CONTRIBUTING.md` for the
  `.gitleaksignore` steps that apply to a finding that isn't a secret.

### ARCHITECTURE.md and the skill

- The link test checks `ARCHITECTURE.md` like every other document. Waiting for the next release
  would mean an exception in the test until then. So the back-link is added by hand now, as one
  line below the title. The generation line stays as it is. Update mode keeps existing text, and the
  skill's structure now includes the line, so regeneration keeps it.
- In `SKILL.md`:
  - the structure in step 4 gains the back-link below `# Architecture`;
  - step 3 reads the roadmap from `docs/roadmap.md` instead of `README.md`;
  - step 3 names `corpus.toml`, `ingest.toml` and `query.toml`.

  The pinned model doesn't change, so the next run is a normal update.

Alternative: leave ARCHITECTURE.md alone and exempt it from the back-link check. That's more honest
about the file being generated, but the exemption would outlive the reason for it.

## Risks / Trade-offs

- **Content lost in the move** → the table above maps every README section. The apply task checks
  each paragraph of the old README against its new home, and lists the removed ones.
- **The anchor rules don't match GitHub's in an unusual heading**, such as one with backticks or
  emoji → the test's anchors follow GitHub's rules for the headings these documents use. If a heading
  ever disagrees, the test fails rather than passing a broken link.
- **The hand-edited line in ARCHITECTURE.md isn't covered by the generation line** → it's the only
  hand edit, its content is fixed by the spec, and the next run regenerates it.
- **A change forgets its changelog entry** → the tasks rule puts the entry in every task list, and
  the owner reviews it with the pull request. Every change gets an entry, because contributors read
  the changelog too, so even a lint change is worth a line. No CI check requires `CHANGELOG.md` to change in
  every pull request. One can be added later if entries go missing.
- **More files to keep consistent** → each topic has one home, and the test catches broken links
  between them.
