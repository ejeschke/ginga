from ginga import toolkit
tkname = toolkit.get_family()

if tkname == 'qt':
    from ginga.qtw.Viewers import *

elif tkname == 'gtk':
    from ginga.gtkw.Viewers import *

elif tkname == 'gtk3':
    from ginga.gtk3w.Viewers import *

elif tkname == 'pg':
    from ginga.web.pgw.Viewers import *

from ginga.table.TableView import TableViewGw
