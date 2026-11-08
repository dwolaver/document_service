"""Run the update-architecture skill, and keep its result only if the pinned model produced it.

Usage: python scripts/update_architecture.py <release>, for example v0.1.0.

Why this script exists
----------------------
ARCHITECTURE.md must come from one deliberately chosen model, so that a change of model is a visible
decision with a more thorough review. The skill pins that model in its `model` field, but Claude
Code can't be relied on to refuse a run when that model isn't the one used:

- The Claude Code documentation says a skill's model that an organization's `availableModels`
  allowlist blocks is ignored, and the skill runs on the session model, with no notice.
  https://code.claude.com/docs/en/skills (the `model` field) and
  https://code.claude.com/docs/en/model-config
- A configured fallback model can take over a run, which the documentation also describes.
- No hook or environment variable reports a skill's model during a run, so nothing can refuse in
  advance. Headless JSON output does report afterwards which models were used, in `modelUsage`.

Testing with Claude Code 2.1.319 in headless mode found that a skill naming an unknown model does
fail with an error. A policy block and a fallback couldn't be tested on this account, and they are
the cases this script exists for. The same testing found that a small helper model can appear in
`modelUsage` beside the requested one, so the check requires the pinned model to do most of the
work, not to be the only model listed.

So this script runs the skill headlessly, checks `modelUsage` afterwards, and puts ARCHITECTURE.md
back as it was unless the pinned model did the work. It rejects a result after the run rather than
preventing the run, which is acceptable for something run once per release.

When to remove it
-----------------
Remove this script, and run the skill directly, once a Claude Code skill can refuse to run when its
model can't be used, including when a policy blocks it or a fallback would replace it. Check the
documentation above at each release, using the key decision about this script in ARCHITECTURE.md.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_RELATIVE_PATH = os.path.join(".claude", "skills", "update-architecture", "SKILL.md")
DOC_RELATIVE_PATH = "ARCHITECTURE.md"

# The headless run may read the repository, inspect git history, and write ARCHITECTURE.md.
ALLOWED_TOOLS = ",".join(
    [
        "Read",
        "Glob",
        "Grep",
        "Write",
        "Edit",
        "Bash(git log:*)",
        "Bash(git diff:*)",
        "Bash(git show:*)",
        "Bash(git rev-parse:*)",
    ]
)

# A full model ID such as claude-opus-5-5. Aliases such as opus move to newer models on their own.
_FULL_MODEL_ID = re.compile(r"claude-[a-z]+-\d+(?:-\d+)*")
_MODEL_FIELD = re.compile(r"^model:\s*(\S+)\s*$", re.MULTILINE)


class ArchitectureError(Exception):
    """A reason not to run, or not to keep a run's result, ready to show."""


def _log_error(message):
    print(message, file=sys.stderr)


def read_pinned_model(skill_path):
    """Return the full model ID from the skill's frontmatter, raising if it's missing or an alias."""
    try:
        with open(skill_path, encoding="utf-8") as skill_file:
            text = skill_file.read()
    except OSError as exc:
        raise ArchitectureError("Can't read the skill at {p!r}: {e}".format(p=skill_path, e=exc)) from exc
    parts = text.split("---")
    match = _MODEL_FIELD.search(parts[1]) if text.startswith("---") and len(parts) > 2 else None
    if match is None:
        raise ArchitectureError("The skill at {p!r} doesn't set a model.".format(p=skill_path))
    model = match.group(1)
    if not _FULL_MODEL_ID.fullmatch(model):
        raise ArchitectureError(
            "The skill's model is {m!r}. A full model ID such as claude-opus-5-5 is required, "
            "because an alias can change models without a decision.".format(m=model)
        )
    return model


def parse_result(stdout):
    """Return the final JSON result from headless output, or ``None`` if there isn't one."""
    for line in reversed(stdout.strip().splitlines()):
        try:
            result = json.loads(line)
        except ValueError:
            continue
        if isinstance(result, dict):
            return result
    return None


def _output_tokens(result):
    usage = result.get("modelUsage")
    if not isinstance(usage, dict):
        return {}
    return {
        model: stats.get("outputTokens", 0) if isinstance(stats, dict) else 0
        for model, stats in usage.items()
    }


def describe_usage(result):
    """Return the models a run used and their output tokens, for messages."""
    tokens = _output_tokens(result) if isinstance(result, dict) else {}
    if not tokens:
        return "no model usage reported"
    return ", ".join("{m}: {t} output tokens".format(m=m, t=t) for m, t in sorted(tokens.items()))


def check_run(exit_code, result, pinned_model):
    """Return ``None`` when the run can be kept, otherwise the reason to reject it.

    The run must exit cleanly and report no error. The pinned model must appear in ``modelUsage``
    and produce more output than any other model, which allows a small helper model but not a
    substitute. ``subtype`` isn't used, because it reported success for a failed run.
    """
    if result is None:
        return "The run produced no JSON result (exit status {c}).".format(c=exit_code)
    if exit_code != 0 or result.get("is_error") is not False:
        return "The run failed (exit status {c}): {r}".format(c=exit_code, r=result.get("result"))
    tokens = _output_tokens(result)
    pinned_tokens = tokens.get(pinned_model)
    if pinned_tokens is None:
        return "The pinned model {m} wasn't used. Models used: {u}.".format(
            m=pinned_model, u=describe_usage(result)
        )
    if any(model != pinned_model and count >= pinned_tokens for model, count in tokens.items()):
        return "Another model did as much of the work as the pinned model {m}: {u}.".format(
            m=pinned_model, u=describe_usage(result)
        )
    return None


def _git(root, *args):
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    ).stdout


def _changed_paths(root):
    """Return changed and untracked paths, relative to ``root``."""
    paths = set()
    for line in _git(root, "status", "--porcelain", "--untracked-files=all").splitlines():
        path = line[3:]
        paths.add(path.split(" -> ")[-1])
    return paths


def _file_hash(root, path):
    full_path = os.path.join(root, path)
    if not os.path.isfile(full_path):
        return None
    with open(full_path, "rb") as changed_file:
        return hashlib.sha256(changed_file.read()).hexdigest()


def _snapshot(root):
    return {path: _file_hash(root, path) for path in _changed_paths(root)}


def _other_changes(root, before):
    """Return files other than ARCHITECTURE.md that changed since ``before`` was taken."""
    changed = []
    for path in sorted(_changed_paths(root) | set(before)):
        if path != DOC_RELATIVE_PATH and before.get(path, "absent") != _file_hash(root, path):
            changed.append(path)
    return changed


def _run_claude(root, release, model):
    """Run the skill headlessly. This is the only call to Claude Code, so tests replace it."""
    command = [
        "claude", "-p", "/update-architecture {r}".format(r=release),
        "--model", model,
        "--output-format", "json",
        "--allowedTools", ALLOWED_TOOLS,
        "--permission-mode", "acceptEdits",
    ]
    return subprocess.run(command, cwd=root, capture_output=True, text=True, stdin=subprocess.DEVNULL)


def _restore(doc_path, original):
    if original is None:
        if os.path.exists(doc_path):
            os.remove(doc_path)
    else:
        with open(doc_path, "wb") as doc_file:
            doc_file.write(original)


def update_architecture(root, release):
    """Run the skill for ``release`` and return its report, raising :class:`ArchitectureError`.

    On any rejection, ARCHITECTURE.md is restored to how it was before the run.
    """
    pinned_model = read_pinned_model(os.path.join(root, SKILL_RELATIVE_PATH))
    before = _snapshot(root)
    if DOC_RELATIVE_PATH in before:
        raise ArchitectureError(
            "{d} has uncommitted changes. Commit or discard them first, so a rejected run can't "
            "overwrite them.".format(d=DOC_RELATIVE_PATH)
        )

    doc_path = os.path.join(root, DOC_RELATIVE_PATH)
    original = None
    if os.path.exists(doc_path):
        with open(doc_path, "rb") as doc_file:
            original = doc_file.read()

    completed = _run_claude(root, release, pinned_model)
    result = parse_result(completed.stdout)
    reason = check_run(completed.returncode, result, pinned_model)
    if reason is None:
        others = _other_changes(root, before)
        if others:
            reason = "The run changed files other than {d}, which were left as they are: {o}".format(
                d=DOC_RELATIVE_PATH, o=", ".join(others)
            )
    if reason is not None:
        _restore(doc_path, original)
        raise ArchitectureError("Rejected, and {d} was restored. {r}".format(d=DOC_RELATIVE_PATH, r=reason))
    return "{report}\n\nModels used: {u}.".format(report=result.get("result", ""), u=describe_usage(result))


def main(argv=None):
    """Console entry point: return 0 when the result is kept, 1 otherwise."""
    parser = argparse.ArgumentParser(description="Update ARCHITECTURE.md with the pinned model.")
    parser.add_argument("release", help="The release the file describes, for example v0.1.0.")
    args = parser.parse_args(argv)
    if not args.release.strip() or any(c.isspace() for c in args.release):
        _log_error("The release must be a single word, for example v0.1.0.")
        return 1
    try:
        report = update_architecture(ROOT, args.release)
    except ArchitectureError as exc:
        _log_error(str(exc))
        return 1
    print(report)
    print("\nReview {d}, then commit it.".format(d=DOC_RELATIVE_PATH))
    return 0


if __name__ == "__main__":
    sys.exit(main())
