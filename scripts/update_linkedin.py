#!/usr/bin/env python3
"""Refresh the LinkedIn activity shown on the site.

LinkedIn has no public read API for a member's own posts -- the Posts API is
gated behind partner review -- so the automated path here consumes a feed URL
that you control:

    LINKEDIN_FEED_URL   RSS 2.0, Atom or JSON Feed of your LinkedIn activity.

Any bridge that emits one of those works (RSS.app, RSSHub, an n8n/Zapier hook
writing a JSON Feed to a gist, ...). See SETUP.md for the walkthrough.

Without that secret the script still runs: it publishes whatever is pinned in
`_data/linkedin_manual.yml` and keeps the previous fetch, so the section never
empties itself out.

Output: `_data/linkedin.json`.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml  # noqa: E402

from common import REPO_ROOT, load_json, log, now_iso, write_json_if_changed  # noqa: E402

MANUAL_PATH = REPO_ROOT / "_data" / "linkedin_manual.yml"
OUTPUT_PATH = REPO_ROOT / "_data" / "linkedin.json"
PROFILE_URL = "https://www.linkedin.com/in/kwesi-a-quagraine-12855153/"
MAX_POSTS = 12
TIMEOUT = 40

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
}

# Matches both /feed/update/urn:li:activity:123 and the ...-activity-123-abcd
# slug form that "Copy link to post" produces.
URN_PATTERNS = [
    re.compile(r"urn:li:(?:activity|share|ugcPost):(\d{6,})", re.I),
    re.compile(r"-activity-(\d{6,})", re.I),
]


def extract_activity_id(*candidates: str) -> str:
    for candidate in candidates:
        if not candidate:
            continue
        for pattern in URN_PATTERNS:
            match = pattern.search(candidate)
            if match:
                return match.group(1)
    return ""


def strip_html(raw: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", raw or "", flags=re.I)
    text = re.sub(r"</p\s*>", "\n\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def first_image(raw: str) -> str:
    match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', raw or "", re.I)
    return match.group(1) if match else ""


def to_iso(value) -> str:
    if not value:
        return ""
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        dt = None
        for parser in (
            lambda s: datetime.fromisoformat(s.replace("Z", "+00:00")),
            parsedate_to_datetime,
        ):
            try:
                dt = parser(text)
                break
            except (TypeError, ValueError):
                continue
        if dt is None:
            return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def make_post(url: str, body: str, title: str = "", published: str = "", image: str = "") -> dict | None:
    text = strip_html(body) or strip_html(title)
    url = (url or "").strip()
    if not url and not text:
        return None
    activity_id = extract_activity_id(url, body, title)
    excerpt = text if len(text) <= 320 else text[:317].rsplit(" ", 1)[0] + "…"
    return {
        "id": activity_id or re.sub(r"\W+", "-", url)[-48:].strip("-"),
        "url": url or PROFILE_URL,
        "activity_id": activity_id,
        "embed_url": (
            f"https://www.linkedin.com/embed/feed/update/urn:li:activity:{activity_id}"
            if activity_id
            else ""
        ),
        "text": text,
        "excerpt": excerpt,
        "published": to_iso(published),
        "image": image or "",
    }


# --------------------------------------------------------------------------
# feed parsing
# --------------------------------------------------------------------------

def parse_rss(root) -> list[dict]:
    posts = []
    for item in root.iter("item"):
        def text_of(tag, ns=None):
            node = item.find(tag, ns) if ns else item.find(tag)
            return (node.text or "") if node is not None else ""

        body = text_of("content:encoded", NS) or text_of("description")
        posts.append(
            make_post(
                url=text_of("link"),
                body=body,
                title=text_of("title"),
                published=text_of("pubDate"),
                image=first_image(body),
            )
        )
    return posts


def parse_atom(root) -> list[dict]:
    posts = []
    for entry in root.iter(f"{{{NS['atom']}}}entry"):
        link = ""
        for node in entry.findall("atom:link", NS):
            if node.get("rel", "alternate") == "alternate":
                link = node.get("href", "")
                break
        content = entry.find("atom:content", NS)
        summary = entry.find("atom:summary", NS)
        body = (content is not None and (content.text or "")) or (
            summary is not None and (summary.text or "")
        ) or ""
        title = entry.find("atom:title", NS)
        # NB: an Element with no children is falsy, so `or` cannot be used here.
        updated = entry.find("atom:published", NS)
        if updated is None:
            updated = entry.find("atom:updated", NS)
        posts.append(
            make_post(
                url=link,
                body=body,
                title=(title.text or "") if title is not None else "",
                published=(updated.text or "") if updated is not None else "",
                image=first_image(body),
            )
        )
    return posts


def parse_json_feed(payload: dict) -> list[dict]:
    posts = []
    for item in payload.get("items", []):
        posts.append(
            make_post(
                url=item.get("url") or item.get("external_url") or "",
                body=item.get("content_html") or item.get("content_text") or "",
                title=item.get("title") or "",
                published=item.get("date_published") or item.get("date_modified") or "",
                image=item.get("image") or item.get("banner_image") or "",
            )
        )
    return posts


def fetch_feed(url: str) -> list[dict]:
    import requests

    response = requests.get(
        url,
        timeout=TIMEOUT,
        headers={"User-Agent": "akumenyi.github.io linkedin sync", "Accept": "*/*"},
    )
    response.raise_for_status()
    body = response.text.strip()

    if body.startswith("{"):
        return [p for p in parse_json_feed(json.loads(body)) if p]

    root = ElementTree.fromstring(body)
    posts = parse_atom(root) if root.tag.endswith("}feed") else parse_rss(root)
    return [p for p in posts if p]


# --------------------------------------------------------------------------

def load_manual() -> list[dict]:
    try:
        with MANUAL_PATH.open(encoding="utf-8") as handle:
            entries = yaml.safe_load(handle) or []
    except OSError:
        entries = []
    posts = []
    for entry in entries:
        post = make_post(
            url=entry.get("url", ""),
            body=entry.get("text", ""),
            title=entry.get("title", ""),
            published=entry.get("published", ""),
            image=entry.get("image", ""),
        )
        if post:
            post["pinned"] = bool(entry.get("pinned"))
            posts.append(post)
    return posts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="skip the network fetch")
    parser.add_argument("--feed-url", default=os.environ.get("LINKEDIN_FEED_URL", "").strip())
    args = parser.parse_args()

    previous = load_json(OUTPUT_PATH, {}) or {}
    manual = load_manual()
    fetched: list[dict] = []
    warnings: list[str] = []
    feed_configured = bool(args.feed_url)

    if args.feed_url and not args.offline:
        try:
            fetched = fetch_feed(args.feed_url)
            log(f"LinkedIn feed: {len(fetched)} items")
        except Exception as exc:  # noqa: BLE001 - never break the site
            warnings.append(f"LinkedIn feed unavailable: {exc}")
            log(f"LinkedIn feed failed, keeping previous posts ({exc})")
    elif not feed_configured:
        log("LINKEDIN_FEED_URL not set: publishing pinned posts only (see SETUP.md)")

    merged: dict[str, dict] = {}
    for post in [*previous.get("posts", []), *fetched, *manual]:
        key = post.get("activity_id") or post.get("url") or post.get("id")
        if not key:
            continue
        merged.setdefault(key, {}).update(post)

    posts = list(merged.values())
    posts.sort(key=lambda p: (not p.get("pinned"), p.get("published") or "", p.get("id")), reverse=False)
    pinned = [p for p in posts if p.get("pinned")]
    rest = sorted(
        (p for p in posts if not p.get("pinned")),
        key=lambda p: p.get("published") or "",
        reverse=True,
    )
    posts = (pinned + rest)[:MAX_POSTS]

    payload = {
        "generated_at": now_iso(),
        "profile_url": PROFILE_URL,
        "feed_configured": feed_configured,
        "warnings": warnings,
        "posts": posts,
    }
    write_json_if_changed(OUTPUT_PATH, payload)
    log(f"done: {len(posts)} posts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
