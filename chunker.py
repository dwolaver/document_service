"""Split RFC sections into chunks that fit a maximum size and can be cited individually."""

import re
from collections import Counter
from dataclasses import dataclass

_PARAGRAPH_BREAK = re.compile(r"\n[ \t]*\n+")


@dataclass(frozen=True)
class Chunk:
    """A citable passage. ``text`` keeps the line layout of the source."""

    chunk_id: str
    rfc_number: int
    rfc_title: str
    family: str
    section_number: str
    section_title: str
    text: str


def _pack(pieces, separator, max_chars):
    """Greedily join pieces in order into strings of at most ``max_chars``."""
    packed = []
    current = ""
    for piece in pieces:
        candidate = current + separator + piece if current else piece
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                packed.append(current)
            current = piece
    if current:
        packed.append(current)
    return packed


def _split_paragraph(paragraph, max_chars):
    """Split an oversized paragraph between lines, cutting a line only if it can't fit alone."""
    lines = []
    for line in paragraph.split("\n"):
        lines.extend(line[i : i + max_chars] for i in range(0, len(line), max_chars) or [0])
    return _pack(lines, "\n", max_chars)


def split_text(text, max_chars):
    """Split ``text`` into parts of at most ``max_chars``, at paragraphs and then at lines."""
    if len(text) <= max_chars:
        return [text] if text.strip() else []
    pieces = []
    for paragraph in _PARAGRAPH_BREAK.split(text):
        if len(paragraph) <= max_chars:
            pieces.append(paragraph)
        else:
            pieces.extend(_split_paragraph(paragraph, max_chars))
    return _pack(pieces, "\n\n", max_chars)


def chunk_sections(sections, rfc_number, rfc_title, family, max_chars):
    """Return the chunks for one RFC's sections. Sections with no body text produce none."""
    chunks = []
    seen_numbers = Counter()
    for section in sections:
        seen_numbers[section.number] += 1
        occurrence = seen_numbers[section.number]
        suffix = "" if occurrence == 1 else "-{n}".format(n=occurrence)
        for position, text in enumerate(split_text(section.text, max_chars)):
            chunk_id = "rfc{rfc}-s{section}{suffix}-p{position}".format(
                rfc=rfc_number, section=section.number, suffix=suffix, position=position
            )
            chunks.append(
                Chunk(chunk_id, rfc_number, rfc_title, family, section.number, section.title, text)
            )
    return chunks
