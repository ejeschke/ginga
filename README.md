# GINGA

[![Powered by Astropy Badge](http://img.shields.io/badge/powered%20by-AstroPy-orange.svg?style=flat)](http://www.astropy.org)
[![Documentation Status](https://readthedocs.org/projects/ginga/badge/?version=latest)](https://ginga.readthedocs.io/en/latest/)
[![Github Actions CI Status](https://github.com/ejeschke/ginga/workflows/CI/badge.svg)](https://github.com/ejeschke/ginga/actions/)

Ginga is a toolkit designed for building viewers for scientific image
data in Python, visualizing 2D pixel data in numpy arrays.
It can view astronomical data such as contained in files based on the
FITS (Flexible Image Transport System) file format.
It is written and is maintained by software engineers at
the National Astronomical Observatory of Japan (NAOJ),
the Space Telescope Science Institute (STScI),
and other contributing entities.

The Ginga toolkit centers around an image display object which supports
zooming and panning, color and intensity mapping, a choice of several
automatic cut levels algorithms and canvases for plotting scalable
geometric forms.  In addition to this widget, a general purpose
"reference" FITS viewer is provided, based on a plugin framework.
A fairly complete set of standard plugins are provided for features
that we expect from a modern FITS viewer: panning and zooming windows,
star catalog access, cuts, star pick/FWHM, thumbnails, etc.

## COPYRIGHT AND LICENSE

Copyright (c) 2011-2024  Ginga Maintainers.  All rights reserved.
Ginga is distributed under an open-source BSD licence.  Please see the
file `LICENSE.txt` in the top-level directory for details.

## BUILDING AND INSTALLATION

The current release of Ginga can be downloaded and installed from `pip` using:

    $ pip install ginga

From source code, you should also use `pip`, e.g.:

    $ cd ginga
    $ pip install -e .

The program can then be run using the command "ginga".

For further information, please see the detailed installation
instructions in the documentation.

## DOCUMENTATION

It is online at
http://ginga.readthedocs.io/en/latest/ (dev) and
http://ginga.readthedocs.io/en/stable/ (latest release).

## CODE OF CONDUCT

See `CODE_OF_CONDUCT.md`.

## FOR DEVELOPERS

See `examples/*/example{1,2}_*.py` .
There is more information for developers in the manual.

## ON THE WEB

http://ejeschke.github.com/ginga

## ETYMOLOGY

"Ginga" is the romanized spelling of the Japanese word "銀河"
(hiragana: ぎんが), meaning "galaxy" (in general) and, more familiarly,
the Milky Way.  This viewer was originally written by software engineers at
Subaru Telescope, National Astronomical Observatory of Japan; thus the
connection.

### Pronunciation

Ginga the viewer may be pronounced "ging-ga" (proper japanese) or
"jing-ga" (perhaps easier for Western tongues). The latter pronunciation
has meaning in the Brazilian dance/martial art capoeira: a fundamental
rocking or back and forth swinging motion. Pronunciation as "jin-ja"
is considered poor form.
