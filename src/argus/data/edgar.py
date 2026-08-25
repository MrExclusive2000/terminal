"""
SEC EDGAR client for the Form 4 path.

Two rules the SEC enforces and one trap the API sets:

  * **Declare yourself.** Fair access requires an identifying User-Agent with a
    contact address. A browser-shaped UA earns an immediate block page, not a
    429, so it fails as an HTML body with status 200 and looks like a parse bug.

  * **Ten requests per second, hard.** The limiter below is deliberately set
    under the ceiling. Nothing in this pipeline is worth being blocked for.

  * **`type=` on the current-filings feed is a PREFIX match.** Requesting
    `type=4` returns 424B2, 425 and 40-33 alongside genuine Form 4s - measured
    at 14 of 40 entries on one live pull. Filtering on the entry's own form type
    is therefore not defensive coding, it is the only correct reading of the feed.

Two further behaviours of this feed, both measured rather than assumed:

  * **It caps at 40 entries** whatever `count` you ask for. Requesting 100 and
    believing you have 100 means silently missing filings while looking healthy.
  * **Each filing appears once per party** - one entry for the reporting owner
    and one for the issuer, so every accession arrives twice. Deduplicating is
    not tidiness: a filing counted twice becomes two insiders in cluster
    detection, which manufactures exactly the signal this system exists to find.
"""
from __future__ import annotations

import json
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from ..insider.form4 import Form4, ParseError, parse
from .http import FetchError, get

BASE = "https://www.sec.gov"
CURRENT = BASE + "/cgi-bin/browse-edgar?action=getcurrent&type={type}&output=atom&count={count}"

#: The feed will not return more than this many entries, whatever `count` says.
#: Measured, not documented by the SEC.
FEED_MAX = 40

#: SEC fair access requires an identifying User-Agent carrying a real contact
#: address. Unidentified traffic is not rate-limited, it is refused with a 403.
#: Read from the environment so the app, the CLI and any scheduled job share one
#: source of truth instead of each passing their own string.
CONTACT_ENV = "ARGUS_SEC_CONTACT"
_CONTACT = ""


class ContactNotConfigured(RuntimeError):
    """Raised before any request rather than letting the SEC answer with a 403.

    A 403 from EDGAR is indistinguishable at the call site from a network fault,
    an outage or a bad URL, so it sends you debugging the wrong thing. This
    fails early and says exactly what to set.
    """

    def __init__(self) -> None:
        super().__init__(
            "SEC EDGAR needs a name and email before it will answer. "
            "Set it in Settings, or via the ARGUS_SEC_CONTACT environment "
            "variable. Without it the SEC returns 403 for every request - "
            "this is their fair-access rule, not a rate limit you can wait out.")


def set_contact(contact: str) -> None:
    """Set the User-Agent contact string. Call once at startup."""
    global _CONTACT
    _CONTACT = (contact or "").strip()


def contact() -> str:
    """The effective contact.

    Precedence: an explicit `set_contact` call, then the environment, then the
    saved desktop setting. Explicit wins so a one-off script can override; the
    environment beats the file so a scheduled run does not need the user's
    settings to be right.
    """
    import os
    if _CONTACT:
        return _CONTACT
    if env := os.environ.get(CONTACT_ENV, "").strip():
        return env
    try:
        from ..config import load
        return load().sec_contact.strip()
    except Exception:  # noqa: BLE001 - settings must never block a fetch path
        return ""


def _looks_like_contact(s: str) -> bool:
    """A name and an email is what the SEC asks for; anything less gets blocked."""
    return bool(re.search(r"[^@\s]+@[^@\s]+\.[^@\s]+", s))


def _ua() -> str:
    c = contact()
    if not _looks_like_contact(c):
        raise ContactNotConfigured()
    return f"argus-terminal/0.1 ({c})"


class RateLimiter:
    """Token-bucket limiter, shared across threads.

    Set below the published ceiling on purpose: the cost of being one request
    per second slower is nothing, and the cost of being blocked is the product.
    """

    def __init__(self, per_second: float = 8.0) -> None:
        self.min_gap = 1.0 / per_second
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            gap = now - self._last
            if gap < self.min_gap:
                time.sleep(self.min_gap - gap)
            self._last = time.monotonic()


_limiter = RateLimiter()


def _fetch(url: str, *, timeout: float = 45.0) -> str:
    _limiter.wait()
    return get(url, user_agent=_ua(), timeout=timeout)


@dataclass(frozen=True)
class FilingRef:
    form_type: str
    title: str
    accession: str
    cik: str
    index_url: str
    updated: datetime | None

    @property
    def folder(self) -> str:
        return self.index_url.rsplit("/", 1)[0]

    @property
    def is_amendment(self) -> bool:
        return self.form_type.endswith("/A")


def _parse_entry(entry: str) -> FilingRef | None:
    title = re.search(r"<title>(.*?)</title>", entry, re.S)
    link = re.search(r'<link[^>]*href="([^"]+)"', entry)
    if not title or not link:
        return None
    title_text = re.sub(r"\s+", " ", title.group(1)).strip()
    # "4 - DOE JOHN (0001234567) (Reporting)"
    form_type = title_text.split(" - ", 1)[0].strip()

    href = link.group(1)
    if href.startswith("/"):
        href = BASE + href

    acc = ""
    if m := re.search(r"/(\d{10}-\d{2}-\d{6})-index", href):
        acc = m.group(1)
    elif m := re.search(r"/(\d{18})/", href):
        raw = m.group(1)
        acc = f"{raw[:10]}-{raw[10:12]}-{raw[12:]}"

    cik = ""
    if m := re.search(r"/data/(\d+)/", href):
        cik = m.group(1)

    updated = None
    if m := re.search(r"<updated>(.*?)</updated>", entry):
        try:
            updated = datetime.fromisoformat(m.group(1).strip().replace("Z", "+00:00"))
        except ValueError:
            updated = None

    return FilingRef(form_type=form_type, title=title_text, accession=acc,
                     cik=cik, index_url=href, updated=updated)


def current(form_types: set[str] | None = None, *, count: int = 100,
            query: str = "4") -> list[FilingRef]:
    """Recent filings from the current-filings feed, filtered on exact form type.

    `query` is what goes to the SEC (a prefix); `form_types` is what we accept
    back. They are separate arguments because they are separate things, and
    conflating them is the bug this docstring exists to prevent.

    Results are deduplicated by accession, keeping the issuer-side entry where
    both are present because it carries the issuer CIK.
    """
    form_types = form_types or {"4", "4/A"}
    if count > FEED_MAX:
        count = FEED_MAX
    feed = _fetch(CURRENT.format(type=query, count=count))

    by_accession: dict[str, FilingRef] = {}
    order: list[str] = []
    for entry in re.findall(r"<entry>(.*?)</entry>", feed, re.S):
        ref = _parse_entry(entry)
        if ref is None or ref.form_type not in form_types:
            continue
        key = ref.accession or ref.index_url
        if key not in by_accession:
            by_accession[key] = ref
            order.append(key)
        elif "(Issuer)" in ref.title:
            by_accession[key] = ref
    return [by_accession[k] for k in order]


def ownership_xml_url(ref: FilingRef) -> str | None:
    """Locate the ownership XML inside an accession folder.

    Uses the folder's `index.json` rather than scraping the HTML index, and
    excludes the `xsl...` rendered variants, which are HTML wearing an .xml
    extension and will not parse as an ownership document.
    """
    try:
        listing = json.loads(_fetch(ref.folder + "/index.json"))
    except (FetchError, json.JSONDecodeError):
        return None

    names = [i.get("name", "") for i in listing.get("directory", {}).get("item", [])]
    cands = [n for n in names
             if n.lower().endswith(".xml") and not n.lower().startswith("xsl")]
    if not cands:
        return None
    # Prefer an explicitly form-shaped name when several XMLs are present.
    for n in cands:
        if re.search(r"form\s*[345]", n, re.I) or "ownership" in n.lower():
            return f"{ref.folder}/{n}"
    return f"{ref.folder}/{cands[0]}"


def fetch_form(ref: FilingRef) -> Form4 | None:
    """Fetch and parse one filing. Returns None if it has no ownership document.

    A parse failure raises rather than returning None: "no document here" and
    "the document did not parse" are different events, and a pipeline that
    treats a schema change as an empty folder goes quiet instead of alerting.
    """
    url = ownership_xml_url(ref)
    if url is None:
        return None
    xml = _fetch(url)
    return parse(xml, accession=ref.accession)


def recent_forms(limit: int = 25, *, count: int = FEED_MAX) -> list[Form4]:
    """Convenience: the most recent genuine Form 4/4A filings, parsed.

    Skips filings whose folder holds no ownership XML (paper filings and the
    occasional oddity) and reports nothing about them - they are not failures.
    """
    forms: list[Form4] = []
    for ref in current(count=count):
        if len(forms) >= limit:
            break
        try:
            form = fetch_form(ref)
        except (FetchError, ParseError):
            continue
        if form is not None:
            forms.append(form)
    return forms
