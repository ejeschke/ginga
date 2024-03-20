# Figure out which widget set we are using and import those wrappers
from ginga import toolkit
tkname = toolkit.get_family()

if tkname == 'qt':
    from ginga.qtw.Plot import *  # noqa

elif tkname == 'gtk3':
    from ginga.gtk3w.Plot import *  # noqa

elif tkname == 'gtk4':
    from ginga.gtk4w.Plot import *  # noqa

elif tkname == 'pg':
    from ginga.web.pgw.Plot import *  # noqa

# END
