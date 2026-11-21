# Proposal

## Why

The three configuration files, `corpus.json`, `ingest.json` and `query.json`, are JSON, which has no
comments. So nothing in a file says what a setting means, what values it takes or how settings
depend on each other. For example, `chars_per_token` and `target_chunk_tokens` together set the
chunk size, and `num_ctx` has to fit the retrieved passages plus the answer. Someone editing a copy
for `--config-dir` has to find that in the README or the code. TOML is Python's standard format for
configuration. It allows comments, and Python 3.11 and later read it with `tomllib`, so no
dependency is needed.

## What Changes

- **BREAKING:** the packaged configuration files become `corpus.toml`, `ingest.toml` and
  `query.toml`, in TOML. The settings, their names and their sections stay the same. The JSON files
  are removed, and JSON is no longer read. A configuration directory or a `--corpus` or `--config`
  file has to be TOML. The project isn't deployed, so existing copies are converted by hand. The
  README says how.
- Each file is commented:
  - **Headers:** the file opens with what it configures and which command reads it.
  - **Sections:** each section opens with what it covers.
  - **Settings:** each setting has a short comment at the end of its line, with its meaning, its
    unit or allowed values, and any limit it has to respect. Values are aligned in groups separated
    by blank lines. Settings that depend on each other get a worked example with the packaged values.
- **Corpus layout:** `corpus.toml` keeps one line per RFC, as an array of inline tables, with
  aligned columns and a ruled divider for each family. The fields of an entry (`number`, `family`,
  `title`) are described once, in the file's banner.
- **Errors:** a file that isn't valid TOML raises `ConfigError`, naming the file and the line and
  column of the problem, as `tomllib` reports them. The current "must be a JSON object" check goes
  away, because a TOML document is always a table. Every other validation rule and message stays.
- **Comment check:** a test checks that every section and setting in the packaged files has a
  comment, so the comments don't fall behind the settings.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `project-packaging`:
  - The configuration directory holds `corpus.toml`, `ingest.toml` and `query.toml`.
  - A new requirement covers the TOML format and the comments on every section and setting.
- `rfc-ingestion`: a manifest or ingestion configuration that isn't valid TOML, rather than valid
  JSON, is a configuration error.

## Impact

- Code:
  - `src/rfc_qa/paths.py` changes its three file names.
  - `ingestion/ingest.py` and `query.py` read with `tomllib`, from files opened in binary mode.
  - `pyproject.toml` changes the package-data pattern to `config/*.toml`.
- Configuration: the three packaged files are rewritten as TOML, with the same values.
- Tests:
  - The tests that write configuration files write TOML through a small helper in the tests. No
    dependency is added.
  - A value the JSON tests set to `null` is left out instead, because TOML has no null.
  - The install test reads the packaged corpus with `tomllib`.
- README: the file names, a note on converting an existing JSON copy, and the `--corpus` example.
- `ARCHITECTURE.md` still names the old files. It's regenerated before each release.
