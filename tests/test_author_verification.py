"""Author identity uses the full list and tolerates supported formatting variants."""

import pytest

from bibtex_verifier.comparator import compare_entry


def compare(declared, actual, **kwargs):
    return compare_entry(
        {"ID": "paper", "title": "Paper", "year": "2025", "author": declared},
        api_data={"title": "Paper", "year": 2025, "authors": actual},
        source="crossref",
        match_score=100,
        **kwargs,
    )


@pytest.mark.parametrize(
    "declared,actual",
    [
        ("LeCun, Bob", ["Yann LeCun"]),
        ("Li, Wei", ["Wei Liu"]),
        ("LeCun, Yann and Smith, Alice", ["Yann LeCun", "Yoshua Bengio"]),
    ],
)
def test_explicit_person_conflicts_are_errors(declared, actual):
    assert compare(declared, actual, author_threshold=0)["status"] == "ERROR"


def test_one_missing_coauthor_is_reported():
    result = compare("Yann LeCun", ["Yann LeCun", "Yoshua Bengio"])
    assert result["status"] == "WARNING"
    assert any("Bengio" in issue for issue in result["issues"])


@pytest.mark.parametrize(
    "declared,actual",
    [
        ("van der Waals, Johannes", ["Johannes van der Waals"]),
        ("LeCun, Y.", ["Yann LeCun"]),
        ("{World Health Organization}", ["World Health Organization"]),
        (
            "{Research and Development Institute} and Alice Smith",
            ["Research and Development Institute", "Alice Smith"],
        ),
        ("LeCun, Yann and others", ["Yann LeCun", "Yoshua Bengio"]),
    ],
)
def test_supported_variants_do_not_create_false_errors(declared, actual):
    assert compare(declared, actual)["status"] == "OK"


def test_author_order_difference_is_a_review_item():
    result = compare("Yoshua Bengio and Yann LeCun", ["Yann LeCun", "Yoshua Bengio"])
    assert result["status"] == "WARNING"


def test_family_name_alone_does_not_establish_person_identity():
    assert compare("Smith", ["Alice Smith"])["status"] == "WARNING"
