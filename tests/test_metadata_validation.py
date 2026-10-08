"""A found registry record does not establish fields absent from either side."""

import pytest

from bibtex_verifier.comparator import compare_entry

ENTRY = {"ID": "paper", "title": "Deep learning", "author": "Yann LeCun", "year": "2015"}
DATA = {"title": "Deep learning", "authors": ["Yann LeCun"], "year": 2015}


@pytest.mark.parametrize(
    "changes", [{"author": ""}, {"title": ""}, {"year": "twenty-fifteen"}, {"year": ""}]
)
def test_missing_or_invalid_input_is_not_ok(changes):
    result = compare_entry({**ENTRY, **changes}, api_data=DATA, source="crossref", match_score=100)
    assert result["status"] == "WARNING"
    assert result["issues"]


@pytest.mark.parametrize(
    "changes", [{"title": ""}, {"authors": []}, {"year": None}, {"year": "unknown"}]
)
def test_missing_or_invalid_source_is_unverified(changes):
    result = compare_entry(ENTRY, api_data={**DATA, **changes}, source="crossref", match_score=100)
    assert result["status"] == "UNVERIFIED"


def test_identifier_only_source_is_unverified():
    result = compare_entry(
        ENTRY, api_data={"doi": "10.1038/nature14539"}, source="crossref", match_score=0
    )
    assert result["status"] == "UNVERIFIED"
    assert len(result["issues"]) == 3


def test_webpage_does_not_require_paper_authors_or_year():
    entry = {"ID": "web", "ENTRYTYPE": "online", "title": "Lab docs"}
    result = compare_entry(entry, api_data={"title": "Lab docs"}, source="webpage", match_score=100)
    assert result["status"] == "OK"


def test_explicit_title_conflict_is_retained_when_other_source_fields_are_missing():
    result = compare_entry(
        ENTRY, api_data={"title": "Fictional Moon Factory"}, source="crossref", match_score=0
    )
    assert result["status"] == "ERROR"
    assert any(issue.startswith("来源元数据缺少") for issue in result["issues"])
