"""Rules from independently developed fixes must survive integration."""

import json

from bibtex_verifier.comparator import compare_entry
from bibtex_verifier.report import save_report


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


def test_nested_output_keeps_coverage_diagnostics(tmp_path):
    output = tmp_path / "reports" / "nested" / "audit.md"
    diagnostics = [{"code": "UNPARSED_ENTRY", "message": "Broken reference"}]
    save_report(
        [], bib_filename="paper.bib", output_path=output,
        save_json=True, diagnostics=diagnostics,
    )
    assert "UNPARSED_ENTRY" in output.read_text(encoding="utf-8")
    coverage = json.loads(output.with_suffix(".coverage.json").read_text(encoding="utf-8"))
    assert coverage["input_complete"] is False
    assert coverage["diagnostics"] == diagnostics
