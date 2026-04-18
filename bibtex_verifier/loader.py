"""BibTeX file loading and parsing."""

from pathlib import Path

import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode


def load_bib(path: Path) -> list[dict]:
    """Parse a .bib file and return a list of entry dicts.

    Args:
        path: Path to the .bib file.

    Returns:
        List of dicts, each representing one BibTeX entry.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    if not path.exists():
        raise FileNotFoundError(f"BibTeX file not found: {path}")
    parser = BibTexParser(common_strings=True)
    parser.customization = convert_to_unicode
    with open(path, encoding="utf-8") as f:
        db = bibtexparser.load(f, parser=parser)
    return db.entries
