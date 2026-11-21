# Design

## Context

There are 106 `.format()` calls, in seven package modules, `scripts/update_architecture.py` and nine
test modules. They fall into three groups:

| Group | Count | Example |
| --- | --- | --- |
| A call ruff's `UP032` rewrites, including messages split across lines | 96 | `"RFC {n}: empty response body.".format(n=rfc_number)` |
| A call `UP032` leaves alone | 5 | three in `scripts/update_architecture.py` (lines 138, 238 and 245), one in `tests/test_query.py` (377) and one in `tests/ingestion/test_ingest.py` (336) |
| A use of a template defined once and filled in later | 5 | `RFC_URL_TEMPLATE` (once), and `SKILL` in `tests/scripts/test_update_architecture.py` (four times) |

Other facts that shape the conversion:

- There's no `%` formatting, and no doubled `{{` or `}}` in any formatted literal.
- One placeholder has a format spec: `{s:.1f}` in `query._print_success`.
- Many placeholders use `!r`, which is what shows a path in quotes.
- `rfc_downloader` builds two regular expressions with `.format()`. They have no `{` quantifier to
  escape.
- The project requires Python 3.14, so f-strings can reuse the enclosing quote character and span
  lines inside the braces.
- ruff is pinned at 0.17.6, and its pyupgrade rules (`UP`) find nothing but `UP032` in the code
  today.

## Goals / Non-Goals

**Goals:**

- No `.format()` call left in `src`, `scripts` or `tests`.
- Every resulting string is the same as before, character for character.
- The lint check rejects new formatting that an f-string can replace.

**Non-Goals:**

- Rewording any message, or changing which values it shows or how they're shown.
- Other cleanups the `UP` rules don't require.
- `ARCHITECTURE.md`, which is regenerated before each release.
- Code blocks in Markdown. The project's ruff config only checks `*.py`.

## Decisions

### Let ruff convert what it can, and convert the rest by hand

`ruff check --select UP032 --fix` rewrites the first group. It keeps conversions and format specs,
and it inlines each argument at its placeholder. Its output is still reviewed, against these rules,
and the second group is converted by hand to match:

- In a message split across string literals, only the pieces that have a placeholder get the `f`
  prefix. A piece without one stays a plain string, because ruff's `F541` (already selected) reports
  an f-string with no placeholder.
- When a value is a call or a longer expression, such as `", ".join(others)` or
  `paths.default_data_dir()`, it's assigned to a local variable first if putting it inline would
  hide the message's wording. Short attribute accesses like `entry.number` go inline.
- The regular expressions in `_header_identifies_rfc` become raw f-strings (`rf"..."`).
- `ruff format` then reflows any line that has changed length.

Alternative: convert all 106 by hand. It's slower and more error-prone for the 96 that the tool
handles exactly.

### Replace the two templates with functions

`RFC_URL_TEMPLATE` becomes `_rfc_url(number: int) -> str`, which returns
`f"https://www.rfc-editor.org/rfc/rfc{number}.txt"`. The test's `SKILL` becomes a function of the
model name, which returns the same frontmatter text. Each is still defined in one place, and the
user chose this so that no `.format()` call remains.

Alternative: keep both as `.format()` templates. Filling a template defined elsewhere is the one case
an f-string can't express directly. The user preferred no exceptions.

### Select the whole `UP` group

`pyproject.toml` adds `"UP"` to `[tool.ruff.lint] select`, with a comment saying it's there for
syntax that the minimum Python version makes outdated. The user chose the whole group over `UP032`
alone. ruff takes the target version from `requires-python = ">=3.14"`, so no `target-version` is
needed.

The code-quality spec states the rule category, not the rule codes, as it does for the other checks.

### Show that the output is unchanged

The test suite already compares many messages exactly: downloader, index, ingestion, query and the
architecture script. Beyond that:

- The error scenarios from the last change are run again through the real commands, and their
  output is compared with `main`: `rfc-search` with a missing index, `rfc-query` with a missing data
  directory, `rfc-ingest` with a missing config directory and with an invalid manifest.
- A working `rfc-search` is compared with `main` too.
- `--help` for each command is compared with `main`, because the help text for `--data-dir` and
  `--config-dir` is built with `.format()`.

## Risks / Trade-offs

- [A hand-converted message changes, for example a lost `!r` or a missing space between split
  literals] → The exact-message tests, the output comparison with `main` and the diff review cover
  it. Every hand-converted call is in the tasks by location.
- [The evaluation order of arguments changes when ruff inlines them out of keyword order] → The
  arguments are names, attributes and calls with no side effects, such as `paths.default_data_dir()`,
  so their order doesn't matter.
- [A future ruff bump adds pyupgrade rules that flag code that's fine today] → ruff is pinned. A bump
  is its own change, which would fix or ignore any new finding.
- [`RFC_URL_TEMPLATE` is removed] → It's private in practice: nothing outside `rfc_downloader` uses
  it, and the project isn't deployed. `ARCHITECTURE.md` drops it at the next release.
