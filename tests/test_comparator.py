"""Tests for the field comparator."""

from bibtex_verifier.comparator import compare_entry

GOOD_ENTRY = {
    "ID": "Vaswani2017",
    "title": "Attention Is All You Need",
    "author": "Vaswani, Ashish and Shazeer, Noam",
    "year": "2017",
    "doi": "",
}
API_DATA = {
    "title": "Attention Is All You Need",
    "year": 2017,
    "authors": ["Ashish Vaswani", "Noam Shazeer"],
    "venue": "NeurIPS",
}


def test_compare_ok_entry():
    result = compare_entry(GOOD_ENTRY, api_data=API_DATA, source="openalex", match_score=98)
    assert result["status"] == "OK"
    assert result["issues"] == []
    assert result["key"] == "Vaswani2017"
    assert result["source"] == "openalex"
    assert result["match_score"] == 98


def test_compare_wrong_year_large_diff():
    entry = {**GOOD_ENTRY, "year": "2013"}
    result = compare_entry(entry, api_data=API_DATA, source="openalex", match_score=98)
    assert result["status"] == "WARNING"
    assert any("年份" in i for i in result["issues"])


def test_compare_wrong_year_one_diff():
    entry = {**GOOD_ENTRY, "year": "2016"}
    result = compare_entry(entry, api_data=API_DATA, source="openalex", match_score=98)
    assert result["status"] == "WARNING"
    assert any("预印本" in i or "年份" in i for i in result["issues"])


def test_compare_wrong_author():
    entry = {**GOOD_ENTRY, "author": "Smith, John"}
    result = compare_entry(entry, api_data=API_DATA, source="openalex", match_score=98)
    assert result["status"] == "ERROR"
    assert any("作者" in i for i in result["issues"])


def test_compare_missing_year():
    entry = {k: v for k, v in GOOD_ENTRY.items() if k != "year"}
    result = compare_entry(entry, api_data=API_DATA, source="openalex", match_score=98)
    assert result["status"] == "WARNING"
    assert any("年份" in i for i in result["issues"])


def test_compare_wrong_title():
    entry = {**GOOD_ENTRY, "title": "Completely Different Paper Title Here"}
    result = compare_entry(entry, api_data=API_DATA, source="openalex", match_score=60)
    assert result["status"] == "ERROR"
    assert any("标题" in i for i in result["issues"])


def test_compare_not_found_returns_not_found():
    result = compare_entry(GOOD_ENTRY, api_data=None, source=None, match_score=0)
    assert result["status"] == "NOT_FOUND"
    assert result["api_data"] is None


def test_compare_author_count_too_few():
    entry = {**GOOD_ENTRY, "author": "Vaswani, Ashish"}
    api = {**API_DATA, "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar", "Jakob Uszkoreit"]}
    result = compare_entry(entry, api_data=api, source="openalex", match_score=98)
    assert result["status"] == "WARNING"
    assert any("作者数量" in i for i in result["issues"])


def test_compare_custom_thresholds():
    entry = {**GOOD_ENTRY, "author": "Smith, John"}
    result = compare_entry(
        entry,
        api_data=API_DATA,
        source="openalex",
        match_score=98,
        author_threshold=10,  # very low threshold - should pass
    )
    assert result["status"] == "OK"
