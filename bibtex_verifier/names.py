"""Compare author lists while accepting initials and compound surnames."""

import re
import unicodedata

from bibtexparser.customization import convert_to_unicode, splitname
from bibtexparser.latexenc import latex_to_unicode


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


def unicode_entry(record: dict) -> dict:
    """Keep protected institution groups when normalizing a parsed author field."""
    raw_authors = record.get("author", "")
    record = convert_to_unicode(record)
    if raw_authors:
        record["author"] = " and ".join(
            "{" + latex_to_unicode(name[1:-1]) + "}"
            if name.startswith("{") and name.endswith("}")
            else latex_to_unicode(name)
            for name in split_authors(raw_authors)
        )
    return record


def _person_parts(value: str) -> tuple[str, list[str], str]:
    if value.strip().startswith("{") and value.strip().endswith("}"):
        return normalize_name(value), [], ""
    suffix = ""
    words = value.split()
    if "," not in value and words and normalize_name(words[-1]) in {"jr", "sr", "ii", "iii", "iv"}:
        suffix = normalize_name(words[-1])
        value = " ".join(words[:-1])
    parsed = splitname(value, strict_mode=False)
    return normalize_name(" ".join(parsed["von"] + parsed["last"])), [
        token for n in parsed["first"] for token in normalize_name(n).split()
    ], normalize_name(" ".join(parsed["jr"])) or suffix


def name_parts(value: str) -> tuple[str, list[str]]:
    family, given, _ = _person_parts(value)
    return family, given


def same_person(left: str, right: str) -> bool:
    if normalize_name(left) == normalize_name(right):
        return True
    left_family, left_given, left_suffix = _person_parts(left)
    right_family, right_given, right_suffix = _person_parts(right)
    if left_suffix and right_suffix and left_suffix != right_suffix:
        return False
    # Display names lose the source's family/given boundary. A compound
    # surname on either side can restore that boundary on the other side.
    left_words, right_words = left_family.split(), right_family.split()
    if len(left_words) > len(right_words):
        full_right = right_given + right_words
        if full_right[-len(left_words):] == left_words:
            right_family, right_given = left_family, full_right[:-len(left_words)]
    elif len(right_words) > len(left_words):
        full_left = left_given + left_words
        if full_left[-len(right_words):] == right_words:
            left_family, left_given = right_family, full_left[:-len(right_words)]
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
    declared = [name for name in declared if name and normalize_name(name) not in {"others", "et al"}]
    candidates = {
        i: sorted(
            [j for j, actual in enumerate(api_authors) if same_person(name, actual)],
            key=lambda j: normalize_name(name) != normalize_name(api_authors[j]),
        )
        for i, name in enumerate(declared)
    }
    assigned = {}

    def assign(i, visited):
        for j in candidates[i]:
            if j in visited:
                continue
            visited.add(j)
            if j not in assigned or assign(assigned[j], visited):
                assigned[j] = i
                return True
        return False

    for i in range(len(declared)):
        assign(i, set())
    matched = {i: j for j, i in assigned.items()}
    remaining = [(j, name) for j, name in enumerate(api_authors) if j not in assigned]
    matched_indices = []
    unmatched = []
    missing_given = []
    for i, name in enumerate(declared):
        if i not in matched:
            unmatched.append(name)
        else:
            actual = api_authors[matched[i]]
            matched_indices.append(matched[i])
            if normalize_name(name) != normalize_name(actual) and (
                not name_parts(name)[1] or not name_parts(actual)[1]
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

    if not declared:
        add("INPUT_AUTHORS_EMPTY", "warning", "作者声明没有任何可核验的作者姓名")

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
