# Tasks

Modules move leaf-first, using `git mv`. After each group, the root modules that haven't moved yet
import the moved ones from `rfc_qa`, and `python -m pytest` passes in full with no new skips.

## 1. Package scaffolding

- [x] 1.1 Add `pyproject.toml` as in design.md, without `[project.scripts]` yet (it comes in group 6, once the targets exist), and add empty `rfc_qa/__init__.py`, `rfc_qa/ingestion/__init__.py`, `rfc_qa/retrieval/__init__.py` and `rfc_qa/generation/__init__.py`; verify `pip install -e .` succeeds in the project venv and `python -c "import rfc_qa.ingestion, rfc_qa.retrieval, rfc_qa.generation"` works from another directory
- [x] 1.2 Add `-e .` to `requirements-dev.txt`; verify `pip install -r requirements-dev.txt` installs `rfc-qa` in editable mode (`pip show rfc-qa`)
- [x] 1.3 Add `rfc_qa/paths.py` with `REPO_ROOT` and the default locations (`CORPUS_PATH`, `INGEST_CONFIG_PATH`, `QUERY_CONFIG_PATH`, `DATA_DIR`, `INDEX_PATH`), and a docstring saying only editable installs are supported; verify `REPO_ROOT` equals the checkout path when imported from another directory

## 2. Shared chunk type and retrieval

- [x] 2.1 Move `Chunk` from `chunker.py` into a new `rfc_qa/chunk.py`, make `chunker.py` import it from there, and update every importer (`keyword_index.py`, `tests/test_chunker.py`, `tests/test_keyword_index.py`, `tests/test_answer_generator.py`, `tests/test_query.py`); verify `grep -rn "from chunker import Chunk"` finds nothing and the suite passes
- [x] 2.2 `git mv keyword_index.py rfc_qa/retrieval/keyword_index.py`, take `DEFAULT_INDEX_PATH` from `rfc_qa.paths`, and change the missing-index message to say to run `rfc-ingest`; update the imports in `ingest.py`, `query.py`, `tests/test_keyword_index.py`, `tests/test_ingest.py` and `tests/test_query.py`; verify the suite passes and a test asserts the message names `rfc-ingest`

## 3. Generation

- [x] 3.1 `git mv answer_generator.py rfc_qa/generation/answer_generator.py` and update the imports and monkeypatch targets in `query.py`, `tests/test_answer_generator.py` and `tests/test_query.py`; verify the suite passes, including `test_module_has_no_way_to_pull_or_start_ollama` reading the moved file

## 4. Ingestion

- [x] 4.1 `git mv` `rfc_downloader.py`, `rfc_parser.py` and `chunker.py` into `rfc_qa/ingestion/`, and update their imports and those in `ingest.py`, `tests/test_rfc_downloader.py`, `tests/test_rfc_parser.py` and `tests/test_chunker.py`, including the `rfc_downloader.requests` and `rfc_downloader.os` patch targets; verify the suite passes
- [x] 4.2 `git mv ingest.py rfc_qa/ingestion/ingest.py`, take its `DEFAULT_*` paths from `rfc_qa.paths`, and update `tests/test_ingest.py`, including the `download_rfc` patch target; verify the suite passes and `python -m rfc_qa.ingestion.ingest --help` shows defaults under the repository root

## 5. Query interface

- [x] 5.1 `git mv query.py rfc_qa/query.py`, take `CONFIG_PATH` and the root for relative `index_path` from `rfc_qa.paths`, and change the unreadable-index message to name `rfc-ingest`; verify `python -m rfc_qa.query --help` works from the repository root
- [x] 5.2 Update `tests/test_query.py`: imports, the `query`/`generate_answer`/`CONFIG_PATH` patch targets, the repository-root assertions (use `rfc_qa.paths.REPO_ROOT`, not `dirname(query.__file__)`), and `test_missing_index` asserting `rfc-ingest`; add a test that a relative `index_path` resolves from the repository root while the working directory is elsewhere (`monkeypatch.chdir(tmp_path)`); verify the suite passes

## 6. Commands, packaging check and documentation

- [x] 6.1 Add `[project.scripts]` for `rfc-ingest`, `rfc-query` and `rfc-search` to `pyproject.toml` and reinstall; verify each `--help` runs from a directory outside the checkout
- [x] 6.2 Add `tests/test_packaging.py`: the `rfc-qa` console-script entry points are exactly the three commands and each loads to a callable (skipped with a reason when the distribution isn't installed); every `.py` file at the repository root is listed in an allow-list that is empty today; the subpackages import from `rfc_qa.ingestion`, `rfc_qa.retrieval` and `rfc_qa.generation`; verify the tests pass, and that pointing an entry point at a missing function makes them fail (revert afterward)
- [x] 6.3 With the local index built, run `rfc-search "three-way handshake"` from a directory outside the checkout, and `rfc-query` with a question if Ollama is running; verify they read `query_config.json` and `data/index.db` from the repository root and print the same output as the old commands
- [x] 6.4 Update `README.md`: the setup steps (`pip install -r requirements-dev.txt` now installs the commands), the commands under "Building the index", searching and querying, the release-script note, and the reason for `python -m pytest` (replace the "modules sit at the repository root" explanation); also check the "Two entry points" paragraph still reads correctly; verify every command in the README runs as written
- [x] 6.5 Update step 3 of `.claude/skills/update-architecture/SKILL.md` to read the `rfc_qa` package and `pyproject.toml` instead of "the Python modules at the repository root"; verify no other line in the skill assumes root modules

## 7. Integration check

- [x] 7.1 In a fresh Python 3.14 venv in the scratch directory, run `pip install -r requirements-dev.txt` and `python -m pytest` from the checkout, as CI does; verify all tests pass with only the existing gated skips, and that `test_packaging.py` runs rather than skips
- [x] 7.2 Verify `git log --follow` shows the pre-move history for each moved module, `grep -rnE "^(from|import) (chunker|rfc_parser|rfc_downloader|keyword_index|answer_generator|ingest|query)\b"` finds no bare-name imports, and `ARCHITECTURE.md` is unchanged

## Workflow follow-up

- Open a pull request from `adopt-package-layout`. The `test` check must pass, and `archive-check` is expected to fail until the archive. The description tells developers to rerun `pip install -r requirements-dev.txt` to get the commands.
- The repository owner reviews the code while CI runs on the pull request. Any changes are made on this branch, in the active change, before the archive, and `test` must pass again.
- Archive the change on this branch as the last step, which makes the change complete and turns `archive-check` green.
- The repository owner merges once CI still passes, so that the code, spec and archive land as one commit on `main`.
