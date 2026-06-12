#
# Figure out which widget set we are using and import those widget wrappers

from ginga import toolkit
tkname = toolkit.get_family()

if tkname == 'qt':
    from ginga.qtw.Widgets import *  # noqa

elif tkname == 'gtk3':
    from ginga.gtk3w.Widgets import *  # noqa

elif tkname == 'gtk4':
    from ginga.gtk4w.Widgets import *  # noqa

elif tkname == 'pg':
    from ginga.web.pgw.Widgets import *  # noqa


# MODULE FUNCTIONS

def get_orientation(container, aspect=1.0):
    if hasattr(container, 'extdata') and hasattr(container.extdata, 'size'):
        wd, ht = container.extdata.size
    else:
        wd, ht = container.get_size()
    if ht == 0:
        return 'horizontal' if wd > 0 else 'vertical'
    calc_aspect = wd / ht
    if calc_aspect <= aspect:
        return 'vertical'
    else:
        return 'horizontal'


def get_oriented_box(container, scrolled=True, fill=False,
                     aspect=2.0, orientation=None):
    """Create a box laid out according to the orientation of *container*.

    The orientation is determined from the container's width/height aspect
    ratio (see get_orientation) -- 'vertical' yields a VBox, 'horizontal'
    an HBox -- unless overridden via the *orientation* keyword.

    The box is set to expand along its main axis (the orientation
    direction) so it fills the area it is given; when *fill* is True it
    also expands on the cross axis.  When *scrolled* is True (the default)
    the box is made the child of a ScrollArea, so its content scrolls when
    it exceeds the available area (while still filling that area when it is
    smaller).

    Returns ``(box, scroll_area, orientation)``.  ``scroll_area`` is None
    when *scrolled* is False.
    """
    if orientation is None:
        orientation = get_orientation(container, aspect=aspect)

    if orientation == 'vertical':
        box = VBox()  # noqa
        # main axis is vertical: always expand vertically; expand
        # horizontally (cross axis) only when fill is requested
        box.set_expanding(fill, True)
    else:
        box = HBox()  # noqa
        # main axis is horizontal: always expand horizontally; expand
        # vertically (cross axis) only when fill is requested
        box.set_expanding(True, fill)

    if scrolled:
        sw = ScrollArea()  # noqa
        sw.set_widget(box)
    else:
        sw = None

    return box, sw, orientation


def get_opposed_box(orientation):
    if orientation == 'vertical':
        box = HBox()  # noqa
    else:
        box = VBox()  # noqa
    return box

# END
