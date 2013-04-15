GINGA ABOUT
-----------
Ginga is a viewer for astronomical data FITS (Flexible Image Transport
System) files.

The Ginga viewer centers around a new FITS display widget which supports 
zooming and panning, color and intensity mapping, a choice of several
automatic cut levels algorithms and canvases for plotting scalable
geometric forms.  In addition to this widget, the fits viewer provides a
flexible plugin framework for extending the viewer with many different
features.  A fairly complete set of "standard" plugins are provided
for features that we expect from a modern viewer: panning and zooming
windows, star catalog access, cuts, star pick/fwhm, thumbnails, etc.

COPYRIGHT AND LICENSE
---------------------
Copyright (c) 2011-2013  Eric R. Jeschke.  All rights reserved.
Ginga is distributed under an open-source BSD licence.  Please see the
file LICENSE.txt in the top-level directory for details.

BUILDING AND INSTALLATION
-------------------------
Ginga uses a standard distutils based install, e.g.

    $ python setup.py build

or

    $ python setup.py install

The program can then be run using the command "ginga"

For further information please see the file ginga/doc/INSTALL.txt

MANUAL
------
You can find copies of a PDF manual online at
https://github.com/ejeschke/ginga/downloads

Also look in ginga/doc/manual

DEVELOPERS
----------
See scripts/example{1,2}_gtk.py and scripts/example{1,2}_qt.py .
There is more information for developers in the manual.

ON THE WEB
----------
http://ejeschke.github.com/ginga

ETYMOLOGY
---------
"Ginga" is the romanized spelling of the Japanese word "銀河"
(hiragana: ぎんが), meaning "galaxy" (in general) and, more familiarly,
the Milky Way.  This viewer was written by software engineers at Subaru
Telescope, National Astronomical Observatory of Japan--thus the
connection. 

Pronunciation
-------------
Ginga the viewer may be pronounced "ging-ga" (proper japanese) or
"jing-ga" (perhaps easier for western tongues).  The latter
pronunciation has meaning in the Brazilian dance/martial art capoeira:
a fundamental rocking or back and forth swinging motion.

