"""Tests for Markdown and JSON report generation."""

from bibtex_verifier.report import build_markdown_report

RESULTS = [
    {
        "key": "A",
        "status": "OK",
        "issues": [],
        "source": "openalex",
        "match_score": 95,
        "bib_title": "Title A",
        "api_data": {"title": "Title A", "year": 2020, "authors": ["Ann Alice"], "venue": "ICML"},
    },
    {
        "key": "B",
        "status": "ERROR",
        "issues": ["标题不匹配 (相似度 55%):\n    bib  : Wrong Title\n    实际 : Correct Title"],
        "source": "openalex",
        "match_score": 55,
        "bib_title": "Wrong Title",
        "api_data": None,
    },
    {
        "key": "C",
        "status": "WARNING",
        "issues": ["年份偏差 2 年: bib=2018, 实际=2020"],
        "source": "crossref",
        "match_score": 99,
        "bib_title": "Some Paper",
        "api_data": {"title": "Some Paper", "year": 2020, "authors": [], "venue": "Nature"},
    },
    {
        "key": "D",
        "status": "NOT_FOUND",
        "issues": ["在 OpenAlex / CrossRef 中未找到匹配论文（标题相似度不足）"],
        "source": None,
        "match_score": 0,
        "bib_title": "Completely Fake Hallucinated Paper Title",
        "api_data": None,
    },
]


def test_report_contains_summary_table():
    md = build_markdown_report(RESULTS, bib_filename="test.bib")
    assert "| ✅" in md
    assert "| ❌" in md
    assert "| ⚠️" in md
    assert "| 🔍" in md


def test_report_lists_error_entries():
    md = build_markdown_report(RESULTS, bib_filename="test.bib")
    assert "标题不匹配" in md
    assert "Wrong Title" in md


def test_report_lists_not_found_entries():
    md = build_markdown_report(RESULTS, bib_filename="test.bib")
    assert "Hallucinated" in md or "NOT_FOUND" in md or "D" in md


def test_report_contains_bib_filename():
    md = build_markdown_report(RESULTS, bib_filename="my_paper.bib")
    assert "my_paper.bib" in md


def test_report_counts_are_correct():
    md = build_markdown_report(RESULTS, bib_filename="test.bib")
    assert "| 1 |" in md  # OK count
    assert "| 1 |" in md  # ERROR, WARNING, NOT_FOUND each 1


def test_report_shows_api_venue():
    md = build_markdown_report(RESULTS, bib_filename="test.bib")
    assert "Nature" in md


def test_empty_results():
    md = build_markdown_report([], bib_filename="empty.bib")
    assert "0" in md
