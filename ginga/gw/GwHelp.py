#
# Figure out which widget set we are using and import those wrappers

from ginga import toolkit
tkname = toolkit.get_family()

if tkname == 'qt':
    from ginga.qtw.QtHelp import *

elif tkname == 'gtk':
    from ginga.gtkw.GtkHelp import *

elif tkname == 'gtk3':
    from ginga.gtk3w.GtkHelp import *

elif tkname == 'pg':
    from ginga.web.pgw.PgHelp import *

#END
