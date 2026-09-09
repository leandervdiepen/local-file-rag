"""`CitationReader` against text arriving one piece at a time."""

from __future__ import annotations

import pytest

from sidecar.domain.citations import Citation, CitationReader

PAGES = {1: "a:1", 2: "b:4"}


def read(chunks: list[str]) -> tuple[str, list[Citation]]:
    """Everything a panel would render, and every citation it would be given."""
    reader = CitationReader(PAGES)
    text: list[str] = []
    found: list[Citation] = []
    for chunk in chunks:
        rendered, citations = reader.feed(chunk)
        text.append(rendered)
        found.extend(citations)
    text.append(reader.flush())
    return "".join(text), found


def test_a_citation_is_lifted_out_of_the_text() -> None:
    text, found = read(["Egress was 18.4 TB [1]."])

    assert text == "Egress was 18.4 TB ."
    assert found == [Citation(index=1, page_id="a:1")]


def test_a_citation_split_across_chunks_is_still_one_citation() -> None:
    text, found = read(["Egress was 18.4 TB ", "[", "1", "]", "."])

    assert text == "Egress was 18.4 TB ."
    assert found == [Citation(index=1, page_id="a:1")]


def test_every_character_comes_out_once_and_in_order() -> None:
    answer = "The invoice [2] lists egress at 18.4 TB [1] and support [2]."
    whole, from_whole = read([answer])
    letter_by_letter, from_letters = read(list(answer))

    assert whole == letter_by_letter
    assert from_whole == from_letters
    assert [c.index for c in from_whole] == [2, 1, 2]


def test_a_bracket_that_is_not_a_citation_is_left_alone() -> None:
    text, found = read(["See [table 3] on the page."])

    assert text == "See [table 3] on the page."
    assert found == []


def test_a_citation_pointing_at_a_page_that_was_not_sent_stays_as_text() -> None:
    text, found = read(["Something [9] happened."])

    assert text == "Something [9] happened."
    assert found == []


def test_an_unclosed_bracket_at_the_end_of_the_stream_is_text() -> None:
    text, found = read(["Cut off mid ["])

    assert text == "Cut off mid ["
    assert found == []


def test_an_answer_with_no_citations_is_untouched() -> None:
    text, found = read(["That is not in your files."])

    assert text == "That is not in your files."
    assert found == []


@pytest.mark.parametrize("noise", ["[]", "[ 1]", "[1a]", "[-1]"])
def test_things_that_look_like_citations_but_are_not(noise: str) -> None:
    text, found = read([f"before {noise} after"])

    assert text == f"before {noise} after"
    assert found == []
