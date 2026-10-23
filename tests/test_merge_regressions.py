"""Rules from independently developed fixes must survive integration."""

from bibtex_verifier.comparator import compare_entry


def test_doi_conflict_stays_error_when_source_metadata_is_incomplete():
    result = compare_entry(
        {"ID": "paper", "title": "Paper", "doi": "10.1000/wrong"},
        api_data={"title": "Paper", "doi": "10.1000/right"},
        source="openalex",
        match_score=100,
        doi_lookup_issue="DOI lookup failed",
    )
    assert result["status"] == "ERROR"
    assert any(issue.startswith("DOI 不匹配") for issue in result["issues"])
    assert any(issue.startswith("来源元数据缺少") for issue in result["issues"])
