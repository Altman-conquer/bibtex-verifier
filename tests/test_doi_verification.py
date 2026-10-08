"""Identifier conflicts must remain visible after successful title lookup."""

import json
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from bibtex_verifier.apis import (
    ApiRequestError,
    crossref_by_doi,
    datacite_by_doi,
    normalize_doi,
)
from bibtex_verifier.cli import app
from bibtex_verifier.comparator import compare_entry

DOI = "10.1038/nature14539"
OA_RECORD = {
    "title": "Deep learning",
    "publication_year": 2015,
    "authorships": [{"author": {"display_name": "Yann LeCun"}}],
    "doi": f"https://doi.org/{DOI}",
    "_match_score": 100,
}


@pytest.mark.parametrize("value", [DOI, f" https://doi.org/{DOI} ", f"http://dx.doi.org/{DOI}", f"DOI: {DOI}"])
def test_common_doi_forms_are_normalized(value):
    assert normalize_doi(value) == DOI


def test_registry_requests_strip_resolver_prefix():
    with patch("bibtex_verifier.apis.http_get", return_value=None) as get:
        crossref_by_doi(f"https://doi.org/{DOI}")
        assert get.call_args.args[0] == "https://api.crossref.org/works/10.1038%2Fnature14539"
        datacite_by_doi(f"https://doi.org/{DOI}")
        assert get.call_args.args[0] == f"https://api.datacite.org/dois/{DOI}"


def run_fallback(tmp_path, doi, crossref_error=None, returned_doi=DOI):
    bib = tmp_path / "paper.bib"
    bib.write_text("@article{paper, title={Deep learning}, author={LeCun, Yann}, year={2015}, doi={" + doi + "}}", encoding="utf-8")
    record = {**OA_RECORD, "doi": f"https://doi.org/{returned_doi}" if returned_doi else ""}
    cr_kwargs = {"side_effect": crossref_error} if crossref_error else {"return_value": None}
    with patch("bibtex_verifier.cli.crossref_by_doi", **cr_kwargs), patch("bibtex_verifier.cli.datacite_by_doi", return_value=None), patch("bibtex_verifier.cli.oa_search", return_value=record), patch("bibtex_verifier.cli.time.sleep"):
        invocation = CliRunner().invoke(app, [str(bib), "--json"])
    result = json.loads(bib.with_suffix(".report.json").read_text(encoding="utf-8"))[0]
    markdown = bib.with_suffix(".report.md").read_text(encoding="utf-8")
    return invocation, result, markdown


def test_wrong_doi_is_not_hidden_by_matching_title(tmp_path):
    invocation, result, markdown = run_fallback(tmp_path, "10.9999/nonexistent")
    assert invocation.exit_code == 1
    assert result["status"] == "ERROR"
    assert result["bib_doi"] == "10.9999/nonexistent"
    assert any("DOI 不匹配" in issue for issue in result["issues"])
    assert f"https://doi.org/{DOI}" in markdown
    assert "10.9999/nonexistent" in markdown


def test_matching_title_without_doi_evidence_is_not_clean_ok(tmp_path):
    _, result, _ = run_fallback(tmp_path, DOI, returned_doi="")
    assert result["status"] == "WARNING"
    assert any("DOI" in issue for issue in result["issues"])


def test_registry_miss_remains_visible_even_when_index_lists_same_doi(tmp_path):
    _, result, _ = run_fallback(tmp_path, DOI)
    assert result["status"] == "WARNING"
    assert any("DOI" in issue for issue in result["issues"])


def test_doi_lookup_failure_is_preserved_after_title_match(tmp_path):
    _, result, _ = run_fallback(tmp_path, DOI, ApiRequestError("HTTP 429"))
    assert result["status"] == "WARNING"
    assert result["api_errors"] == ["CrossRef: HTTP 429"]
    assert any("429" in issue for issue in result["issues"])


def test_doi_comparison_accepts_case_and_resolver_variations():
    result = compare_entry({"ID": "paper", "doi": "DOI: 10.1000/ABC", "title": "Paper"}, api_data={"title": "Paper", "doi": "https://doi.org/10.1000/abc"}, source="crossref", match_score=100)
    assert result["status"] == "OK"
