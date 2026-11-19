"""Parse the plain text of an RFC into numbered sections.

RFC layouts vary by era. This module removes page furniture, finds section headings across those
layouts, and drops sections with little retrieval value. See ``parse_rfc``.
"""

import re
from dataclasses import dataclass

# Numbers for sections that are kept even though the RFC doesn't number them.
_KEPT_UNNUMBERED_SECTIONS = {"abstract": "abstract", "security considerations": "security"}

_FOOTER = re.compile(r"\[Page [0-9ivxlc]+\]\s*$")
_RUNNING_HEADER = re.compile(r"^RFC ?\d+\s.*\b\d{4}\s*$")
_EARLY_DATE_HEADER = re.compile(r"^\s*[A-Z][a-z]+ \d{4}\s*$")

_DOTTED_LEADER = re.compile(r"\.\s?\.\s?\.")
_MARGIN_SUBSECTION = re.compile(r"^\d+\.\d+(\.\d+)*\.?\s+[A-Za-z]")
_HEADING = re.compile(
    r"^(?P<indent>\s*)"
    r"(?:Appendix\s+(?P<appendix>[A-Z])[.:]?(?:\s+-)?"
    r"|(?P<letter>[A-Z](?:\.\d+)*)\."
    r"|(?P<lettered>[A-Z](?:\.\d+)+)"
    r"|(?P<number>\d+(?:\.\d+)*)\.?)"
    r"\s+(?P<title>\S.*?)\s*$"
)

_MAX_TITLE_LENGTH = 75
_MAX_TOP_LEVEL_NUMBER = 99
# Top-level numbers may skip one value, as a few RFCs do. A larger jump is a body line.
_MAX_TOP_LEVEL_STEP = 2
_INDENT_PER_LEVEL = 3
_MIN_CENTERED_INDENT = 10

_TOC_TITLE = re.compile(r"table of contents", re.IGNORECASE)
# Unnumbered headings: they close the current section, and their text is dropped.
_EXCLUDED_UNNUMBERED_TITLES = re.compile(
    r"status of this memo"
    r"|copyright notice"
    r"|table of contents"
    r"|acknowledge?ments?"
    r"|contributors?"
    r"|authors?'? ?(address(es)?|information)"
    r"|author's address"
    r"|editors?'? ?(address(es)?|information)"
    r"|index"
    r"|(normative |informative )?references"
    r"|full copyright statement"
    r"|intellectual property( statement)?"
    r"|working group information"
    r"|other contributors"
    r"|editors"
    r"|credits"
    r"|comments",
    re.IGNORECASE,
)
# Numbered sections that are dropped, along with their subsections.
_EXCLUDED_NUMBERED_TITLES = re.compile(
    r"(normative |informative )?references(( and notes)?|\s*:.*)"
    r"|acknowledge?ments?"
    r"|contributors?"
    r"|authors?'? ?(address(es)?|information)"
    r"|author's address"
    r"|editors?'? ?(address(es)?|information)"
    r"|index"
    r"|full copyright statement"
    r"|copyright notice",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Section:
    """One section of an RFC, with its source line layout preserved."""

    number: str
    title: str
    text: str


@dataclass(frozen=True)
class _Heading:
    number: str
    title: str


def _remove_header(lines):
    if not lines:
        return lines
    if _RUNNING_HEADER.match(lines[0]):
        return lines[1:]
    if _EARLY_DATE_HEADER.match(lines[0]):
        # Early RFCs run a date, a title and sometimes a chapter name together as a block.
        index = 1
        while index < len(lines) and lines[index].strip():
            index += 1
        return lines[index:]
    return lines


def _strip_blank_edges(lines):
    start, end = 0, len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return lines[start:end]


def _clean_page(page):
    lines = _strip_blank_edges(page.split("\n"))
    lines = _strip_blank_edges(_remove_header(lines))
    if lines and _FOOTER.search(lines[-1]):
        lines = _strip_blank_edges(lines[:-1])
    return lines


def remove_page_furniture(text):
    """Remove page headers, footers and form feeds, joining text across page breaks."""
    text = text.replace("\r\n", "\n")
    if "\f" not in text:
        return text
    lines = []
    for page in text.split("\f"):
        lines.extend(_clean_page(page))
    return "\n".join(lines)


def _sort_key(number):
    """Return an ordering key where appendices sort after numbered sections."""
    parts = number.split(".")
    if parts[0].isdigit():
        return (0, *(int(part) for part in parts))
    return (1, ord(parts[0]) - ord("A"), *(int(part) for part in parts[1:]))


def _heading_number(match):
    return match["appendix"] or match["letter"] or match["lettered"] or match["number"]


def _match_heading_shape(line):
    """Return (number, title, indent) for a line shaped like a heading, otherwise ``None``."""
    if _DOTTED_LEADER.search(line):
        return None
    match = _HEADING.match(line)
    if match is None:
        return None
    return _heading_number(match), match["title"], len(match["indent"])


def _is_plausible_title(title, number, indent):
    if len(title) > _MAX_TITLE_LENGTH or title.endswith((";", ":")):
        return False
    # A few RFCs end margin headings with a period, and RFC 1122 wraps deep headings after a comma.
    if title.endswith(".") and indent != 0:
        return False
    if title.endswith(",") and number.count(".") < 2:
        return False
    # Subsections at the margin can be lowercase field names like "max-age". Anywhere else, text
    # like "6.1 of [RFC7231]" or "10 seconds" is wrapped body text.
    if indent == 0 and "." in number:
        return True
    return title[0].isupper() or title[0].isdigit()


def _is_expected_indent(number, title, indent, indents_subsections):
    if indent == 0:
        return True
    depth = number.count(".") + 1
    if depth > 1:
        return indents_subsections and indent == _INDENT_PER_LEVEL * (depth - 1)
    # Early RFCs center top-level headings in uppercase.
    return indent >= _MIN_CENTERED_INDENT and title.isupper()


def _follows(number, previous):
    """Return whether ``number`` can come next after ``previous`` in section order."""
    key = _sort_key(number)
    if previous is None:
        return key[0] == 0 or key[1] == 0
    previous_key = _sort_key(previous)
    if key <= previous_key:
        return False
    if key[0] != previous_key[0]:
        return key[1] == 0
    return key[1] - previous_key[1] <= _MAX_TOP_LEVEL_STEP


def _parse_heading(line, previous, indents_subsections):
    shape = _match_heading_shape(line)
    if shape is None:
        return None
    number, title, indent = shape
    if number[0].isdigit() and int(number.split(".")[0]) > _MAX_TOP_LEVEL_NUMBER:
        return None
    if not _is_plausible_title(title, number, indent):
        return None
    if not _is_expected_indent(number, title, indent, indents_subsections):
        return None
    if not _follows(number, previous):
        return None
    return _Heading(number, title.rstrip(" .,"))


def _indents_subsections(lines):
    """Return whether this RFC indents subsection headings by depth, as some older RFCs do.

    Layout is consistent within a document, so an RFC with subsection headings at the margin never
    has indented ones. There, an indented "1.2 Foo" is wrapped body text.
    """
    return not any(_MARGIN_SUBSECTION.match(line) for line in lines)


def _body_start_after_toc(lines, toc_index, indents_subsections):
    """Return the line index where numbered content resumes after a table of contents.

    The first entry's number appears once in the table, so its next appearance as a heading is the
    real section. Tables of contents have no reliable end marker of their own.
    """
    first_number = None
    for index in range(toc_index + 1, len(lines)):
        if first_number is None:
            entry = _HEADING.match(lines[index])
            first_number = None if entry is None else _heading_number(entry)
            continue
        heading = _parse_heading(lines[index], None, indents_subsections)
        if heading is not None and heading.number == first_number:
            return index
    return toc_index + 1


def _unnumbered_title(line):
    title = line.strip().rstrip(":")
    is_centered_or_marginal = line == line.lstrip() or len(line) - len(line.lstrip()) >= _MIN_CENTERED_INDENT
    if not title or not is_centered_or_marginal:
        return None
    if title.lower() in _KEPT_UNNUMBERED_SECTIONS or _EXCLUDED_UNNUMBERED_TITLES.fullmatch(title):
        return title
    return None


def _split_blocks(lines):
    """Yield (number, title, body lines) for each block. ``number`` is ``None`` when unnumbered."""
    indents_subsections = _indents_subsections(lines)
    blocks = []
    current = None
    previous_number = None
    index = 0
    while index < len(lines):
        line = lines[index]
        unnumbered = _unnumbered_title(line)
        if unnumbered is not None:
            current = (None, unnumbered, [])
            blocks.append(current)
            index += 1
            if _TOC_TITLE.fullmatch(unnumbered):
                index = _body_start_after_toc(lines, index - 1, indents_subsections)
            continue
        heading = _parse_heading(line, previous_number, indents_subsections)
        if heading is not None:
            previous_number = heading.number
            current = (heading.number, heading.title, [])
            blocks.append(current)
        elif current is not None:
            current[2].append(line)
        index += 1
    return blocks


def _is_descendant(number, ancestor):
    return number.startswith(ancestor + ".")


def _sections_from_blocks(blocks):
    sections = []
    excluded_ancestor = None
    for number, title, body in blocks:
        text = "\n".join(_strip_blank_edges(body))
        if number is None:
            kept_number = _KEPT_UNNUMBERED_SECTIONS.get(title.lower())
            if kept_number is not None:
                sections.append(Section(kept_number, title, text))
            continue
        if excluded_ancestor is not None and _is_descendant(number, excluded_ancestor):
            continue
        if _EXCLUDED_NUMBERED_TITLES.fullmatch(title):
            excluded_ancestor = number
            continue
        sections.append(Section(number, title, text))
    return sections


def parse_rfc(text):
    """Return the retained sections of an RFC, in document order.

    Front matter before the first recognized heading and excluded sections are dropped. A section
    whose heading has no body text is returned with empty ``text``.
    """
    lines = remove_page_furniture(text).split("\n")
    return _sections_from_blocks(_split_blocks(lines))
