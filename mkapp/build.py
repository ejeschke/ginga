#!/usr/bin/env python
#
# build.py -- freeze a standalone Ginga app with PyInstaller.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""Build a standalone Ginga application (macOS ``.app`` / Windows ``.exe``).

    python build.py            # clean previous output, then freeze the app
    python build.py --no-clean # freeze without cleaning first
    python build.py --clean    # only remove build/ and dist/, then exit
    python build.py --icon     # (re)generate Ginga.ico from the source PNG

Runs the same on macOS and Windows (and Linux, for a smoke build).  Unlike a
Makefile it needs no ``make`` -- only the Python already required to build --
and it drives PyInstaller through its Python API, so the ``pyinstaller``
console script does not need to be on PATH.

Prerequisites (in the build env): ``pip install ginga[pyinstaller]`` plus one
Qt binding (e.g. ``pip install ginga[qt5]``).  See README.rst.
"""
import argparse
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = HERE / "ginga.spec"
ICON_SRC = HERE.parent / "ginga" / "icons" / "ginga-512x512.png"
ICON_OUT = HERE / "Ginga.ico"
ICO_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48),
             (64, 64), (128, 128), (256, 256)]


def clean():
    for name in ("build", "dist", "__pycache__"):
        path = HERE / name
        if path.exists():
            print("removing", path)
            shutil.rmtree(path)


def make_icon():
    from PIL import Image
    print("generating %s from %s" % (ICON_OUT.name, ICON_SRC))
    Image.open(ICON_SRC).convert("RGBA").save(ICON_OUT, sizes=ICO_SIZES)


def build():
    import PyInstaller.__main__
    print("freezing app from", SPEC.name)
    PyInstaller.__main__.run(["--noconfirm", str(SPEC)])
    result = "dist/Ginga.app" if sys.platform == "darwin" else "dist/Ginga/"
    print("\nDone.  Result: %s" % result)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Build a standalone Ginga app with PyInstaller.")
    ap.add_argument("--clean", action="store_true",
                    help="remove build/ and dist/, then exit")
    ap.add_argument("--icon", action="store_true",
                    help="regenerate Ginga.ico from the source PNG, then exit")
    ap.add_argument("--no-clean", action="store_true",
                    help="do not clean before building")
    args = ap.parse_args(argv)

    if args.clean:
        clean()
        return
    if args.icon:
        make_icon()
        return
    if not args.no_clean:
        clean()
    build()


if __name__ == "__main__":
    main()

# END
