# Tasks

## 1. Documents

- [x] 1.1 Create a branch `organize-documentation` from `main`. Save `main`'s `README.md` in the scratchpad, and split it into paragraphs, code blocks and list items in a numbered list. Create `docs/configuration.md`, `docs/usage.md` and `docs/library.md` from the README sections the design's table assigns to them, each with `[Back to README](../README.md)` below its title, and with links between the guides where the text refers to another topic. Remove the paragraph on reinstalling after the move to `src/`, the paragraph on moving an old `data/` folder with its commands, and the query section's directory precedence paragraph. Verify that every command in `docs/usage.md` and `docs/configuration.md` that doesn't need Ollama or the network runs as written from `/tmp`, including `rfc-search "three-way handshake"` and each command's `--help`
- [x] 1.2 Create `docs/how-it-was-built.md` from the full "How this was built" section, `docs/roadmap.md` from the roadmap and its open questions, and `docs/releasing.md` with the numbered steps from the documentation spec. In `docs/releasing.md`, the steps are: a release branch; `scripts/update_architecture.py` with the version; `[Unreleased]` renamed to the version and date, with a new empty `[Unreleased]` and the compare links updated; `version` in `pyproject.toml`; the pull request, its review and CI; then, after the owner merges, the tag on `main` and `gh release create` with the version's changelog section as notes. Give each document the back-link. Verify that the "Updating ARCHITECTURE.md" text in the old README is all in `docs/releasing.md`, and that the release steps match `scripts/update_architecture.py --help`
- [x] 1.3 Create `CONTRIBUTING.md` from the Development section, and `SECURITY.md` as in the design: supported versions, private reporting through the Security tab with no public issue and no email address, and the leaked-secret paragraph. Link `CONTRIBUTING.md`'s secret-scanning text to `SECURITY.md`, and `SECURITY.md` to `CONTRIBUTING.md` for `.gitleaksignore`. Give both the back-link `[Back to README](README.md)`. Verify that every command in `CONTRIBUTING.md` runs as written in the repository, apart from `python3.14 -m venv venv` and `pre-commit install`
- [x] 1.4 Rewrite `README.md` in the design's order: the opening paragraph, a short "How this was built" with three or four headline decisions and a link to `docs/how-it-was-built.md`, "Approach", "Quick start" with the example answer, "Roadmap" with the diagram and a link to `docs/roadmap.md`, "Documentation" with a table of every other document and what it covers, and "License". Verify that it's about 100 lines. Then go through the numbered list from 1.1, and record for each entry the document that now holds it, or that it was removed on purpose. Verify that no entry is unaccounted for, and that the only removed entries are the three named in 1.1

## 2. Changelog

- [x] 2.1 For each pull request from #9 to #26, read it with `gh pr view` and read its archived proposal. Check the design's grouping against them, including which of #16 and #21 made the user data directory the default. Write `CHANGELOG.md` in the Keep a Changelog format with the back-link, an `[Unreleased]` section holding the grouped entries and this change's entry, a `[0.1.0] - 2026-11-08` section summarizing the first release, and compare links at the bottom. Verify in a scratch list that every pull request from #9 to #26 is covered by an entry, and that `[0.1.0]` lists no archive pull request
- [x] 2.2 Add a tasks rule to `openspec/config.yaml`: each change's task list includes a tracked task that adds the change's entry under `[Unreleased]` in `CHANGELOG.md`, in the category that fits, written for users and contributors. Mention the entry in `CONTRIBUTING.md`'s description of the change flow. Verify that `openspec instructions tasks --change organize-documentation --json` returns the new rule alongside the existing two

## 3. Architecture document

- [x] 3.1 In `.claude/skills/update-architecture/SKILL.md`: add `[Back to README](README.md)` below `# Architecture` in the step 4 structure; read the roadmap from `docs/roadmap.md` instead of `README.md` in step 3; and name `corpus.toml`, `ingest.toml` and `query.toml` instead of the JSON files. Leave the pinned model and every other step unchanged. Add the same back-link line below the title in `ARCHITECTURE.md`, and change nothing else in it. Verify that `git diff ARCHITECTURE.md` shows one added line and one blank line, that `grep -n "\.json\|README" .claude/skills/update-architecture/SKILL.md` finds only the back-link line, and that `pytest tests/scripts` passes

## 4. Documentation test

- [x] 4.1 Add `tests/test_docs.py` as in the design, parametrized by document: links and anchors resolve, a back-link appears before the first `##` heading, the README links to every other document, and `CHANGELOG.md`'s first section is `[Unreleased]`. Verify that it passes. Then verify the anchor rule against GitHub: render `README.md`, `docs/configuration.md` and `docs/usage.md` with `gh api markdown -f mode=gfm`, and check that the `id` of every heading equals the anchor the test computes for it
- [x] 4.2 One at a time, plant a link to a missing file, a link to a missing anchor, a guide without its back-link, a new `docs/` file the README doesn't list, and a `CHANGELOG.md` whose first section isn't `[Unreleased]`. Verify that each makes the test fail and names the document and, for a link, the link. Then remove each one, and verify that `git status` shows none of them left

## 5. Project name

- [x] 5.1 Title the README `rfc-qa`, with the tagline "RFC Q&A: cited answers from the IETF RFCs." in place of "Document Q&amp;A Service". Name the project `rfc-qa` in `ARCHITECTURE.md`'s first sentence, the Purpose of `openspec/specs/rfc-downloader/spec.md` and the `src/rfc_qa/query.py` docstring, and add an entry to `CHANGELOG.md`. Leave the archived changes and the GitHub links as they are. Verify that `git grep -n -i "document q\|document service\|document_service" -- . ':!openspec/changes/archive'` finds only the GitHub links and this change's own artifacts, and that `openspec validate --specs` passes

## 6. Checks

- [x] 6.1 Run `pytest`, with and without `RFC_QA_INSTALL_TESTS=1`, and `pre-commit run --all-files`, and verify that all pass. The install tests copy `README.md` into the build, so they show that the package still builds with the new README

## Workflow follow-up

- Open a pull request from `organize-documentation`. The `test`, `quality` and `secrets` checks must pass, and `archive-check` is expected to fail until the archive.
- The repository owner reviews the documents on GitHub, where the links and anchors can be followed as readers will, while CI runs on the pull request. Any changes are made on this branch, in the active change, before the archive, and the checks must pass again.
- Archive the change on this branch as the last step, which creates the documentation spec, syncs the architecture-docs spec, makes the change complete and turns `archive-check` green.
- The repository owner merges once CI still passes, so that the documents, specs and archive land as one commit on `main`.
