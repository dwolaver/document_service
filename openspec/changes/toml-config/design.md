# Design

## Context

- **Readers:** the three files are read in two places.
  - `ingest._load_json` reads the manifest and the ingestion configuration.
  - `query.load_query_config` reads the query configuration.

  Both open a `paths.ConfigFile`, which is a path string or a packaged `Traversable`, and parse it
  with `json.load`. Both raise `ConfigError("Failed to read '…': …")` for an `OSError` or a parse
  error, and "Config '…' must be a JSON object." for a top-level value that isn't an object.
- **Validation:** every other rule checks the parsed values: types, ranges, families, duplicates.
  It reports a missing key and a `null` value the same way, because both reach it as `None`
  through `.get()`.
- **Packaging:** `pyproject.toml` ships `config/*.json` as package data. The install test checks the
  wheel's contents and reads the packaged corpus.
- **Parser:** Python 3.14's `tomllib` reads TOML 1.0, from binary files only. It has no writer.
- **Layout of `ingest.json`:** two top-level settings and one table (`embedding_model`). In TOML,
  top-level keys have to come before the first `[table]`.
- **Corpus order:** `corpus.json` is already grouped by family: 24 HTTP RFCs, then 17 TLS, then 18
  TCP.

## Goals / Non-Goals

**Goals:**

- The settings and values are the same, read from TOML.
- Every setting explains itself in the file.
- A malformed file is reported with its location.

**Non-Goals:**

- **No renamed or regrouped settings:** they keep their names and sections. The query config's
  `[retrieval]` and `[llm]`, and the ingestion config's `[embedding_model]`, stay as they are.
- **No JSON fallback,** and no conversion tool. The project isn't deployed.
- **No schema files** or schema validation library. The existing validation in code stays.
- **No writer:** the library doesn't write TOML, so it doesn't need `tomli-w`.
- **`ARCHITECTURE.md`** is regenerated at the next release.

## Decisions

### One reader for every configuration file

`paths.py` gains `read_toml(file: ConfigFile) -> dict[str, Any]`. It opens the file with
`as_traversable(file).open("rb")` and returns `tomllib.load(...)`. It turns an `OSError` or
`tomllib.TOMLDecodeError` into `ConfigError(f"Failed to read {str(file)!r}: {exc}") from exc`.

`tomllib`'s message ends with the location, for example `Invalid value (at line 1, column 5)`, so
the error names the file, the line and the column. `ingest._load_json` and the inline read in
`load_query_config` are replaced by this one function. The "must be a JSON object" checks are
removed, because a TOML document is always a table.

A JSON file fails to parse as TOML (`{` can't start a statement), so it's reported the same way
with no special case.

Alternative: keep a reader in each module. The two would stay identical, as they are now, and
`paths` already owns `ConfigFile`.

### File layout and comments

The files are laid out to be read by a person, with the same look in all three:

- **Banners:** a framed banner opens each file, saying what it configures, which command reads it,
  and that every number must be positive. A ruled banner opens each table and says what it covers.
- **Blank lines:** settings that belong together sit in a group, with blank lines around it.
- **Short comments to the right:** each setting's `=` and value line up within its group, and a
  short comment at the end of the line gives its meaning, unit or allowed values. A comment that
  runs onto a second line is indented under the first.
- **Worked examples:** where settings depend on each other, a comment block after the group shows
  the arithmetic with the packaged values. These are the context-window budget in `query.toml` and
  the longest chunk in `ingest.toml`.
- **The corpus as a table:** the corpus lists one RFC per line, as the user chose. Its numbers are
  right-aligned and its families padded, so the titles start in one column, with a ruled divider for
  each family. The three fields of an entry are described once, in the file's banner.

TOML allows spaces around `=` and inside inline tables, and comments at the end of a line, so none
of this changes the parsed values. The user asked for this layout after reviewing a first version
that put every comment on its own line above the setting.

`query.toml`:

```toml
# ==================================================================================================
#  Query settings
# ==================================================================================================
#
#  Read by rfc-query and by rfc_qa.query.query(). Every number must be positive.
#
#  The index isn't set here: it's always index.db in the data directory.


# --------------------------------------------------------------------------------------------------
#  [retrieval]   How passages are found in the index for each question
# --------------------------------------------------------------------------------------------------
[retrieval]

limit = 5   # passages sent to the model, an integer (they must fit in llm.num_ctx, see below)


# --------------------------------------------------------------------------------------------------
#  [llm]   The local Ollama model that answers from the passages
# --------------------------------------------------------------------------------------------------
[llm]

model    = "llama3.2"                 # Ollama model name. Install it with `ollama pull llama3.2`
base_url = "http://localhost:11434"   # Ollama's address. OLLAMA_BASE_URL replaces it when set,
                                      # but this value is still required

num_ctx           = 8192   # the model's context window, in tokens (an integer)
max_answer_tokens = 512    # the most tokens the answer may use (an integer)
timeout_seconds   = 120    # how long to wait for Ollama to respond, in seconds

#  The context window has to hold the passages, the prompt and the answer:
#
#      retrieval.limit  x  target_chunk_tokens  +  prompt  +  max_answer_tokens   <=  num_ctx
#            5          x         1100          +   512    +        512           =   6524 <= 8192
#
#  target_chunk_tokens comes from the index, which records the value in ingest.toml when it's
#  built. A query that doesn't fit fails before calling the model.
```

`ingest.toml`:

```toml
# ==================================================================================================
#  Ingestion settings: how the RFCs are cut into chunks
# ==================================================================================================
#
#  Read by rfc-ingest. Every number must be positive. The index records these values, so a query
#  can check that its passages fit the model's context window (see query.toml).

target_chunk_tokens = 1100   # the chunk size to aim for, in tokens (an integer)
chars_per_token     = 1.6    # the average characters per token for this corpus (see below)

#  The longest chunk, in characters, is the token target times the characters per token:
#
#      target_chunk_tokens  x  chars_per_token  =  1100  x  1.6  =  1760 characters
#
#  chars_per_token was measured on this corpus with the embedding model's tokenizer. Measure it
#  again if the corpus or the model changes.


# --------------------------------------------------------------------------------------------------
#  [embedding_model]   The model that chunks are sized for
# --------------------------------------------------------------------------------------------------
[embedding_model]

name       = "nomic-embed-text"   # the model's name, recorded in the index
max_tokens = 2048                 # the most tokens it accepts: target_chunk_tokens can't exceed it
```

`corpus.toml`, opening lines:

```toml
# ==================================================================================================
#  Corpus: the RFCs that rfc-ingest downloads and indexes
# ==================================================================================================
#
#  Every RFC listed here must download and produce chunks, or the run fails and the index is left
#  as it was. Each entry has three fields, and each RFC is listed once:
#
#      number   the RFC number, a positive integer
#      family   the protocol family: "http", "tls" or "tcp"
#      title    the RFC's title, shown in citations
#
#  Obsolete RFCs are listed on purpose, together with the RFCs that replaced them, so that retrieval
#  can be measured against real version conflicts.

# The RFCs, grouped by family.
rfcs = [
    # ------------------------------------------------------------------------------------------------
    #  HTTP
    # ------------------------------------------------------------------------------------------------
    { number = 9110, family = "http", title = "HTTP Semantics" },
    { number = 9111, family = "http", title = "HTTP Caching" },
    { number = 9112, family = "http", title = "HTTP/1.1" },
    { number = 9113, family = "http", title = "HTTP/2" },
    ...
]
```

The comments repeat only what the validation enforces and what the README says. The worked budget in
`query.toml` uses `PROMPT_ALLOWANCE_TOKENS`, shown as "prompt 512", the number the error message
already gives. The obsolete-RFC note reflects the existing requirement "Include obsolete RFCs in the
corpus".

Each converted file is checked against the JSON it replaces. Before the JSON files are removed, a
one-off comparison loads both and asserts the parsed values are equal.

### A test that every setting has a comment

`tests/test_packaging.py` reads each packaged file line by line, because `tomllib` discards comments.
The rules are:

- **The file** must start with a comment.
- **A table header** (`[name]`) must have a comment on the line directly above it.
- **A setting** (`key = …`) must have a comment at the end of its own line. A comment block above
  isn't enough, because one that explains something else, such as the worked budget, would hide a
  setting added below it without a comment.
- **A setting that opens a multi-line array** (`rfcs = [`) must have a comment on the line above
  instead. The entries inside the array are exempt.
- **The corpus** banner must describe `number`, `family` and `title`, each on a line that starts
  with the field's name.

The test checks its own rules on small examples, including a setting placed under an unrelated
comment block.

The packaged files are loaded and validated by the existing "real config loads" tests, under the new
names.

### Tests write TOML through a helper

`tests/conftest.py` gains `write_toml(path, data) -> str` for the dictionaries the tests build. It
writes each top-level key as `key = <inline value>`, using inline tables for nested dictionaries
(`embedding_model = { name = "x", max_tokens = 2048 }`). That's valid TOML and parses to the same
dictionary. It handles strings, booleans, integers, floats, lists and dictionaries. Strings are
written with `json.dumps`, which gives a valid TOML basic string for the test values.

A `None` value is left out, because TOML has no null. The validation reports a missing key and a
`None` the same way, so those tests keep their expected messages. The one case TOML can't express
at all, a manifest whose top level is a list (`[]`), is dropped from
`test_malformed_manifest_is_rejected`.

Alternative: add `tomli-w` as a development dependency. It's a new pin for about 20 lines of test
code.

### File moves

The files are moved with `git mv corpus.json corpus.toml` (and likewise for the others) before
their contents are rewritten. Git may still show a delete and an add, because most lines change.
`paths.CORPUS_FILE`, `INGEST_CONFIG_FILE` and `QUERY_CONFIG_FILE` change their extensions, and
every other use goes through these constants. The one exception is the install test, which names
the files itself.

## Risks / Trade-offs

- **A value changes in the conversion,** such as `1.6` becoming a string, or an RFC dropped →
  Before the JSON is deleted, a one-off comparison checks that the loaded TOML equals the loaded
  JSON. The tests that load the real config, and the install test, run as before.
- **Someone's own JSON copy stops working** → The project isn't deployed, and the error names the
  file. The README describes only the TOML files, as the user asked, so it doesn't explain the
  change from JSON. The pull request does.
- **The comments drift from the code over time** → The comment test catches a setting added without
  a comment. It can't check that the wording is right. Review covers that, and the comments are
  kept to what validation enforces.
- **TOML 1.0 inline tables have to stay on one line**, so 13 of the 59 corpus entries are longer
  than 110 characters. The longest is RFC 6125's, at 249. → `corpus.json` has the same long lines
  today. The 110-character limit applies to Python code, and ruff only checks `*.py`. If an entry is
  split by mistake, the TOML parser rejects it and names the line.
