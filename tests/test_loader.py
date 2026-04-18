from pathlib import Path

import pytest

from bibtex_verifier.loader import load_bib


def test_load_bib_returns_entries(tmp_path):
    bib = tmp_path / "test.bib"
    bib.write_text(
        """
@article{Smith2020,
  title  = {A Great Paper},
  author = {Smith, John},
  year   = {2020},
}
""",
        encoding="utf-8",
    )
    entries = load_bib(bib)
    assert len(entries) == 1
    assert entries[0]["ID"] == "Smith2020"
    assert "title" in entries[0]


def test_load_bib_multiple_entries(tmp_path):
    bib = tmp_path / "multi.bib"
    bib.write_text(
        """
@article{A2020,
  title = {Paper A},
  author = {Alice, Ann},
  year = {2020},
}
@inproceedings{B2021,
  title = {Paper B},
  author = {Bob, Bill},
  year = {2021},
}
""",
        encoding="utf-8",
    )
    entries = load_bib(bib)
    assert len(entries) == 2
    ids = {e["ID"] for e in entries}
    assert ids == {"A2020", "B2021"}


def test_load_bib_missing_file():
    with pytest.raises(FileNotFoundError):
        load_bib(Path("nonexistent.bib"))


def test_load_bib_with_doi(tmp_path):
    bib = tmp_path / "doi.bib"
    bib.write_text(
        """
@article{Vaswani2017,
  title  = {Attention Is All You Need},
  author = {Vaswani, Ashish and Shazeer, Noam},
  year   = {2017},
  doi    = {10.48550/arxiv.1706.03762},
}
""",
        encoding="utf-8",
    )
    entries = load_bib(bib)
    assert len(entries) == 1
    assert entries[0].get("doi") == "10.48550/arxiv.1706.03762"
