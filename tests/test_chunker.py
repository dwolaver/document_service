from chunker import chunk_sections, split_text
from rfc_parser import Section


def _chunks(sections, max_chars=100):
    return chunk_sections(sections, 9110, "HTTP Semantics", "http", max_chars)


# --- Splitting (task 3.1) ---

def test_section_that_fits_is_one_chunk():
    assert split_text("short text", 100) == ["short text"]


def test_section_at_exactly_the_maximum_is_one_chunk():
    assert split_text("x" * 100, 100) == ["x" * 100]


def test_oversized_section_splits_between_paragraphs():
    first, second = "a" * 60, "b" * 60
    assert split_text(first + "\n\n" + second, 100) == [first, second]


def test_paragraphs_are_packed_together_up_to_the_maximum():
    paragraphs = ["a" * 40, "b" * 40, "c" * 40]
    assert split_text("\n\n".join(paragraphs), 100) == [
        paragraphs[0] + "\n\n" + paragraphs[1],
        paragraphs[2],
    ]


def test_oversized_paragraph_splits_between_lines():
    lines = ["line {n} ".format(n=n) + "x" * 30 for n in range(6)]
    parts = split_text("\n".join(lines), 100)
    assert len(parts) > 1
    for part in parts:
        assert len(part) <= 100
        for line in part.split("\n"):
            assert line in lines


def test_line_longer_than_the_maximum_is_cut():
    parts = split_text("x" * 250, 100)
    assert [len(part) for part in parts] == [100, 100, 50]


def test_parts_stay_within_the_maximum_and_keep_all_text_in_order():
    paragraphs = ["para{n} ".format(n=n) + "word " * (n * 7 % 40 + 1) for n in range(30)]
    text = "\n\n".join(p.strip() for p in paragraphs)
    parts = split_text(text, 100)
    assert all(len(part) <= 100 for part in parts)
    assert "".join("".join(parts).split()) == "".join(text.split())


def test_empty_section_produces_nothing():
    assert split_text("", 100) == []
    assert split_text("   \n  ", 100) == []


def test_heading_with_no_body_produces_no_chunk():
    assert _chunks([Section("1", "Introduction", "")]) == []


def test_chunks_never_mix_sections():
    sections = [Section("1", "One", "first"), Section("2", "Two", "second")]
    assert [chunk.text for chunk in _chunks(sections)] == ["first", "second"]


# --- Identity and metadata (task 3.2) ---

def test_chunk_metadata():
    chunk = _chunks([Section("15.5.1", "400 Bad Request", "Body.")])[0]
    assert chunk.chunk_id == "rfc9110-s15.5.1-p0"
    assert (chunk.rfc_number, chunk.rfc_title, chunk.family) == (9110, "HTTP Semantics", "http")
    assert (chunk.section_number, chunk.section_title) == ("15.5.1", "400 Bad Request")
    assert chunk.text == "Body."


def test_parts_of_a_section_have_positions():
    section = Section("3", "Long", "a" * 60 + "\n\n" + "b" * 60)
    assert [chunk.chunk_id for chunk in _chunks([section])] == ["rfc9110-s3-p0", "rfc9110-s3-p1"]


def test_abstract_id():
    assert _chunks([Section("abstract", "Abstract", "x")])[0].chunk_id == "rfc9110-sabstract-p0"


def test_repeated_section_numbers_get_unique_ids():
    sections = [Section("1", "One", "first"), Section("1", "One again", "second")]
    ids = [chunk.chunk_id for chunk in _chunks(sections)]
    assert ids == ["rfc9110-s1-p0", "rfc9110-s1-2-p0"]


def test_ids_are_stable_across_runs():
    sections = [Section("1", "One", "a" * 60 + "\n\n" + "b" * 60), Section("2", "Two", "c")]
    assert _chunks(sections) == _chunks(sections)


def test_figure_keeps_its_indentation():
    figure = "     +--------+\n     | Client |\n     +--------+"
    text = "a" * 90 + "\n\n" + figure + "\n\n" + "b" * 90
    assert figure in [chunk.text for chunk in _chunks([Section("1", "One", text)])]
