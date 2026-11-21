# Design

## Context

ruff is pinned at 0.17.6. `select` is `E4, E7, E9, F, I, B, UP, LOG, G`, and the line length is
110. I ran each candidate group against `src`, `scripts` and `tests` to count its findings:

| Group | Findings | What they are |
| --- | --- | --- |
| `E501` | 1 | `answer_generator.SYSTEM_PROMPT`, a 122-character line inside a triple-quoted string |
| `SIM` | 6 | five `open(...).read()` in tests (`SIM115`), one `assert 0 < x` (`SIM300`) |
| `RUF` | 15 | ten unescaped `pytest.raises` patterns (`RUF043`); two `int(round(...))` (`RUF046`); two mutable class attributes on test fakes (`RUF012`); one list concatenation (`RUF005`) |
| `PERF` | 1 | a loop in `scripts/update_architecture.py` that appends to a list (`PERF401`) |
| `PT` | 34 | 16 parametrize names written as one string (`PT006`); 14 `assert a and b` (`PT018`); two parametrize values written as tuples (`PT007`); one fixture whose leading `_` says its value is unused, when a test uses it (`PT019`); one `pytest.raises` block holding a `try` statement (`PT012`) |

That's 57 findings in all. The user chose `E501`, `SIM`, `RUF` and `PERF` first, then asked for
`PT` as well.

## Goals / Non-Goals

**Goals:**

- Lint fails on long strings and comments, simplifiable code, ruff's own checks, list-building
  loops and departures from pytest's conventions.
- Every current finding is fixed, with no `noqa` and no per-file ignore.
- The prompt, the messages and the command output don't change.

**Non-Goals:** the other groups. Each was run and left out, for these reasons:

- **`PTH` (pathlib, 118 findings):** a rewrite of working `os.path` code, with no bug found.
- **`S` (bandit, 650 findings):** nearly all are `assert` in tests. The rest flag the release
  script's `subprocess` calls, which take fixed arguments.
- **`D` (docstrings, 388 findings):** docstring style the project doesn't follow.
- **`PL` (pylint):** mostly "magic values" in test assertions.
- **`ARG`:** test fakes keep the real function's arguments on purpose.
- **`TRY003` and `EM`:** these would forbid building the error message at the `raise`, which the
  error-handling spec requires ("a message ready to show").
- **`T20`:** the commands print by design. Library printing is already caught by the `ast` test.
- **`INP`:** it asks for `__init__.py` files in `tests/`, which work as a namespace package today.
  Whether to add them is a separate decision.
- **`FBT` and `TC`:** they reshape signatures and imports with no bug behind them.
- **No-finding groups:** groups with no findings today (`W`, `C4`, `PIE`, `RET`, `ISC`, `A`, `N`,
  `BLE`, `ERA`, `FURB`, `TID`) were offered as "no-cost guards", and the user didn't choose them
  this time. They can be added later without changing any code.

## Decisions

### Select the whole groups

`pyproject.toml` adds `"E501", "SIM", "RUF", "PERF", "PT"` to `select`, and extends the comment with
a line for each. `E501` is added on its own, rather than all of `E5`, because it's the only rule in
that family. ruff is pinned, so a group only gains rules when the pin is bumped, and that's its own
change, as for `UP`.

### Fix each finding where it is

- **`RUF043`:** each pattern becomes a raw string, and a literal `.` in a file name is escaped:
  - `r"Rejected, and ARCHITECTURE\.md was restored"`;
  - `r"files other than ARCHITECTURE\.md.*module\.py"`;
  - `r"notes\.txt"`;
  - `r"module\.py"`.

  The `^…$` downloader and ingestion patterns only need the `r` prefix, because their text has no
  other metacharacter. Each changed test is run before and after, and checked to still fail when its
  message changes.
- **`SIM115`:** `open(path).read()` becomes `pathlib.Path(path).read_bytes()` or `.read_text()`,
  which closes the file.
- **`SIM300`:** `assert 0 < config.max_chunk_chars` becomes `assert config.max_chunk_chars > 0`.
- **`RUF046`:** `int(round(x))` becomes `round(x)`. `round` with no `ndigits` already returns an
  `int`, and mypy agrees.
- **`RUF012`:** the test fakes' class attributes, such as `calls = []` on `Setup` and
  `requests = []` on `Model`, are annotated `ClassVar[list[…]]`. They're shared on purpose and reset
  by their fixtures, so the annotation states what the code already does.
- **`RUF005`:** `PAGINATED_LAYOUTS + ["unpaginated"]` becomes `[*PAGINATED_LAYOUTS, "unpaginated"]`.
- **`PERF401`:** `_other_changes` returns a list comprehension instead of appending in a loop.
- **`PT006` and `PT007`:** parametrize names become a tuple, such as `("use_env", "source")`, and
  their values a list. ruff makes these edits itself with `--fix --unsafe-fixes --select PT006,PT007`.
  They're marked unsafe only because ruff can't know the test's intent, and the tests' results show
  nothing changed.
- **`PT018`:** each `assert a and b` becomes two `assert` statements, so a failure names the part
  that failed. The checks don't change.
- **`PT019`:** the autouse fixture `_isolated_default_data_dir` in `tests/conftest.py` is renamed
  `isolated_default_data_dir`. Its leading `_` follows the pytest convention for a fixture whose
  value isn't used, but `test_tests_use_a_temporary_default_data_directory` reads its value, so the
  name is what's wrong. It stays autouse.
- **`PT012`:** in `test_one_kind_is_not_caught_by_another`, the `try` statement moves into a small
  nested function, and the `pytest.raises` block calls it. The test still shows that an
  `except IndexUnavailableError` doesn't catch a `ConfigError`.
- **`E501`:** the long line in `SYSTEM_PROMPT` is split with a backslash at the end of the first
  part. Inside a non-raw triple-quoted string, a backslash before the newline joins the two lines, so
  the prompt text stays character for character the same. A one-off comparison with `main`'s
  `SYSTEM_PROMPT` confirms the text is equal, because the prompt tests only check parts of it.

Alternative for the prompt: a `# noqa: E501`. It's simpler, but this change adds no suppressions,
and the next edit to the prompt would hide behind it.

### Show that nothing else changed

- `pytest`, with and without the install tests, and `pre-commit`.
- The one-off `SYSTEM_PROMPT` comparison.
- `ruff check` passes with the new groups. A temporary long comment and a temporary
  `open(...).read()` each fail it.
- A working `rfc-search` and an error case from `/tmp`, compared with `main`.

## Risks / Trade-offs

- **`RUF` is broad, and some of its rules are preview-only or opinionated** → Only stable rules
  run, because preview isn't enabled. The pin stops new ones appearing until a deliberate bump.
- **`E501` makes long URLs or data hard to write** → The only long data is in TOML, which ruff
  doesn't check. If a long line is ever unavoidable in Python, a `noqa` with its reason can be
  decided then.
- **A pattern that becomes raw changes what it matches** → In a raw string, `\.` is a regex escape,
  and in a normal string the `\` would be an invalid string escape. The patterns gain escapes only
  where a `.` was meant literally, so each matches the same messages or fewer, never more.
