"""BibTeX file loading and parsing."""

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode


@dataclass
class BibInput:
    entries: list[dict]
    diagnostics: list[dict]


def inspect_bib(path: Path) -> BibInput:
    """Retain parsing diagnostics, nonstandard entries and source locations."""
    if not path.exists():
        raise FileNotFoundError(f"BibTeX file not found: {path}")
    text = path.read_text(encoding="utf-8-sig")
    parser = BibTexParser(common_strings=True, ignore_nonstandard_types=False)
    parser.customization = convert_to_unicode
    diagnostics = []
    try:
        db = parser.parse(text)
    except Exception as exc:
        db = parser.bib_database
        diagnostics.append(
            {"code": "PARSE_ERROR", "file": str(path), "message": str(exc), "severity": "error"}
        )
    for comment in db.comments:
        if re.search(r"(?im)^\s*@\w+\s*[{(]", comment):
            diagnostics.append(
                {
                    "code": "UNPARSED_ENTRY",
                    "file": str(path),
                    "message": comment[:180],
                    "severity": "error",
                }
            )
    if not db.entries:
        diagnostics.append(
            {
                "code": "NO_ENTRIES",
                "file": str(path),
                "message": "没有解析出引用，未完成核验",
                "severity": "error",
            }
        )
    for key, count in Counter(entry["ID"] for entry in db.entries).items():
        if count > 1:
            diagnostics.append(
                {
                    "code": "DUPLICATE_KEY",
                    "file": str(path),
                    "message": f"重复引用键 {key}（{count} 条）",
                    "severity": "error",
                }
            )
    used_offsets = {}
    for entry in db.entries:
        key = entry["ID"]
        matches = list(re.finditer(r"@\w+\s*[{(]\s*" + re.escape(key) + r"\s*,", text, re.I))
        index = used_offsets.get(key, 0)
        entry["_source_file"] = str(path.resolve())
        entry["_source_line"] = (
            text.count("\n", 0, matches[index].start()) + 1 if index < len(matches) else None
        )
        used_offsets[key] = index + 1
        if not entry.get("year") and re.match(r"^\d{4}(?:-|$)", entry.get("date", "")):
            entry["year"] = entry["date"][:4]
    return BibInput(db.entries, diagnostics)


def load_bib(path: Path) -> list[dict]:
    """Parse a .bib file and return a list of entry dicts.

    Args:
        path: Path to the .bib file.

    Returns:
        List of dicts, each representing one BibTeX entry.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    return inspect_bib(path).entries
