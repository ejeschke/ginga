========================================
Building a standalone Ginga application
========================================

This folder builds a self-contained Ginga desktop application -- a macOS
``.app`` bundle or a Windows ``.exe`` -- with `PyInstaller
<https://pyinstaller.org/>`_, so end users can run Ginga without installing
Python or any packages.

A single spec (``ginga.spec``) drives both platforms.  **Build on the OS you
are targeting** -- PyInstaller does not cross-compile, so a macOS ``.app`` must
be built on macOS and a Windows ``.exe`` on Windows.

Files
=====

``Ginga_launch.py``
    The entry script that is frozen into the app.  It simply calls Ginga's
    normal command-line entry point (``ginga.rv.main:_main``).

``ginga.spec``
    The PyInstaller build recipe (collects Ginga's data files and backends,
    the scientific stack, and one Qt binding; sets the app icon, version, and
    -- on macOS -- the ``Info.plist``).

``Ginga.icns`` / ``Ginga.ico``
    Application icons for macOS and Windows.  ``Ginga.ico`` is generated from
    ``ginga/icons/ginga-512x512.png`` (see "Regenerating the Windows icon").

``build.py``
    Cross-platform build driver (``python build.py``).  No ``make`` required,
    so it works the same on macOS and Windows.

Prerequisites
=============

In the build environment (a virtualenv or conda env is recommended):

1. Install Ginga plus the PyInstaller tooling::

       pip install -e ..[pyinstaller]      # or: pip install ginga[pyinstaller]

2. Install **exactly one** Qt binding -- whichever is importable is the one
   bundled into the app::

       pip install ginga[qt5]      # or ginga[qt6] / ginga[pyside2] / ginga[pyside6]

   Having more than one installed can bundle conflicting Qt libraries; keep a
   single binding in the build env.

Building
========

From this directory::

    python build.py

(equivalently ``pyinstaller --noconfirm ginga.spec``).  Useful options::

    python build.py --clean     # remove build/ and dist/, then exit
    python build.py --icon      # regenerate Ginga.ico from the source PNG
    python build.py --no-clean  # build without cleaning first

Output:

- **macOS:** ``dist/Ginga.app`` -- double-click to run, or drag into
  ``/Applications``.
- **Windows:** ``dist/Ginga/`` -- a one-folder build; run ``dist/Ginga/Ginga.exe``.
  Zip the ``dist/Ginga`` folder to distribute.

``python build.py --clean`` removes the ``build/`` and ``dist/`` directories.

Notes and caveats
=================

- **Qt binding:** the app uses whatever binding was bundled.  You can override
  Ginga's toolkit at runtime as usual (e.g. ``Ginga.app/Contents/MacOS/Ginga
  -t qt6``) as long as that binding was the one built in.

- **Size:** the scientific stack (numpy/scipy/astropy/matplotlib) makes the
  bundle large (hundreds of MB).  To slim it, drop unused packages from the
  ``_collect(...)`` calls in ``ginga.spec`` and add them to ``excludes``.

- **First launch on macOS:** an unsigned/unnotarized ``.app`` triggers
  Gatekeeper.  For personal use, right-click -> Open once; for distribution,
  code-sign and notarize the bundle (outside the scope of this spec).

- **Missing modules at runtime:** because Ginga loads GUI/renderer backends
  dynamically, the spec bundles *all* ``ginga`` submodules.  If you add a new
  optional dependency that is imported dynamically and it is missing from the
  frozen app, add it to ``hiddenimports`` in ``ginga.spec``.

Building in a conda environment
===============================

``build.py`` works fine from an activated conda environment -- it drives
PyInstaller in-process, so it uses the interpreter and libraries of whatever
env you run ``python build.py`` in.  However, conda's scientific stack causes
two well-known PyInstaller issues, so a **clean pip virtualenv is the more
reliable choice** (pip's numpy/scipy wheels use a statically-linked OpenBLAS
that freezes cleanly):

- **MKL bloat.** Conda's numpy/scipy are typically linked against Intel MKL,
  which pulls dozens of large shared libraries (hundreds of MB) into the
  bundle.

- **Missing MKL/OpenMP libraries at runtime.** PyInstaller can miss MKL
  libraries that numpy/scipy load lazily, so the *build* succeeds but the
  frozen app fails on launch with a ``cannot load mkl_...`` error.  This only
  shows up when the app is actually run, so always test the frozen app, not
  just the build.

If you must build in conda, drop MKL first::

    conda install nomkl        # switches numpy/scipy to OpenBLAS

or install numpy/scipy from pip into the env.  Also keep a single Qt binding
in the env: mixing a conda-forge Qt with a pip Qt binding can bundle
conflicting Qt libraries.

Regenerating the Windows icon
=============================

``Ginga.ico`` is a multi-resolution icon generated from
``ginga/icons/ginga-512x512.png`` in the source tree.  Regenerate it with::

    python build.py --icon
