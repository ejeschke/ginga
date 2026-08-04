#!/usr/bin/env python
#
# Ginga_launch.py -- entry point for the frozen (PyInstaller) Ginga app.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""Launch the Ginga reference viewer from a frozen app bundle.

This is the script PyInstaller freezes into the macOS ``.app`` / Windows
``.exe`` (see ``ginga.spec``).  It defers to the very same entry point the
``ginga`` console command uses -- ``ginga.rv.main:_main`` -- which parses
``sys.argv`` and starts the reference viewer.
"""
import multiprocessing

from ginga.rv.main import _main

if __name__ == "__main__":
    # A frozen app may re-exec itself to spawn worker processes (the
    # Windows / macOS "spawn" start method).  freeze_support() makes those
    # children return here and run as workers instead of relaunching the
    # whole GUI; it is a harmless no-op in the parent process.
    multiprocessing.freeze_support()
    _main()

# END
