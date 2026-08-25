"""
Settings, versioning and packaging-support tests. No network, no GUI.

These cover the machinery a packaged desktop app needs and a script does not:
a settings file that survives a bad shutdown, version comparison that refuses
to guess, and a secrets boundary that holds even when the caller asks nicely.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "src")

PASS = FAIL = 0


def check(label: str, cond: bool) -> bool:
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    return cond


def main() -> int:
    tmp = tempfile.mkdtemp()
    os.environ["ARGUS_DATA_DIR"] = tmp
    os.environ.pop("ARGUS_SEC_CONTACT", None)

    from argus import config, update
    from argus.app import server

    print("\n[config] location and defaults")
    check("data dir honours the override", str(config.data_dir()) == tmp)
    check("settings file sits inside it",
          config.settings_path().parent == Path(tmp))
    s = config.load()
    check("a missing file yields defaults", s.sec_contact == "")
    check("defaults are not 'configured'", not s.contact_ok())
    check("version is readable", bool(config.version()))
    check("not frozen when run from source", config.frozen() is False)
    check("bundled UI resolves from source layout",
          config.resource("app", "ui.html").exists())

    print("\n[config] persistence")
    s.sec_contact = "Jane Doe jane@example.com"
    s.balance = 50000.0
    config.save(s)
    again = config.load()
    check("round-trips the contact", again.contact() == "Jane Doe jane@example.com")
    check("round-trips a float", again.balance == 50000.0)
    check("contact with an email validates", again.contact_ok())

    print("\n[config] survives a damaged file")
    config.settings_path().write_text("{ truncated", encoding="utf-8")
    check("corrupt JSON falls back to defaults, no raise",
          config.load().sec_contact == "")
    config.settings_path().write_text("[]", encoding="utf-8")
    check("wrong top-level type falls back", config.load().sec_contact == "")
    config.settings_path().write_text(
        json.dumps({"sec_contact": "A B a@b.co", "risk_percent": "not a number",
                    "balance": "5000", "unknown_future_key": {"x": 1}}),
        encoding="utf-8")
    r = config.load()
    check("a bad field falls back to its default", r.risk_percent == 1.0)
    check("a coercible field is coerced", r.balance == 5000.0)
    check("unknown keys are ignored, not fatal", r.contact() == "A B a@b.co")

    print("\n[config] atomic write leaves no debris")
    config.update(sec_contact="Jane Doe jane@example.com")
    leftovers = [p for p in Path(tmp).iterdir() if p.name.startswith(".settings-")]
    check("no temp files left behind", leftovers == [])

    print("\n[config] the environment overrides the file")
    os.environ["ARGUS_SEC_CONTACT"] = "Env Person env@example.com"
    check("env wins for the effective contact",
          config.load().contact() == "Env Person env@example.com")
    check("public() flags the override", config.load().public()["contact_from_env"])
    os.environ.pop("ARGUS_SEC_CONTACT", None)

    print("\n[config] secrets never touch the settings file")
    os.environ["ANTHROPIC_API_KEY"] = "sk-test-should-never-persist"
    pub = config.load().public()
    check("public() reports presence, not the value", pub["api_key_present"] is True)
    check("public() contains no key field", "api_key" not in pub)
    blob = config.settings_path().read_text(encoding="utf-8")
    check("the key is absent from the settings file on disk",
          "sk-test-should-never-persist" not in blob)
    res = server.ep_settings_save({"api_key": "sk-abc"})
    check("POSTing a secret is refused, not silently dropped", res["ok"] is False)
    check("the refusal explains where the key should go",
          "ANTHROPIC_API_KEY" in res["error"])
    blob = config.settings_path().read_text(encoding="utf-8")
    check("a refused POST wrote nothing", "sk-abc" not in blob)
    os.environ.pop("ANTHROPIC_API_KEY", None)

    print("\n[settings api] whitelist")
    check("unknown-only payloads are rejected",
          server.ep_settings_save({"evil": 1})["ok"] is False)
    ok = server.ep_settings_save({"balance": 1234.0, "evil": 1})
    check("a valid field saves", ok["ok"] is True and config.load().balance == 1234.0)
    check("the unknown field alongside it is dropped",
          "evil" not in json.loads(config.settings_path().read_text(encoding="utf-8")))
    check("saved settings come back without secrets",
          "api_key" not in ok["settings"])

    print("\n[update] version comparison refuses to guess")
    for cand, cur, want in (("0.2.0", "0.1.0", True), ("0.1.0", "0.1.0", False),
                            ("0.1.0", "0.2.0", False), ("v1.0.0", "0.9.9", True),
                            ("0.10.0", "0.9.0", True), ("garbage", "0.1.0", False),
                            ("0.1.0", "garbage", False), ("", "0.1.0", False),
                            ("1.0.0-beta", "1.0.0", False)):
        check(f"is_newer({cand!r}, {cur!r}) is {want}",
              update.is_newer(cand, cur) is want)
    check("parse_version tolerates a v prefix",
          update.parse_version("v2.3.4") == (2, 3, 4))
    check("parse_version returns None on junk",
          update.parse_version("not-a-version") is None)

    print("\n[launcher] single instance")
    sys.path.insert(0, ".")
    import run as launcher
    first = launcher._acquire_single_instance()
    check("the first process takes the lock", first is not None)
    check("a second process is refused", launcher._acquire_single_instance() is None)
    if first:
        first.close()
    check("the lock is reusable once released",
          (lambda s: (s is not None, s and s.close())[0])(
              launcher._acquire_single_instance()))

    print("\n[packaging] the build inputs exist and are well-formed")
    import struct
    ico = Path("packaging/argus.ico")
    check("icon exists", ico.exists())
    d = ico.read_bytes()
    reserved, kind, count = struct.unpack("<HHH", d[:6])
    check("icon is a valid ICO container", reserved == 0 and kind == 1 and count >= 5)
    sizes = []
    good_png = True
    for i in range(count):
        w, _h, _c, _r, _p, _b, sz, off = struct.unpack("<BBBBHHII", d[6 + 16 * i:22 + 16 * i])
        sizes.append(w or 256)
        good_png &= d[off:off + 8] == b"\x89PNG\r\n\x1a\n"
    check("every icon entry is a real PNG", good_png)
    check("includes a 16px entry for the taskbar", 16 in sizes)
    check("includes a 256px entry for high DPI", 256 in sizes)
    import ast
    ast.parse(Path("packaging/argus.spec").read_text())
    check("the PyInstaller spec parses as Python", True)
    iss = Path("packaging/argus.iss").read_text()
    check("the installer is per-user (no admin prompt)",
          "PrivilegesRequired=lowest" in iss)
    check("uninstall does not delete the user's data",
          "LOCALAPPDATA" in iss and "{userappdata}" not in iss)
    wf = Path(".github/workflows/build-windows.yml").read_text()
    check("CI builds on a Windows runner", "runs-on: windows-latest" in wf)
    check("CI verifies bundled assets, not just that the exe exists",
          "missing bundled asset" in wf)

    print(f"\n{'-' * 60}\n  {PASS} passed, {FAIL} failed\n")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
