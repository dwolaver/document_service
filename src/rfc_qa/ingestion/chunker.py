"""Split RFC sections into chunks that fit a maximum size and can be cited individually."""

import re
from collections import Counter
from collections.abc import Iterable

from rfc_qa.chunk import Chunk
from rfc_qa.ingestion.rfc_parser import Section

_PARAGRAPH_BREAK = re.compile(r"\n[ \t]*\n+")


def _pack(pieces: Iterable[str], separator: str, max_chars: int) -> list[str]:
    """Greedily join pieces in order into strings of at most ``max_chars``."""
    packed: list[str] = []
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


def _split_paragraph(paragraph: str, max_chars: int) -> list[str]:
    """Split an oversized paragraph between lines, cutting a line only if it can't fit alone."""
    lines: list[str] = []
    for line in paragraph.split("\n"):
        lines.extend(line[i : i + max_chars] for i in range(0, len(line), max_chars) or [0])
    return _pack(lines, "\n", max_chars)


def split_text(text: str, max_chars: int) -> list[str]:
    """Split ``text`` into parts of at most ``max_chars``, at paragraphs and then at lines."""
    if len(text) <= max_chars:
        return [text] if text.strip() else []
    pieces: list[str] = []
    for paragraph in _PARAGRAPH_BREAK.split(text):
        if len(paragraph) <= max_chars:
            pieces.append(paragraph)
        else:
            pieces.extend(_split_paragraph(paragraph, max_chars))
    return _pack(pieces, "\n\n", max_chars)


def chunk_sections(
    sections: Iterable[Section], rfc_number: int, rfc_title: str, family: str, max_chars: int
) -> list[Chunk]:
    """Return the chunks for one RFC's sections. Sections with no body text produce none."""
    chunks: list[Chunk] = []
    seen_numbers: Counter[str] = Counter()
    for section in sections:
        seen_numbers[section.number] += 1
        occurrence = seen_numbers[section.number]
        suffix = "" if occurrence == 1 else f"-{occurrence}"
        for position, text in enumerate(split_text(section.text, max_chars)):
            chunk_id = f"rfc{rfc_number}-s{section.number}{suffix}-p{position}"
            chunks.append(Chunk(chunk_id, rfc_number, rfc_title, family, section.number, section.title, text))
    return chunks
