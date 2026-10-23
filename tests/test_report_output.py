"""Completed verification results can be saved into a new nested directory."""

import json

import pytest

from bibtex_verifier.report import save_report


def test_nested_output_saves_markdown_and_json(tmp_path):
    results = [
        {
            "key": "paper",
            "status": "OK",
            "issues": [],
            "source": None,
            "bib_title": "Paper",
            "api_data": None,
        }
    ]
    output = tmp_path / "reports" / "new" / "audit.md"
    save_report(results, bib_filename="paper.bib", output_path=output, save_json=True)
    assert "Paper" in output.read_text()
    assert json.loads(output.with_suffix(".json").read_text()) == results


def test_output_directory_collision_preserves_existing_file(tmp_path):
    occupied = tmp_path / "reports"
    occupied.write_text("existing data")
    with pytest.raises(FileExistsError):
        save_report([], bib_filename="paper.bib", output_path=occupied / "audit.md")
    assert occupied.read_text() == "existing data"
