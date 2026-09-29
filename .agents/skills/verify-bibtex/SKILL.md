---
name: verify-bibtex
description: Set up this repository's BibTeX Verifier and check a user's .bib file, then explain citation matches, warnings, missing records, and API failures. Use when asked to verify references with this GitHub project.
---

# Verify BibTeX

Use the checked-out source of this repository; a published package may lag behind it. If the user supplied only the GitHub URL, obtain the repository and locate the `.bib` file or pasted BibTeX they want checked. Ask for the bibliography if it was not provided. Do not change the user's `.bib` file unless asked.

1. Ensure Python 3.9+ is available. Use an existing working environment or create an isolated virtual environment and install this checkout with `python -m pip install -e .` from the repository root. Run its `bibverify` entry point, not an older globally installed copy.
2. Check whether `OPENALEX_API_KEY` is already available without printing its value. If absent, ask the user to configure their own OpenAlex key. Use a secret-input mechanism or a process environment variable; do not put a key in the repository, command text, logs, report, or chat response. Never assume this repository includes a shared key. Anonymous lookup is possible, but rate limits can leave entries `UNVERIFIED`.
3. Run `bibverify /path/to/references.bib --json`. The command writes a Markdown report and a JSON report next to the input by default. An exit code of 1 can mean reported `ERROR`, `NOT_FOUND`, or `UNVERIFIED`; inspect the generated JSON before treating the run as a failure.
4. Tell the user the counts for `OK`, `WARNING`, `ERROR`, `NOT_FOUND`, and `UNVERIFIED`, with links or paths to the reports. For each non-OK entry, give its citation key, specific field discrepancy, matched source and identifier when available, and a concrete next check. Do not call a citation fabricated solely because it is `NOT_FOUND` or `ERROR`.
5. Review unresolved items against identifiers already present in their BibTeX (`doi`, `eprint`, arXiv IDs in `journal` or `url`, and publisher links). The CLI currently prioritizes explicit DOI lookup and OpenAlex title search; an arXiv ID embedded elsewhere can explain `NOT_FOUND`. Distinguish a database coverage gap, a web/product citation outside scholarly indexes, a conflicting identifier, and an API failure. Mark conclusions that could not be independently verified.

Keep the report evidence-based. `WARNING` often reflects preprint versus publication metadata or author-list conventions; `UNVERIFIED` means the lookup did not complete. Do not silently lower matching thresholds to make warnings disappear.
