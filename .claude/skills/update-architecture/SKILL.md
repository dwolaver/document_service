---
name: update-architecture
description: Create or update ARCHITECTURE.md from the source code before a release. Run it through scripts/update_architecture.py, which checks that the pinned model produced the result.
argument-hint: <release, for example v0.1.0>
disable-model-invocation: true
model: claude-opus-5-5
---

# Update ARCHITECTURE.md

You keep `ARCHITECTURE.md` accurate for the release named in the arguments: `$ARGUMENTS`. The source
code is the source of truth. Everything the file says exists must be true of the code at `HEAD`.

## 1. Check your model

This skill must run as `claude-opus-5-5`. Your system prompt states your exact model ID. If it isn't
exactly `claude-opus-5-5`, stop now, change no files, and reply only with:

`MODEL_MISMATCH: running as <your model ID>, but this skill requires claude-opus-5-5.`

If no release was given in the arguments, stop, change no files, and reply only with
`MISSING_RELEASE: pass the release, for example v0.1.0.`

## 2. Choose the mode

Run `git rev-parse --short HEAD` to get the current commit. Then read `ARCHITECTURE.md` if it exists.
Its last line, after a horizontal rule, is the generation line:

`Generated from commit <commit> by <model ID>, for release <release>.`

- **Create:** the file doesn't exist. Write it from the source code.
- **Update:** the file exists and its generation line names `claude-opus-5-5`. Choose the starting
  point, then revise the sections the changes since it affect.

  1. Run `git rev-parse --verify --quiet '<recorded release>^{commit}'`. If it prints a commit, the
     release tag is the starting point, even if the recorded commit also exists.
  2. Otherwise, run `git rev-parse --verify --quiet '<recorded commit>^{commit}'`. If it prints a
     commit, the recorded commit is the starting point.
  3. Otherwise, there's no starting point. This happens when the release was never tagged and the
     recorded commit was lost, for example after a squash merge and branch deletion. Don't treat it
     as an error or as a model switch: keep the existing text as the base, check every section
     against the code in step 6, and keep the key decisions under the rules in step 5.

  With a starting point, run `git diff --stat <starting point>..HEAD` and
  `git log --oneline <starting point>..HEAD` to find what changed.
- **Model switch:** the file exists and its generation line names a different model, or it has no
  readable generation line. Regenerate every section except Key decisions from the source code, ignoring the old text.
  At the end, list what changed in meaning compared with the previous file, so the owner can review
  it in detail.

In every mode, finish with the verification in step 6. Following only the changes would let an old
mistake survive.

## 3. Read the code

Read what you need to describe the system accurately:

- The Python modules at the repository root, and `scripts/`.
- Configuration and data definitions: `corpus.json`, `ingest_config.json`, `query_config.json`,
  `requirements.txt`, `requirements-dev.txt` and `pytest.ini`.
- `.github/workflows/`, for how changes are checked.
- `README.md`, only to see which roadmap steps are planned, so that you don't describe them.
- `openspec/changes/archive/*/design.md`, only for the reasons behind key decisions. When a design
  and the code disagree, the code wins.

Tests show intended behavior, and can help you confirm what the code does, but the file describes
the code, not the tests.

## 4. Write the file in this structure

```
# Architecture

## Overview
## Workflows
## Public interfaces
## Internal interfaces
## Key decisions

---

Generated from commit <commit> by claude-opus-5-5, for release <release>.
```

The generation line goes last because it's for maintainers, and readers don't need it.

- **Overview:** what the system does and its main parts, in a few paragraphs, with a Mermaid diagram
  of the components and how data moves between them.
- **Workflows:** one subsection per workflow the code implements, such as building the index and
  answering a question. Each has a Mermaid diagram (`flowchart` or `sequenceDiagram`) and a short
  explanation of each step, naming the functions involved.
- **Public interfaces:** what outside users and callers rely on: the query API and its response
  types, the command lines and their arguments, and the configuration and data files with their
  fields.
- **Internal interfaces:** the functions, classes and data types without a leading underscore that
  connect one module to another, grouped by module, with what each takes and returns.
- **Key decisions:** see step 5.

Rules for every section:

- Never document a name that starts with an underscore.
- Describe only what the code implements. Don't describe roadmap steps or planned features.
- Refer to files by path, without line numbers, because line numbers go stale.
- Keep Mermaid diagrams simple enough to render on GitHub. Quote node labels that contain
  punctuation.

## 5. Key decisions

The section is a table with these columns, in this order:

`| Decision | Why | Assumption to revisit | Status | Last reviewed | Source |`

Include only decisions that would be expensive to reverse, or that rest on something that can stop
being true. Aim for 10 to 15. Take the reason from the archived design that made the decision, and
link that design in Source.

These rules protect the owner's review, so follow them exactly:

- **Keep every existing row.** Copy each one over, including `Superseded` rows, even in model switch
  mode. Don't reword them.
- **You may add a row** for a decision that isn't in the table yet. Its Status is `New` and its Last
  reviewed is `-`.
- **You may set a row to `Review needed`** when the code no longer reflects the decision, or when the
  changes since the starting point touched its assumption. Add the reason in the Status cell, for
  example `Review needed: index now stores vectors`.
- **Never set a row to `Current`, and never change Last reviewed.** Only the owner does that.
- **Don't mark a row `Superseded`.** That happens through an OpenSpec change, which the owner records.

## 6. Verify against the code

Before you finish, check every file path, module, function, class, parameter, configuration field and
command line that the file names. Use `Grep` or `Read` to confirm each one exists in the code at
`HEAD`, with the stated signature or fields. Confirm that each diagram step matches the code's order.
Fix anything that doesn't match, in any section.

## 7. Write and report

Write the result to `ARCHITECTURE.md` at the repository root, with the generation line updated to the
current commit and the release from the arguments. Don't create or change any other file.

Then reply with a short report:

- The mode you used.
- In update mode, the starting point: the release tag or the recorded commit, by name, or that no
  starting point was found, so every section was checked against the code without a diff.
- The sections you changed, and why.
- Key decisions you added or set to `Review needed`, with reasons.
- Questions for the owner: every assumption in Key decisions that can't be checked from the code,
  such as a library's features or measured values.
- In model switch mode, what changed in meaning compared with the previous file.
