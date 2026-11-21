# Proposal

## Why

The README is 463 lines, written for five kinds of reader at once: someone reviewing the portfolio, a
user, a Python caller, a contributor and the maintainer making a release. A reviewer has to scroll
past the development setup and the configuration rules to find what the project does and how it was
built. The project also has none of the standard files people look for in a repository: there's no
changelog, no contributing guide and no security policy. The only record of what changed is the
v0.1.0 release notes, which GitHub generated and which list archive pull requests as if they were
features.

## What Changes

- **A README for portfolio reviewers first.** It keeps the opening paragraph, then a short version of
  "How this was built", the approach, a quick start with the sample answer, the roadmap diagram, a
  documentation index and the license. The full list of decisions moves to its own document.
- **Standard files at the root:**
  - `CHANGELOG.md`, in the Keep a Changelog format, with entries filled in for the 18 pull requests
    since v0.1.0 (#9 to #26) and a summary of v0.1.0.
  - `CONTRIBUTING.md`: setup, tests and their environment variables, the lint, format, type and
    secret checks, and the pull request, archive and merge flow with its CI checks.
  - `SECURITY.md`: which versions are supported, how to report a vulnerability privately through
    GitHub, and what to do about a leaked secret.
  - `ARCHITECTURE.md` and `LICENSE` stay where they are.
- **Topic guides in `docs/`:** `configuration.md`, `usage.md`, `library.md`, `how-it-was-built.md`,
  `roadmap.md` and `releasing.md`.
- **Links both ways.** The README links to every other document, and every other document links back
  to the README near its top. A test checks this, and checks that every relative link and anchor in
  the documents resolves.
- **The changelog stays current.** Each change adds its own entry under `[Unreleased]`, through a new
  tasks rule in `openspec/config.yaml`. At release time, `docs/releasing.md` turns `[Unreleased]` into
  the version's heading.
- **Outdated notes removed.** The project isn't deployed, so the notes about moving an old `data/`
  folder and reinstalling after the move to `src/` are removed. The query section's repeat of the
  directory precedence rules is replaced by a link to the configuration guide.
- **The architecture skill follows the move.**
  - The `update-architecture` skill reads the roadmap from `docs/roadmap.md`.
  - It keeps a link back to the README below the title.
  - It lists the TOML configuration files, which replaced the JSON ones in #25.
  - `ARCHITECTURE.md` gets the back-link now as a one-line edit, so the link test passes before the
    next release regenerates the file.
- **The project's name is `rfc-qa`.** "Document service" was a placeholder from the start of the
  project, and the package, the commands and the data directory already say `rfc-qa`. The README's
  title becomes `rfc-qa`, with the tagline "RFC Q&A: cited answers from the IETF RFCs." The
  overview sentence in `ARCHITECTURE.md`, the rfc-downloader spec's Purpose and the `query.py`
  docstring use the name too. The links to the GitHub repository keep `document_service` until the
  owner renames the repository after this change merges, because GitHub redirects the old name to
  the new one but not the other way round. They're updated in a follow-up.
- **Not in this change:** a release skill. The procedure is written down first, as a checklist in
  `docs/releasing.md`, and followed by hand at the next release. Whether to automate it is decided
  after that.

## Capabilities

### New Capabilities

- `documentation`: how the project's documents are laid out, what the README links to, the links back
  and the check that links resolve, the changelog and how it's kept, the security policy, and the
  written release procedure.

### Modified Capabilities

- `architecture-docs`: the file links back to the README, and planned work is left to the roadmap in
  `docs/roadmap.md` instead of the README's roadmap.

## Impact

- Documents: `README.md` is rewritten. `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md` and six files
  in `docs/` are new. `ARCHITECTURE.md` gains one line and names the project `rfc-qa`.
- Workflow: `openspec/config.yaml` gains a tasks rule for the changelog entry.
  `.claude/skills/update-architecture/SKILL.md` changes where it reads the roadmap, adds the
  back-link to its structure, and names the TOML files.
- Tests: a new `tests/test_docs.py`.
- Code: only the `query.py` module docstring.
- No change to the package, the commands, their output or the configuration. `pyproject.toml` still
  names `README.md` as the readme.
