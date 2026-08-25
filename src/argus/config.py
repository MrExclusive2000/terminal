"""
Where Argus keeps its settings, and where it refuses to keep them.

A packaged desktop app cannot ask its user to set an environment variable, so
this replaces `ARGUS_SEC_CONTACT` as the primary source while still honouring
it when present - that keeps the CLI and any scheduled job working unchanged.

**Secrets are deliberately not stored here.** This file is plaintext JSON in a
user-readable directory. The plan is explicit that API keys need OS-level key
isolation (CNG/TPM with a passphrase) and that DPAPI alone is not protection
against the realistic adversary. Until that exists, `api_key` is read from the
environment only and is never written to disk - an app that quietly saves your
key to a plaintext file next to your watchlist has made a security decision on
your behalf, and the wrong one.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

APP_NAME = "Argus"
SETTINGS_FILE = "settings.json"

#: Honoured when set, so existing scripts and CI keep working.
CONTACT_ENV = "ARGUS_SEC_CONTACT"
#: Never persisted. Read at use, held in memory only.
API_KEY_ENV = "ANTHROPIC_API_KEY"

_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def data_dir() -> Path:
    """Per-user writable directory, correct for the platform.

    Windows uses LOCALAPPDATA rather than APPDATA on purpose: this holds a
    cache and a lake that can reach tens of gigabytes, and roaming profiles
    should not try to sync it across machines.
    """
    if override := os.environ.get("ARGUS_DATA_DIR"):
        return Path(override).expanduser()
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        return Path(base or Path.home() / "AppData/Local") / APP_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support" / APP_NAME
    base = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local/share")
    return Path(base) / APP_NAME.lower()


def settings_path() -> Path:
    return data_dir() / SETTINGS_FILE


def frozen() -> bool:
    """True when running from a PyInstaller bundle rather than source."""
    return bool(getattr(sys, "frozen", False))


def resource(*parts: str) -> Path:
    """Locate a bundled read-only asset.

    PyInstaller unpacks data files to `sys._MEIPASS` at runtime, so any path
    built from `__file__` points into the wrong place - or into a directory that
    does not exist at all in a onefile build. Every asset lookup goes through
    here so the frozen and source layouts cannot drift apart.
    """
    if frozen():
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        return base.joinpath(*parts)
    return Path(__file__).resolve().parent.joinpath(*parts)


def version() -> str:
    """App version, written at build time and falling back for source runs."""
    try:
        return (resource("VERSION").read_text(encoding="utf-8").strip()
                or "0.0.0-dev")
    except OSError:
        return "0.0.0-dev"


@dataclass
class Settings:
    #: Name and email. SEC fair access refuses unidentified traffic with a 403.
    sec_contact: str = ""
    #: Non-professional status is the single largest cost variable in the plan,
    #: so it is an explicit setting rather than an assumption.
    professional: bool = False
    account_currency: str = "GBP"
    risk_percent: float = 1.0
    balance: float = 25000.0
    insider_limit: int = 40
    update_check: bool = True
    window: dict[str, int] = field(default_factory=dict)
    #: Bumped when a first run has completed, so onboarding shows exactly once.
    onboarded: bool = False

    def contact(self) -> str:
        """Effective SEC contact: environment first, then the saved setting.

        Environment wins so a scheduled run can override the desktop setting
        without editing the user's file underneath them.
        """
        return (os.environ.get(CONTACT_ENV, "").strip() or self.sec_contact.strip())

    def contact_ok(self) -> bool:
        return bool(_EMAIL.search(self.contact()))

    @staticmethod
    def api_key() -> str:
        """Read at point of use. Never stored, never logged, never returned to the UI."""
        return os.environ.get(API_KEY_ENV, "").strip()

    def public(self) -> dict[str, Any]:
        """Settings safe to hand to the UI. No secrets pass through here."""
        d = asdict(self)
        d["contact_ok"] = self.contact_ok()
        d["contact_from_env"] = bool(os.environ.get(CONTACT_ENV, "").strip())
        d["api_key_present"] = bool(self.api_key())
        d["data_dir"] = str(data_dir())
        return d


def load() -> Settings:
    """Load settings, tolerating a missing or corrupt file.

    A malformed settings file returns defaults rather than raising: losing your
    preferences is annoying, but an app that will not start because one JSON
    file got truncated by a bad shutdown is worse.
    """
    p = settings_path()
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError, UnicodeDecodeError):
        return Settings()
    if not isinstance(raw, dict):
        return Settings()

    known = {f.name: f for f in fields(Settings)}
    kwargs: dict[str, Any] = {}
    for name, value in raw.items():
        f = known.get(name)
        if f is None:
            continue                      # forward-compatible: ignore unknown keys
        try:
            if f.type in ("bool", bool):
                kwargs[name] = bool(value)
            elif f.type in ("int", int):
                kwargs[name] = int(value)
            elif f.type in ("float", float):
                kwargs[name] = float(value)
            elif f.type in ("str", str):
                kwargs[name] = str(value)
            elif name == "window" and isinstance(value, dict):
                kwargs[name] = {k: int(v) for k, v in value.items()
                                if isinstance(v, (int, float))}
        except (TypeError, ValueError):
            continue                      # a bad field falls back to its default
    return Settings(**kwargs)


def save(s: Settings) -> Path:
    """Write settings atomically.

    Temp file plus replace, so a crash or a pulled power cable during the write
    leaves the previous file intact rather than a half-written one. The naive
    open-and-write is how config files get truncated to zero bytes.
    """
    d = data_dir()
    d.mkdir(parents=True, exist_ok=True)
    p = settings_path()
    payload = json.dumps(asdict(s), indent=2, sort_keys=True)

    fd, tmp = tempfile.mkstemp(dir=str(d), prefix=".settings-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, p)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return p


def update(**changes: Any) -> Settings:
    """Load, apply changes, save. Unknown keys are ignored, not an error."""
    s = load()
    known = {f.name for f in fields(Settings)}
    for k, v in changes.items():
        if k in known:
            setattr(s, k, v)
    save(s)
    return s
