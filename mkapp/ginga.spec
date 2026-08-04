# -*- mode: python ; coding: utf-8 -*-
#
# ginga.spec -- PyInstaller build spec for a standalone Ginga application.
#
# Builds a macOS ``.app`` or a Windows ``.exe`` from the same spec; run it on
# the target OS:
#
#     pyinstaller ginga.spec
#         macOS   -> dist/Ginga.app
#         Windows -> dist/Ginga/Ginga.exe   (one-folder build)
#
# The build environment must have Ginga and its runtime dependencies
# installed, plus PyInstaller and *exactly one* Qt binding (PyQt5, PyQt6,
# PySide2, or PySide6) -- whichever is importable is the one bundled.  See
# README.rst for the full recipe.
#
# Targets PyInstaller >= 6 (the 5.x ``cipher=`` / ``block_cipher`` arguments
# were removed and are intentionally not used here).

import re
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules

# --- version -----------------------------------------------------------------
# CFBundleVersion (macOS) and the Windows product version want a clean numeric
# X.Y.Z; strip any PEP 440 dev/local suffix, e.g.
# '7.2.0.dev4+g8c332901d.d20260804' -> '7.2.0'.
from ginga import __version__ as _ginga_version   # noqa: E402
_m = re.match(r'\d+(?:\.\d+){0,2}', _ginga_version)
version = _m.group(0) if _m else '0.0.0'

# --- collect dependencies ----------------------------------------------------
datas, binaries, hiddenimports = [], [], []


def _collect(pkg, required=False):
    global datas, binaries, hiddenimports
    try:
        d, b, h = collect_all(pkg)
    except Exception as e:
        if required:
            raise
        print("ginga.spec: skipping optional package %r (%s)" % (pkg, e))
        return
    datas += d
    binaries += b
    hiddenimports += h


# Ginga itself: grab its data files (icons, fonts, cursors, help docs,
# examples, GLSL, locale) AND every submodule -- the GUI/renderer backends are
# imported dynamically via the toolkit selection, so PyInstaller's import
# follower cannot see them on its own.
_collect('ginga', required=True)
hiddenimports += collect_submodules('ginga')

# Scientific stack that ships data files / has dynamically loaded pieces.
for _pkg in ('astropy', 'matplotlib', 'scipy', 'PIL'):
    _collect(_pkg)

# Bundle whichever single Qt binding is installed in the build env; qtpy then
# selects it at runtime.
_qt_binding = None
for _binding in ('PyQt5', 'PyQt6', 'PySide2', 'PySide6'):
    try:
        __import__(_binding)
    except ImportError:
        continue
    _qt_binding = _binding
    _collect(_binding, required=True)
    hiddenimports += ['qtpy']
    break
if _qt_binding is None:
    raise SystemExit("ginga.spec: no Qt binding found in the build env; "
                     "install one of PyQt5/PyQt6/PySide2/PySide6")
print("ginga.spec: bundling Qt binding %r, version %s" % (_qt_binding, version))

# --- analysis / build --------------------------------------------------------
a = Analysis(
    ['Ginga_launch.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Keep the bundle lean and avoid Qt-binding clashes: drop the dead PyQt4,
    # the other GUI toolkits Ginga can use but we are not shipping here, and
    # OpenCV (large, optional accel only).
    excludes=['PyQt4', 'tkinter', 'gi', 'cv2'],
    noarchive=False,
)
pyz = PYZ(a.pure)

icon = 'Ginga.ico' if sys.platform == 'win32' else 'Ginga.icns'

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Ginga',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # windowed GUI app (no console window on Windows)
    disable_windowed_traceback=False,
    icon=icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Ginga',
)

if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='Ginga.app',
        icon='Ginga.icns',
        bundle_identifier='org.naoj.Ginga',
        version=version,
        info_plist={
            'CFBundleName': 'Ginga',
            'CFBundleDisplayName': 'Ginga',
            'CFBundleExecutable': 'Ginga',
            'CFBundleIdentifier': 'org.naoj.Ginga',
            'CFBundleShortVersionString': version,
            'CFBundleVersion': version,
            'CFBundleDevelopmentRegion': 'English',
            'NSHumanReadableCopyright':
                'Copyright © 2010-2026, Eric Jeschke (eric@naoj.org)',
            # Retina / HiDPI rendering
            'NSHighResolutionCapable': True,
        },
    )

# END
