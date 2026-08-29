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


def _raises(fn) -> bool:
    """True if `fn` raises. Used where refusing is the correct behaviour."""
    try:
        fn()
    except Exception:  # noqa: BLE001
        return True
    return False


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
    check("public() reports presence, not the value",
          pub["api_key"]["present"] is True)
    check("public() never carries the key itself",
          "should-never-persist" not in json.dumps(pub))
    blob = config.settings_path().read_text(encoding="utf-8")
    check("the key is absent from the settings file on disk",
          "sk-test-should-never-persist" not in blob)
    res = server.ep_settings_save({"api_key": "sk-abc"})
    check("POSTing a secret to /api/settings is refused", res["ok"] is False)
    check("the refusal points at the right endpoint",
          "/api/secret" in res["error"])
    blob = config.settings_path().read_text(encoding="utf-8")
    check("a refused POST wrote nothing", "sk-abc" not in blob)
    os.environ.pop("ANTHROPIC_API_KEY", None)

    print("\n[secrets] storage and the environment override")
    from argus import secrets as sec
    os.environ.pop("ANTHROPIC_API_KEY", None)
    sec.set_secret("anthropic_api_key", "")
    check("an unset secret reports absent", sec.get("anthropic_api_key") == "")
    check("status on an unset secret is clean",
          sec.status("anthropic_api_key")["present"] is False)
    sec.set_secret("anthropic_api_key", "sk-ant-api03-ROUNDTRIPVALUE001")
    check("a stored secret round-trips",
          sec.get("anthropic_api_key") == "sk-ant-api03-ROUNDTRIPVALUE001")
    check("status masks to the last four only",
          sec.status("anthropic_api_key")["masked"] == "...E001")
    check("status never carries the value",
          "ROUNDTRIPVALUE" not in json.dumps(sec.status("anthropic_api_key")))
    check("secrets live outside settings.json",
          sec.secrets_path() != config.settings_path())
    check("settings.json never contains the secret",
          "ROUNDTRIPVALUE" not in config.settings_path().read_text(encoding="utf-8"))
    if os.name != "nt":
        check("the secret file is owner-only",
              oct(sec.secrets_path().stat().st_mode & 0o777) == "0o600")
    check("an unknown secret name is rejected", _raises(lambda: sec.get("nope")))
    check("writing an unknown secret is rejected",
          _raises(lambda: sec.set_secret("nope", "x")))
    os.environ["ANTHROPIC_API_KEY"] = "sk-env-wins-here-000000"
    check("the environment overrides the stored value",
          sec.get("anthropic_api_key") == "sk-env-wins-here-000000")
    check("and the override is flagged for the UI",
          sec.status("anthropic_api_key")["from_env"] is True)
    os.environ.pop("ANTHROPIC_API_KEY", None)
    check("Settings.api_key() reads through the secret store",
          config.Settings.api_key() == "sk-ant-api03-ROUNDTRIPVALUE001")
    check("protection is named honestly",
          sec.protection() in ("dpapi", "plaintext"))
    check("the protection note states what it does NOT stop",
          "malware" in sec.protection_note().lower()
          or "plaintext" in sec.protection_note().lower())
    sec.set_secret("anthropic_api_key", "")
    check("clearing removes it", sec.get("anthropic_api_key") == "")

    print("\n[secrets api] the key never travels through settings")
    r = server.ep_secret_save({"anthropic_api_key": "not-a-key"})
    check("a malformed key is refused", r["ok"] is False and "sk-" in r["error"])
    check("and nothing was written", sec.get("anthropic_api_key") == "")
    r = server.ep_secret_save({"anthropic_api_key": "sk-ant-api03-VIAENDPOINT123"})
    check("a well-formed key is stored", r["ok"] is True)
    check("the response returns status, not the key",
          "VIAENDPOINT" not in json.dumps(r))
    check("an empty value clears the key",
          server.ep_secret_save({"anthropic_api_key": ""})["cleared"] is True)

    print("\n[settings] broker and AI fields")
    d = config.load()
    check("mt5 fields exist with safe defaults",
          d.mt5_path == "" and d.mt5_suffix == "" and d.mt5_enabled is True)
    check("ai defaults to opus-5 at high effort",
          d.ai_model == "claude-opus-5" and d.ai_effort == "high")
    check("a monthly budget is set", d.ai_monthly_budget_usd > 0)
    ok = server.ep_settings_save({"mt5_suffix": ".a", "mt5_path": "C:/mt5/terminal64.exe",
                                  "ai_model": "claude-sonnet-5", "ai_effort": "xhigh"})
    check("broker and AI settings save", ok["ok"] is True)
    d = config.load()
    check("the suffix persisted", d.mt5_suffix == ".a")
    check("the model persisted", d.ai_model == "claude-sonnet-5")
    check("an unknown model is refused",
          server.ep_settings_save({"ai_model": "gpt-4"})["ok"] is False)
    check("an unknown effort is refused",
          server.ep_settings_save({"ai_effort": "turbo"})["ok"] is False)
    check("the refused model did not overwrite the stored one",
          config.load().ai_model == "claude-sonnet-5")
    pub = config.load().public()
    check("public() offers only models this build knows",
          set(pub["ai_models"]) <= {"claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5"})
    check("public() reports key status without the key",
          "api_key" in pub and "masked" in pub["api_key"])

    print("\n[connection tests] fail honestly rather than raising")
    m = server.ep_test_mt5()
    check("the MT5 test returns a verdict, never an exception",
          isinstance(m, dict) and "ok" in m)
    if not m["ok"]:
        check("a failed MT5 test explains itself", bool(m.get("error")))
    a = server.ep_test_ai()
    check("the AI test returns a verdict", isinstance(a, dict) and "ok" in a)
    check("the AI test never echoes the key", "sk-" not in json.dumps(a))
    config.update(ai_model="claude-opus-5")

    print("\n[settings api] whitelist")
    check("unknown-only payloads are rejected",
          server.ep_settings_save({"evil": 1})["ok"] is False)
    ok = server.ep_settings_save({"balance": 1234.0, "evil": 1})
    check("a valid field saves", ok["ok"] is True and config.load().balance == 1234.0)
    check("the unknown field alongside it is dropped",
          "evil" not in json.loads(config.settings_path().read_text(encoding="utf-8")))
    check("saved settings come back without a usable secret",
          "sk-test-should-never-persist" not in json.dumps(ok["settings"]))

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

    print("\n[update] release parsing against real release metadata")
    from argus import update as upd
    raw = json.loads((Path("tests/fixtures/release-latest.json")).read_text())
    rel = upd._parse_release(raw)
    check("version parsed without the v prefix", rel.version == "0.1.2")
    check("the installer asset is found", rel.asset.name.endswith(".exe"))
    check("the size is carried", rel.asset.size == 26907375)
    check("the sha256 is extracted from the digest field",
          rel.asset.sha256 == "7f997a52086a1cade97857d636706debb1a8455ef782cbaca332d4bebc4d7fba")
    check("the asset reports itself verifiable", rel.asset.verifiable)
    check("a draft release is ignored", upd._parse_release({**raw, "draft": True}) is None)
    check("a release with no assets still parses",
          upd._parse_release({**raw, "assets": []}).asset is None)
    no_digest = {**raw, "assets": [{**raw["assets"][0], "digest": ""}]}
    check("an asset with no digest is not verifiable",
          not upd._parse_release(no_digest).asset.verifiable)

    print("\n[update] a download is verified before anything is executed")
    import functools
    import hashlib
    import http.server
    import threading
    payload = b"PRETEND INSTALLER " * 4000
    good = hashlib.sha256(payload).hexdigest()
    srv_dir = Path(tmp) / "served"
    srv_dir.mkdir(exist_ok=True)
    (srv_dir / "setup.exe").write_bytes(payload)
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):      # keep the suite output readable
            pass

    handler = functools.partial(QuietHandler, directory=str(srv_dir))

    class Quiet(http.server.HTTPServer):
        def handle_error(self, *a):
            pass
    httpd = Quiet(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{httpd.server_address[1]}/setup.exe"
    saved_hosts = upd.ALLOWED_HOSTS

    def attempt(sha, size):
        a = upd.Asset(name="setup.exe", url=url, size=size, sha256=sha)
        d = Path(tmp) / f"dl{abs(hash((sha, size)))}"
        try:
            return upd.download(a, dest_dir=str(d)), d
        except upd.UpdateError as exc:
            return exc, d

    try:
        upd.ALLOWED_HOSTS = {"127.0.0.1"}
        ok, d = attempt(good, len(payload))
        check("a matching download succeeds", isinstance(ok, Path) and ok.is_file())
        bad, d = attempt("0" * 64, len(payload))
        check("a checksum mismatch is refused", isinstance(bad, upd.UpdateError))
        check("and the rejected file is deleted, never left runnable",
              not any(p.suffix in (".exe", ".part") for p in d.iterdir()))
        wrong, _ = attempt(good, len(payload) + 1)
        check("a size mismatch is refused", isinstance(wrong, upd.UpdateError))
        none, _ = attempt("", len(payload))
        check("an unverifiable asset is refused outright",
              isinstance(none, upd.UpdateError) and "SHA-256" in str(none))
        upd.ALLOWED_HOSTS = {"github.com"}
        off, _ = attempt(good, len(payload))
        check("a host off the allow-list is refused",
              isinstance(off, upd.UpdateError) and "Refusing" in str(off))
    finally:
        upd.ALLOWED_HOSTS = saved_hosts
        httpd.shutdown()

    check("applying is refused off Windows",
          _raises(lambda: upd.apply(Path(tmp) / "nope.exe")))

    print("\n[update] modes and endpoints")
    check("auto is the default mode", config.Settings().update_mode == "auto")
    check("all three modes are offered",
          set(config.UPDATE_MODES) == {"auto", "notify", "off"})
    check("an unknown mode is refused",
          server.ep_settings_save({"update_mode": "yolo"})["ok"] is False)
    check("a known mode saves",
          server.ep_settings_save({"update_mode": "notify"})["ok"] is True)
    config.update(update_mode="off")
    off_res = server.ep_update_check({})
    check("mode off short-circuits the check", off_res.get("disabled") is True)
    check("...and makes no network call", off_res.get("checked") is False)
    forced = server.ep_update_check({"force": ["1"]})
    check("but an explicit check still runs", "disabled" not in forced)
    config.update(update_mode="auto")

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

    print("\n[packaging] frozen vs source asset layout")
    # v0.1.0 shipped broken: the frozen branch of resource() dropped the
    # "argus" prefix, so VERSION fell back to 0.0.0-dev and ui.html raised
    # inside the request handler, which sent no response at all.
    import argus.config as cfg
    real_frozen, real_meipass = getattr(sys, "frozen", None), getattr(sys, "_MEIPASS", None)
    bundle = Path(tmp) / "bundle"
    (bundle / "argus" / "app").mkdir(parents=True, exist_ok=True)
    (bundle / "argus" / "VERSION").write_text("9.9.9", encoding="utf-8")
    (bundle / "argus" / "app" / "ui.html").write_text("<title>Argus</title>", encoding="utf-8")
    (bundle / "knowledge" / "packs").mkdir(parents=True, exist_ok=True)
    sys.frozen = True                       # type: ignore[attr-defined]
    sys._MEIPASS = str(bundle)              # type: ignore[attr-defined]
    try:
        check("frozen() detects the bundle", cfg.frozen() is True)
        check("frozen resource() keeps the argus/ package prefix",
              cfg.resource("app", "ui.html") == bundle / "argus" / "app" / "ui.html")
        check("frozen VERSION resolves inside the package",
              cfg.resource("VERSION").exists() and cfg.version() == "9.9.9")
        check("frozen version() is not the 0.0.0-dev fallback",
              cfg.version() != "0.0.0-dev")
        check("frozen bundled() stays at the bundle root, outside the package",
              cfg.bundled("knowledge", "packs") == bundle / "knowledge" / "packs")
        check("the packs directory resolves when frozen",
              cfg.bundled("knowledge", "packs").exists())
        from argus.app.server import _ui_path
        check("the server resolves the UI from the bundle", _ui_path().exists())
    finally:
        if real_frozen is None:
            del sys.frozen                  # type: ignore[attr-defined]
        else:
            sys.frozen = real_frozen        # type: ignore[attr-defined]
        if real_meipass is None:
            if hasattr(sys, "_MEIPASS"):
                del sys._MEIPASS            # type: ignore[attr-defined]
        else:
            sys._MEIPASS = real_meipass     # type: ignore[attr-defined]
    check("source layout still resolves after the frozen test",
          cfg.resource("app", "ui.html").exists() and cfg.version() != "0.0.0-dev")

    print("\n[packaging] a broken bundle answers, rather than dropping the connection")
    # ERR_EMPTY_RESPONSE gives the user nothing to report. A 500 with the
    # looked-in path is the difference between five minutes and an afternoon.
    err = server._startup_error(FileNotFoundError("no such file"))
    check("the failure page is real HTML", b"<!doctype html>" in err.lower())
    check("it names the exception", b"FileNotFoundError" in err)
    check("it says where it looked", b"Looked in" in err)

    print("\n[packaging] the self-check verifies serving, not just liveness")
    import run as launcher
    src = Path("run.py").read_text()
    check("self_check requests the page over loopback", "urlopen" in src)
    check("self_check asserts the interface actually rendered",
          "viewDesk" in src and "<title>Argus</title>" in src)
    check("self_check catches the 0.0.0-dev fallback", "0.0.0-dev" in src)
    check("self_check returns a non-zero exit code on failure",
          "return 0 if ok else 1" in src)
    check("the launcher exposes --check", "--check" in src)
    wf2 = Path(".github/workflows/build-windows.yml").read_text()
    check("CI runs the frozen app's self-check", "--check-out" in wf2)
    check("CI fails the build when the self-check fails", "self-check failed" in wf2)
    check("running the self-check from source passes", launcher.self_check() == 0)

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
