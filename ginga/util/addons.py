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


def add_zoom_buttons(viewer, canvas=None, color='black'):
    """Add zoom buttons to a canvas.

    Parameters
    ----------
    viewer : an ImageView subclass instance
        If True, show the color bar; else remove it if present.

    canvas : a DrawingCanvas instance
        The canvas to which the buttons should be added.  If not supplied
        defaults to the private canvas of the viewer.

    color : str
        A color name, hex triplet. The default is 'black'.

    """
    def zoom(box, canvas, event, pt, viewer, n):
        zl = viewer.get_zoom()
        zl += n
        if zl == 0.0:
            zl += n
        viewer.zoom_to(zl + n)

    def add_buttons(viewer, canvas, tag):
        objs = []
        wd, ht = viewer.get_window_size()
        SquareBox = canvas.get_draw_class('squarebox')
        Text = canvas.get_draw_class('text')
        Compound = canvas.get_draw_class('compoundobject')
        x1, y1 = wd - 20, ht // 2 + 20
        zoomin = SquareBox(x1, y1, 15, color='yellow', fill=True,
                           fillcolor='gray', fillalpha=0.5, coord='window')
        zoomin.editable = False
        zoomin.pickable = True
        zoomin.add_callback('pick-down', zoom, viewer, 1)
        objs.append(zoomin)
        x2, y2 = wd - 20, ht // 2 - 20
        zoomout = SquareBox(x2, y2, 15, color='yellow', fill=True,
                            fillcolor='gray', fillalpha=0.5, coord='window')
        zoomout.editable = False
        zoomout.pickable = True
        zoomout.add_callback('pick-down', zoom, viewer, -1)
        objs.append(zoomout)
        objs.append(Text(x1 - 4, y1 + 6, text='+', fontsize=18, color=color,
                         coord='window'))
        objs.append(Text(x2 - 4, y2 + 6, text='--', fontsize=18, color=color,
                         coord='window'))
        obj = Compound(*objs)
        obj.opaque = False
        canvas.add(obj, tag=tag)

    def zoom_resize(viewer, width, height, canvas, tag):
        try:
            canvas.get_object_by_tag(tag)
        except KeyError:
            return False

        canvas.delete_object_by_tag(tag)
        add_buttons(viewer, canvas, tag)

    tag = '_$zoom_buttons'
    if canvas is None:
        canvas = viewer.get_private_canvas()
    canvas.ui_set_active(True, viewer)
    canvas.register_for_cursor_drawing(viewer)
    canvas.set_draw_mode('pick')
    viewer.add_callback('configure', zoom_resize, canvas, tag)

    add_buttons(viewer, canvas, tag)


# END
