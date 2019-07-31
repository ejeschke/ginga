#
# Figure out which widget set we are using and import those wrappers

from ginga import toolkit
tkname = toolkit.get_family()

if tkname == 'qt':
    from ginga.qtw.QtHelp import *  # noqa

elif tkname == 'gtk3':
    from ginga.gtk3w.GtkHelp import *  # noqa

elif tkname == 'pg':
    from ginga.web.pgw.PgHelp import *  # noqa

# END
