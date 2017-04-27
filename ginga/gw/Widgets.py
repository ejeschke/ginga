#
# Figure out which widget set we are using and import those widget wrappers

from ginga import toolkit
tkname = toolkit.get_family()

if tkname == 'qt':
    from ginga.qtw.Widgets import *  # noqa

elif tkname == 'gtk':
    from ginga.gtkw.Widgets import *  # noqa

elif tkname == 'gtk3':
    from ginga.gtk3w.Widgets import *  # noqa

elif tkname == 'pg':
    from ginga.web.pgw.Widgets import *  # noqa

# END
