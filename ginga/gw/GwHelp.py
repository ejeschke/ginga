#
# Figure out which widget set we are using and import those wrappers

from ginga import toolkit
tkname = toolkit.get_family()

if tkname == 'gtk':
    from ginga.gtkw.GtkHelp import *

elif tkname == 'qt':
    from ginga.qtw.QtHelp import *

elif tkname == 'pg':
    from ginga.web.pgw.PgHelp import *

#END
