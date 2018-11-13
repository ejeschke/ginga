# -*- coding: iso-8859-1 -*-
"""
Build a standalone application for Mac OS X and MS Windows platforms

 Usage (Mac OS X):
     python setup.py py2app

 Usage (Windows):
     python setup.py py2exe
"""
import sys
from setuptools import setup

info_plist_template = u"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleName</key>
	<string>Ginga</string>
	<key>CFBundlePackageType</key>
	<string>APPL</string>
	<key>CFBundleGetInfoString</key>
	<string>Copyright © 2010-2016, Eric Jeschke (eric@naoj.org)</string>
	<key>CFBundleIconFile</key>
	<string>Ginga.icns</string>
	<!-- Version number - appears in About box -->
	<key>CFBundleShortVersionString</key>
	<string>%(version)s</string>
	<!-- Build number - appears in About box -->
	<key>CFBundleVersion</key>
	<string>%(build)s</string>
	<!-- Copyright notice - apears in About box -->
	<key>NSHumanReadableCopyright</key>
	<string>Copyright © 2010-2016, Eric Jeschke (eric@naoj.org)</string>
	<!-- Globally unique identifier -->
	<key>CFBundleIdentifier</key>
	<string>org.naoj.Ginga</string>
	<key>CFBundleDevelopmentRegion</key>
	<string>English</string>
	<key>CFBundleExecutable</key>
	<string>Ginga</string>
	<key>CFBundleDisplayName</key>
	<string>Ginga</string>
</dict>
</plist>
"""

from ginga import __version__

d = dict(version=__version__, build=__version__.replace('.', ''))
plist = info_plist_template % d

with open('Info.plist', 'w') as out_f:
    out_f.write(plist)


APP = ['Ginga.py']
DATA_FILES = []

OPTIONS = {'argv_emulation': True,
           'compressed': True,
           #'packages': 'ginga,scipy,numpy,kapteyn,astropy,PIL,matplotlib',
           'packages': 'ginga,scipy,numpy,astropy,PIL,matplotlib',
           'includes': ['sip', 'PyQt4._qt',],
           # currently creating some problems with the app build on mac os x
           # so exclude
           'excludes': ['cv2',],
           'matplotlib_backends': 'Qt4Agg',
           }

if sys.platform == 'darwin':
    # mac-specific options
    OPTIONS['plist'] = 'Info.plist'
    OPTIONS['iconfile'] = 'Ginga.icns'
    extra_options = dict(
        setup_requires=['py2app'],
        options={'py2app': OPTIONS},
    )

elif sys.platform == 'win32':
    extra_options = dict(
        setup_requires=['py2exe'],
        options={'py2exe': OPTIONS},
    )
else:
    extra_options = dict(
        # Normally unix-like platforms will use "setup.py install"
        # and install the main script as such
        scripts=["ginga"],
    )

    setup_requires=['py2app'],

setup(
    name="Ginga",
    app=APP,
    data_files=DATA_FILES,
    **extra_options
)
