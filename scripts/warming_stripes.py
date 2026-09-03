#!/usr/bin/env python3
"""Render warming stripes for the countries listed in `_data/cvf_members.yml`.

One SVG per country under `assets/img/stripes/`, plus `_data/warming_stripes.json`
describing what was drawn. The site uses them as page backdrops and as a grid on
the home page.

DATA. Annual temperature anomalies come from Berkeley Earth's regional and
global text files -- the same source behind Ed Hawkins' #ShowYourStripes. No
series is ever synthesised: a country that cannot be fetched is left out of the
output entirely, so the site can only ever display real measurements.

METHOD, following the #ShowYourStripes convention:
  * annual value = mean of that year's twelve monthly anomalies (all twelve
    must be present, so a partial current year is dropped rather than biased);
  * anomalies re-centred on the 1971-2000 mean;
  * colour scale spans +/- 2.6 standard deviations of the 1901-2000 annual
    values, mapped onto ColorBrewer RdBu reversed.
Both reference windows fall back to the full record for a short series.

Usage:
    python scripts/warming_stripes.py                 # fetch and render
    python scripts/warming_stripes.py --only ghana    # one country
    python scripts/warming_stripes.py --offline       # re-render nothing, report state
"""

from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml  # noqa: E402

from common import REPO_ROOT, load_json, log, now_iso, write_json_if_changed  # noqa: E402

MEMBERS_PATH = REPO_ROOT / "_data" / "cvf_members.yml"
OUTPUT_PATH = REPO_ROOT / "_data" / "warming_stripes.json"
SVG_DIR = REPO_ROOT / "assets" / "img" / "stripes"

# Hand-supplied series take priority over the remote archive. Berkeley Earth
# froze its public per-country text files at December 2020; current country
# data comes from its Synthesis platform, which needs a (free) login and so
# cannot be fetched unattended. Drop an export here as `<slug>.txt` or
# `<slug>.csv` and it is used instead of the 2020 archive. See SETUP.md.
LOCAL_DIR = REPO_ROOT / "_berkeley"

TIMEOUT = 60

# #ShowYourStripes starts at 1850. Berkeley's land record reaches back to 1750,
# but the 18th-century years rest on very sparse coverage and read as noise.
# Override per country with `start_year` in _data/cvf_members.yml.
DEFAULT_START_YEAR = 1850

# Berkeley Earth mirrors the same tree under more than one host; try each.
URL_TEMPLATES = [
    "https://berkeley-earth-temperature.s3.us-west-1.amazonaws.com/Regional/TAVG/{slug}-TAVG-Trend.txt",
    "https://berkeley-earth-temperature.s3.amazonaws.com/Regional/TAVG/{slug}-TAVG-Trend.txt",
    # Older layouts of the same archive, kept as fallbacks.
    "https://berkeley-earth-temperature.s3.us-west-1.amazonaws.com/Regional/TAVG/Text/{slug}-TAVG-Trend.txt",
    "http://berkeleyearth.lbl.gov/auto/Regional/TAVG/Text/{slug}-TAVG-Trend.txt",
]

SOURCE_NAME = "Berkeley Earth"
SOURCE_URL = "https://berkeleyearth.org/data/"

# ColorBrewer RdBu-11, cold to warm.
RDBU = [
    (5, 48, 97), (33, 102, 172), (67, 147, 195), (146, 197, 222), (209, 229, 240),
    (247, 247, 247),
    (253, 219, 199), (244, 165, 130), (214, 96, 77), (178, 24, 43), (103, 0, 31),
]


def colour_for(t: float) -> str:
    """Interpolate the RdBu ramp at t in [0, 1]."""
    t = min(max(t, 0.0), 1.0)
    position = t * (len(RDBU) - 1)
    low = int(position)
    high = min(low + 1, len(RDBU) - 1)
    frac = position - low
    r, g, b = (round(RDBU[low][i] + (RDBU[high][i] - RDBU[low][i]) * frac) for i in range(3))
    return f"#{r:02x}{g:02x}{b:02x}"


# --------------------------------------------------------------------------
# parsing
# --------------------------------------------------------------------------

def parse_region_name(text: str) -> str:
    """The region Berkeley says this file describes, from its `Name:` header."""
    for line in text.splitlines()[:60]:
        stripped = line.lstrip("%").strip()
        if stripped.startswith("Name:"):
            return stripped[5:].strip()
    return ""


def parse_berkeley(text: str) -> dict[int, float]:
    """Annual means from a Berkeley Earth monthly anomaly file.

    Columns are: year, month, monthly anomaly, uncertainty, then running
    averages. Comment lines start with '%' and gaps are spelled 'NaN'.
    """
    monthly: dict[int, list[float]] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("%"):
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        try:
            year = int(parts[0])
            month = int(parts[1])
            value = float(parts[2])
        except ValueError:
            continue
        if not 1 <= month <= 12 or value != value:      # NaN check
            continue
        monthly.setdefault(year, []).append(value)

    # Require a complete year so a partial current year cannot skew the colour.
    return {year: statistics.fmean(values) for year, values in monthly.items() if len(values) == 12}


def parse_csv(text: str) -> dict[int, float]:
    """Annual means from a plain CSV export.

    Two shapes are accepted, both with a header row naming the columns:
    `year,month,anomaly` (monthly, and a year still needs all twelve months)
    or `year,anomaly` (already annual, taken as given). Extra columns are
    ignored, so a Synthesis export can be handed over with its uncertainty
    column still attached.
    """
    rows = [r.strip() for r in text.splitlines() if r.strip()]
    if not rows:
        return {}
    header = [h.strip().lower() for h in rows[0].split(",")]
    if "year" not in header:
        return {}
    y_at = header.index("year")
    m_at = header.index("month") if "month" in header else None
    # The value column is whichever of these names appears first.
    v_at = next((header.index(n) for n in
                 ("anomaly", "temperature_c", "temperature", "tavg", "value")
                 if n in header), None)
    if v_at is None:
        return {}

    monthly: dict[int, list[float]] = {}
    annual: dict[int, float] = {}
    for row in rows[1:]:
        parts = [c.strip() for c in row.split(",")]
        if len(parts) <= max(y_at, v_at, m_at or 0):
            continue
        try:
            year, value = int(parts[y_at]), float(parts[v_at])
        except ValueError:
            continue
        if value != value:                              # NaN check
            continue
        if m_at is None:
            annual[year] = value
            continue
        try:
            month = int(parts[m_at])
        except ValueError:
            continue
        if 1 <= month <= 12:
            monthly.setdefault(year, []).append(value)

    if m_at is None:
        return annual
    return {y: statistics.fmean(v) for y, v in monthly.items() if len(v) == 12}


def parse_series(text: str) -> dict[int, float]:
    """Pick a parser by what the file looks like, not by its extension."""
    head = "\n".join(text.splitlines()[:40]).lower()
    if "year" in head and "," in head:
        parsed = parse_csv(text)
        if parsed:
            return parsed
    return parse_berkeley(text)


def read_local(slug: str) -> str | None:
    for suffix in (".txt", ".csv"):
        path = LOCAL_DIR / f"{slug}{suffix}"
        if path.exists():
            return path.read_text(encoding="utf-8", errors="replace")
    return None


def window_or_all(series: dict[int, float], start: int, end: int) -> list[float]:
    inside = [v for y, v in series.items() if start <= y <= end]
    return inside if len(inside) >= 10 else list(series.values())


def build_stripes(series: dict[int, float], start_year: int = DEFAULT_START_YEAR) -> dict:
    series = {y: v for y, v in series.items() if y >= start_year}
    years = sorted(series)
    baseline = statistics.fmean(window_or_all(series, 1971, 2000))
    spread = window_or_all(series, 1901, 2000)
    sigma = statistics.pstdev(spread) if len(spread) > 1 else 1.0
    limit = (2.6 * sigma) or 1.0

    stripes = []
    for year in years:
        anomaly = series[year] - baseline
        t = anomaly / (2 * limit) + 0.5
        stripes.append({"year": year, "anomaly": round(anomaly, 3), "colour": colour_for(t)})
    return {
        "stripes": stripes,
        "first_year": years[0],
        "last_year": years[-1],
        "baseline": "1971-2000",
        "scale": round(limit, 3),
    }


def render_svg(name: str, built: dict) -> str:
    """A viewBox-only SVG that stretches to whatever box the CSS gives it."""
    stripes = built["stripes"]
    # Rects overlap by a hair: at fractional scales adjacent 1-unit rects leave
    # sub-pixel gaps, which show up as white hairlines in the thin rules.
    rects = "".join(
        f'<rect x="{i}" y="0" width="1.02" height="1" fill="{s["colour"]}"/>'
        for i, s in enumerate(stripes)
    )
    label = f"Warming stripes for {name}, {built['first_year']} to {built['last_year']}"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {len(stripes)} 1" '
        f'preserveAspectRatio="none" shape-rendering="crispEdges" role="img" aria-label="{label}">'
        f"<title>{label}</title>{rects}</svg>\n"
    )


# --------------------------------------------------------------------------

def fetch(session, entry: dict) -> str | None:
    local = read_local(entry["slug"])
    if local is not None:
        log(f"  {entry['slug']}: using the local export in _berkeley/")
        return local
    urls = [entry["url"]] if entry.get("url") else [
        template.format(slug=entry.get("berkeley", entry["slug"]))
        for template in URL_TEMPLATES
    ]
    for url in urls:
        try:
            response = session.get(url, timeout=TIMEOUT)
        except Exception as exc:  # noqa: BLE001
            log(f"  {entry['slug']}: {type(exc).__name__} on {url}")
            continue
        if response.status_code == 200 and "%" in response.text[:2000]:
            return response.text
        log(f"  {entry['slug']}: HTTP {response.status_code} on {url}")
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", help="restrict to one slug")
    parser.add_argument("--offline", action="store_true", help="skip fetching; report current state")
    args = parser.parse_args()

    members = yaml.safe_load(MEMBERS_PATH.read_text(encoding="utf-8")) or []
    if args.only:
        members = [m for m in members if m["slug"] == args.only]

    previous = load_json(OUTPUT_PATH, {}) or {}
    previous_countries = {c["slug"]: c for c in previous.get("countries", [])}

    if args.offline:
        log(f"offline: {len(previous_countries)} countries already rendered")
        return 0

    try:
        import requests
    except ImportError:
        log("requests is not installed; run `pip install -r scripts/requirements.txt`")
        return 2

    session = requests.Session()
    session.headers["User-Agent"] = "akumenyi.github.io warming-stripes sync"
    SVG_DIR.mkdir(parents=True, exist_ok=True)

    countries, failures = [], []
    for entry in members:
        slug = entry["slug"]
        text = fetch(session, entry)
        if not text:
            failures.append(slug)
            # Keep whatever was rendered on a previous successful run.
            if slug in previous_countries and (SVG_DIR / f"{slug}.svg").exists():
                countries.append(previous_countries[slug])
                log(f"{slug}: fetch failed, keeping the existing stripes")
            else:
                log(f"{slug}: fetch failed and nothing cached — omitted")
            continue

        # Guard against a renamed or re-pointed slug silently mislabelling a
        # country: Berkeley states the region in the file itself.
        reported = parse_region_name(text)
        if reported and reported.lower() != entry["name"].lower() and not entry.get("allow_name_mismatch"):
            failures.append(slug)
            log(f"{slug}: file reports region {reported!r}, expected {entry['name']!r} — omitted")
            continue

        series = parse_series(text)
        if len([y for y in series if y >= entry.get("start_year", DEFAULT_START_YEAR)]) < 30:
            failures.append(slug)
            log(f"{slug}: only {len(series)} complete years parsed — omitted")
            continue

        built = build_stripes(series, entry.get("start_year", DEFAULT_START_YEAR))
        (SVG_DIR / f"{slug}.svg").write_text(render_svg(entry["name"], built), encoding="utf-8")
        countries.append({
            "slug": slug,
            "name": entry["name"],
            "region": entry.get("region", ""),
            "reported_name": reported,
            "local": read_local(slug) is not None,
            "feature": bool(entry.get("feature")),
            "first_year": built["first_year"],
            "last_year": built["last_year"],
            "years": len(built["stripes"]),
            "baseline": built["baseline"],
            "warming": round(
                statistics.fmean([s["anomaly"] for s in built["stripes"][-10:]])
                - statistics.fmean([s["anomaly"] for s in built["stripes"][:30]]),
                2,
            ),
            "svg": f"/assets/img/stripes/{slug}.svg",
        })
        log(f"{slug}: {built['first_year']}-{built['last_year']}, {len(built['stripes'])} years")

    payload = {
        "generated_at": now_iso(),
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "method": "Annual means re-centred on 1971-2000; colour scale spans ±2.6σ of 1901-2000.",
        "failures": failures,
        "countries": countries,
    }
    write_json_if_changed(OUTPUT_PATH, payload)
    log(f"done: {len(countries)} rendered, {len(failures)} failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
