#!/usr/bin/env python3
"""Refresh the publication record and citation metrics for Kwesi A. Quagraine.

Sources, in order of trust:

  1. `_data/publications_manual.yml` -- hand-curated, always wins on metadata.
  2. OpenAlex, filtered on ORCID 0000-0002-7887-6040 -- new papers + citations.
  3. Google Scholar via SerpAPI (optional, needs SERPAPI_API_KEY) -- Scholar's
     own citation counts, h-index and i10-index.
  4. The previous `_data/publications.json` -- so a bad network day never
     deletes anything.

Output: `_data/publications.json`, which the Jekyll site renders directly.

DISAMBIGUATION. More than one researcher publishes under the surname
"Quagraine", including co-authors on these papers. Harvesting on surname alone
would silently merge their records with this one, so every candidate that did
not arrive with a matching ORCID must pass `author_is_kaq()` -- a paper whose
only Quagraine is "K. T." is dropped. Do not relax this to a surname match.

Usage:
    python scripts/update_publications.py            # fetch and merge
    python scripts/update_publications.py --offline  # rebuild from local files
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml  # noqa: E402

from common import (  # noqa: E402
    REPO_ROOT,
    load_json,
    log,
    normalise_doi,
    normalise_title,
    now_iso,
    slugify,
    strip_accents,
    write_json_if_changed,
)

ORCID = "0000-0002-7887-6040"
OPENALEX_MAILTO = os.environ.get("OPENALEX_MAILTO", "kq@cvfv20.org")
SCHOLAR_ID = "hoI1ZjkAAAAJ"
TIMEOUT = 45

MANUAL_PATH = REPO_ROOT / "_data" / "publications_manual.yml"
OUTPUT_PATH = REPO_ROOT / "_data" / "publications.json"

# Initial patterns that identify this researcher, and the ones that identify a
# different Quagraine and must therefore be excluded.
SELF_PATTERNS = [
    re.compile(r"\bquagraine\b[\s,]*(kwesi\s+a|k\.?\s*a)\b", re.I),
    re.compile(r"\b(kwesi\s+a\.?|k\.?\s*a\.?)\s*[\s,]*quagraine\b", re.I),
]
OTHER_QUAGRAINE_PATTERNS = [
    re.compile(r"\bquagraine\b[\s,]*(kwesi\s+t|k\.?\s*t)\b", re.I),
    re.compile(r"\b(kwesi\s+t\.?|k\.?\s*t\.?)\s*[\s,]*quagraine\b", re.I),
]

VENUE_FIXES = {
    "journal of geophysical research: atmospheres": "Journal of Geophysical Research: Atmospheres",
    "bulletin of the american meteorological society": "Bulletin of the American Meteorological Society",
}

# Earliest plausible year for this researcher's output. OpenAlex ORCID records
# occasionally carry works mis-linked from an author-name collision; the first
# production run pulled in two 1960 soil-science papers this way.
MIN_YEAR = int(os.environ.get("PUBLICATIONS_MIN_YEAR", "2005"))

# Every paper in this record is open access apart from a handful behind a
# publisher paywall, so open access is the default and exceptions are declared
# in _data/publications_manual.yml with `open_access: false`. OpenAlex's own
# is_oa flag is deliberately not used to override this: the author knows the
# licensing of their own work, and an OpenAlex lag would silently drop the
# marker from papers that really are open.
DEFAULT_OPEN_ACCESS = True

# OpenAlex work types that are not publications in their own right.
EXCLUDED_TYPES = {
    "peer-review", "erratum", "paratext", "supplementary-materials",
    "grant", "libguides", "other", "dataset", "reference-entry",
}

# Titles that mark an artefact of the publishing process rather than a paper.
EXCLUDED_TITLE_PREFIXES = (
    "comment on", "publisher correction", "author correction", "correction to",
    "corrigendum", "erratum", "reply to", "response to",
)

# Repository deposits duplicate the version of record. They are kept only when
# nothing else carries the same title, and always rank below the journal copy.
REPOSITORY_SOURCES = (
    "zenodo", "research square", "researchsquare", "biorxiv", "medrxiv",
    "arxiv", "eartharxiv", "essoar", "ssrn", "preprints.org", "authorea",
    "figshare", "osf", "hal", "egusphere", "copernicus gmbh",
)

TYPE_MAP = {
    "article": "article",
    "journal-article": "article",
    "review": "article",
    "editorial": "comment",
    "letter": "comment",
    "preprint": "preprint",
    "posted-content": "preprint",
    "book-chapter": "chapter",
    "report": "report",
}


# --------------------------------------------------------------------------
# author identity
# --------------------------------------------------------------------------

def author_is_kaq(name: str) -> bool:
    """True when `name` unambiguously refers to Kwesi A. Quagraine."""
    flat = strip_accents(name or "")
    if any(p.search(flat) for p in SELF_PATTERNS):
        return True
    # A bare "Quagraine, K." with no second initial is ambiguous on its own but
    # is only ever produced by sources we already ORCID-matched, so an explicit
    # "K. T." is the sole disqualifier.
    if any(p.search(flat) for p in OTHER_QUAGRAINE_PATTERNS):
        return False
    return bool(re.search(r"\bkwesi\b.*\bquagraine\b|\bquagraine\b[\s,]*kwesi\b", flat, re.I))


def record_belongs_to_kaq(authors: list[str], orcid_matched: bool) -> bool:
    if orcid_matched:
        return True
    if any(author_is_kaq(a) for a in authors):
        return True
    log("  dropped (no unambiguous K. A. Quagraine): " + "; ".join(authors[:4]))
    return False


# Placeholders that stand in for omitted authors and must never be reformatted
# as if they were names ("et al." would otherwise become "al., e.").
AUTHOR_PLACEHOLDERS = {"…", "...", "et al.", "et al", "and others"}


def format_author(raw: str) -> str:
    """Render "Kwesi A. Quagraine" as "Quagraine, K. A." to match the site style."""
    raw = " ".join((raw or "").split())
    if not raw or raw.lower() in AUTHOR_PLACEHOLDERS:
        return raw
    if "," in raw:
        return raw
    parts = raw.split()
    if len(parts) < 2:
        return raw
    family = parts[-1]
    initials = " ".join(f"{p[0]}." for p in parts[:-1] if p)
    return f"{family}, {initials}"


# --------------------------------------------------------------------------
# manual record
# --------------------------------------------------------------------------

def load_manual() -> list[dict]:
    with MANUAL_PATH.open(encoding="utf-8") as handle:
        entries = yaml.safe_load(handle) or []
    out = []
    for entry in entries:
        item = dict(entry)
        item.setdefault("id", slugify(item["title"]))
        item.setdefault("type", "article")
        item.setdefault("status", "published")
        item.setdefault("topics", [])
        item["authors"] = [format_author(a) for a in item.get("authors", [])]
        item["source"] = "manual"
        item["manual"] = True
        out.append(item)
    log(f"manual record: {len(out)} entries")
    return out


# --------------------------------------------------------------------------
# OpenAlex
# --------------------------------------------------------------------------

def openalex_get(session, url: str, params: dict):
    params = dict(params or {})
    params["mailto"] = OPENALEX_MAILTO
    response = session.get(url, params=params, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def fetch_openalex_works(session) -> list[dict]:
    works: list[dict] = []
    cursor = "*"
    while cursor:
        payload = openalex_get(
            session,
            "https://api.openalex.org/works",
            {
                "filter": f"author.orcid:https://orcid.org/{ORCID}",
                "per-page": 200,
                "cursor": cursor,
            },
        )
        works.extend(payload.get("results", []))
        cursor = (payload.get("meta") or {}).get("next_cursor")
        if not payload.get("results"):
            break
    log(f"OpenAlex: {len(works)} ORCID-matched works")
    return works


def openalex_to_entry(work: dict) -> dict | None:
    title = (work.get("title") or work.get("display_name") or "").strip()
    if not title:
        return None

    lowered = title.lower().lstrip()
    if lowered.startswith(EXCLUDED_TITLE_PREFIXES):
        return None

    raw_type = (work.get("type") or "").lower()
    if raw_type in EXCLUDED_TYPES:
        return None

    year = work.get("publication_year")
    if year and year < MIN_YEAR:
        log(f"  dropped (published {year}, before {MIN_YEAR}): {title[:60]}")
        return None

    authorships = work.get("authorships") or []
    authors, orcid_matched = [], False
    for authorship in authorships:
        author = authorship.get("author") or {}
        name = author.get("display_name") or ""
        if (author.get("orcid") or "").endswith(ORCID):
            orcid_matched = True
        authors.append(format_author(name))

    if not record_belongs_to_kaq(authors, orcid_matched):
        return None

    location = work.get("primary_location") or {}
    source = location.get("source") or {}
    venue = source.get("display_name") or ""
    venue = VENUE_FIXES.get(venue.lower(), venue)

    doi = normalise_doi(work.get("doi"))
    crossref_type = (work.get("type_crossref") or work.get("type") or "").lower()

    return {
        "id": slugify(title),
        "title": title,
        "authors": authors,
        "year": work.get("publication_year"),
        "venue": venue,
        "doi": doi,
        "url": work.get("doi") or (location.get("landing_page_url") or ""),
        "open_access_url": ((work.get("best_oa_location") or {}).get("pdf_url") or ""),
        "type": TYPE_MAP.get(crossref_type, "article"),
        "status": "published",
        "citations": work.get("cited_by_count") or 0,
        "openalex_id": (work.get("id") or "").rsplit("/", 1)[-1],
        "is_repository": any(r in venue.lower() for r in REPOSITORY_SOURCES) if venue else False,
        "topics": [t["display_name"] for t in (work.get("topics") or [])[:3] if t.get("display_name")],
        "source": "openalex",
        "manual": False,
    }


def fetch_openalex_metrics(session) -> dict:
    payload = openalex_get(session, f"https://api.openalex.org/authors/https://orcid.org/{ORCID}", {})
    stats = payload.get("summary_stats") or {}
    return {
        "citations": payload.get("cited_by_count") or 0,
        "h_index": stats.get("h_index") or 0,
        "i10_index": stats.get("i10_index") or 0,
        "works_count": payload.get("works_count") or 0,
        "source": "OpenAlex",
    }


# --------------------------------------------------------------------------
# Google Scholar (optional, via SerpAPI)
# --------------------------------------------------------------------------

def fetch_scholar(session) -> tuple[dict, dict]:
    """Return (metrics, {normalised_title: citations}) from Google Scholar.

    Google Scholar has no public API and blocks datacentre scraping, so this
    path runs only when a SERPAPI_API_KEY secret is configured. Without it the
    site falls back to OpenAlex counts, which track Scholar closely.
    """
    api_key = os.environ.get("SERPAPI_API_KEY", "").strip()
    if not api_key:
        log("Google Scholar: SERPAPI_API_KEY not set, skipping (OpenAlex counts will be used)")
        return {}, {}

    citations: dict[str, int] = {}
    metrics: dict = {}
    start = 0
    while True:
        response = session.get(
            "https://serpapi.com/search",
            params={
                "engine": "google_scholar_author",
                "author_id": SCHOLAR_ID,
                "api_key": api_key,
                "num": 100,
                "start": start,
            },
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()

        if not metrics:
            table = (payload.get("cited_by") or {}).get("table") or []
            flat = {k: v for row in table for k, v in row.items()}
            metrics = {
                "citations": (flat.get("citations") or {}).get("all", 0),
                "h_index": (flat.get("h_index") or {}).get("all", 0),
                "i10_index": (flat.get("i10_index") or {}).get("all", 0),
                "source": "Google Scholar",
            }

        articles = payload.get("articles") or []
        for article in articles:
            key = normalise_title(article.get("title", ""))
            if key:
                citations[key] = int((article.get("cited_by") or {}).get("value") or 0)
        if len(articles) < 100:
            break
        start += 100

    log(f"Google Scholar: metrics + {len(citations)} article citation counts")
    return metrics, citations


# --------------------------------------------------------------------------
# merge
# --------------------------------------------------------------------------

def merge(manual: list[dict], fetched: list[dict], previous: list[dict]) -> list[dict]:
    """Collapse every record of one paper into a single entry.

    Two records describe the same paper if they share a DOI *or* a normalised
    title, and neither test alone is sufficient:

      * same title, different DOI -- a Zenodo or Research Square deposit of a
        paper carries its own DOI alongside the version of record;
      * same DOI, different title -- a manuscript is routinely retitled between
        submission and publication, so a curated entry written at submission
        and the publisher's record disagree on the title.

    Matching on either key alone therefore leaves duplicates, so entries are
    grouped by union-find over both keys and each group merged into one.

    Curated metadata wins within a group, with one exception: where a curated
    entry and a fetched record share a DOI but disagree on the title, the
    publisher's title is taken, since a title recorded at submission is simply
    out of date once the paper is out.
    """
    entries: list[dict] = list(manual) + sorted(
        fetched, key=lambda e: (bool(e.get("is_repository")), not e.get("venue"))
    )
    is_manual = [True] * len(manual) + [False] * len(fetched)

    # --- group records of the same paper -----------------------------------
    parent = list(range(len(entries)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)      # keep the earliest as root

    def keys_of(entry: dict) -> list[str]:
        keys = []
        doi = normalise_doi(entry.get("doi"))
        if doi:
            keys.append(f"doi:{doi}")
        title = normalise_title(entry.get("title", ""))
        if title:
            keys.append(f"title:{title}")
        return keys or [f"id:{entry.get('id', '')}"]

    seen: dict[str, int] = {}
    for index, entry in enumerate(entries):
        for key in keys_of(entry):
            if key in seen:
                union(index, seen[key])
            else:
                seen[key] = index

    groups: dict[int, list[int]] = {}
    for index in range(len(entries)):
        groups.setdefault(find(index), []).append(index)

    # --- merge each group ---------------------------------------------------
    results: list[dict] = []
    for root in sorted(groups):
        members = groups[root]
        current = dict(entries[members[0]])
        current_is_manual = is_manual[members[0]]

        for index in members[1:]:
            entry, authoritative = entries[index], is_manual[index]
            if authoritative:
                for field, value in entry.items():
                    if value not in (None, "", []):
                        current[field] = value
                current_is_manual = True
                continue

            for field, value in entry.items():
                if value in (None, "", []):
                    continue
                if field == "citations":
                    # Duplicate records of one work report different counts --
                    # a repository deposit usually reports none. Keep the best.
                    current[field] = max(int(value or 0), int(current.get(field) or 0))
                elif field in {"openalex_id", "open_access_url"}:
                    current[field] = value
                elif current.get(field) in (None, "", [], {}):
                    # `in` rather than falsiness: a stored False is a decision,
                    # not a gap, and must not be filled over.
                    current[field] = value

            # A curated title written at submission loses to the published one.
            same_doi = normalise_doi(entry.get("doi")) and normalise_doi(entry.get("doi")) == normalise_doi(current.get("doi"))
            if current_is_manual and same_doi and entry.get("title"):
                if normalise_title(entry["title"]) != normalise_title(current.get("title", "")):
                    log(f"  retitled from the publisher record: {current['title'][:58]}")
                    current["title"] = entry["title"]

            current.setdefault("source", "openalex")

        results.append(current)

    # Retain citation counts from the last successful run for anything the
    # current run could not reach.
    previous_by_key: dict[str, dict] = {}
    for entry in previous:
        for key in keys_of(entry):
            previous_by_key.setdefault(key, entry)
    for entry in results:
        if not entry.get("citations"):
            for key in keys_of(entry):
                if key in previous_by_key:
                    entry["citations"] = previous_by_key[key].get("citations", 0)
                    break

    for entry in results:
        entry.pop("is_repository", None)
        entry.setdefault("citations", 0)
        entry["authors"] = [format_author(a) for a in entry.get("authors", [])]
        entry["first_author"] = bool(entry["authors"]) and author_is_kaq(entry["authors"][0])
        entry["author_positions"] = ["self" if author_is_kaq(a) else "other" for a in entry["authors"]]
        if entry.get("open_access") is None:
            entry["open_access"] = DEFAULT_OPEN_ACCESS
        if entry.get("doi") and not entry.get("url"):
            entry["url"] = f"https://doi.org/{entry['doi']}"
    results.sort(key=lambda e: (-(e.get("year") or 0), 0 if e.get("status") == "under_review" else 1, e.get("title", "")))
    return results


def prune_empty(entry: dict) -> dict:
    """Drop empty values.

    Liquid treats an empty string as truthy, so a blank `doi` or
    `open_access_url` would render an empty chip on the page. Omitting the key
    entirely makes the template's `{% if %}` behave as intended.
    """
    return {k: v for k, v in entry.items() if v is False or v not in (None, "", [], {})}


def build_metrics(publications: list[dict], scholar: dict, openalex: dict, previous: dict) -> dict:
    published = [p for p in publications if p.get("status") != "under_review"]
    counted = sorted((p.get("citations") or 0) for p in published)[::-1]
    derived_h = sum(1 for i, c in enumerate(counted, start=1) if c >= i)

    metrics = {
        "publications": len(published),
        "under_review": sum(1 for p in publications if p.get("status") == "under_review"),
        "first_author": sum(1 for p in published if p.get("first_author")),
        "citations": sum(counted),
        "h_index": derived_h,
        "i10_index": sum(1 for c in counted if c >= 10),
        "since_year": min((p.get("year") or 9999) for p in published) if published else None,
        "citation_source": "Derived from the site record",
    }

    # Prefer the profile-level numbers when we have them: they cover work this
    # site does not list and match what a reader sees on Scholar.
    for source in (scholar, openalex):
        if source.get("citations"):
            metrics.update(
                citations=source["citations"],
                h_index=source.get("h_index") or metrics["h_index"],
                i10_index=source.get("i10_index") or metrics["i10_index"],
                citation_source=source.get("source", metrics["citation_source"]),
            )
            break
    else:
        if previous.get("citations", 0) > metrics["citations"]:
            metrics.update(
                citations=previous["citations"],
                h_index=previous.get("h_index", metrics["h_index"]),
                i10_index=previous.get("i10_index", metrics["i10_index"]),
                citation_source=previous.get("citation_source", metrics["citation_source"]),
            )
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="skip all network calls")
    args = parser.parse_args()

    previous_payload = load_json(OUTPUT_PATH, {}) or {}
    previous_pubs = previous_payload.get("publications", [])
    previous_metrics = previous_payload.get("metrics", {})

    manual = load_manual()
    fetched: list[dict] = []
    scholar_metrics: dict = {}
    scholar_citations: dict = {}
    openalex_metrics: dict = {}
    warnings: list[str] = []

    if not args.offline:
        try:
            import requests
        except ImportError:
            log("requests is not installed; run `pip install -r scripts/requirements.txt`")
            return 2

        session = requests.Session()
        session.headers["User-Agent"] = f"akumenyi.github.io publication sync (mailto:{OPENALEX_MAILTO})"

        try:
            works = fetch_openalex_works(session)
        except Exception as exc:  # noqa: BLE001 - never fail the site build
            works = []
            warnings.append(f"OpenAlex unavailable: {exc}")
            log(f"OpenAlex failed, keeping existing record ({exc})")

        skipped = 0
        for work in works:
            try:
                entry = openalex_to_entry(work)
            except Exception as exc:  # noqa: BLE001
                skipped += 1
                log(f"  skipped a malformed OpenAlex record ({exc})")
                continue
            if entry:
                fetched.append(entry)
        if skipped:
            warnings.append(f"{skipped} OpenAlex records could not be read")

        # Fetched separately: a failure here must not discard the works above.
        try:
            openalex_metrics = fetch_openalex_metrics(session)
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"OpenAlex author metrics unavailable: {exc}")
            log(f"OpenAlex author metrics failed ({exc})")

        try:
            scholar_metrics, scholar_citations = fetch_scholar(session)
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"Google Scholar unavailable: {exc}")
            log(f"Google Scholar failed ({exc})")
    else:
        log("offline mode: rebuilding from manual record + previous output")

    publications = merge(manual, fetched, previous_pubs)

    if scholar_citations:
        for entry in publications:
            hit = scholar_citations.get(normalise_title(entry.get("title", "")))
            if hit is not None:
                entry["citations"] = max(hit, entry.get("citations", 0))

    metrics = build_metrics(publications, scholar_metrics, openalex_metrics, previous_metrics)

    publications = [prune_empty(entry) for entry in publications]

    payload = {
        "generated_at": now_iso(),
        "orcid": ORCID,
        "scholar_id": SCHOLAR_ID,
        "metrics": metrics,
        "warnings": warnings,
        "publications": publications,
    }
    write_json_if_changed(OUTPUT_PATH, payload)

    log(
        f"done: {metrics['publications']} published, {metrics['under_review']} under review, "
        f"{metrics['citations']} citations ({metrics['citation_source']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
