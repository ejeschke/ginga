#
# Figure out which widget set we are using and import those widget wrappers

from ginga import toolkit
tkname = toolkit.get_family()

if tkname == 'gtk':
    from ginga.gtkw.Widgets import *

elif tkname == 'qt':
    from ginga.qtw.Widgets import *

#END
