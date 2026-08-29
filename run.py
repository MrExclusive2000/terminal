#!/usr/bin/env python3
"""
Argus - desktop launcher.

Named run.py, not argus.py, deliberately: a module named argus.py in the repo
root shadows the argus package under src/ for anything that imports it.

Starts the local backend and opens it in a native window. The server binds to
127.0.0.1 on an ephemeral port, so there is no listener reachable from outside
this machine - the no-distribution invariant is structural rather than a
promise.

    python run.py
"""
from __future__ import annotations

import json
import os
import socket
import sys
import threading
import urllib.request
import webbrowser
from pathlib import Path

if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).parent / "src"))

from argus import config                      # noqa: E402
from argus.app.server import serve            # noqa: E402

#: Fixed port used only as a single-instance lock, never bound for traffic.
_LOCK_PORT = 49411


def _acquire_single_instance() -> socket.socket | None:
    """Hold a loopback port for the lifetime of the process.

    A lock *file* is the usual approach and it is wrong for a desktop app: a
    hard shutdown leaves the file behind and the next launch refuses to start.
    A held socket is released by the kernel when the process dies, however it
    dies, so it cannot go stale.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", _LOCK_PORT))
        s.listen(1)
        return s
    except OSError:
        s.close()
        return None


def self_check(report_path: str | None = None) -> int:
    """Boot the app and prove it actually serves. Exit 0 only if it does.

    This exists because the first shipped build passed CI and was broken on
    arrival. The smoke test checked that the bundled files existed and that the
    process was still alive after launch - both true - but never asked the
    running app for a page. A mislocated asset therefore sailed through: the
    process stayed up while every request died in the handler, and the user got
    ERR_EMPTY_RESPONSE.

    "Still running" is not "working". This makes the request.
    """
    checks: list[tuple[str, bool, str]] = []

    def note(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, ok, detail))

    note("version resolves", config.version() != "0.0.0-dev",
         f"version()={config.version()!r}"
         + (" - VERSION was not found in the bundle" if config.version() == "0.0.0-dev" else ""))

    ui = config.resource("app", "ui.html")
    note("ui.html is present", ui.exists(), str(ui))

    httpd = None
    try:
        httpd, url = serve()

        with urllib.request.urlopen(url, timeout=15) as r:
            body = r.read().decode("utf-8", "replace")
            note("GET / returns 200", r.status == 200, f"status={r.status}")
            note("GET / returns the interface",
                 "<title>Argus</title>" in body and "viewDesk" in body,
                 f"{len(body)} bytes")

        with urllib.request.urlopen(url + "api/settings", timeout=15) as r:
            data = json.loads(r.read())
            note("settings API responds", isinstance(data, dict), "")
            note("secrets are not exposed by the API", "api_key" not in data, "")
    except Exception as exc:  # noqa: BLE001 - any failure here is a failure
        note("app serves over loopback", False, f"{type(exc).__name__}: {exc}")
    finally:
        if httpd is not None:
            httpd.shutdown()

    ok = all(c[1] for c in checks)
    lines = [f"Argus self-check - {'PASS' if ok else 'FAIL'}",
             f"  version : {config.version()}",
             f"  frozen  : {config.frozen()}", ""]
    lines += [f"  {'ok  ' if c[1] else 'FAIL'} {c[0]}" + (f"  ({c[2]})" if c[2] else "")
              for c in checks]
    report = "\n".join(lines)

    # A windowed build has no console, so the report goes to a file and the
    # verdict travels in the exit code.
    if report_path:
        Path(report_path).write_text(report, encoding="utf-8")
    else:
        print(report)
    return 0 if ok else 1


def _geometry() -> tuple[int, int]:
    w = config.load().window
    return (max(900, int(w.get("width", 1500))),
            max(600, int(w.get("height", 920))))


def main() -> int:
    if "--check" in sys.argv:
        out = None
        if "--check-out" in sys.argv:
            out = sys.argv[sys.argv.index("--check-out") + 1]
        return self_check(out)

    lock = _acquire_single_instance()
    if lock is None:
        print("Argus is already running.", file=sys.stderr)
        return 3

    httpd, url = serve()
    version = config.version()
    if not config.frozen():
        print(f"Argus {version} - backend on {url}")

    width, height = _geometry()
    try:
        import webview  # type: ignore

        window = webview.create_window(f"Argus {version}", url,
                                       width=width, height=height,
                                       background_color="#0C1013")

        def remember() -> None:
            """Persist size on close so the window reopens where you left it."""
            try:
                config.update(window={"width": int(window.width),
                                      "height": int(window.height)})
            except Exception:  # noqa: BLE001 - never block shutdown on settings
                pass

        window.events.closed += remember
        webview.start()
    except ImportError:
        # Still runs without pywebview, because an app that refuses to start
        # over a missing optional dependency is not shipping.
        if not config.frozen():
            print("pywebview not installed - opening in your browser instead.\n"
                  "For a native window:  pip install pywebview")
        webbrowser.open(url)
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass
    finally:
        httpd.shutdown()
        lock.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
