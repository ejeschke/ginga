from ginga import toolkit
tkname = toolkit.get_family()

if tkname == 'qt':
    from ginga.qtw.Viewers import *  # noqa

elif tkname == 'gtk3':
    from ginga.gtk3w.Viewers import *  # noqa

elif tkname == 'pg':
    from ginga.web.pgw.Viewers import *  # noqa

from ginga.table.TableView import TableViewGw  # noqa

from .PlotView import PlotViewGw  # noqa
