"""API clients for OpenAlex and CrossRef."""

import json
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

from rapidfuzz import fuzz

# ── Constants ─────────────────────────────────────────────────────────────────

OA_SEARCH_URL = "https://api.openalex.org/works"
OA_RATE_LIMIT = 0.15  # seconds between requests (~7 req/s, conservative)

CR_URL = "https://api.crossref.org/works/"

TITLE_MATCH_THRESHOLD = 82  # minimum fuzzy match score for title (0-100)

# ── HTTP helper ───────────────────────────────────────────────────────────────

_DEFAULT_EMAIL: Optional[str] = None


def set_polite_email(email: str) -> None:
    """Register an email for API Polite Pool (higher rate limits)."""
    global _DEFAULT_EMAIL
    _DEFAULT_EMAIL = email


def http_get(
    url: str,
    params: Optional[dict] = None,
    timeout: int = 15,
    retries: int = 3,
) -> Optional[dict]:
    """Send a GET request and return parsed JSON.

    Handles 429/5xx with exponential back-off. Returns None on failure.
    """
    if params:
        url = url + "?" + urllib.parse.urlencode(params)

    headers = {"User-Agent": "BibVerifier/1.0 (academic-tool)"}
    if _DEFAULT_EMAIL:
        headers["User-Agent"] += f"; mailto:{_DEFAULT_EMAIL}"

    req = urllib.request.Request(url, headers=headers)
    wait = 5.0
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504):
                if attempt < retries - 1:
                    time.sleep(wait)
                    wait *= 2
                else:
                    return None
            else:
                return None
        except Exception:
            return None
    return None


# ── Text normalisation ────────────────────────────────────────────────────────


def normalize_title(title: str) -> str:
    """Strip LaTeX commands, braces, punctuation; return lowercase."""
    title = re.sub(r"\{([^{}]*)\}", r"\1", title)  # {X} → X
    title = re.sub(r"\\[a-zA-Z]+\s*", " ", title)  # \cmd → space
    title = re.sub(r"[^\w\s]", " ", title)  # punctuation → space
    return re.sub(r"\s+", " ", title).strip().lower()


def normalize_lastname(name: str) -> str:
    """Normalise a last name for comparison: lowercase, ß→ss, strip diacritics."""
    name = name.lower().replace("ß", "ss")
    name = unicodedata.normalize("NFD", name)
    return "".join(c for c in name if unicodedata.category(c) != "Mn")


def extract_first_author_lastname(author_field: str) -> str:
    """Return the normalised last name of the first author in a BibTeX author field."""
    first = author_field.split(" and ")[0].strip()
    first = re.sub(r"\{([^{}]*)\}", r"\1", first)
    first = re.sub(r"\\[a-zA-Z]+\s*", "", first)
    if "," in first:
        return normalize_lastname(first.split(",")[0].strip())
    parts = first.split()
    return normalize_lastname(parts[-1]) if parts else ""


# ── OpenAlex API ──────────────────────────────────────────────────────────────


def oa_search(title: str) -> Optional[dict]:
    """Search OpenAlex by title; return the best-matching paper dict or None."""
    data = http_get(
        OA_SEARCH_URL,
        params={
            "search": title,
            "per-page": 5,
            "select": "title,authorships,publication_year,primary_location,doi",
        },
    )
    if not data or not data.get("results"):
        return None

    norm_q = normalize_title(title)
    best_paper: Optional[dict] = None
    best_score = 0

    for paper in data["results"]:
        api_title = paper.get("title") or ""
        if not api_title:
            continue
        score = fuzz.token_sort_ratio(norm_q, normalize_title(api_title))
        if score > best_score:
            best_score = score
            best_paper = paper

    if best_score < TITLE_MATCH_THRESHOLD:
        return None

    best_paper["_match_score"] = best_score  # type: ignore[index]
    return best_paper


def oa_extract(paper: dict) -> dict:
    """Extract normalised fields from an OpenAlex paper dict."""
    title = paper.get("title") or ""
    year = paper.get("publication_year")
    authors = [
        a["author"]["display_name"]
        for a in paper.get("authorships", [])
        if a.get("author", {}).get("display_name")
    ]
    loc = paper.get("primary_location") or {}
    source = loc.get("source") or {}
    venue = source.get("display_name") or ""
    doi = paper.get("doi") or ""
    return {"title": title, "year": year, "authors": authors, "venue": venue, "doi": doi}


# ── CrossRef API ──────────────────────────────────────────────────────────────


def crossref_by_doi(doi: str) -> Optional[dict]:
    """Fetch the CrossRef message dict for a given DOI, or None on failure."""
    doi_encoded = urllib.parse.quote(doi.strip(), safe="")
    data = http_get(f"{CR_URL}{doi_encoded}")
    if data and data.get("status") == "ok":
        return data.get("message")
    return None


def crossref_extract(msg: dict) -> dict:
    """Extract normalised fields from a CrossRef message dict."""
    titles = msg.get("title", [])
    title = titles[0] if titles else ""

    year = None
    for key in ("published-print", "published-online", "issued"):
        dp = msg.get(key, {}).get("date-parts", [[]])
        if dp and dp[0]:
            year = dp[0][0]
            break

    authors = [
        f"{a.get('given', '')} {a.get('family', '')}".strip()
        for a in msg.get("author", [])
    ]
    container = msg.get("container-title", [])
    venue = container[0] if container else ""
    return {"title": title, "year": year, "authors": authors, "venue": venue}
