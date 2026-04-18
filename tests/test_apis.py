"""Tests for OpenAlex and CrossRef API clients."""

from unittest.mock import patch

from bibtex_verifier.apis import (
    crossref_by_doi,
    crossref_extract,
    normalize_title,
    oa_extract,
    oa_search,
)
from tests.conftest import CR_RESPONSE, OA_LOW_SCORE_RESPONSE, OA_RESPONSE


def test_normalize_title_removes_latex():
    title = r"{\em Attention} Is {All} You Need"
    result = normalize_title(title)
    assert "{" not in result
    assert "}" not in result
    assert result == result.lower()


def test_normalize_title_removes_punctuation():
    result = normalize_title("Hello, World! A: Test")
    assert "," not in result
    assert "!" not in result
    assert ":" not in result


def test_oa_search_returns_best_match():
    with patch("bibtex_verifier.apis.http_get", return_value=OA_RESPONSE):
        result = oa_search("Attention Is All You Need")
    assert result is not None
    assert "Attention" in result["title"]
    assert "_match_score" in result
    assert result["_match_score"] >= 82


def test_oa_search_returns_none_on_low_score():
    with patch("bibtex_verifier.apis.http_get", return_value=OA_LOW_SCORE_RESPONSE):
        result = oa_search("Attention Is All You Need")
    assert result is None


def test_oa_search_returns_none_on_empty_results():
    with patch("bibtex_verifier.apis.http_get", return_value={"results": []}):
        result = oa_search("Attention Is All You Need")
    assert result is None


def test_oa_search_returns_none_on_api_failure():
    with patch("bibtex_verifier.apis.http_get", return_value=None):
        result = oa_search("Attention Is All You Need")
    assert result is None


def test_oa_extract_fields():
    paper = OA_RESPONSE["results"][0]
    paper["_match_score"] = 98
    data = oa_extract(paper)
    assert data["title"] == "Attention Is All You Need"
    assert data["year"] == 2017
    assert "Ashish Vaswani" in data["authors"]
    assert data["venue"] == "NeurIPS"
    assert "doi" in data


def test_crossref_by_doi_success():
    with patch("bibtex_verifier.apis.http_get", return_value=CR_RESPONSE):
        result = crossref_by_doi("10.48550/arxiv.1706.03762")
    assert result is not None
    assert result["title"][0] == "Attention Is All You Need"


def test_crossref_by_doi_not_found():
    with patch("bibtex_verifier.apis.http_get", return_value=None):
        result = crossref_by_doi("10.9999/fake.doi")
    assert result is None


def test_crossref_extract_fields():
    msg = CR_RESPONSE["message"]
    data = crossref_extract(msg)
    assert data["title"] == "Attention Is All You Need"
    assert data["year"] == 2017
    assert "Vaswani Ashish" in data["authors"]
    assert "Advances in Neural" in data["venue"]
