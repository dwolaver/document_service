# Releasing

[Back to README](../README.md)

A release updates `ARCHITECTURE.md` and the changelog, sets the version, and goes through a pull
request like any other change. The tag and the GitHub release come after the merge. The steps below
use `v0.2.0` as the example version.

## Steps

1. **Start a release branch** from an up-to-date `main`:

   ```
   git checkout main && git pull
   git checkout -b release/v0.2.0
   ```

2. **Update `ARCHITECTURE.md`**, as described in [Updating
   ARCHITECTURE.md](#updating-architecturemd) below, review its report, and commit the result:

   ```
   python scripts/update_architecture.py v0.2.0
   ```

3. **Turn `[Unreleased]` into the release** in [`CHANGELOG.md`](../CHANGELOG.md):
   - rename the `## [Unreleased]` heading to `## [0.2.0] - <today's date>`, in `YYYY-MM-DD` form;
   - add a new, empty `## [Unreleased]` above it;
   - at the bottom, point the `[Unreleased]` link at `v0.2.0...HEAD`, and add a `[0.2.0]` link
     comparing the previous tag with `v0.2.0`.

4. **Set the version** in `pyproject.toml`: `version = "0.2.0"`. The wheel name in
   [Installing](usage.md#installing) follows it.

5. **Open a pull request** from the release branch. It doesn't change an OpenSpec change, so
   `archive-check` passes, and the other checks have to pass as for any change. The owner reviews
   and merges it.

6. **Tag the merge on `main`**, after the merge:

   ```
   git checkout main && git pull
   git tag v0.2.0
   git push origin v0.2.0
   ```

7. **Publish the GitHub release**, with the version's changelog section as its notes. v0.1.0 was
   published as a pre-release, and `--prerelease` keeps that while the version is below 1.0:

   ```
   awk '/^## \[0\.2\.0\]/{on=1; next} /^## \[/{on=0} on' CHANGELOG.md > notes.md
   gh release create v0.2.0 --title v0.2.0 --notes-file notes.md --prerelease
   rm notes.md
   ```

## Updating ARCHITECTURE.md

`ARCHITECTURE.md` is generated from the source code just before each release, and reviewed in a pull
request. It doesn't go through the OpenSpec process. From a release branch:

```
python scripts/update_architecture.py v0.1.0
```

The script runs the `update-architecture` skill in headless Claude Code with the model pinned in
[its `SKILL.md`](../.claude/skills/update-architecture/SKILL.md), and keeps the result only if that
model did the work. Otherwise it restores the file and exits with an error. Commit or discard any
edits to `ARCHITECTURE.md` first, because the script won't run over them.

The run reports the key decisions it added or flagged for review, and the assumptions it can't check
from the code. Only the repository owner marks a decision as reviewed. Changing the pinned model is a
deliberate edit to `SKILL.md`, and the next run regenerates the file for a more thorough review.
