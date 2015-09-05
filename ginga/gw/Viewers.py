# Figure out which widget set we are using and import those canvas types
from ginga import toolkit
tkname = toolkit.get_family()

if tkname == 'gtk':
    from ginga.gtkw.ImageViewGtk import *
    from ginga.gtkw.ImageViewCanvasGtk import *

elif tkname == 'qt':
    from ginga.qtw.ImageViewQt import *
    from ginga.qtw.ImageViewCanvasQt import *
