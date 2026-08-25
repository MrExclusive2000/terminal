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

import os
import socket
import sys
import threading
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


def _geometry() -> tuple[int, int]:
    w = config.load().window
    return (max(900, int(w.get("width", 1500))),
            max(600, int(w.get("height", 920))))


def main() -> int:
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
