#
# Widgets.py -- Widget set wrappers
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#

# Figure out which widget set we are using and import those wrappers
from ginga import toolkit
tkname = toolkit.get_family()
    
if tkname == 'gtk':
    from ginga.gtkw.Widgets import *
elif tkname == 'qt':
    from ginga.qtw.Widgets import *

# END
