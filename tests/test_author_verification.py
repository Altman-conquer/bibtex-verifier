"""Author identity uses the full list and tolerates supported formatting variants."""

import pytest

from bibtex_verifier.comparator import compare_entry
from bibtex_verifier.loader import load_bib


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


@pytest.mark.parametrize("declared,actual", [("Smith, J.P.", ["John Paul Smith"]), ("Smith, J.-P.", ["Jean-Paul Smith"])])
def test_compact_initials_match_the_corresponding_full_given_names(declared, actual):
    assert compare(declared, actual)["status"] == "OK"


def test_initial_match_does_not_consume_the_only_match_for_a_full_name():
    assert compare("Smith, J. and Smith, John", ["John Smith", "Jane Smith"])["status"] == "WARNING"


def test_truncation_without_an_actual_author_is_not_ok():
    assert compare("others", ["Alice Smith"])["status"] == "WARNING"


def test_corporate_author_survives_real_bibtex_parsing(tmp_path):
    bib = tmp_path / "paper.bib"
    bib.write_text('@article{org,title={Paper},author={{Research and Development Institute} and Smith, Alice},year={2025}}')
    entry = load_bib(bib)[0]
    result = compare_entry(entry, api_data={"title": "Paper", "authors": ["Research and Development Institute", "Alice Smith"], "year": 2025}, source="crossref", match_score=100)
    assert result["status"] == "OK"
