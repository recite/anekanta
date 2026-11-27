import re

import pytest

from anekanta.extract import find_passages
from anekanta.matching import author_year_pattern


@pytest.mark.parametrize(
    "citation",
    [
        "Chattopadhyay and Duflo (2004)",
        "(Chattopadhyay & Duflo, 2004)",
        "(Chattopad-\nhyay and Duflo 2004b)",
    ],
)
def test_pair_search_keeps_original_passage(citation):
    pattern = re.compile(
        author_year_pattern("Chattopadhyay", "2004", "Duflo"), re.IGNORECASE
    )
    sentence = f"See {citation} for the road results."
    (passage,) = find_passages("Title\f" + sentence, pattern)
    assert passage["quote"] == " ".join(sentence.split())
    assert passage["location"] == {"pdf_page": 2}
    assert passage["review"] == "unchecked"


def test_pair_search_requires_both_names_and_the_year():
    pattern = re.compile(
        author_year_pattern("Chattopadhyay", "2004", "Duflo"), re.IGNORECASE
    )
    for citation in [
        "Chattopadhyay (2004)",
        "Duflo and Chattopadhyay (2004)",
        "Chattopadhyay and Duflo (2003)",
        "Chattopadhyay and Duflo (20040)",
    ]:
        assert not pattern.search(citation)
