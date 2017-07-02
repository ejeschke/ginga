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

# MODULE FUNCTIONS

def get_orientation(container):
    if not hasattr(container, 'size'):
        return 'vertical'
    (wd, ht) = container.size
    # wd, ht = container.get_size()
    # print('container size is %dx%d' % (wd, ht))
    if wd < ht:
        return 'vertical'
    else:
        return 'horizontal'


def get_oriented_box(container, scrolled=True, fill=False):
    orientation = get_orientation(container)

    if orientation == 'vertical':
        box1 = VBox()
        box2 = VBox()
    else:
        box1 = HBox()
        box2 = VBox()

    box2.add_widget(box1, stretch=0)
    if not fill:
        box2.add_widget(Label(''), stretch=1)
    if scrolled:
        sw = ScrollArea()
        sw.set_widget(box2)
    else:
        sw = box2

    return box1, sw, orientation


def get_opposed_box(orientation):
    if orientation == 'vertical':
        box = HBox()
    else:
        box = VBox()
    return box

# END
