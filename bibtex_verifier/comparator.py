"""Field-level comparison between BibTeX entries and API data."""

from typing import Optional

from rapidfuzz import fuzz

from bibtex_verifier.apis import normalize_title
from bibtex_verifier.names import author_issues, name_parts, same_person, split_authors

# Default thresholds (can be overridden per call)
DEFAULT_TITLE_THRESHOLD = 82
DEFAULT_AUTHOR_THRESHOLD = 72


def compare_entry(
    entry: dict,
    *,
    api_data: Optional[dict],
    source: Optional[str],
    match_score: int,
    title_threshold: int = DEFAULT_TITLE_THRESHOLD,
    author_threshold: int = DEFAULT_AUTHOR_THRESHOLD,
    api_errors: Optional[list[str]] = None,
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

    Returns:
        Dict with keys: key, status, issues, source, match_score,
        bib_title, api_data.
    """
    key = entry.get("ID", "unknown")
    bib_title = entry.get("title", "")
    bib_year = entry.get("year", "")
    bib_authors = entry.get("author", "")

    if api_data is None:
        return {
            "key": key,
            "status": "UNVERIFIED" if api_errors else "NOT_FOUND",
            "issues": [f"未完成核验：{'; '.join(api_errors)}"] if api_errors else ["已完成的数据库检索中未找到匹配记录；建议人工核查"],
            "source": None,
            "match_score": 0,
            "bib_title": bib_title,
            "api_data": None,
        }

    issues: list[str] = []

    # ── Title ─────────────────────────────────────────────────────────────────
    if api_data.get("title"):
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
        except ValueError:
            pass
    elif api_data.get("year") and not bib_year:
        issues.append(f"bib 中缺少年份字段，API 显示为 {api_data['year']}")

    # ── First-author last name ────────────────────────────────────────────────
    if api_data.get("authors") and bib_authors:
        issues.extend(author_issues(bib_authors, api_data["authors"]))
        bib_first = name_parts(split_authors(bib_authors)[0])[0]
        api_first_lastname = name_parts(api_data["authors"][0])[0]
        a_score = fuzz.ratio(bib_first, api_first_lastname)
        first_declared = split_authors(bib_authors)[0]
        if a_score < author_threshold and not same_person(first_declared, api_data["authors"][0]):
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
    critical = [i for i in issues if "标题" in i or "作者姓氏" in i or i.startswith("作者列表不匹配")]
    if critical:
        status = "ERROR"
    elif issues:
        status = "WARNING"
    else:
        status = "OK"

    return {
        "key": key,
        "status": status,
        "issues": issues,
        "source": source,
        "match_score": match_score,
        "bib_title": bib_title,
        "api_data": api_data,
    }
