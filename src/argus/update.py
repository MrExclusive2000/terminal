"""
Update checking and applying, with the verification that makes it defensible.

The first version of this module refused to download anything, on the grounds
that "an updater that cannot verify what it fetched is a remote code execution
path rather than a feature". That reasoning was right and the conclusion was
too broad: there *is* something to verify against short of code signing.

**What is verified.** The GitHub releases API returns, for every asset, a
`digest` field of the form `sha256:...` alongside its size. So the flow is:

  1. fetch release metadata from api.github.com over TLS,
  2. download the asset from the URL that metadata names,
  3. hash the received bytes and compare with the digest the API stated,
  4. only then execute it.

**What that is worth, precisely.** It defeats a corrupted or truncated
download, and it defeats an asset substituted at the storage or CDN layer
without a matching change to the API response. It does **not** defeat a
compromise of the repository itself: an attacker who can publish a release can
publish a matching digest, and the hash then verifies a file they chose. Only
code signing fixes that, by moving trust to a key that GitHub does not hold.

That residual is stated in the UI rather than papered over. It is also worth
being clear that the manual path has the *same* exposure - a user who clicks
the release link and runs the installer trusts exactly the same publisher - so
this does not meaningfully widen the threat surface. What it adds is the loss
of a human pause, which is why the default is to ask before installing.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .data.http import FetchError, get

REPO = "MrExclusive2000/terminal"
RELEASES = f"https://api.github.com/repos/{REPO}/releases/latest"

#: The only hosts an update may be fetched from. GitHub serves release assets
#: via a redirect to its object storage, so both are needed. Checked after
#: redirects, because a permitted URL that redirects anywhere is not a control.
ALLOWED_HOSTS = {"github.com", "api.github.com", "objects.githubusercontent.com",
                 "release-assets.githubusercontent.com"}

#: Refuse anything implausible before writing it to disk.
MAX_BYTES = 300 * 1024 * 1024

_SEMVER = re.compile(r"(\d+)\.(\d+)\.(\d+)(?:[-+](.*))?")


def parse_version(v: str) -> tuple[int, int, int] | None:
    m = _SEMVER.search((v or "").strip().lstrip("vV"))
    if not m:
        return None
    return int(m[1]), int(m[2]), int(m[3])


def is_newer(candidate: str, current: str) -> bool:
    """True if `candidate` is a strictly higher release than `current`.

    Build metadata is ignored for ordering, and an unparseable version on
    either side returns False - "I could not tell" must never present as
    "you are out of date".
    """
    c, n = parse_version(candidate), parse_version(current)
    if c is None or n is None:
        return False
    return c > n


@dataclass(frozen=True)
class Asset:
    name: str
    url: str
    size: int
    sha256: str          # lowercase hex, "" when the API did not state one

    @property
    def verifiable(self) -> bool:
        return len(self.sha256) == 64


@dataclass(frozen=True)
class Release:
    version: str
    url: str
    notes: str
    asset: Asset | None


def _parse_release(raw: dict) -> Release | None:
    if not isinstance(raw, dict) or raw.get("draft"):
        return None
    tag = str(raw.get("tag_name") or "").strip()
    if not tag:
        return None

    asset = None
    for a in raw.get("assets") or []:
        name = str(a.get("name") or "")
        if not name.lower().endswith(".exe"):
            continue
        digest = str(a.get("digest") or "")
        sha = digest.split("sha256:", 1)[1].strip().lower() if "sha256:" in digest else ""
        asset = Asset(name=name, url=str(a.get("browser_download_url") or ""),
                      size=int(a.get("size") or 0), sha256=sha)
        break

    return Release(version=tag.lstrip("vV"), url=str(raw.get("html_url") or ""),
                   notes=str(raw.get("body") or "")[:2000], asset=asset)


def latest(*, timeout: float = 12.0) -> Release | None:
    """The newest published release, or None if it cannot be determined.

    Never raises: a failed update check is not a reason to show the user an
    error. It is a reason to say nothing.
    """
    try:
        raw = json.loads(get(RELEASES, timeout=timeout, attempts=2,
                             user_agent=f"argus-terminal updater ({REPO})"))
    except Exception:  # noqa: BLE001
        return None
    return _parse_release(raw)


def check(current: str) -> dict:
    """UI-shaped result. Always returns; never throws."""
    rel = latest()
    if rel is None:
        return {"checked": False, "current": current,
                "message": "Could not reach the update service."}
    if not is_newer(rel.version, current):
        return {"checked": True, "update_available": False, "current": current,
                "latest": rel.version, "message": "You are on the latest version."}
    return {"checked": True, "update_available": True, "current": current,
            "latest": rel.version, "url": rel.url, "notes": rel.notes,
            "asset": rel.asset.name if rel.asset else None,
            "size": rel.asset.size if rel.asset else 0,
            "verifiable": bool(rel.asset and rel.asset.verifiable),
            "can_install": bool(rel.asset and rel.asset.verifiable
                                and sys.platform == "win32"),
            "message": f"Version {rel.version} is available."}


# --------------------------------------------------------------------------
# download and verify
# --------------------------------------------------------------------------

class UpdateError(RuntimeError):
    pass


def _host_of(url: str) -> str:
    from urllib.parse import urlparse
    return (urlparse(url).hostname or "").lower()


def download(asset: Asset, *, dest_dir: str | None = None,
             timeout: float = 300.0) -> Path:
    """Fetch `asset`, verify it, and return the path. Raises on any mismatch.

    The file is written with a `.part` suffix and only renamed once the hash
    matches, so a half-written or wrong download can never be mistaken for an
    installer that is ready to run.
    """
    if not asset.verifiable:
        raise UpdateError(
            "The release does not publish a SHA-256 for this asset, so the "
            "download cannot be verified. Install manually from the releases "
            "page instead.")
    if _host_of(asset.url) not in ALLOWED_HOSTS:
        raise UpdateError(f"Refusing to download from {_host_of(asset.url)!r}.")

    d = Path(dest_dir or tempfile.mkdtemp(prefix="argus-update-"))
    d.mkdir(parents=True, exist_ok=True)
    part = d / (asset.name + ".part")

    req = urllib.request.Request(
        asset.url, headers={"User-Agent": f"argus-terminal updater ({REPO})"})
    digest = hashlib.sha256()
    total = 0
    with urllib.request.urlopen(req, timeout=timeout) as r:
        # Re-check the host *after* redirects: GitHub redirects to object
        # storage, and permitting the first URL while ignoring where it lands
        # would not be a control at all.
        final = _host_of(r.geturl())
        if final not in ALLOWED_HOSTS:
            raise UpdateError(f"Download redirected to {final!r}; refusing.")
        with open(part, "wb") as fh:
            while chunk := r.read(1 << 16):
                total += len(chunk)
                if total > MAX_BYTES:
                    raise UpdateError("Download exceeded the size limit.")
                digest.update(chunk)
                fh.write(chunk)

    got = digest.hexdigest()
    if asset.size and total != asset.size:
        part.unlink(missing_ok=True)
        raise UpdateError(f"Size mismatch: expected {asset.size}, got {total}.")
    if got != asset.sha256:
        part.unlink(missing_ok=True)
        raise UpdateError(
            f"Checksum mismatch. Expected {asset.sha256[:16]}…, got {got[:16]}…. "
            "The download was discarded and nothing was run.")

    final_path = d / asset.name
    part.replace(final_path)
    return final_path


def apply(installer: Path, *, silent: bool = True) -> None:
    """Launch the verified installer and leave. Windows only.

    Detached on purpose: the installer has to replace this executable, which it
    cannot do while we hold it open. The caller is expected to exit immediately
    afterwards.
    """
    if sys.platform != "win32":
        raise UpdateError("Applying an update is only supported on Windows.")
    if not installer.is_file():
        raise UpdateError(f"Installer not found: {installer}")

    args = [str(installer)]
    if silent:
        # Inno Setup: no wizard, no prompts, but keep the progress window so a
        # user is never left wondering why their app vanished for ten seconds.
        args += ["/SILENT", "/NOCANCEL", "/RESTARTAPPLICATIONS"]

    creation = getattr(subprocess, "DETACHED_PROCESS", 0) | \
        getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    subprocess.Popen(args, close_fds=True, creationflags=creation)
