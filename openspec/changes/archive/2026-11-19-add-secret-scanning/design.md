# Design

## Context

`.pre-commit-config.yaml` has three `repo: local` hooks (`ruff-check`, `ruff-format`, `mypy`) that
run tools pinned in `requirements-dev.txt`. `.github/workflows/ci.yml` has two jobs, `test` and
`quality`, both with `contents: read`. `quality` runs `pre-commit run --all-files`. The `main` ruleset
requires `test`, `quality` and `archive-check`. Pull requests are squash-merged.

gitleaks is a Go program, so it can't be pinned in `requirements-dev.txt` like the Python tools. The
latest release is v8.30.1. The gitleaks repository publishes pre-commit hooks:

- `gitleaks`: `language: golang`, `gitleaks git --pre-commit --redact --staged --verbose`
- `gitleaks-docker` and `gitleaks-system`, with the same command.

Neither gitleaks nor Go is installed on the development machine. The repository is owned by a personal
account and is public.

## Goals / Non-Goals

**Goals:**
- One gitleaks version, set in one place, used by the hook and by CI.
- A CI scan of every commit in a pull request, not only the final tree.
- No secret values in public CI logs.

**Non-Goals:**
- Rewriting history. If the history scan finds a real secret, the change stops for the owner to decide,
  because rotating a credential and rewriting a public history can't be done by the change itself.

## Decisions

### The hook comes from the gitleaks repository

```yaml
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.30.1
    hooks:
      - id: gitleaks
```

pre-commit builds the hook with Go on first use, and downloads a Go toolchain itself when none is
installed. The build took 11 seconds when measured, once, and is then cached. The hook scans only the staged
changes, with the secret value redacted.

Alternatives: the `gitleaks-system` hook, which needs each developer to install gitleaks and lets
versions drift; and `gitleaks-docker`, which needs Docker running for every commit. Both were rejected
by the repository owner.

This hook is pinned in `.pre-commit-config.yaml` rather than `requirements-dev.txt`. That's the only
place a Go tool can be pinned, and the code-quality requirement about one pinned version covers the
Python tools only.

### CI runs the gitleaks release named by the hook

A `secrets` job in `ci.yml`:

1. Checks out with `fetch-depth: 0`, so the commits being scanned are present.
2. Reads the `rev` of the gitleaks hook from `.pre-commit-config.yaml`: the `rev:` line that follows the
   gitleaks repository URL. It fails if no `rev` is found.
3. Downloads that release's `linux_x64` archive and `checksums.txt` from GitHub, and checks the
   archive with `sha256sum --check`.
4. Runs `gitleaks git --redact --verbose --log-opts="<range>"`:
   - on a pull request: `BASE_SHA..HEAD_SHA`, the pull request's own commits;
   - on a push to `main`: `before..after` for the push, or the full history when `before` is all
     zeros (a new branch).

Reading the version from the hook configuration keeps one version for both. A pull request that bumps
the hook's `rev` changes CI in the same commit.

Alternative: `gitleaks/gitleaks-action@v3`. Rejected for three reasons:
- its license is no longer MIT;
- it comments on pull requests, which needs `pull-requests: write`, and the checks are kept read-only;
- it runs its own built-in gitleaks version unless one is configured separately, which would be a
  second place to pin it.

Alternative: run the gitleaks hook in the `quality` job. Rejected because the hook scans staged changes
only, so in CI it has nothing to scan, and a file scan would miss a secret added and then deleted
within a pull request.

### `quality` skips the gitleaks hook

`quality` sets `SKIP: gitleaks` for `pre-commit run --all-files`. With nothing staged, the hook would
pass without scanning anything, after building gitleaks.

### False positives go in `.gitleaksignore`

gitleaks reads `.gitleaksignore` at the repository root, with one finding fingerprint per line
(`commit:file:rule:line`). It's created only if a reviewed finding isn't a secret. A `.gitleaks.toml`
with custom rules is out of scope.

### The history scan happens first

Before any configuration changes, `gitleaks git --redact` scans all of the repository's history,
using the built hook binary. A finding stops the apply until it's reviewed. A false positive is
recorded in `.gitleaksignore`. A real secret is reported to the owner.

## Risks / Trade-offs

- [The first commit after installing the hook pauses for a few seconds while pre-commit builds
  gitleaks] → It happens once per machine. The README says so.
- [The hook needs network access the first time, to fetch gitleaks and Go] → It's cached afterwards.
  CI scans every pull request either way.
- [A hand-written download step in CI] → The archive is checked against the release's published
  checksums, and the step fails if the version can't be read.
- [gitleaks can't detect every kind of secret] → It catches the common credential formats. The
  README asks contributors to rotate any secret that reaches a commit, whether or not it was caught.

## Migration Plan

All in one pull request. After it merges, each developer runs `pre-commit install` again only if
they never did. The new hook is picked up from the configuration. The owner adds `secrets` to the
required checks once it has run on the pull request. To roll back, revert the commit and remove the
required check.
