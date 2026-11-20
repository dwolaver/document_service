"""The citable passage shared by ingestion, retrieval and generation."""

from dataclasses import dataclass


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
