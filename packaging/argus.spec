# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for the Argus Windows build.

onedir rather than onefile, deliberately. onefile unpacks the whole bundle to a
temp directory on every launch, which costs seconds of startup and trips
aggressive antivirus heuristics; onedir starts fast and gives the installer a
normal directory to lay down and to patch on update.

Run from the repository root:
    pyinstaller packaging/argus.spec --noconfirm
"""
from pathlib import Path

ROOT = Path(SPECPATH).parent          # noqa: F821 - SPECPATH is injected
SRC = ROOT / "src"

datas = [
    (str(SRC / "argus" / "app" / "ui.html"), "argus/app"),
    (str(SRC / "argus" / "VERSION"), "argus"),
]
# Knowledge packs ship with the app so a fresh install has something to reason
# from before it has ever reached the network.
packs = ROOT / "knowledge" / "packs"
if packs.is_dir():
    datas.append((str(packs), "knowledge/packs"))

a = Analysis(                                     # noqa: F821
    [str(ROOT / "run.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=datas,
    # pywebview resolves its GUI backend at runtime, so PyInstaller's static
    # analysis cannot see these and the frozen app fails with "no GUI backend"
    # unless they are named explicitly.
    hiddenimports=[
        "webview", "webview.platforms.edgechromium", "webview.platforms.winforms",
        "clr_loader", "pythonnet",
        # Imported lazily at their call sites so the app still starts when they
        # are absent. That laziness also hides them from PyInstaller's static
        # analysis, so without these names the AI and broker features would be
        # permanently dead in the packaged build - settings for a feature that
        # cannot run.
        "anthropic", "MetaTrader5",
        # numpy is named explicitly, and the reason is subtle. MetaTrader5
        # declares numpy>=1.7 so pip installs it, and it is not in `excludes`.
        # But MetaTrader5 is a compiled .pyd: its `import numpy` happens inside
        # C code, where PyInstaller's static analysis cannot see it. Nothing in
        # the graph therefore asked for numpy and it was left out, producing a
        # bundle that carried MetaTrader5 and died on
        # "numpy._core.multiarray failed to import". Removing the exclude was
        # necessary but not sufficient - a binary extension's imports are
        # invisible and have to be declared by hand.
        "numpy",
        "argus.insider.pipeline", "argus.data.edgar", "argus.config",
        "argus.update", "argus.secrets", "argus.ai.analyst",
        "argus.bridge.mt5_bridge", "argus.analysis.bias",
        "argus.analysis.sessions", "argus.analysis.calendar",
    ],
    hookspath=[],
    runtime_hooks=[],
    # Trim what a research terminal has no use for. Each of these drags in tens
    # of megabytes.
    #
    # numpy is NOT excluded, and the reason is worth recording: it is not
    # imported by any first-party module here, but MetaTrader5 depends on it.
    # Excluding it produced a bundle that carried MetaTrader5 and failed to
    # import it at runtime with "numpy._core.multiarray failed to import" -
    # the broker bridge dead in a shipped build. An exclude list must be
    # reasoned about transitively, not from a grep of your own imports.
    excludes=["tkinter", "matplotlib", "pandas", "scipy", "PIL",
              "pytest", "setuptools", "pip", "test", "unittest"],
    noarchive=False,
)

pyz = PYZ(a.pure)                                 # noqa: F821

exe = EXE(                                        # noqa: F821
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="Argus",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                 # UPX-packed binaries are a reliable AV false positive
    console=False,             # no console window behind the app
    disable_windowed_traceback=False,
    icon=str(ROOT / "packaging" / "argus.ico"),
    version=str(ROOT / "packaging" / "version_info.txt"),
)

coll = COLLECT(                                   # noqa: F821
    exe, a.binaries, a.datas,
    strip=False, upx=False, name="Argus",
)
