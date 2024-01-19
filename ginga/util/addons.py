#
# addons.py -- Goodies for enhancing a Ginga viewer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#


def show_pan_mark(viewer, tf, color='red'):
    """Show a mark in the pan position (center of window).

    Parameters
    ----------
    viewer : an ImageView subclass instance
        If True, show the color bar; else remove it if present.

    tf : bool
        If True, show the mark; else remove it if present.

    color : str
        Color of the mark; default is 'red'.
    """
    tag = '_$pan_mark'
    radius = 10

    canvas = viewer.get_private_canvas()
    try:
        mark = canvas.get_object_by_tag(tag)
        if not tf:
            canvas.delete_object_by_tag(tag)
        else:
            mark.color = color

    except KeyError:
        if tf:
            Point = canvas.get_draw_class('point')
            canvas.add(Point(0, 0, radius, style='plus', color=color,
                             coord='cartesian'),
                       tag=tag, redraw=False)

    canvas.update_canvas(whence=3)


def show_mode_indicator(viewer, tf, corner='ur'):
    """Show a keyboard mode indicator in one of the corners.

    Parameters
    ----------
    viewer : an ImageView subclass instance
        If True, show the color bar; else remove it if present.

    tf : bool
        If True, show the mark; else remove it if present.

    corner : str
        One of 'll', 'lr', 'ul' or 'ur' selecting a corner.
        The default is 'ur'.

    """
    tag = '_$mode_indicator'

    canvas = viewer.get_private_canvas()
    try:
        indic = canvas.get_object_by_tag(tag)
        if not tf:
            canvas.delete_object_by_tag(tag)
        else:
            indic.corner = corner

    except KeyError:
        if tf:
            # force a redraw if the mode changes
            bm = viewer.get_bindmap()
            bm.add_callback('mode-set',
                            lambda *args: viewer.redraw(whence=3))

            Indicator = canvas.get_draw_class('modeindicator')
            canvas.add(Indicator(corner=corner),
                       tag=tag, redraw=False)

    canvas.update_canvas(whence=3)


def show_color_bar(viewer, tf, side='bottom'):
    """Show a color bar in the window.

    Parameters
    ----------
    viewer : an ImageView subclass instance
        If True, show the color bar; else remove it if present.

    tf : bool
        If True, show the color bar; else remove it if present.

    side : str
        One of 'top' or 'bottom'. The default is 'bottom'.

    """

    tag = '_$color_bar'
    canvas = viewer.get_private_canvas()
    try:
        cbar = canvas.get_object_by_tag(tag)
        if not tf:
            canvas.delete_object_by_tag(tag)
        else:
            cbar.side = side

    except KeyError:
        if tf:
            Cbar = canvas.get_draw_class('colorbar')
            canvas.add(Cbar(side=side), tag=tag, redraw=False)

    canvas.update_canvas(whence=3)


def show_focus_indicator(viewer, tf, color='white'):
    """Show a focus indicator in the window.

    Parameters
    ----------
    viewer : an ImageView subclass instance
        If True, show the color bar; else remove it if present.

    tf : bool
        If True, show the color bar; else remove it if present.

    color : str
        Color for the focus indicator.

    """

    tag = '_$focus_indicator'
    canvas = viewer.get_private_canvas()
    try:
        fcsi = canvas.get_object_by_tag(tag)
        if not tf:
            canvas.delete_object_by_tag(tag)
        else:
            fcsi.color = color

    except KeyError:
        if tf:
            Fcsi = canvas.get_draw_class('focusindicator')
            fcsi = Fcsi(color=color)
            canvas.add(fcsi, tag=tag, redraw=False)
            viewer.add_callback('focus', fcsi.focus_cb)

    canvas.update_canvas(whence=3)
