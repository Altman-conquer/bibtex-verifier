# BibTeX Verifier

[![CI](https://github.com/Altman-conquer/bibtex-verifier/actions/workflows/ci.yml/badge.svg)](https://github.com/Altman-conquer/bibtex-verifier/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/bibtex-verifier)](https://pypi.org/project/bibtex-verifier/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/bibtex-verifier)](https://pypistats.org/packages/bibtex-verifier)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Online Tool](https://img.shields.io/badge/Online%20Tool-GitHub%20Pages-blueviolet)](https://altman-conquer.github.io/bibtex-verifier/)

**BibTeX Verifier** is an open-source CLI tool that automatically validates every reference in a `.bib` file against **OpenAlex**, **CrossRef**, and **DataCite** to flag metadata inconsistencies and references needing manual review before submission.

> **BibTeX 引用验证工具** 是一个开源命令行工具，通过 OpenAlex、CrossRef 和 DataCite 核验 `.bib` 文件中的标题、作者、年份等书目信息，帮助研究者在投稿前定位需要人工核查的引用。

---

## Features / 功能特性

| Feature | Description |
|---|---|
| **Reference review** | Flags unresolved metadata for manual verification; missing database records do not prove fabrication |
| **Multi-source verification** | CrossRef and DataCite (DOI lookup) + OpenAlex (title search) |
| **Field-level checking** | Title, year, first-author last name, author count |
| **Markdown report** | Human-readable report with per-entry details and a summary table |
| **JSON output** | Machine-readable raw results for further processing |
| **CLI & Python API** | Use as a command or import as a library |
| **Free OpenAlex key** | Recommended for reliable batch searches; set `OPENALEX_API_KEY` |
| **Explicit API failures** | Rate limits/timeouts are `UNVERIFIED`, never `NOT_FOUND` |

---

## Online Tool / 在线工具

No installation needed — use the web interface directly:

**[https://altman-conquer.github.io/bibtex-verifier/](https://altman-conquer.github.io/bibtex-verifier/)**

Upload your `.bib` file or paste BibTeX from Overleaf and get a verification report in your browser. The `.bib` file stays in your browser; its metadata is sent directly to OpenAlex, CrossRef, and DataCite for lookup.

---

## Quick Start / 快速开始

```bash
git clone https://github.com/Altman-conquer/bibtex-verifier.git
cd bibtex-verifier
python -m pip install -e .
bibverify my_paper.bib
```

This generates `my_paper.report.md` with a full verification report.

---

## AI Agent Skill / AI 助手核验

This repository includes a [Codex skill](.agents/skills/verify-bibtex/SKILL.md) and a [Claude Code skill](.claude/skills/verify-bibtex/SKILL.md). To start from any workspace, attach your `.bib` file (or give an absolute path the agent can read) and send this single prompt to Codex or Claude Code:

```text
请用 https://github.com/Altman-conquer/bibtex-verifier 的 verify-bibtex skill 检查我提供的 paper.bib。请克隆仓库并读取对应的 SKILL.md，安装当前仓库版本，运行核验，给出报告路径、各状态数量和每条异常的具体原因。如果没有 OPENALEX_API_KEY，请让我在本机配置；不要保存或显示 key。
```

If you have already cloned the repository, start the agent from its root directory and invoke the skill directly:

| Agent | Prompt |
|---|---|
| Codex | `$verify-bibtex 检查 /absolute/path/paper.bib` |
| Claude Code | `/verify-bibtex /absolute/path/paper.bib` |

OpenAlex keys are **not bundled**. To make a key available to the agent, export `OPENALEX_API_KEY` in the same terminal **before starting Codex or Claude Code** (see below), or let the agent ask you to configure it. Without a key, OpenAlex may rate-limit the run. A repository link alone cannot supply your bibliography or API key.

---

## Installation / 安装

**From PyPI:**

```bash
pip install bibtex-verifier
```

The PyPI release may lag behind the GitHub source. Use the source installation for the latest OpenAlex key support and agent skills.

**From source:**

```bash
git clone https://github.com/Altman-conquer/bibtex-verifier.git
cd bibtex-verifier
pip install -e .
```

**Requirements:** Python 3.9+. A free OpenAlex API key is recommended for reliable batch search.

---

## OpenAlex API Key / 获取与使用

1. Sign in or create a free account at [OpenAlex API settings](https://openalex.org/settings/api), then copy your API key.
2. For the CLI, set the key in the current shell without putting it in command history. In Bash (Linux/macOS):

   ```bash
   read -rsp 'OpenAlex API key: ' OPENALEX_API_KEY
   echo
   export OPENALEX_API_KEY
   bibverify paper.bib --json
   unset OPENALEX_API_KEY
   ```

   To use the agent skill, start `codex` or `claude` from this same shell after `export OPENALEX_API_KEY`, instead of running `bibverify` directly. Run `unset OPENALEX_API_KEY` after leaving the agent.

3. For the [online tool](https://altman-conquer.github.io/bibtex-verifier/), enter the key in its **OpenAlex API key** field before verification. The page sends it to OpenAlex and does not save it.

Use your own key. Do not commit it to Git, put it in a shared `.env` file, or include it in a report. Without a key, OpenAlex may return HTTP 429 and leave some entries `UNVERIFIED`. See the [official authentication guide](https://developers.openalex.org/guides/authentication) for current limits.

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

# Use the OpenAlex key configured above for reliable batch search
bibverify paper.bib

# Optional contact email for API requests
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
| `--email` | — | Optional contact email for API requests |
| `OPENALEX_API_KEY` | — | Environment variable for a free OpenAlex key |
| `--rate-limit` | `0.15` | Seconds between API calls |
| `--version / -V` | — | Show version and exit |

### Python API

For programmatic lookups, API failures raise `ApiRequestError`; a missing database match returns `None`:

```python
from bibtex_verifier.apis import ApiRequestError, datacite_by_doi, datacite_extract

try:
    record = datacite_by_doi("10.48550/arxiv.2505.09388")
    if record:
        print(datacite_extract(record)["title"])
except ApiRequestError as exc:
    print("UNVERIFIED:", exc)
```

Use `bibverify paper.bib --json` for the complete multi-source verification chain and machine-readable results.

---

## Sample Output / 输出示例

```
BibTeX Verifier v0.1.1
Parsing paper.bib ...
Found 8 entries

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
│ ⏳ UNVERIFIED  │ 0      │
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
| ⏳ 未完成核验 (UNVERIFIED) | 0 |

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
│  2. CrossRef miss?                      │
│     └─► DataCite exact DOI lookup       │
│  3. No DOI match?                       │
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
| **NOT_FOUND** | All queried sources answered, but no matching metadata was found; check manually |
| **UNVERIFIED** | One or more API calls failed or were rate-limited, so no reliable conclusion is possible |

---

## Data Sources / 数据来源

### OpenAlex

- **URL**: [openalex.org](https://openalex.org)
- A free API key is recommended for batch searches: set `OPENALEX_API_KEY` for CLI or enter it in the web settings. Anonymous access is limited and may return HTTP 429.
- Search has a daily free budget; see the [official authentication guide](https://developers.openalex.org/guides/authentication).

### DataCite

- **URL**: [datacite.org](https://datacite.org)
- Used for DOI lookup when CrossRef has no match, including registered arXiv DOIs.

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
- **Chinese/Japanese author names** may trigger false positives; lower `--author-threshold` if the database uses a different romanization.
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
