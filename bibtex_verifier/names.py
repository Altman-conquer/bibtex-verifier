"""Compare author lists while accepting initials and compound surnames."""

import re
import unicodedata

from bibtexparser.customization import splitname


def normalize_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold().replace("ß", "ss"))
    value = "".join(c for c in value if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^\w\s]", " ", value).split())


def split_authors(value: str) -> list[str]:
    """Treat brace-protected institution names as one author, including 'and'."""
    parts = []
    depth = 0
    start = 0
    scanned = 0
    for match in re.finditer(r"\s+and\s+", value, re.I):
        for character in value[scanned : match.start()]:
            depth += (character == "{") - (character == "}")
        if depth == 0:
            parts.append(value[start : match.start()].strip())
            start = match.end()
        scanned = match.end()
    parts.append(value[start:].strip())
    return parts


def name_parts(value: str) -> tuple[str, list[str]]:
    if value.strip().startswith("{") and value.strip().endswith("}"):
        return normalize_name(value), []
    parsed = splitname(value, strict_mode=False)
    return normalize_name(" ".join(parsed["von"] + parsed["last"])), [
        normalize_name(n) for n in parsed["first"]
    ]


def same_person(left: str, right: str) -> bool:
    if normalize_name(left) == normalize_name(right):
        return True
    left_family, left_given = name_parts(left)
    right_family, right_given = name_parts(right)
    if left_family != right_family:
        return False
    for first, second in zip(left_given, right_given):
        if first != second and not (
            first and second and first[0] == second[0] and min(len(first), len(second)) == 1
        ):
            return False
    return True


def author_checks(bib_authors: str, api_authors: list[str]) -> list[dict]:
    declared = split_authors(bib_authors)
    abbreviated = any(normalize_name(name) in {"others", "et al"} for name in declared)
    declared = [name for name in declared if normalize_name(name) not in {"others", "et al"}]
    remaining = list(enumerate(api_authors))
    matched_indices = []
    unmatched = []
    missing_given = []
    for name in declared:
        match = next(((i, actual) for i, actual in remaining if same_person(name, actual)), None)
        if match is None:
            unmatched.append(name)
        else:
            remaining.remove(match)
            matched_indices.append(match[0])
            if normalize_name(name) != normalize_name(match[1]) and (
                not name_parts(name)[1] or not name_parts(match[1])[1]
            ):
                missing_given.append(name)
    issues = []

    def add(code, severity, message):
        issues.append(
            {
                "code": code,
                "field": "authors",
                "severity": severity,
                "input_value": bib_authors,
                "source_value": api_authors,
                "message": message,
            }
        )

    if unmatched:
        add("AUTHOR_MISMATCH", "error", "作者列表不匹配：未匹配作者 " + "; ".join(unmatched))
    if remaining and not abbreviated:
        add(
            "AUTHORS_INCOMPLETE",
            "warning",
            "作者数量或列表不完整：来源中还有 " + "; ".join(name for _, name in remaining),
        )
    if matched_indices != sorted(matched_indices) and not unmatched:
        add("AUTHOR_ORDER", "warning", "作者顺序与来源不同，请核查版本或团队署名")
    if missing_given:
        add(
            "AUTHOR_GIVEN_NAME_MISSING",
            "warning",
            "作者名字信息不足，不能仅凭同姓确认身份：" + "; ".join(missing_given),
        )
    return issues


def author_issues(bib_authors: str, api_authors: list[str]) -> list[str]:
    return [item["message"] for item in author_checks(bib_authors, api_authors)]
