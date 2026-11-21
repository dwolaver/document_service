"""Check the links between the project's Markdown documents.

The documents are the Markdown files at the repository root and in ``docs/``. Every relative link and
anchor in them must resolve, every document other than the README must link back to it before its
first section, and the README must link to every other document. Links to web addresses aren't
checked, because that would need the network.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"
DOCUMENTS = sorted(REPO_ROOT.glob("*.md")) + sorted((REPO_ROOT / "docs").glob("*.md"))
OTHER_DOCUMENTS = [doc for doc in DOCUMENTS if doc != README]

LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
INLINE_CODE = re.compile(r"`[^`]*`")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


def _name(doc: Path) -> str:
    return doc.relative_to(REPO_ROOT).as_posix()


def _prose_lines(text: str) -> list[str]:
    """Return the lines outside fenced code blocks, with inline code removed."""
    lines, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            lines.append("")
        elif fenced:
            lines.append("")
        else:
            lines.append(INLINE_CODE.sub("", line))
    return lines


def _links(lines: list[str]) -> list[str]:
    return [target for line in lines for target in LINK.findall(line)]


def github_anchor(heading: str) -> str:
    """Return the anchor GitHub gives a heading, before any suffix for a repeat."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading).replace("`", "")
    text = re.sub(r"[^\w\- ]", "", text.strip().lower())
    return text.replace(" ", "-")


def anchors(text: str) -> set[str]:
    """Return every heading anchor in a document, numbering repeats as GitHub does."""
    seen: dict[str, int] = {}
    result = set()
    fenced = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        match = None if fenced else HEADING.match(line)
        if match:
            anchor = github_anchor(match.group(2))
            count = seen.get(anchor, 0)
            seen[anchor] = count + 1
            result.add(anchor if count == 0 else f"{anchor}-{count}")
    return result


def _resolves(doc: Path, target: str) -> bool:
    """Return whether a relative link from ``doc`` names an existing file, and heading if it has one."""
    path_part, _, fragment = target.partition("#")
    path = (doc.parent / path_part).resolve() if path_part else doc
    if not path.exists():
        return False
    if not fragment or path.suffix != ".md":
        return True
    return fragment in anchors(path.read_text(encoding="utf-8"))


def _broken_links(doc: Path) -> list[str]:
    targets = _links(_prose_lines(doc.read_text(encoding="utf-8")))
    return [target for target in targets if not SCHEME.match(target) and not _resolves(doc, target)]


def _resolved_targets(doc: Path, lines: list[str]) -> set[Path]:
    targets = set()
    for target in _links(lines):
        path_part = target.partition("#")[0]
        if path_part and not SCHEME.match(target):
            targets.add((doc.parent / path_part).resolve())
    return targets


@pytest.mark.parametrize("doc", DOCUMENTS, ids=_name)
def test_links_resolve(doc):
    broken = _broken_links(doc)
    assert not broken, f"{_name(doc)} has links that don't resolve: {broken}"


@pytest.mark.parametrize("doc", OTHER_DOCUMENTS, ids=_name)
def test_document_links_back_to_the_readme(doc):
    lines = _prose_lines(doc.read_text(encoding="utf-8"))
    first_section = next((i for i, line in enumerate(lines) if line.startswith("## ")), len(lines))
    assert README in _resolved_targets(doc, lines[:first_section]), (
        f"{_name(doc)} has no link to the README before its first section"
    )


@pytest.mark.parametrize("doc", OTHER_DOCUMENTS, ids=_name)
def test_readme_links_to_document(doc):
    lines = _prose_lines(README.read_text(encoding="utf-8"))
    assert doc in _resolved_targets(README, lines), f"README.md doesn't link to {_name(doc)}"


def test_changelog_starts_with_unreleased():
    lines = _prose_lines((REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8"))
    sections = [line for line in lines if line.startswith("## ")]
    assert sections, "CHANGELOG.md has no sections"
    assert sections[0] == "## [Unreleased]", (
        f"CHANGELOG.md starts with {sections[0]!r}, not '## [Unreleased]'"
    )


@pytest.mark.parametrize(
    ("heading", "anchor"),
    [
        ("Asking a question", "asking-a-question"),
        ("Updating ARCHITECTURE.md", "updating-architecturemd"),
        ("Lint, format, type and secret checks", "lint-format-type-and-secret-checks"),
        ("[0.1.0] - 2026-11-08", "010---2026-11-08"),
        ("The `rfc_qa` package", "the-rfc_qa-package"),
    ],
)
def test_github_anchor(heading, anchor):
    assert github_anchor(heading) == anchor


def test_repeated_headings_are_numbered():
    assert anchors("# Setup\n\n## Setup\n\n```\n# not a heading\n```\n## Setup\n") == {
        "setup",
        "setup-1",
        "setup-2",
    }
