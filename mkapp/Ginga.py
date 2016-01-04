#!/usr/bin/env python
#
# ginga -- astronomical image viewer and toolkit
#
"""
Usage:
    ginga --help
    ginga [options] [fitsfile] ...
"""
import sys
from ginga import main, trcalc
try:
    trcalc.use('opencv')
except ImportError:
    pass

if __name__ == "__main__":
    main.reference_viewer(sys.argv)
