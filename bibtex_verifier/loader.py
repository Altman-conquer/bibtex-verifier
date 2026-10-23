"""BibTeX file loading and parsing."""

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from bibtexparser.bparser import BibTexParser

from bibtex_verifier.names import unicode_entry


@dataclass
class BibInput:
    entries: list[dict]
    diagnostics: list[dict]


def _declaration_end(text: str, start: int):
    opening = text[start]
    braces, parentheses = (1, 0) if opening == "{" else (0, 1)
    quoted = False
    i = start + 1
    while i < len(text):
        char = text[i]
        if char == "\\":
            i += 2
            continue
        if char == '"' and not braces:
            quoted = not quoted
        elif not quoted:
            if char == "{":
                braces += 1
            elif char == "}":
                braces -= 1
                if opening == "{" and braces == 0:
                    return i + 1
            elif not braces and char == "(":
                parentheses += 1
            elif not braces and char == ")":
                parentheses -= 1
                if opening == "(" and parentheses == 0:
                    return i + 1
        i += 1
    return None


def mask_bib_comments(text: str) -> str:
    """Hide explicit/line comments without moving entry positions or line numbers."""
    masked = list(text)
    position = 0
    pattern = re.compile(r"@([A-Za-z]+)\b\s*([({])?|%")
    while match := pattern.search(text, position):
        if match.group() == "%" or (match.group(1).lower() == "comment" and not match.group(2)):
            end = text.find("\n", match.start())
            end = len(text) if end == -1 else end
        elif match.group(2):
            end = _declaration_end(text, match.end() - 1)
            if end is None:
                position = match.end()
                continue
        else:
            position = match.end()
            continue
        if match.group() == "%" or match.group(1).lower() == "comment":
            for i in range(match.start(), end):
                if text[i] != "\n":
                    masked[i] = " "
        position = end
    return "".join(masked)


def inspect_bib(path: Path) -> BibInput:
    """Retain parsing diagnostics, nonstandard entries and source locations."""
    if not path.exists():
        raise FileNotFoundError(f"BibTeX file not found: {path}")
    text = path.read_text(encoding="utf-8-sig")
    parsed_text = mask_bib_comments(text)
    parser = BibTexParser(common_strings=True, ignore_nonstandard_types=False)
    parser.customization = unicode_entry
    diagnostics = []
    try:
        db = parser.parse(parsed_text)
    except Exception as exc:
        db = parser.bib_database
        diagnostics.append(
            {"code": "PARSE_ERROR", "file": str(path), "message": str(exc), "severity": "error"}
        )
    for comment in db.comments:
        # A broken declaration may be missing its opening delimiter or type.
        # Keep ordinary free text and email addresses outside the diagnostics.
        if re.search(r"(?<!\w)@(?:\w+\s*[{(]|\w+[ \t,]+[^@\r\n]*=|[{(])", comment):
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
        matches = list(re.finditer(r"@\w+\s*[{(]\s*" + re.escape(key) + r"\s*,", parsed_text, re.I))
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
