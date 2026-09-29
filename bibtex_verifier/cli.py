"""Command-line interface for bibtex-verifier."""

import time
from pathlib import Path
from typing import Optional

import typer
from rapidfuzz import fuzz
from rich.console import Console
from rich.table import Table

from bibtex_verifier import __version__
from bibtex_verifier.apis import (
    OA_RATE_LIMIT,
    ApiRequestError,
    crossref_by_doi,
    crossref_extract,
    datacite_by_doi,
    datacite_extract,
    normalize_title,
    oa_extract,
    oa_search,
    set_polite_email,
)
from bibtex_verifier.comparator import compare_entry
from bibtex_verifier.loader import load_bib
from bibtex_verifier.report import save_report

app = typer.Typer(
    name="bibverify",
    help="Check BibTeX metadata against CrossRef, DataCite and OpenAlex.",
    add_completion=False,
)
console = Console()

STATUS_STYLE = {
    "OK": "[green]OK    [/green]",
    "WARNING": "[yellow]WARN  [/yellow]",
    "ERROR": "[red]ERR   [/red]",
    "NOT_FOUND": "[dim]N/F   [/dim]",
    "UNVERIFIED": "[yellow]N/A   [/yellow]",
}


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"bibverify {__version__}")
        raise typer.Exit()


@app.command()
def verify(
    bib_file: Path = typer.Argument(..., help=".bib file to verify", exists=True),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Report output path (default: <bib>.report.md)"
    ),
    save_json: bool = typer.Option(False, "--json", help="Also save raw JSON results alongside the report"),
    title_threshold: int = typer.Option(
        82, "--title-threshold", min=0, max=100, help="Title fuzzy match threshold (0-100)"
    ),
    author_threshold: int = typer.Option(
        72, "--author-threshold", min=0, max=100, help="Author fuzzy match threshold (0-100)"
    ),
    email: Optional[str] = typer.Option(
        None,
        "--email",
        help="Contact email for API requests (OpenAlex searches need OPENALEX_API_KEY for reliable usage)",
    ),
    rate_limit: float = typer.Option(
        OA_RATE_LIMIT, "--rate-limit", help="Seconds to wait between API calls"
    ),
    version: Optional[bool] = typer.Option(
        None, "--version", "-V", callback=_version_callback, is_eager=True, help="Show version and exit"
    ),
) -> None:
    """Verify all entries in a .bib file and generate a Markdown report."""

    if email:
        set_polite_email(email)

    # ── Load ──────────────────────────────────────────────────────────────────
    console.print(f"\n[bold]BibTeX Verifier[/bold] v{__version__}")
    console.print(f"Parsing [cyan]{bib_file}[/cyan] ...")

    try:
        entries = load_bib(bib_file)
    except FileNotFoundError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    if not entries:
        console.print("[yellow]No entries found in the .bib file.[/yellow]")
        raise typer.Exit(0)

    console.print(f"Found [bold]{len(entries)}[/bold] entries\n")

    # ── Verify ────────────────────────────────────────────────────────────────
    results: list[dict] = []
    for i, entry in enumerate(entries, 1):
        key = entry.get("ID", "unknown")
        bib_title = entry.get("title", "")
        bib_doi = entry.get("doi", "")
        doi_tag = "[DOI]" if bib_doi else "     "

        console.print(
            f"  [{i:3d}/{len(entries)}] [dim]{key:<40}[/dim] {doi_tag}",
            end=" ",
        )

        api_data = None
        source = None
        match_score = 0
        api_errors = []

        # 1. Try CrossRef by DOI first
        if bib_doi:
            for name, lookup, extract in (
                ("CrossRef", crossref_by_doi, crossref_extract),
                ("DataCite", datacite_by_doi, datacite_extract),
            ):
                try:
                    record = lookup(bib_doi)
                except ApiRequestError as exc:
                    api_errors.append(f"{name}: {exc}")
                    continue
                if record:
                    api_data = extract(record)
                    source = name.lower()
                    match_score = fuzz.token_sort_ratio(
                        normalize_title(bib_title), normalize_title(api_data["title"])
                    )
                    break

        # 2. Fall back to OpenAlex title search
        if source is None and bib_title:
            try:
                oa_paper = oa_search(bib_title, threshold=title_threshold)
            except ApiRequestError as exc:
                api_errors.append(f"OpenAlex: {exc}")
            else:
                if oa_paper:
                    source = "openalex"
                    match_score = oa_paper.get("_match_score", 0)
                    api_data = oa_extract(oa_paper)

        if source is None and not bib_title and not bib_doi:
            api_errors.append("缺少标题和 DOI，无法检索")

        result = compare_entry(
            entry,
            api_data=api_data,
            source=source,
            match_score=match_score,
            title_threshold=title_threshold,
            author_threshold=author_threshold,
            api_errors=api_errors,
        )
        results.append(result)

        status_label = STATUS_STYLE.get(result["status"], result["status"])
        score_str = f"score={int(match_score):3d}%" if source else "         "
        console.print(f"{status_label}  {score_str}")

        time.sleep(rate_limit)

    # ── Report ────────────────────────────────────────────────────────────────
    if output is None:
        output = bib_file.with_suffix(".report.md")

    save_report(
        results,
        bib_filename=bib_file.name,
        output_path=output,
        save_json=save_json,
    )

    console.print(f"\n[bold green]Done![/bold green] Report saved to [cyan]{output}[/cyan]")
    if save_json:
        console.print(f"JSON data saved to [cyan]{output.with_suffix('.json')}[/cyan]")

    # Summary table
    ok = sum(1 for r in results if r["status"] == "OK")
    warn = sum(1 for r in results if r["status"] == "WARNING")
    err = sum(1 for r in results if r["status"] == "ERROR")
    nf = sum(1 for r in results if r["status"] == "NOT_FOUND")
    unverified = sum(1 for r in results if r["status"] == "UNVERIFIED")

    table = Table(title="\nVerification Summary", show_header=True)
    table.add_column("Status", style="bold")
    table.add_column("Count", justify="right")
    table.add_row("✅ OK", str(ok))
    table.add_row("[yellow]⚠️  WARNING[/yellow]", f"[yellow]{warn}[/yellow]")
    table.add_row("[red]❌ ERROR[/red]", f"[red]{err}[/red]")
    table.add_row("[dim]🔍 NOT_FOUND[/dim]", f"[dim]{nf}[/dim]")
    table.add_row("[yellow]⏳ UNVERIFIED[/yellow]", f"[yellow]{unverified}[/yellow]")
    console.print(table)

    if err + nf + unverified > 0:
        raise typer.Exit(1)
