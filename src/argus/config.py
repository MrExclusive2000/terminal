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

#: Offered in the settings screen. Opus 5 is the default and the right choice
#: for analysis; Sonnet is the cheaper high-volume option. Kept as an explicit
#: list so the UI cannot offer a model id this build has never been run against.
AI_MODELS = ["claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5"]
AI_EFFORTS = ["low", "medium", "high", "xhigh", "max"]


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


def bundle_root() -> Path:
    """Root that bundled data paths are relative to.

    Frozen, PyInstaller unpacks data to `sys._MEIPASS` (the `_internal`
    directory in a onedir build). From source, the equivalent root is the
    repository, because that is what the spec's destination paths are written
    against.
    """
    if frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parents[2]


def resource(*parts: str) -> Path:
    """Locate an asset that lives *inside the argus package*.

    The spec bundles these to `argus/...` under `_MEIPASS`, mirroring their
    source location under `src/argus/`, so the package prefix has to be applied
    in the frozen branch too.

    This is exactly where the first shipped build broke: the frozen branch
    returned `_MEIPASS/app/ui.html` while the file was at
    `_MEIPASS/argus/app/ui.html`. VERSION silently fell back to "0.0.0-dev"
    (visible in the title bar) and the UI raised FileNotFoundError inside the
    request handler, which killed the thread without sending a response - the
    browser reported ERR_EMPTY_RESPONSE with nothing to go on. An earlier
    version of this docstring claimed the two layouts "cannot drift apart".
    They drifted. `--check` in the launcher now proves they have not.
    """
    if frozen():
        return bundle_root().joinpath("argus", *parts)
    return Path(__file__).resolve().parent.joinpath(*parts)


def bundled(*parts: str) -> Path:
    """Locate an asset bundled at the root of the bundle, outside the package.

    Knowledge packs are the case: the spec places them at `knowledge/packs`,
    not under `argus/`.
    """
    return bundle_root().joinpath(*parts)


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

    # -- broker (MetaTrader 5) -----------------------------------------
    #: Path to terminal64.exe. Blank means "attach to whatever terminal is
    #: already running", which is the normal case and needs no configuration.
    mt5_path: str = ""
    #: Brokers suffix their symbols by account type - IC Markets uses forms
    #: like XAUUSD, XAUUSD.a, XAUUSD.r. Getting this wrong reads as "symbol not
    #: found" rather than as a configuration problem, so it is an explicit
    #: setting with a discovery button beside it.
    mt5_suffix: str = ""
    mt5_enabled: bool = True

    # -- AI ------------------------------------------------------------
    #: The API key is NOT here. It lives in secrets.py, which encrypts it under
    #: DPAPI on Windows. See that module for what that is and is not worth.
    ai_enabled: bool = True
    ai_model: str = "claude-opus-5"
    #: Effort trades thoroughness against tokens. "high" is the API default and
    #: the sensible desk setting; "low" is for a quick read.
    ai_effort: str = "high"
    #: A hard monthly ceiling the cost meter checks before each call, so a
    #: runaway loop cannot quietly spend a fortune.
    ai_monthly_budget_usd: float = 25.0

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
        """Read at point of use. Never logged, never returned to the UI.

        Delegates to the secret store, which checks the environment first and
        falls back to the DPAPI-protected file.
        """
        try:
            from .secrets import get
            return get("anthropic_api_key")
        except Exception:  # noqa: BLE001
            return os.environ.get(API_KEY_ENV, "").strip()

    def public(self) -> dict[str, Any]:
        """Settings safe to hand to the UI. No secrets pass through here."""
        d = asdict(self)
        d["contact_ok"] = self.contact_ok()
        d["contact_from_env"] = bool(os.environ.get(CONTACT_ENV, "").strip())
        d["data_dir"] = str(data_dir())
        d["version"] = version()
        try:
            from .secrets import status
            d["api_key"] = status("anthropic_api_key")
        except Exception:  # noqa: BLE001 - the settings screen must still open
            d["api_key"] = {"present": False, "protection": "unknown",
                            "protection_note": "Secret store unavailable."}
        d["ai_models"] = AI_MODELS
        d["ai_efforts"] = AI_EFFORTS
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
