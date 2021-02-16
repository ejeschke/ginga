#
# Figure out which widget set we are using and import those widget wrappers

from ginga import toolkit
tkname = toolkit.get_family()

if tkname == 'qt':
    from ginga.qtw.Widgets import *  # noqa

elif tkname == 'gtk3':
    from ginga.gtk3w.Widgets import *  # noqa

elif tkname == 'pg':
    from ginga.web.pgw.Widgets import *  # noqa


# MODULE FUNCTIONS

def get_orientation(container, aspect=1.0):
    if not hasattr(container, 'size'):
        return 'vertical'
    (wd, ht) = container.size
    # wd, ht = container.get_size()
    # print('container size is %dx%d' % (wd, ht))
    if ht == 0:
        return 'horizontal' if wd > 0 else 'vertical'
    calc_aspect = wd / ht
    if calc_aspect <= aspect:
        return 'vertical'
    else:
        return 'horizontal'


def get_oriented_box(container, scrolled=True, fill=False,
                     aspect=2.0, orientation=None):
    if orientation is None:
        orientation = get_orientation(container, aspect=aspect)

    if orientation == 'vertical':
        box1 = VBox()  # noqa
        box2 = VBox()  # noqa
    else:
        box1 = HBox()  # noqa
        box2 = VBox()  # noqa

    box2.add_widget(box1, stretch=0)
    if not fill:
        box2.add_widget(Label(''), stretch=1)  # noqa
    if scrolled:
        sw = ScrollArea()  # noqa
        sw.set_widget(box2)
    else:
        sw = box2

    return box1, sw, orientation


def get_opposed_box(orientation):
    if orientation == 'vertical':
        box = HBox()  # noqa
    else:
        box = VBox()  # noqa
    return box

# END
