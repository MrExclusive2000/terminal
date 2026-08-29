"""
Secret storage, and an honest account of what it protects against.

The first build stored nothing and read the API key from an environment
variable. That is defensible on a server and wrong on a desktop: a user who
double-clicks an installer has no reasonable way to set a persistent
environment variable, so the AI features were effectively unreachable. Worse,
it was not even a security win - user environment variables live in the
registry in plaintext and are readable by anything running as that user, so the
"safer" option was equally exposed *and* unusable.

**What this does.** On Windows, secrets are encrypted with DPAPI
(`CryptProtectData`) under the current user and written to a file separate from
settings.json. On other platforms there is no equivalent, so the value is
written in plaintext with owner-only permissions and `protection()` says so.

**What that is worth, precisely.** DPAPI stops:

  * the key sitting in plaintext on disk, so a stray backup, a synced folder or
    a support screenshot of settings.json does not leak it;
  * another *user account* on the same machine reading it.

It does **not** stop malware running as you. Any process with your token can
call `CryptUnprotectData` and get the plaintext back - that is exactly what the
current infostealer families do, and Chrome's App-Bound Encryption tried to fix
this class of problem and was bypassed in about 45 days.

The plan is explicit that "DPAPI alone for secrets, *presented as protection*"
is an anti-pattern. Presenting it accurately is not. The real control is a
passphrase-derived key with CNG/TPM isolation; until that exists this is the
honest middle, and every surface that shows it says the same thing.
"""
from __future__ import annotations

import base64
import ctypes
import os
import sys
import tempfile
from pathlib import Path
from typing import Literal

from .config import data_dir

# ctypes.wintypes is Windows-shaped and has historically raised on other
# platforms depending on the Python build. This module must never fail at
# import - it is loaded on the settings path of a cross-platform app - so the
# import is guarded and the DPAPI branch is unreachable without it anyway.
try:
    from ctypes import wintypes as _wintypes
except Exception:  # noqa: BLE001 - non-Windows, or a build without it
    _wintypes = None

SECRETS_FILE = "secrets.dat"
Protection = Literal["dpapi", "plaintext"]

#: Keys this store will hold. An unknown name is rejected rather than written,
#: so a typo cannot silently create an orphan secret that nothing reads back.
KNOWN = {"anthropic_api_key"}

#: Environment overrides, checked before stored values so a scheduled run or a
#: CI job can supply a key without touching the user's file.
ENV = {"anthropic_api_key": "ANTHROPIC_API_KEY"}


def secrets_path() -> Path:
    return data_dir() / SECRETS_FILE


def protection() -> Protection:
    return "dpapi" if (sys.platform == "win32" and _wintypes is not None) else "plaintext"


def protection_note() -> str:
    """One sentence for the UI. Accurate, not reassuring."""
    if protection() == "dpapi":
        return ("Encrypted with Windows DPAPI under your user account. That keeps "
                "it out of plaintext on disk and away from other accounts on this "
                "PC. It does not protect against malware running as you.")
    return ("Stored as plaintext with owner-only file permissions - this platform "
            "has no DPAPI equivalent in this build. Prefer the ANTHROPIC_API_KEY "
            "environment variable here.")


# --------------------------------------------------------------------------
# Windows DPAPI via ctypes - no third-party dependency
# --------------------------------------------------------------------------

if _wintypes is not None:
    class _Blob(ctypes.Structure):
        _fields_ = [("cbData", _wintypes.DWORD),
                    ("pbData", ctypes.POINTER(ctypes.c_char))]
else:                                        # pragma: no cover - non-Windows
    class _Blob(ctypes.Structure):           # type: ignore[no-redef]
        _fields_ = [("cbData", ctypes.c_ulong),
                    ("pbData", ctypes.POINTER(ctypes.c_char))]


def _blob(data: bytes) -> _Blob:
    buf = ctypes.create_string_buffer(data, len(data))
    return _Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))


def _blob_bytes(b: _Blob) -> bytes:
    return ctypes.string_at(b.pbData, b.cbData)


def _dpapi(data: bytes, *, encrypt: bool) -> bytes:
    """Round-trip through CryptProtectData / CryptUnprotectData."""
    crypt32 = ctypes.windll.crypt32          # type: ignore[attr-defined]
    kernel32 = ctypes.windll.kernel32        # type: ignore[attr-defined]
    fn = crypt32.CryptProtectData if encrypt else crypt32.CryptUnprotectData

    src, out = _blob(data), _Blob()
    # CRYPTPROTECT_UI_FORBIDDEN (0x1): never prompt. This runs in a GUI app with
    # no console; a blocking system dialog would look like a hang.
    args = ([ctypes.byref(src), None, None, None, None, 0x1, ctypes.byref(out)]
            if encrypt else
            [ctypes.byref(src), None, None, None, None, 0x1, ctypes.byref(out)])
    if not fn(*args):
        raise OSError(f"DPAPI {'encrypt' if encrypt else 'decrypt'} failed "
                      f"(error {ctypes.get_last_error()})")
    try:
        return _blob_bytes(out)
    finally:
        kernel32.LocalFree(out.pbData)


def _seal(plaintext: str) -> str:
    raw = plaintext.encode("utf-8")
    if protection() == "dpapi":
        raw = _dpapi(raw, encrypt=True)
    return base64.b64encode(raw).decode("ascii")


def _unseal(stored: str) -> str:
    raw = base64.b64decode(stored.encode("ascii"))
    if protection() == "dpapi":
        raw = _dpapi(raw, encrypt=False)
    return raw.decode("utf-8")


# --------------------------------------------------------------------------
# store
# --------------------------------------------------------------------------

def _read_all() -> dict[str, str]:
    try:
        text = secrets_path().read_text(encoding="utf-8")
    except (FileNotFoundError, OSError, UnicodeDecodeError):
        return {}
    out: dict[str, str] = {}
    for line in text.splitlines():
        name, _, value = line.partition("=")
        if name.strip() in KNOWN and value.strip():
            out[name.strip()] = value.strip()
    return out


def _write_all(rows: dict[str, str]) -> None:
    d = data_dir()
    d.mkdir(parents=True, exist_ok=True)
    body = "".join(f"{k}={v}\n" for k, v in sorted(rows.items()))

    fd, tmp = tempfile.mkstemp(dir=str(d), prefix=".secrets-", suffix=".tmp")
    try:
        os.chmod(tmp, 0o600)      # owner only, before anything is written
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(body)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, secrets_path())
        os.chmod(secrets_path(), 0o600)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def get(name: str) -> str:
    """The secret, environment first. Returns "" when unset or unreadable.

    A decryption failure returns "" rather than raising: DPAPI ciphertext does
    not survive a different Windows user or a restored profile, and an app that
    refuses to start because an optional API key cannot be decrypted has turned
    a re-entry into an outage.
    """
    if name not in KNOWN:
        raise KeyError(f"unknown secret {name!r}")
    if env := os.environ.get(ENV.get(name, ""), "").strip():
        return env
    stored = _read_all().get(name)
    if not stored:
        return ""
    try:
        return _unseal(stored)
    except Exception:  # noqa: BLE001 - unreadable is the same as absent here
        return ""


def set_secret(name: str, value: str) -> None:
    """Store or, with an empty value, remove a secret."""
    if name not in KNOWN:
        raise KeyError(f"unknown secret {name!r}")
    rows = _read_all()
    value = (value or "").strip()
    if value:
        rows[name] = _seal(value)
    else:
        rows.pop(name, None)
    _write_all(rows)


def status(name: str) -> dict:
    """UI-shaped state. Never returns the secret itself.

    `masked` shows only the last four characters, which is enough to confirm
    *which* key is loaded without putting the value on screen or in a log.
    """
    if name not in KNOWN:
        raise KeyError(f"unknown secret {name!r}")
    from_env = bool(os.environ.get(ENV.get(name, ""), "").strip())
    value = get(name)
    return {"present": bool(value),
            "from_env": from_env,
            "stored": name in _read_all(),
            "masked": f"...{value[-4:]}" if len(value) >= 8 else ("set" if value else ""),
            "protection": protection(),
            "protection_note": protection_note()}
