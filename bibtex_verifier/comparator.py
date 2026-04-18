"""Field-level comparison between BibTeX entries and API data."""

from typing import Optional

from rapidfuzz import fuzz

from bibtex_verifier.apis import extract_first_author_lastname, normalize_title

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
            "status": "NOT_FOUND",
            "issues": ["在 OpenAlex / CrossRef 中未找到匹配论文（标题相似度不足）"],
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
        bib_first = extract_first_author_lastname(bib_authors)
        api_first_parts = api_data["authors"][0].split()
        api_first_lastname = api_first_parts[-1].lower() if api_first_parts else ""
        a_score = fuzz.ratio(bib_first, api_first_lastname)
        if a_score < author_threshold:
            issues.append(
                f"第一作者姓氏不匹配: bib={bib_first!r}, 实际={api_first_lastname!r} (相似度 {a_score}%)"
            )

        # ── Author count ──────────────────────────────────────────────────────
        bib_count = len(bib_authors.split(" and "))
        api_count = len(api_data["authors"])
        if api_count > bib_count + 1 and "others" not in bib_authors.lower():
            issues.append(
                f"作者数量少于实际: bib={bib_count} 人, 实际={api_count} 人"
            )

    # ── Derive status ─────────────────────────────────────────────────────────
    critical = [i for i in issues if "标题" in i or "作者姓氏" in i]
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
