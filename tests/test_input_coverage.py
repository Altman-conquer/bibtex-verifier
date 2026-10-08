"""Incomplete input must remain visible in saved reports, including zero results."""

import json
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from bibtex_verifier.cli import app
from bibtex_verifier.loader import inspect_bib, load_bib

BIB = "@article{real,title={Deep learning},author={Yann LeCun},year={2015},doi={10.1038/nature14539}}\n"
RAW = {
    "title": ["Deep learning"],
    "author": [{"given": "Yann", "family": "LeCun"}],
    "issued": {"date-parts": [[2015]]},
}


@pytest.mark.parametrize(
    "text", ["@article{broken,title={Unclosed", BIB + "@article{broken,title={Unclosed", BIB + BIB]
)
def test_cli_saves_incomplete_coverage_and_fails(tmp_path, text):
    bib = tmp_path / "paper.bib"
    bib.write_text(text, encoding="utf-8")
    with (
        patch("bibtex_verifier.cli.crossref_by_doi", return_value=RAW),
        patch("bibtex_verifier.cli.time.sleep"),
    ):
        invocation = CliRunner().invoke(app, [str(bib), "--json"])
    assert invocation.exit_code == 1
    coverage = json.loads(bib.with_suffix(".report.coverage.json").read_text())
    results = json.loads(bib.with_suffix(".report.json").read_text())
    assert not coverage["input_complete"]
    assert coverage["diagnostics"]
    assert coverage["checked_entries"] == len(results)
    markdown = bib.with_suffix(".report.md").read_text()
    assert "解析覆盖完整：否" in markdown
    assert coverage["diagnostics"][0]["code"] in markdown


def test_nonstandard_entries_and_biblatex_dates_are_kept(tmp_path):
    bib = tmp_path / "paper.bib"
    bib.write_text(
        BIB + "@online{web,title={Docs},url={https://example.org},date={2025-04-12}}",
        encoding="utf-8-sig",
    )
    parsed = inspect_bib(bib)
    assert not parsed.diagnostics
    assert [entry["ID"] for entry in parsed.entries] == ["real", "web"]
    assert parsed.entries[1]["year"] == "2025"
    assert load_bib(bib) == parsed.entries


def test_clean_cli_preserves_results_list_and_marks_complete(tmp_path):
    bib = tmp_path / "paper.bib"
    bib.write_text(BIB)
    with (
        patch("bibtex_verifier.cli.crossref_by_doi", return_value=RAW),
        patch("bibtex_verifier.cli.time.sleep"),
    ):
        invocation = CliRunner().invoke(app, [str(bib), "--json"])
    assert invocation.exit_code == 0
    assert isinstance(json.loads(bib.with_suffix(".report.json").read_text()), list)
    assert json.loads(bib.with_suffix(".report.coverage.json").read_text())["input_complete"]


def test_damage_after_free_text_is_not_silently_ignored(tmp_path):
    bib = tmp_path / "paper.bib"
    bib.write_text(BIB + "a note @article{broken,title={Never closed")
    parsed = inspect_bib(bib)
    assert [entry["ID"] for entry in parsed.entries] == ["real"]
    assert any(item["code"] == "UNPARSED_ENTRY" for item in parsed.diagnostics)


def test_comment_examples_do_not_become_references_or_change_source_lines(tmp_path):
    bib = tmp_path / "paper.bib"
    bib.write_text('@comment{\n@article{example,title={Ignore this template}}\n}\n% @article{line,title={Ignore too}}\n' + BIB)
    parsed = inspect_bib(bib)
    assert not parsed.diagnostics
    assert [entry["ID"] for entry in parsed.entries] == ["real"]
    assert parsed.entries[0]["_source_line"] == 5


def test_comment_like_text_inside_fields_is_preserved(tmp_path):
    bib = tmp_path / "paper.bib"
    bib.write_text('@article{real,title={A 50% effect with @comment text},author={Alice Smith},year={2025}}')
    parsed = inspect_bib(bib)
    assert not parsed.diagnostics
    assert parsed.entries[0]["title"] == "A 50% effect with @comment text"
