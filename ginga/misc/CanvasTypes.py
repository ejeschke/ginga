#
# CanvasTypes.py -- Canvas drawing types
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#

# Figure out which widget set we are using and import those canvas types
from ginga import toolkit
tkname = toolkit.get_family()
    
if tkname == 'gtk':
    from ginga.gtkw.ImageViewCanvasGtk import *
    from ginga.gtkw.ImageViewCanvasTypesGtk import *
    
elif tkname == 'qt':
    from ginga.qtw.ImageViewCanvasQt import *
    from ginga.qtw.ImageViewCanvasTypesQt import *

# END
