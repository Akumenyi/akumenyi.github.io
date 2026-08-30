"""Shared helpers for the research-data refresh scripts."""

from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def log(message: str) -> None:
    print(f"[{datetime.now(timezone.utc):%H:%M:%S}] {message}", file=sys.stderr, flush=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path, default):
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return default


def write_json_if_changed(path: Path, payload: dict, volatile_keys=("generated_at",)) -> bool:
    """Write `payload`, but leave the file alone when only the timestamp moved.

    Keeps the scheduled job from producing an empty commit every single day.
    """
    previous = load_json(path, None)
    if previous is not None:
        a = {k: v for k, v in previous.items() if k not in volatile_keys}
        b = {k: v for k, v in payload.items() if k not in volatile_keys}
        if a == b:
            log(f"{path.name}: no substantive change, leaving file untouched")
            return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False, sort_keys=False)
        handle.write("\n")
    log(f"{path.name}: updated")
    return True


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def slugify(text: str, max_length: int = 60) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", strip_accents(text).lower()).strip("-")
    return slug[:max_length].rstrip("-")


def normalise_title(title: str) -> str:
    """Aggressive title key used only for de-duplication across sources."""
    return re.sub(r"[^a-z0-9]+", "", strip_accents(title or "").lower())


def normalise_doi(doi: str | None) -> str:
    if not doi:
        return ""
    doi = doi.strip().lower()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
    doi = re.sub(r"^doi:", "", doi)
    return doi if doi.startswith("10.") else ""


def env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}
