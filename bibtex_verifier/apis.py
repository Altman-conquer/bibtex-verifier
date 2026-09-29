"""API clients for OpenAlex, CrossRef and DataCite."""

import json
import os
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
DC_URL = "https://api.datacite.org/dois/"

TITLE_MATCH_THRESHOLD = 82  # minimum fuzzy match score for title (0-100)

# ── HTTP helper ───────────────────────────────────────────────────────────────

_DEFAULT_EMAIL: Optional[str] = None


class ApiRequestError(Exception):
    """An API could not be checked; absence of a match is not established."""


def set_polite_email(email: str) -> None:
    """Include a contact email in API request headers."""
    global _DEFAULT_EMAIL
    _DEFAULT_EMAIL = email


def http_get(
    url: str,
    params: Optional[dict] = None,
    timeout: int = 6,
    retries: int = 3,
) -> Optional[dict]:
    """Send a GET request and return parsed JSON.

    Return None only for a genuine 404; raise on rate limits and transport errors.
    """
    if params:
        url = url + "?" + urllib.parse.urlencode(params)

    headers = {"User-Agent": "BibVerifier/1.0 (academic-tool)"}
    if _DEFAULT_EMAIL:
        headers["User-Agent"] += f"; mailto:{_DEFAULT_EMAIL}"

    req = urllib.request.Request(url, headers=headers)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            if (exc.code == 429 or 500 <= exc.code < 600) and attempt < retries - 1:
                time.sleep(2**attempt)
                continue
            raise ApiRequestError(f"HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt < retries - 1:
                time.sleep(2**attempt)
                continue
            raise ApiRequestError(f"{type(exc).__name__}: {exc}") from exc
        except ValueError as exc:
            raise ApiRequestError(f"{type(exc).__name__}: {exc}") from exc
    raise ApiRequestError("API request failed")



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
    first = re.split(r"\s+and\s+", author_field, maxsplit=1, flags=re.I)[0].strip()
    first = re.sub(r"\{([^{}]*)\}", r"\1", first)
    first = re.sub(r"\\[a-zA-Z]+\s*", "", first)
    if "," in first:
        return normalize_lastname(first.split(",")[0].strip())
    parts = first.split()
    return normalize_lastname(parts[-1]) if parts else ""


# ── OpenAlex API ──────────────────────────────────────────────────────────────


def oa_search(title: str, threshold: int = TITLE_MATCH_THRESHOLD) -> Optional[dict]:
    """Search OpenAlex by title; return the best-matching paper dict or None."""
    params = {
        "search": normalize_title(title),
        "per-page": 5,
        "select": "title,authorships,publication_year,primary_location,doi",
    }
    if os.environ.get("OPENALEX_API_KEY"):
        params["api_key"] = os.environ["OPENALEX_API_KEY"]
    data = http_get(OA_SEARCH_URL, params=params)
    if data is None or "results" not in data:
        raise ApiRequestError("OpenAlex returned no usable search response")
    if not data["results"]:
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

    if best_score < threshold:
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
    """Fetch CrossRef metadata, or None if the DOI is not registered there."""
    doi_encoded = urllib.parse.quote(doi.strip(), safe="")
    data = http_get(f"{CR_URL}{doi_encoded}")
    if data is None:
        return None
    if data.get("status") != "ok" or not data.get("message"):
        raise ApiRequestError("CrossRef returned malformed metadata")
    return data["message"]


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


# ── DataCite DOI API ──────────────────────────────────────────────────────────


def datacite_by_doi(doi: str) -> Optional[dict]:
    """Fetch metadata for a DOI registered with DataCite."""
    data = http_get(f"{DC_URL}{urllib.parse.quote(doi.strip(), safe='/')}")
    if data is None:
        return None
    attrs = data.get("data", {}).get("attributes")
    if not attrs:
        raise ApiRequestError("DataCite returned malformed metadata")
    return attrs


def datacite_extract(attrs: dict) -> dict:
    titles = attrs.get("titles") or []
    return {
        "title": titles[0].get("title", "") if titles else "",
        "year": attrs.get("publicationYear"),
        "authors": [a.get("name", "") for a in attrs.get("creators", []) if a.get("name")],
        "venue": attrs.get("publisher", "") if isinstance(attrs.get("publisher"), str) else (attrs.get("publisher") or {}).get("name", ""),
        "doi": attrs.get("doi", ""),
    }
