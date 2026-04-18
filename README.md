# BibTeX Verifier

[![CI](https://github.com/your-username/bibtex-verifier/actions/workflows/ci.yml/badge.svg)](https://github.com/your-username/bibtex-verifier/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/bibtex-verifier)](https://pypi.org/project/bibtex-verifier/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**BibTeX Verifier** is an open-source CLI tool that automatically validates every reference in a `.bib` file against two authoritative academic databases — **OpenAlex** and **CrossRef** — to catch typos, wrong years, misattributed authors, and AI-hallucinated citations before they reach your paper.

> **BibTeX 引用验证工具** 是一个开源命令行工具，通过调用 OpenAlex 和 CrossRef 两个权威学术数据库，自动核验 `.bib` 文件中每条引用的标题、作者、年份等元数据，帮助研究者在论文提交前发现引用错误和 AI 幻觉引用。

---

## Features / 功能特性

| Feature | Description |
|---|---|
| **AI hallucination detection** | Flags papers that simply do not exist in any academic database |
| **Dual-source verification** | CrossRef (exact DOI lookup) + OpenAlex (fuzzy title search) |
| **Field-level checking** | Title, year, first-author last name, author count |
| **Markdown report** | Human-readable report with per-entry details and a summary table |
| **JSON output** | Machine-readable raw results for further processing |
| **CLI & Python API** | Use as a command or import as a library |
| **No registration needed** | OpenAlex is free and open; CrossRef is public |
| **Rate-limit safe** | Built-in throttling and exponential back-off on HTTP errors |

---

## Quick Start / 快速开始

```bash
pip install bibtex-verifier
bibverify my_paper.bib
```

This generates `my_paper.report.md` with a full verification report.

---

## Installation / 安装

**From PyPI:**

```bash
pip install bibtex-verifier
```

**From source:**

```bash
git clone https://github.com/your-username/bibtex-verifier.git
cd bibtex-verifier
pip install -e .
```

**Requirements:** Python 3.9+, no API keys required.

---

## Usage / 使用方法

### CLI

```bash
# Basic usage
bibverify paper.bib

# Save report to a custom path
bibverify paper.bib --output reports/verification.md

# Also export raw JSON results
bibverify paper.bib --json

# Use your email for higher API rate limits (Polite Pool)
bibverify paper.bib --email you@university.edu

# Adjust fuzzy-match thresholds
bibverify paper.bib --title-threshold 85 --author-threshold 70
```

#### All Options / 参数说明

| Option | Default | Description |
|---|---|---|
| `BIB_FILE` | — | Path to the `.bib` file to verify |
| `--output / -o` | `<bib>.report.md` | Report output file path |
| `--json` | `false` | Also write a `.json` results file |
| `--title-threshold` | `82` | Minimum fuzzy score for title match (0–100) |
| `--author-threshold` | `72` | Minimum fuzzy score for author match (0–100) |
| `--email` | — | Email for Polite Pool (faster rate limits) |
| `--rate-limit` | `0.15` | Seconds between API calls |
| `--version / -V` | — | Show version and exit |

### Python API

```python
from pathlib import Path
from bibtex_verifier.loader import load_bib
from bibtex_verifier.apis import oa_search, oa_extract, crossref_by_doi, crossref_extract
from bibtex_verifier.comparator import compare_entry
from bibtex_verifier.report import build_markdown_report

entries = load_bib(Path("paper.bib"))

results = []
for entry in entries:
    # Try CrossRef first if DOI is available
    api_data, source, score = None, None, 0
    if entry.get("doi"):
        msg = crossref_by_doi(entry["doi"])
        if msg:
            api_data = crossref_extract(msg)
            source = "crossref"
            score = 100  # DOI is exact
    # Fall back to OpenAlex
    if not source:
        paper = oa_search(entry.get("title", ""))
        if paper:
            api_data = oa_extract(paper)
            source = "openalex"
            score = paper["_match_score"]

    result = compare_entry(entry, api_data=api_data, source=source, match_score=score)
    results.append(result)

print(build_markdown_report(results, bib_filename="paper.bib"))
```

---

## Sample Output / 输出示例

```
BibTeX Verifier v0.1.0
Parsing paper.bib ...
Found 8 entries — estimated time: ~5s

  [  1/8] Vaswani2017attention                    [DOI] OK      score= 98%
  [  2/8] He2016resnet                                  OK      score= 95%
  [  3/8] Touvron2023llama                              WARN    score= 97%
  [  4/8] Brown2020gpt3                                 WARN    score= 99%
  [  5/8] Smith2020vit                                  ERR     score= 94%
  [  6/8] Devlin2019bert                                ERR     score= 81%
  [  7/8] Johnson2021hallucinated                       N/F     score=  0%
  [  8/8] LeCun1989backprop                       [DOI] OK      score=100%

Done! Report saved to paper.report.md

┌─────────────────────────┐
│  Verification Summary   │
├────────────────┬────────┤
│ ✅ OK          │ 3      │
│ ⚠️  WARNING    │ 2      │
│ ❌ ERROR       │ 2      │
│ 🔍 NOT_FOUND   │ 1      │
└────────────────┴────────┘
```

The generated Markdown report looks like:

```markdown
# BibTeX 引用验证报告

> 验证文件: `paper.bib`  共 8 条引用

## 汇总

| 状态 | 数量 |
|------|------|
| ✅ 正常 (OK) | 3 |
| ⚠️ 警告 (WARNING) | 2 |
| ❌ 错误 (ERROR) | 2 |
| 🔍 未找到 (NOT_FOUND) | 1 |

## ❌ 错误 (ERROR) (2 条)

### `Smith2020vit`
- **标题 (bib)**: An Image is Worth 16x16 Words...
- **验证来源**: OPENALEX (标题匹配度 94%)
- **问题**:
  - 第一作者姓氏不匹配: bib='smith', 实际='dosovitskiy' (相似度 0%)
```

---

## How It Works / 工作原理

```
.bib file
    │
    ▼
┌─────────────┐
│   loader    │  Parse entries with bibtexparser
└──────┬──────┘
       │  entry dict
       ▼
┌─────────────────────────────────────────┐
│              Lookup chain               │
│                                         │
│  1. DOI present?                        │
│     └─► CrossRef exact lookup           │
│                                         │
│  2. No DOI / CrossRef miss?             │
│     └─► OpenAlex fuzzy title search     │
│         (rapidfuzz token_sort_ratio)    │
└────────────────────┬────────────────────┘
                     │  api_data dict
                     ▼
           ┌──────────────────┐
           │   comparator     │  Check title / year /
           │                  │  author / count
           └────────┬─────────┘
                    │  result dict
                    ▼
           ┌──────────────────┐
           │     report       │  Markdown + JSON
           └──────────────────┘
```

### Status Levels / 状态说明

| Status | Meaning |
|---|---|
| **OK** | All checked fields match within thresholds |
| **WARNING** | Minor discrepancy (year ±1, too few authors) — review recommended |
| **ERROR** | Significant mismatch (title or author wrong) — likely an error |
| **NOT_FOUND** | No matching paper found — possible AI hallucination or misspelling |

---

## Data Sources / 数据来源

### OpenAlex

- **URL**: [openalex.org](https://openalex.org)
- **Free and open**, no registration or API key required
- Rate limit: ~10 req/s (tool defaults to ~7 req/s for safety)
- Coverage: 250M+ works
- Tip: Providing `--email` enables the [Polite Pool](https://docs.openalex.org/how-to-use-the-api/rate-limits-and-authentication) with higher rate limits

### CrossRef

- **URL**: [crossref.org](https://www.crossref.org)
- **Free**, no registration required
- Used only when a DOI is present in the `.bib` entry (exact lookup)
- Coverage: 150M+ DOI-registered works

---

## Match Thresholds / 比对阈值

Thresholds control sensitivity. Lowering them may reduce false positives at the cost of missing real errors.

| Parameter | Default | Controls |
|---|---|---|
| `--title-threshold` | 82 | Minimum `token_sort_ratio` score for title fuzzy match |
| `--author-threshold` | 72 | Minimum `ratio` score for first-author last-name match |
| Year tolerance | ±1 = WARNING, >1 = WARNING | Preprints often appear a year before formal publication |

---

## Development / 开发指南

```bash
# Clone and install in development mode
git clone https://github.com/your-username/bibtex-verifier.git
cd bibtex-verifier
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
ruff check bibtex_verifier/
```

### Project Structure / 项目结构

```
bibtex_verifier/
├── __init__.py     # version
├── loader.py       # .bib file parsing
├── apis.py         # OpenAlex & CrossRef clients, HTTP helpers
├── comparator.py   # field-level comparison logic
├── report.py       # Markdown/JSON report generation
└── cli.py          # Typer CLI (bibverify command)
tests/
├── conftest.py     # shared mock data
├── test_loader.py
├── test_apis.py
├── test_comparator.py
└── test_report.py
examples/
└── example_paper.bib   # demo file covering all verification scenarios
```

### Contributing / 贡献

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Add tests for your changes
4. Ensure `pytest tests/ -v` and `ruff check bibtex_verifier/` both pass
5. Open a Pull Request

---

## Known Limitations / 已知限制

- **Conference proceedings** may have lower match scores due to inconsistent venue naming across databases.
- **Chinese/Japanese author names** may trigger false positives in the author comparison; consider raising `--author-threshold` in such cases.
- OpenAlex coverage of very old papers (pre-1990) may be incomplete.
- The tool checks metadata only — it does not verify that the cited content actually supports your claim.

---

## License / 许可证

MIT License. See [LICENSE](LICENSE) for details.

---

## Citation / 引用

If you use this tool in your research, please cite:

```bibtex
@software{bibtex_verifier2025,
  title   = {BibTeX Verifier: Automatic Reference Validation Against OpenAlex and CrossRef},
  year    = {2025},
  url     = {https://github.com/your-username/bibtex-verifier},
  license = {MIT},
}
```
