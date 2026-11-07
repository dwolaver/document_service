import os

import pytest

from rfc_parser import parse_rfc, remove_page_furniture

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _load(name):
    with open(os.path.join(FIXTURE_DIR, name + ".txt"), encoding="utf-8") as fixture:
        return fixture.read()


def _sections(name):
    return {section.number: section for section in parse_rfc(_load(name))}


PAGINATED_LAYOUTS = ["early", "hierarchical", "paginated"]
ALL_LAYOUTS = PAGINATED_LAYOUTS + ["unpaginated"]


# --- Page furniture (task 2.2) ---

@pytest.mark.parametrize("name", PAGINATED_LAYOUTS)
def test_page_furniture_is_removed(name):
    cleaned = remove_page_furniture(_load(name))
    assert "\f" not in cleaned
    assert "[Page" not in cleaned
    assert "RFC 2616                        HTTP/1.1" not in cleaned
    assert "RFC1122                       INTRODUCTION" not in cleaned
    assert "September 1981\nTransmission Control Protocol\nIntroduction" not in cleaned


@pytest.mark.parametrize(
    "name, section, first, second",
    [
        ("early", "1.1", "continues across a page", "break and finishes here."),
        ("paginated", "2", "continues across a page", "   break and finishes here."),
    ],
)
def test_paragraph_across_page_break_stays_adjacent(name, section, first, second):
    lines = _sections(name)[section].text.split("\n")
    assert lines[lines.index(next(l for l in lines if first in l)) + 1] == second


def test_unpaginated_text_is_unchanged():
    text = _load("unpaginated")
    assert remove_page_furniture(text) == text


def test_windows_line_endings_are_normalized():
    assert remove_page_furniture("one\r\ntwo") == "one\ntwo"


def test_body_line_that_mentions_a_page_is_kept():
    text = "first page\n\n     [Page 1]\n\fsee [Page 2] of the report\nmore text\n\n     [Page 2]\n"
    assert "see [Page 2] of the report" in remove_page_furniture(text)


# --- Section detection (task 2.3) ---

def test_modern_heading():
    text = "14.  One\n\n15.  Two\n\n15.5.  Three\n\n15.5.1.  400 Bad Request\n\n   Body.\n"
    assert parse_rfc(text)[-1].number == "15.5.1"
    assert parse_rfc(text)[-1].title == "400 Bad Request"


def test_older_heading_without_trailing_period():
    text = "13 Caching\n\n13.1.1 Cache Correctness\n\n   Body.\n"
    assert parse_rfc(text)[-1].number == "13.1.1"
    assert parse_rfc(text)[-1].title == "Cache Correctness"


def test_top_level_older_heading():
    assert _sections("paginated")["2"].title == "Caching in HTTP"


def test_centered_uppercase_heading():
    assert _sections("early")["1"].title == "INTRODUCTION"


def test_indented_heading_by_depth():
    sections = _sections("hierarchical")
    assert sections["1.1"].title == "The Internet Architecture"
    assert sections["1.1.1"].title == "Internet Hosts"


def test_wrapped_indented_heading_keeps_its_text_and_drops_the_comma():
    sections = _sections("hierarchical")
    assert sections["2.2.2.8"].title == "TCP Connection State Diagram: RFC-793 Section 3.2"


def test_appendix_headings_sort_after_numbered_sections():
    numbers = [section.number for section in parse_rfc(_load("unpaginated"))]
    assert numbers[-3:] == ["A", "A.1", "B"]


def test_appendix_title():
    sections = _sections("unpaginated")
    assert sections["B"].title == "Changes from RFC 7230"
    assert sections["A.1"].title == "Example"


def test_lowercase_field_name_heading_at_the_margin():
    assert _sections("unpaginated")["2.2.1"].title == "max-age"


def test_heading_with_trailing_period_at_the_margin():
    text = "1.  Introduction\n\n   Text.\n\n2.  Window Probes.\n\n   More text.\n"
    assert [(s.number, s.title) for s in parse_rfc(text)][-1] == ("2", "Window Probes")


@pytest.mark.parametrize("name", ALL_LAYOUTS)
def test_table_of_contents_creates_no_duplicate_sections(name):
    numbers = [section.number for section in parse_rfc(_load(name))]
    assert len(numbers) == len(set(numbers))
    assert "1" in numbers


@pytest.mark.parametrize("name", ALL_LAYOUTS)
def test_table_of_contents_text_is_not_in_any_section(name):
    for section in parse_rfc(_load(name)):
        assert "......" not in section.text


def test_table_of_contents_does_not_start_a_section_body():
    assert parse_rfc(_load("unpaginated"))[1].number == "1"
    assert "Field Lines" not in _sections("unpaginated")["abstract"].text


@pytest.mark.parametrize(
    "name, section, item",
    [
        ("early", "3.9", "1.  CLOSED"),
        ("hierarchical", "1.1.1", "1.  Send datagrams."),
        ("paginated", "1.1", "1. The first numbered item."),
        ("unpaginated", "1.1", "1.  The first numbered item."),
    ],
)
def test_restarted_numbered_list_stays_in_its_section(name, section, item):
    assert item in _sections(name)[section].text


def test_wrapped_number_in_body_text_is_not_a_heading():
    sections = _sections("unpaginated")
    assert "1.1 Purpose of Something" in sections["1.1"].text
    assert "1.0 or later" in sections["abstract"].text


def test_citation_number_at_line_start_does_not_block_later_headings():
    text = (
        "1.  Introduction\n\n   See Section\n   6.1 of [RFC7231]), and those.\n\n"
        "2.  Next\n\n2.1.  Child\n\n   Body.\n"
    )
    assert [section.number for section in parse_rfc(text)] == ["1", "2", "2.1"]


def test_skipped_section_number_still_parses():
    text = "1.  One\n\n   Text.\n\n3.  Three\n\n   Text.\n"
    assert [section.number for section in parse_rfc(text)] == ["1", "3"]


def test_large_number_in_body_is_not_a_heading():
    text = "1.  One\n\nThe rate is low.\n1000 Bytes per second are used.\n\n2.  Two\n\n   Text.\n"
    assert [section.number for section in parse_rfc(text)] == ["1", "2"]


def test_indented_heading_is_wrapped_text_when_subsections_sit_at_the_margin():
    text = (
        "1.  One\n\n   Wrapped text about TLS\n   1.2 [RFC6347] in 2012.\n   1.2 Looks Like One\n\n"
        "1.1.  Real\n\n1.2.  Also Real\n\n   Body.\n"
    )
    assert [section.number for section in parse_rfc(text)] == ["1", "1.1", "1.2"]
    assert parse_rfc(text)[-1].title == "Also Real"


def test_body_text_with_no_headings_produces_no_sections():
    assert parse_rfc("just some text\nwith no structure\n") == []


# --- Front and back matter (task 2.4) ---

def test_abstract_is_a_section():
    sections = _sections("unpaginated")
    assert sections["abstract"].title == "Abstract"
    assert "stateless application-" in sections["abstract"].text


def test_abstract_ends_before_status_memo():
    assert "Internet Standards Track" not in _sections("unpaginated")["abstract"].text


@pytest.mark.parametrize(
    "heading",
    ["Index", "Authors' Addresses", "Author's Address", "Acknowledgments", "Acknowledgements",
     "Contributors", "References", "Normative References", "Intellectual Property"],
)
def test_back_matter_does_not_attach_to_the_last_section(heading):
    text = "1.  Last Section\n\n   Body text.\n\n{h}\n\n   Back matter.\n".format(h=heading)
    sections = parse_rfc(text)
    assert len(sections) == 1
    assert "Back matter" not in sections[0].text


@pytest.mark.parametrize(
    "marker",
    ["Internet Standards Track", "Copyright (c)", "many contributions", "accelerator",
     "Roy T. Fielding", "Rescorla", "Alvestrand"],
)
def test_excluded_text_is_not_in_any_section(marker):
    for name in ("unpaginated", "paginated"):
        for section in parse_rfc(_load(name)):
            assert marker not in section.text


def test_numbered_references_and_children_are_excluded():
    numbers = _sections("unpaginated")
    assert "6" not in numbers
    assert "6.1" not in numbers
    assert "6.2" not in numbers
    assert "4" not in _sections("paginated")


def test_unnumbered_security_considerations_is_its_own_section():
    sections = _sections("hierarchical")
    assert "many security issues" in sections["security"].text
    assert "many security issues" not in sections["2.2.2.8"].text


def test_centered_back_matter_is_recognized():
    text = "1.  Intro\n\n   Body.\n\n                                REFERENCES\n\n[1]  Item.\n"
    assert "Item" not in parse_rfc(text)[0].text


def test_security_and_iana_sections_are_kept():
    sections = _sections("unpaginated")
    assert sections["4"].title == "Security Considerations"
    assert sections["5"].title == "IANA Considerations"
    assert "Security Considerations" in {s.title for s in parse_rfc(_load("paginated"))}


def test_change_history_is_kept():
    assert "Many changes" in _sections("unpaginated")["B"].text


def test_heading_with_no_body_has_empty_text():
    assert _sections("unpaginated")["1"].text == ""


def test_figure_indentation_is_preserved():
    assert "     | Client | -----> | Server |" in _sections("unpaginated")["2"].text
