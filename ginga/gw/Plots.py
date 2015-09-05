# Figure out which widget set we are using and import those wrappers
from ginga import toolkit
tkname = toolkit.get_family()

if tkname == 'gtk':
    from ginga.gtkw.Plot import *

elif tkname == 'qt':
    from ginga.qtw.Plot import *

#END
