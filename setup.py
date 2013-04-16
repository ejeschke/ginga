#! /usr/bin/env python
#
from distutils.core import setup
from ginga.version import version
import os

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

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
    data_files = [('', ['LICENSE.txt', 'README.txt'])],
    scripts = ['scripts/ginga'],
    classifiers = [
        "License :: OSI Approved :: BSD License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Topic :: Scientific/Engineering :: Astronomy",
    ],
)

