#!/usr/bin/env python3
"""
Argus - launcher.

Named run.py, not argus.py, deliberately: a module named argus.py in the repo
root shadows the argus package under src/ for anything that imports it.

Starts the local backend and opens it in a native window. Falls back to the
default browser if pywebview is not installed, so it always runs.

    python run.py
"""
from __future__ import annotations

import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from argus.app.server import serve  # noqa: E402


def main() -> int:
    httpd, url = serve()
    print(f"Argus backend on {url}")
    try:
        import webview  # type: ignore
        webview.create_window("Argus", url, width=1500, height=920,
                              background_color="#0C1013")
        webview.start()
    except ImportError:
        print("pywebview not installed - opening in your browser instead.")
        print("For a proper window:  pip install pywebview")
        webbrowser.open(url)
        print("Ctrl+C to stop.")
        try:
            import threading
            threading.Event().wait()
        except KeyboardInterrupt:
            pass
    finally:
        httpd.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
