"""
Update checking against GitHub Releases.

Deliberately **check-and-tell, never download-and-run**. The app reports that a
newer version exists and links to it; it does not fetch and execute anything.

That is a security decision, not laziness. A silent self-updater is a remote
code execution path into your machine that is only as strong as the release
channel behind it, and this build has no code signing yet - so there is nothing
to verify a downloaded binary against. An updater that cannot verify what it
downloaded is worse than no updater. When signing exists, this becomes a
verify-then-apply step; until then it stays a notification.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .data.http import FetchError, get

REPO = "MrExclusive2000/terminal"
RELEASES = f"https://api.github.com/repos/{REPO}/releases/latest"

_SEMVER = re.compile(r"(\d+)\.(\d+)\.(\d+)(?:[-+](.*))?")


def parse_version(v: str) -> tuple[int, int, int] | None:
    m = _SEMVER.search((v or "").strip().lstrip("vV"))
    if not m:
        return None
    return int(m[1]), int(m[2]), int(m[3])


def is_newer(candidate: str, current: str) -> bool:
    """True if `candidate` is a strictly higher release than `current`.

    Pre-release suffixes are ignored for ordering; an unparseable version on
    either side returns False, because "I could not tell" must not present as
    "you are out of date".
    """
    c, n = parse_version(candidate), parse_version(current)
    if c is None or n is None:
        return False
    return c > n


@dataclass(frozen=True)
class Release:
    version: str
    url: str
    notes: str


def latest(*, timeout: float = 12.0) -> Release | None:
    """Fetch the newest published release, or None if it cannot be determined.

    Never raises into the caller: an update check failing is not a reason for
    the application to report an error at the user. It is a reason to say
    nothing.
    """
    try:
        raw = json.loads(get(RELEASES, timeout=timeout, attempts=2,
                             user_agent=f"argus-terminal updater ({REPO})"))
    except (FetchError, json.JSONDecodeError, Exception):  # noqa: BLE001
        return None
    if not isinstance(raw, dict) or raw.get("draft"):
        return None
    tag = str(raw.get("tag_name") or "").strip()
    if not tag:
        return None
    return Release(version=tag.lstrip("vV"),
                   url=str(raw.get("html_url") or ""),
                   notes=(str(raw.get("body") or "")[:2000]))


def check(current: str) -> dict:
    """UI-shaped result. Always returns; never throws."""
    rel = latest()
    if rel is None:
        return {"checked": False, "current": current,
                "message": "Could not reach the update service."}
    if is_newer(rel.version, current):
        return {"checked": True, "update_available": True, "current": current,
                "latest": rel.version, "url": rel.url, "notes": rel.notes,
                "message": f"Version {rel.version} is available."}
    return {"checked": True, "update_available": False, "current": current,
            "latest": rel.version, "message": "You are on the latest version."}
