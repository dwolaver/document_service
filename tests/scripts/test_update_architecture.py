import json
import os
import subprocess
from types import SimpleNamespace

import pytest

from scripts import update_architecture as ua
from scripts.update_architecture import (
    ArchitectureError,
    check_run,
    main,
    parse_result,
    read_pinned_model,
    update_architecture,
)

PINNED = "claude-opus-5-5"
SKILL = "---\nname: update-architecture\nmodel: {m}\n---\n\nInstructions.\n"


def _result(usage, is_error=False, result="Report."):
    return {
        "type": "result",
        "subtype": "success",
        "is_error": is_error,
        "result": result,
        "modelUsage": {m: {"inputTokens": 10, "outputTokens": t} for m, t in usage.items()},
    }


# --- Pinned model (task 2.1) ---

def _skill(tmp_path, text):
    path = tmp_path / "SKILL.md"
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_real_skill_pins_a_full_model_id():
    path = os.path.join(ua.ROOT, ua.SKILL_RELATIVE_PATH)
    assert read_pinned_model(path) == PINNED


def test_reads_the_model_from_frontmatter(tmp_path):
    assert read_pinned_model(_skill(tmp_path, SKILL.format(m="claude-sonnet-5-5"))) == "claude-sonnet-5-5"


@pytest.mark.parametrize("alias", ["opus", "sonnet", "claude-opus", "inherit", "default", "opus[1m]"])
def test_alias_is_rejected(tmp_path, alias):
    with pytest.raises(ArchitectureError, match="full model ID"):
        read_pinned_model(_skill(tmp_path, SKILL.format(m=alias)))


def test_missing_model_is_rejected(tmp_path):
    with pytest.raises(ArchitectureError, match="doesn't set a model"):
        read_pinned_model(_skill(tmp_path, "---\nname: x\n---\nmodel: claude-opus-5-5\n"))


def test_missing_skill_is_rejected(tmp_path):
    with pytest.raises(ArchitectureError, match="Can't read"):
        read_pinned_model(str(tmp_path / "missing.md"))


# --- Result parsing and the acceptance rule (task 2.1) ---

def test_parse_result_takes_the_last_json_line():
    stdout = "[claude-code:warning] something\n" + json.dumps(_result({PINNED: 5}))
    assert parse_result(stdout)["is_error"] is False


@pytest.mark.parametrize("stdout", ["", "not json", "[1, 2]"])
def test_parse_result_without_json(stdout):
    assert parse_result(stdout) is None


def test_pinned_model_alone_is_accepted():
    assert check_run(0, _result({PINNED: 4000}), PINNED) is None


def test_smaller_helper_model_is_accepted():
    assert check_run(0, _result({PINNED: 4000, "claude-haiku-5-5": 17}), PINNED) is None


def test_larger_other_model_is_rejected():
    reason = check_run(0, _result({PINNED: 10, "claude-sonnet-5-5": 4000}), PINNED)
    assert "Another model" in reason
    assert "claude-sonnet-5-5: 4000 output tokens" in reason


def test_equal_other_model_is_rejected():
    assert check_run(0, _result({PINNED: 100, "claude-sonnet-5-5": 100}), PINNED) is not None


def test_missing_pinned_model_is_rejected():
    reason = check_run(0, _result({"claude-haiku-5-5": 4000}), PINNED)
    assert "wasn't used" in reason


def test_error_result_is_rejected_even_when_subtype_says_success():
    result = _result({}, is_error=True, result="There's an issue with the selected model")
    assert result["subtype"] == "success"
    assert "issue with the selected model" in check_run(1, result, PINNED)


def test_non_zero_exit_is_rejected():
    assert "exit status 2" in check_run(2, _result({PINNED: 4000}), PINNED)


def test_missing_is_error_is_rejected():
    result = _result({PINNED: 4000})
    del result["is_error"]
    assert check_run(0, result, PINNED) is not None


def test_no_result_is_rejected():
    assert "no JSON result" in check_run(1, None, PINNED)


def test_no_model_usage_is_rejected():
    result = _result({})
    del result["modelUsage"]
    assert check_run(0, result, PINNED) is not None


# --- The run (task 2.2) ---

def _git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    skill = root / ".claude" / "skills" / "update-architecture"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(SKILL.format(m=PINNED), encoding="utf-8")
    (root / "module.py").write_text("def public():\n    pass\n", encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "add", ".")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
    return root


def _commit_doc(repo, text):
    (repo / "ARCHITECTURE.md").write_text(text, encoding="utf-8")
    _git(repo, "add", "ARCHITECTURE.md")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "doc")


@pytest.fixture
def claude(monkeypatch):
    """Replace the headless run. It writes ``claude.doc`` and returns ``claude.result``."""
    state = SimpleNamespace(
        doc="# Architecture\n\nNew text.\n",
        result=_result({PINNED: 4000, "claude-haiku-5-5": 17}),
        exit_code=0,
        also_write=None,
        calls=[],
    )

    def fake_run(root, release, model):
        state.calls.append((root, release, model))
        if state.doc is not None:
            with open(os.path.join(root, "ARCHITECTURE.md"), "w", encoding="utf-8") as doc:
                doc.write(state.doc)
        if state.also_write:
            with open(os.path.join(root, state.also_write), "w", encoding="utf-8") as other:
                other.write("changed\n")
        stdout = "" if state.result is None else json.dumps(state.result)
        return SimpleNamespace(returncode=state.exit_code, stdout=stdout, stderr="")

    monkeypatch.setattr(ua, "_run_claude", fake_run)
    return state


def _doc(repo):
    path = repo / "ARCHITECTURE.md"
    return path.read_text(encoding="utf-8") if path.exists() else None


def test_accepted_run_keeps_the_new_file(repo, claude):
    report = update_architecture(str(repo), "v0.1.0")
    assert _doc(repo) == "# Architecture\n\nNew text.\n"
    assert "Report." in report
    assert "claude-opus-5-5: 4000 output tokens" in report
    assert claude.calls == [(str(repo), "v0.1.0", PINNED)]


def test_rejected_run_restores_an_existing_file(repo, claude):
    _commit_doc(repo, "# Architecture\n\nOld text.\n")
    claude.result = _result({"claude-sonnet-5-5": 4000})
    with pytest.raises(ArchitectureError, match="Rejected, and ARCHITECTURE.md was restored"):
        update_architecture(str(repo), "v0.1.0")
    assert _doc(repo) == "# Architecture\n\nOld text.\n"


def test_rejected_run_removes_a_new_file(repo, claude):
    claude.result = _result({}, is_error=True, result="There's an issue with the selected model")
    claude.exit_code = 1
    with pytest.raises(ArchitectureError, match="issue with the selected model"):
        update_architecture(str(repo), "v0.1.0")
    assert _doc(repo) is None


def test_run_with_no_json_is_rejected(repo, claude):
    claude.result = None
    claude.exit_code = 1
    with pytest.raises(ArchitectureError, match="no JSON result"):
        update_architecture(str(repo), "v0.1.0")
    assert _doc(repo) is None


def test_uncommitted_doc_changes_refuse_before_running(repo, claude):
    _commit_doc(repo, "# Architecture\n\nOld text.\n")
    (repo / "ARCHITECTURE.md").write_text("# Architecture\n\nMy edit.\n", encoding="utf-8")
    with pytest.raises(ArchitectureError, match="uncommitted changes"):
        update_architecture(str(repo), "v0.1.0")
    assert claude.calls == []
    assert _doc(repo) == "# Architecture\n\nMy edit.\n"


def test_untracked_doc_refuses_before_running(repo, claude):
    (repo / "ARCHITECTURE.md").write_text("draft\n", encoding="utf-8")
    with pytest.raises(ArchitectureError, match="uncommitted changes"):
        update_architecture(str(repo), "v0.1.0")
    assert claude.calls == []


def test_other_changed_file_is_rejected_and_left_alone(repo, claude):
    _commit_doc(repo, "# Architecture\n\nOld text.\n")
    claude.also_write = "module.py"
    with pytest.raises(ArchitectureError, match="files other than ARCHITECTURE.md.*module.py"):
        update_architecture(str(repo), "v0.1.0")
    assert _doc(repo) == "# Architecture\n\nOld text.\n"
    assert (repo / "module.py").read_text(encoding="utf-8") == "changed\n"


def test_new_untracked_file_from_the_run_is_rejected(repo, claude):
    claude.also_write = "notes.txt"
    with pytest.raises(ArchitectureError, match="notes.txt"):
        update_architecture(str(repo), "v0.1.0")
    assert (repo / "notes.txt").exists()


def test_existing_dirty_file_the_run_leaves_alone_is_fine(repo, claude):
    (repo / "module.py").write_text("def public():\n    return 1\n", encoding="utf-8")
    update_architecture(str(repo), "v0.1.0")
    assert _doc(repo) == "# Architecture\n\nNew text.\n"


def test_existing_dirty_file_the_run_changes_is_rejected(repo, claude):
    (repo / "module.py").write_text("def public():\n    return 1\n", encoding="utf-8")
    claude.also_write = "module.py"
    with pytest.raises(ArchitectureError, match="module.py"):
        update_architecture(str(repo), "v0.1.0")


def test_alias_refuses_before_running(repo, claude):
    skill = repo / ".claude" / "skills" / "update-architecture" / "SKILL.md"
    skill.write_text(SKILL.format(m="opus"), encoding="utf-8")
    with pytest.raises(ArchitectureError, match="full model ID"):
        update_architecture(str(repo), "v0.1.0")
    assert claude.calls == []


def test_command_line_runs_the_pinned_model_with_limited_tools(monkeypatch, repo):
    calls = []
    real_run = subprocess.run

    def fake_subprocess_run(command, **kwargs):
        if command[0] == "git":
            return real_run(command, **kwargs)
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout=json.dumps(_result({PINNED: 1})), stderr="")

    monkeypatch.setattr(ua.subprocess, "run", fake_subprocess_run)
    update_architecture(str(repo), "v0.1.0")
    command, kwargs = calls[0]
    assert command[:3] == ["claude", "-p", "/update-architecture v0.1.0"]
    assert command[command.index("--model") + 1] == PINNED
    assert command[command.index("--output-format") + 1] == "json"
    tools = command[command.index("--allowedTools") + 1].split(",")
    assert set(tools) == {
        "Read", "Glob", "Grep", "Write", "Edit",
        "Bash(git log:*)", "Bash(git diff:*)", "Bash(git show:*)", "Bash(git rev-parse:*)",
    }
    assert kwargs["cwd"] == str(repo)
    assert kwargs["stdin"] is subprocess.DEVNULL


# --- Console ---

def test_main_success(monkeypatch, repo, claude, capsys):
    monkeypatch.setattr(ua, "ROOT", str(repo))
    assert main(["v0.1.0"]) == 0
    assert "Review ARCHITECTURE.md, then commit it." in capsys.readouterr().out


def test_main_rejection_is_non_zero(monkeypatch, repo, claude, capsys):
    monkeypatch.setattr(ua, "ROOT", str(repo))
    claude.result = _result({"claude-sonnet-5-5": 4000})
    assert main(["v0.1.0"]) == 1
    assert "Rejected" in capsys.readouterr().err


@pytest.mark.parametrize("release", ["", "v0.1.0 extra"])
def test_main_rejects_a_bad_release(release, capsys):
    assert main([release]) == 1
    assert "single word" in capsys.readouterr().err


# --- Rationale (task 2.3) ---

def test_opening_comment_explains_the_script():
    doc = ua.__doc__
    assert "https://code.claude.com/docs/en/skills" in doc
    assert "availableModels" in doc
    assert "fallback" in doc
    assert "Remove this script" in doc
    assert "can refuse to run" in doc
