"""Field-level comparison between BibTeX entries and API data."""

import re
from typing import Optional

from rapidfuzz import fuzz

from bibtex_verifier.apis import normalize_doi, normalize_title
from bibtex_verifier.names import (
    author_issues,
    name_parts,
    normalize_name,
    same_person,
    split_authors,
)

# Default thresholds (can be overridden per call)
DEFAULT_TITLE_THRESHOLD = 82
DEFAULT_AUTHOR_THRESHOLD = 72


def valid_year(value) -> bool:
    return bool(re.fullmatch(r"\d{4}", str(value).strip())) and int(value) > 0


def compare_entry(
    entry: dict,
    *,
    api_data: Optional[dict],
    source: Optional[str],
    match_score: int,
    title_threshold: int = DEFAULT_TITLE_THRESHOLD,
    author_threshold: int = DEFAULT_AUTHOR_THRESHOLD,
    api_errors: Optional[list[str]] = None,
    doi_lookup_issue: Optional[str] = None,
) -> dict:
    """Compare a single BibTeX entry against API-retrieved data.

    Args:
        entry: BibTeX entry dict (from loader.load_bib).
        api_data: Normalised dict returned by oa_extract / crossref_extract,
                  or None if the paper was not found.
        source: "openalex" | "crossref" | None.
        match_score: Fuzzy title match score used when locating the paper.
        title_threshold: Minimum score to consider titles matching.
        author_threshold: Minimum score to consider author last-names matching.
        doi_lookup_issue: A registry miss or incomplete DOI lookup that must
                         remain visible after a title-search fallback.

    Returns:
        Dict with keys: key, status, issues, source, match_score,
        bib_title, api_data.
    """
    key = entry.get("ID", "unknown")
    bib_title = entry.get("title", "")
    bib_year = entry.get("year", "")
    bib_authors = entry.get("author", "")
    bib_doi = entry.get("doi", "")

    if api_data is None:
        return {
            "key": key,
            "status": "UNVERIFIED" if api_errors else "NOT_FOUND",
            "issues": [f"未完成核验：{'; '.join(api_errors)}"] if api_errors else ["已完成的数据库检索中未找到匹配记录；建议人工核查"],
            "source": None,
            "match_score": 0,
            "bib_title": bib_title,
            "api_data": None,
            "bib_doi": bib_doi,
            "api_errors": api_errors or [],
        }

    issues: list[str] = []
    if doi_lookup_issue:
        issues.append(doi_lookup_issue)
    if bib_doi and api_data.get("doi"):
        if normalize_doi(bib_doi).casefold() != normalize_doi(api_data["doi"]).casefold():
            issues.append(f"DOI 不匹配: bib={bib_doi}, 实际={api_data['doi']}")
    paper = entry.get("ENTRYTYPE", "article") in {"article", "inproceedings", "incollection"}
    missing_source = []
    if not api_data.get("title"):
        missing_source.append("标题")
    if paper and not api_data.get("authors"):
        missing_source.append("作者")
    if paper and not api_data.get("year"):
        missing_source.append("年份")
    elif api_data.get("year"):
        if not valid_year(api_data["year"]):
            missing_source.append("有效年份")
    issues.extend(f"来源元数据缺少{field}，无法完成核验" for field in missing_source)
    if not bib_title:
        issues.append("bib 中缺少标题字段")
    if paper and not bib_authors:
        issues.append("bib 中缺少作者字段")
    if bib_year:
        if not valid_year(bib_year):
            issues.append(f"年份格式无效：{bib_year}")

    # ── Title ─────────────────────────────────────────────────────────────────
    if api_data.get("title") and bib_title:
        t_score = fuzz.token_sort_ratio(
            normalize_title(bib_title), normalize_title(api_data["title"])
        )
        if t_score < title_threshold:
            issues.append(
                f"标题不匹配 (相似度 {t_score}%):\n"
                f"    bib  : {bib_title}\n"
                f"    实际 : {api_data['title']}"
            )

    # ── Year ──────────────────────────────────────────────────────────────────
    if api_data.get("year") and bib_year:
        try:
            diff = abs(int(bib_year) - int(api_data["year"]))
            if diff > 1:
                issues.append(
                    f"年份偏差 {diff} 年: bib={bib_year}, 实际={api_data['year']}"
                )
            elif diff == 1:
                issues.append(
                    f"年份偏差 1 年 (可能是预印本 vs 正式发表): bib={bib_year}, 实际={api_data['year']}"
                )
        except (ValueError, TypeError):
            if not any(issue.startswith("年份格式无效") for issue in issues):
                issues.append(f"来源年份格式无效：{api_data['year']}")
    elif api_data.get("year") and not bib_year:
        issues.append(f"bib 中缺少年份字段，API 显示为 {api_data['year']}")

    # ── First-author last name ────────────────────────────────────────────────
    if api_data.get("authors") and bib_authors:
        issues.extend(author_issues(bib_authors, api_data["authors"]))
        bib_first = name_parts(split_authors(bib_authors)[0])[0]
        api_first_lastname = name_parts(api_data["authors"][0])[0]
        a_score = fuzz.ratio(bib_first, api_first_lastname)
        first_declared = split_authors(bib_authors)[0]
        if normalize_name(first_declared) not in {"", "others", "et al"} and a_score < author_threshold and not same_person(first_declared, api_data["authors"][0]):
            if any(
                name_parts(name)[0] == bib_first
                for name in api_data["authors"][1:]
            ):
                issues.append("数据库第一作者与 bib 不同，但 bib 第一作者见于数据库作者列表（可能为团队署名或版本差异）")
            else:
                issues.append(
                    f"第一作者姓氏不匹配: bib={bib_first!r}, 实际={api_first_lastname!r} (相似度 {a_score}%)"
                )

    # ── Derive status ─────────────────────────────────────────────────────────
    critical = [
        i for i in issues
        if i.startswith(("标题不匹配", "第一作者姓氏不匹配", "DOI 不匹配", "作者列表不匹配"))
    ]
    if critical:
        status = "ERROR"
    elif issues:
        status = "WARNING"
    else:
        status = "OK"
    if missing_source and not critical:
        status = "UNVERIFIED"

    return {
        "key": key,
        "status": status,
        "issues": issues,
        "source": source,
        "match_score": match_score,
        "bib_title": bib_title,
        "api_data": api_data,
        "bib_doi": bib_doi,
        "api_errors": api_errors or [],
    }
