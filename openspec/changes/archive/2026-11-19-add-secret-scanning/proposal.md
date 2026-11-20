# Proposal

## Why

The repository is public, and nothing stops a credential from being committed. The code doesn't need
any secrets today, but the roadmap's cloud deployment will bring API keys and tokens. A secret pushed
to a public repository has to be treated as leaked, even if a later commit deletes it, because the
earlier commit is still visible on GitHub. Checking before the commit, and again on every pull
request, catches a secret while it can still be removed from the history.

## What Changes

- A **gitleaks** pre-commit hook scans the staged changes before each commit, and stops the commit
  when it finds a secret. The hook comes from the gitleaks repository, pinned to a release tag in
  `.pre-commit-config.yaml`. pre-commit builds it on first use, so developers install nothing
  themselves.
- A new **`secrets`** check in CI scans every commit a pull request adds, and every commit pushed to
  `main`. A secret committed and then deleted in a later commit of the same pull request still fails
  the check. The check uses the same gitleaks version as the hook.
- Reports redact the secret's value, because CI logs on a public repository are public.
- The repository's existing history is scanned once while this change is applied, so the project
  starts from a known-clean history.
- The README describes the hook and what to do when it finds a real secret, which is to rotate it, not
  only delete it.

Out of scope: scanning on a schedule, GitHub's own secret scanning and push protection (repository
settings, not code), and custom detection rules.

## Capabilities

### New Capabilities
- `secret-scanning`: Detecting committed secrets before a commit and in every pull request, how
  findings are reported, and how a reviewed false positive is accepted.

### Modified Capabilities
- `continuous-integration`: The automated checks include a separate, required secret scan of each
  pull request's commits.

## Impact

- `.pre-commit-config.yaml`: a gitleaks hook from `https://github.com/gitleaks/gitleaks`, at `v8.30.1`.
- `.github/workflows/ci.yml`: a `secrets` job. The `quality` job skips the gitleaks hook, which has
  nothing to scan when no files are staged. The repository owner adds `secrets` to the required checks
  for `main`.
- `README.md`: the "Development" section.
- Possibly `.gitleaksignore`, only if the history scan finds a false positive.
- No Python code or runtime dependencies change.
