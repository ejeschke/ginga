#! /usr/bin/env python
#
from distutils.core import setup
import version

setup(
    name = "Ginga",
    version = version.version,
    author = "Eric Jeschke",
    author_email = "eric@naoj.org",
    description = ("An astronomical (FITS) image viewer."),
    license = "BSD",
    keywords = "FITS image viewer astronomy",
    url = "http://ejeschke.github.com/ginga",
    package_dir = { '': 'Ginga' },
    packages = ['ginga', 'ginga.gtkw', 'ginga.gtkw.plugins', 'ginga.gtkw.tests',
                'ginga.qtw', 'ginga.qtw.plugins', 'ginga.qtw.tests',
                'ginga.misc', 'ginga.misc.plugins',
                'ginga.icons', 'ginga.tests', 'ginga.util',
                'ginga.doc'],
    package_data = { 'icons': ['*.ppm', '*.png'], 'doc': ['manual/*.html'], },
    scripts = ['ginga.py'],
    classifiers = [
        "Development Status :: 5 - Stable",
        "Topic :: Utilities",
        "License :: OSI Approved :: BSD License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
    ],
)

