#! /usr/bin/env python
#
from distutils.core import setup
from ginga.version import version
import os

try:  # Python 3.x
    from distutils.command.build_py import build_py_2to3 as build_py
except ImportError:  # Python 2.x
    from distutils.command.build_py import build_py

def read(fname):
    buf = open(os.path.join(os.path.dirname(__file__), fname), 'r').read()
    return buf

setup(
    name = "ginga",
    version = version,
    author = "Eric Jeschke",
    author_email = "eric@naoj.org",
    description = ("An astronomical (FITS) image viewer and toolkit."),
    long_description = read('README.txt'),
    license = "BSD",
    keywords = "FITS image viewer astronomy",
    url = "http://ejeschke.github.com/ginga",
    packages = ['ginga', 'ginga.gtkw', 'ginga.gtkw.plugins', 'ginga.gtkw.tests',
                'ginga.qtw', 'ginga.qtw.plugins', 'ginga.qtw.tests',
                'ginga.misc', 'ginga.misc.plugins',
                'ginga.icons', 'ginga.util',
                'ginga.doc'],
    package_data = { 'ginga.icons': ['*.ppm', '*.png'],
                     'ginga.doc': ['manual/*.html'],
                     'ginga.gtkw': ['gtk_rc'],
                     },
    scripts = ['scripts/ginga', 'scripts/grc'],
    classifiers = [
        "License :: OSI Approved :: BSD License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Topic :: Scientific/Engineering :: Astronomy",
    ],
    cmdclass={'build_py': build_py}
)

