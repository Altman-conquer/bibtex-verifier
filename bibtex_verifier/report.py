"""Markdown and JSON report generation for verification results."""

import json
from pathlib import Path
from typing import Optional


def build_markdown_report(results: list[dict], *, bib_filename: str) -> str:
    """Build a Markdown verification report from a list of result dicts.

    Args:
        results: List of dicts as returned by comparator.compare_entry.
        bib_filename: Display name of the source .bib file.

    Returns:
        Markdown string.
    """
    ok = [r for r in results if r["status"] == "OK"]
    warnings = [r for r in results if r["status"] == "WARNING"]
    errors = [r for r in results if r["status"] == "ERROR"]
    not_found = [r for r in results if r["status"] == "NOT_FOUND"]

    lines: list[str] = [
        "# BibTeX 引用验证报告",
        "",
        f"> 验证文件: `{bib_filename}`  共 {len(results)} 条引用",
        "",
        "## 汇总",
        "",
        "| 状态 | 数量 |",
        "|------|------|",
        f"| ✅ 正常 (OK) | {len(ok)} |",
        f"| ⚠️ 警告 (WARNING) | {len(warnings)} |",
        f"| ❌ 错误 (ERROR) | {len(errors)} |",
        f"| 🔍 未找到 (NOT_FOUND) | {len(not_found)} |",
        "",
    ]

    def _section(title_str: str, items: list[dict], icon: str) -> None:
        if not items:
            return
        lines.append(f"## {icon} {title_str} ({len(items)} 条)")
        lines.append("")
        for r in items:
            lines.append(f"### `{r['key']}`")
            lines.append(f"- **标题 (bib)**: {r['bib_title']}")
            if r.get("api_data"):
                ad = r["api_data"]
                source_label = (r.get("source") or "").upper()
                lines.append(
                    f"- **验证来源**: {source_label} (标题匹配度 {r['match_score']}%)"
                )
                if ad.get("title"):
                    lines.append(f"- **标题 (API)**: {ad['title']}")
                if ad.get("year"):
                    lines.append(f"- **年份 (API)**: {ad['year']}")
                if ad.get("authors"):
                    authors_str = ", ".join(ad["authors"][:4])
                    if len(ad["authors"]) > 4:
                        authors_str += " ..."
                    lines.append(f"- **作者 (API)**: {authors_str}")
                if ad.get("venue"):
                    lines.append(f"- **发表场所 (API)**: {ad['venue']}")
            elif r.get("source"):
                lines.append(
                    f"- **验证来源**: {r['source'].upper()} (标题匹配度 {r['match_score']}%)"
                )
            if r.get("issues"):
                lines.append("- **问题**:")
                for issue in r["issues"]:
                    for j, sub in enumerate(issue.splitlines()):
                        prefix = "  - " if j == 0 else "    "
                        lines.append(f"{prefix}{sub}")
            lines.append("")

    _section("错误 (ERROR)", errors, "❌")
    _section("警告 (WARNING)", warnings, "⚠️")
    _section("未找到 (NOT_FOUND)", not_found, "🔍")
    _section("正常 (OK)", ok, "✅")

    return "\n".join(lines)


def save_report(
    results: list[dict],
    *,
    bib_filename: str,
    output_path: Path,
    save_json: bool = False,
) -> None:
    """Write the Markdown report (and optionally JSON) to disk.

    Args:
        results: Verification results list.
        bib_filename: Display name used in the report header.
        output_path: Destination .md file path.
        save_json: If True, also write a .json file alongside the report.
    """
    md = build_markdown_report(results, bib_filename=bib_filename)
    output_path.write_text(md, encoding="utf-8")

    if save_json:
        json_path = output_path.with_suffix(".json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)


def print_summary(results: list[dict]) -> None:
    """Print a one-line summary to stdout."""
    ok = sum(1 for r in results if r["status"] == "OK")
    warn = sum(1 for r in results if r["status"] == "WARNING")
    err = sum(1 for r in results if r["status"] == "ERROR")
    nf = sum(1 for r in results if r["status"] == "NOT_FOUND")
    print(f"\n统计: OK={ok}  WARN={warn}  ERR={err}  NOT_FOUND={nf}")
