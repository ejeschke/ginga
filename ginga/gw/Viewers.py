from ginga import toolkit
tkname = toolkit.get_family()

if tkname == 'gtk':
    from ginga.gtkw.Viewers import *

elif tkname == 'qt':
    from ginga.qtw.Viewers import *

elif tkname == 'pg':
    from ginga.web.pgw.Viewers import *
