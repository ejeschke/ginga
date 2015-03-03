"""
Ginga is a toolkit designed for building viewers for scientific image
data in Python, visualizing 2D pixel data in numpy arrays.  
The Ginga toolkit centers around an image display class which supports 
zooming and panning, color and intensity mapping, a choice of several
automatic cut levels algorithms and canvases for plotting scalable
geometric forms.  In addition to this widget, a general purpose
'reference' FITS viewer is provided, based on a plugin framework.

Copyright (c) 2011-2015 Eric R. Jeschke. All rights reserved.

Ginga is distributed under an open-source BSD licence. Please see the
file LICENSE.txt in the top-level directory for details. 
"""

try:
    from .version import version as __version__
except ImportError:
    __version__ = ''

#END
