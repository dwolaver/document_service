# Configuration

[Back to README](../README.md)

The commands read their settings from a configuration directory and keep generated data in a data
directory. Both have defaults, so nothing needs setting up to run the commands in
[Usage](usage.md).

## Configuration files

The default configuration ships inside the package, in [`src/rfc_qa/config/`](../src/rfc_qa/config).
The files are [TOML](https://toml.io), and a comment in each one describes every section and
setting, with its unit or allowed values and any other setting it has to agree with.
[`corpus.toml`](../src/rfc_qa/config/corpus.toml) lists the RFCs, with their family and title.
[`ingest.toml`](../src/rfc_qa/config/ingest.toml) sets the chunk size limit:

- `embedding_model` is the embedding model and its token limit, which is the hard ceiling.
- `target_chunk_tokens` is the chunk size to aim for inside that ceiling.
- `chars_per_token` is measured for this corpus with this model's tokenizer, so measure it again
  if either one changes.

The maximum chunk size in characters is `target_chunk_tokens` x `chars_per_token`. The index
records the configuration that built it.

## Query settings

[`query.toml`](../src/rfc_qa/config/query.toml) sets the model, the Ollama address, the context
window, the answer length limit, the request timeout and how many passages to retrieve. A query fails
before calling the model if those passages and the answer wouldn't fit in the context window. The
index location isn't a setting: it's always `index.db` in the data directory.

When the `OLLAMA_BASE_URL` environment variable is set and not empty, it replaces the Ollama address
from `query.toml`, for example to reach Ollama in another container. The file must still give an
address of its own. If Ollama can't be reached, the error names the address that was tried, which
shows when a leftover variable is redirecting queries.

```
OLLAMA_BASE_URL=http://ollama:11434 rfc-query "What does a 404 status code mean?"
```

## Choosing the configuration directory

To read the configuration from another directory, such as a mounted folder in a container, name it
with `--config-dir` or the `RFC_QA_CONFIG_DIR` environment variable. The flag wins over the
variable, and both win over the packaged defaults. A relative path resolves from the working
directory, and an empty variable counts as unset. A selected directory has to hold every file the
command reads: a missing file is an error, and the packaged copy isn't used instead. `--corpus` and
`--config` name a single manifest or ingestion configuration file instead, and take precedence over
the directory for that file.

In an editable install, the packaged defaults are the files in `src/rfc_qa/config/`, so edit them
there. After a regular install they're inside the installed package, which shouldn't be edited. Copy
them into a directory of your own and select it:

```
cp -r "$(python -c 'from importlib.resources import files; print(files("rfc_qa") / "config")')" my-config
rfc-ingest --config-dir my-config
```

```
RFC_QA_CONFIG_DIR=/srv/rfc-qa/config rfc-ingest
rfc-ingest --config-dir staging --corpus small-corpus.toml
```

A configuration directory that doesn't exist stops the run before anything is downloaded, with a
message naming the directory and whether it came from the flag or the variable.

## Choosing the data directory

Generated data goes in one data directory: the downloaded RFCs in its `rfcs/` folder and the index in
`index.db`. To put it somewhere else, such as a mounted volume, name the directory with `--data-dir`
or the `RFC_QA_DATA_DIR` environment variable. The precedence is the same as for configuration: the
flag, then the variable, then the [user data directory](usage.md#building-the-index). `rfc-ingest`
creates the directory if it doesn't exist. `rfc-query` and `rfc-search` choose their data directory
the same way, so they read the index that `rfc-ingest` built there.

```
RFC_QA_DATA_DIR=/srv/rfc-qa/data rfc-ingest
rfc-ingest --data-dir scratch
```

A data directory without an index gives the index error, which names the index path and says to run
`rfc-ingest`.
