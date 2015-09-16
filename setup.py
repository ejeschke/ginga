#! /usr/bin/env python
#
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
from ginga.version import version
import os

srcdir = os.path.dirname(__file__)

from distutils.command.build_py import build_py

def read(fname):
    buf = open(os.path.join(srcdir, fname), 'r').read()
    return buf

# not yet working...
def get_docs():
    docdir = os.path.join(srcdir, 'doc')
    res = []
    # ['../../doc/Makefile', 'doc/conf.py', 'doc/*.rst',
    #                              'doc/manual/*.rst', 'doc/figures/*.png']
    return res

setup(
    name = "ginga",
    version = version,
    author = "Eric Jeschke",
    author_email = "eric@naoj.org",
    description = ("An astronomical image viewer and toolkit."),
    long_description = read('README.txt'),
    license = "BSD",
    keywords = "scientific image viewer numpy toolkit astronomy FITS",
    url = "http://ejeschke.github.com/ginga",
    packages = ['ginga',
                # Gtk version
                'ginga.cairow', 'ginga.gtkw', 'ginga.gtkw.plugins',
                'ginga.gtkw.tests',
                # Qt version
                'ginga.qtw', 'ginga.qtw.plugins', 'ginga.qtw.tests',
                # Tk version
                'ginga.tkw',
                # Matplotlib version
                'ginga.mplw',
                # aggdraw backend
                'ginga.aggw',
                # OpenCv backend
                'ginga.cvw',
                # PIL backend
                'ginga.pilw',
                # Mock version
                'ginga.mockw',
                # Ginga (wrapped) widgets
                'ginga.gw',
                # Web backends
                'ginga.web', 'ginga.web.pgw',
                'ginga.web.pgw.js', 'ginga.web.pgw.templates',
                # Common stuff
                'ginga.misc', 'ginga.misc.plugins', 'ginga.base',
                'ginga.canvas', 'ginga.canvas.types', 'ginga.util',
                # Misc
                'ginga.icons', 'ginga.doc', 'ginga.tests',
                'ginga.fonts',
                ],
    package_data = { 'ginga.icons': ['*.ppm', '*.png'],
                     'ginga.gtkw': ['gtk_rc'],
                     #'ginga.doc': get_docs(),
                     'ginga.doc': ['manual/*.html'],
                     'ginga.web.pgw': ['templates/*.html', 'js/*.js'],
                     'ginga.fonts': ['*/*.ttf', '*/*.txt'],
                     },
    scripts = ['scripts/ginga', 'scripts/grc', 'scripts/gris'],
    install_requires = ['numpy>=1.7'],
    test_suite = "ginga.tests",
    classifiers=[
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: BSD License',
          'Operating System :: MacOS :: MacOS X',
          'Operating System :: Microsoft :: Windows',
          'Operating System :: POSIX',
          'Programming Language :: C',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3.3',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3',
          'Topic :: Scientific/Engineering :: Astronomy',
          'Topic :: Scientific/Engineering :: Physics',
          ],
    cmdclass={'build_py': build_py}
)
