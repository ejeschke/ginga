#
# ap_region.py -- AstroPy regions support
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
This module provides Ginga support for DS9 type region files and objects via
the Astropy ``regions`` module.
"""
import numpy as np

from ginga.canvas.CanvasObject import get_canvas_types

from astropy import units as u

HAVE_REGIONS = False
try:
    import regions
    HAVE_REGIONS = True
except ImportError:
    pass


__all__ = ['astropy_region_to_ginga_canvas_object', 'add_region',
           'ginga_canvas_object_to_astropy_region']


# mappings of point styles
pt_ginga = dict(square='*', cross='x', plus='+', diamond='D')
pt_regions = {v: k for k, v in pt_ginga.items()}


def astropy_region_to_ginga_canvas_object(r):
    """
    Convert an Astropy region object to a Ginga canvas object.

    Parameters
    ----------
    r : subclass of `~regions.PixelRegion`
        The region object to be converted

    Returns
    -------
    obj : subclass of `~ginga.canvas.CanvasObject`
        The corresponding Ginga canvas object

    """
    if not HAVE_REGIONS:
        raise ValueError("Please install the Astropy 'regions' package to use this function")

    dc = get_canvas_types()
    obj = None
    if isinstance(r, (regions.CirclePixelRegion,)):
        obj = dc.Circle(r.center.x, r.center.y, r.radius)

    elif isinstance(r, (regions.EllipsePixelRegion,)):
        obj = dc.Ellipse(r.center.x, r.center.y, r.width / 2, r.height / 2.,
                         rot_deg=r.angle.to(u.deg).value)

    # NOTE: need to check for Text before Point, because Text seems to be
    # a subclass of Point in regions
    elif isinstance(r, (regions.TextPixelRegion,)):
        # NOTE: font needed here, but will be overridden later if specified
        # in the region's visuals
        obj = dc.Text(r.center.x, r.center.y, text=r.text, font='sans',
                      rot_deg=float(r.visual.get('textangle', 0.0)))

    elif isinstance(r, (regions.PointPixelRegion,)):
        # what is a reasonable default radius?
        radius = 15

        style = r.visual.get('symbol', '*')
        style = pt_regions.get(style, 'square')
        obj = dc.Point(r.center.x, r.center.y, radius, style=style)

    elif isinstance(r, (regions.LinePixelRegion,)):
        obj = dc.Line(r.start.x, r.start.y, r.end.x, r.end.y)
        if r.meta.get('line', '0') == '1':
            obj.arrow = 'both'

    elif isinstance(r, (regions.RectanglePixelRegion,)):
        obj = dc.Box(r.center.x, r.center.y, r.width / 2, r.height / 2.,
                     rot_deg=r.angle.to(u.deg).value)

    elif isinstance(r, (regions.PolygonPixelRegion,)):
        points = np.array(r.vertices.xy).T
        obj = dc.Polygon(points)

    elif isinstance(r, (regions.CircleAnnulusPixelRegion,)):
        rin = r.inner_radius
        rout = r.outer_radius
        wd = rout - rin
        obj = dc.Annulus(r.center.x, r.center.y, rin, width=wd,
                         atype='circle')

    elif isinstance(r, (regions.EllipseAnnulusPixelRegion,)):
        xwd = (r.outer_width - r.inner_width) / 2.0
        ywd = (r.outer_height - r.inner_height) / 2.0
        obj = dc.Annulus2R(r.center.x, r.center.y,
                           r.inner_width / 2.0, r.inner_height / 2.0,
                           xwidth=xwd, ywidth=ywd,
                           atype='ellipse',
                           rot_deg=r.angle.to(u.deg).value)

    elif isinstance(r, (regions.RectangleAnnulusPixelRegion,)):
        xwd = (r.outer_width - r.inner_width) / 2.0
        ywd = (r.outer_height - r.inner_height) / 2.0
        obj = dc.Annulus2R(r.center.x, r.center.y,
                           r.inner_width / 2.0, r.inner_height / 2.0,
                           xwidth=xwd, ywidth=ywd,
                           atype='box',
                           rot_deg=r.angle.to(u.deg).value)

    else:
        raise ValueError("Don't know how to convert this object")

    # Set visual styling attributes
    obj.color = r.visual.get('color', 'green')
    if hasattr(obj, 'font'):
        obj.font = r.visual.get('font', 'Sans')
        if 'fontsize' in r.visual:
            obj.fontsize = int(r.visual['fontsize'])

    if hasattr(obj, 'linewidth'):
        obj.linewidth = r.visual.get('linewidth', 1)

    if hasattr(obj, 'fill'):
        obj.fill = r.visual.get('fill', False)

    # Limited support for other metadata
    obj.editable = r.meta.get('edit', True)
    obj.set_data(name=r.meta.get('name', None))

    # needed for compound objects like annulus
    obj.sync_state()

    return obj


def add_region(canvas, r, tag=None, redraw=True):
    """
    Convenience function to plot an Astropy regions object on a Ginga
    canvas.

    Parameters
    ----------
    canvas : `~ginga.canvas.types.layer.DrawingCanvas`
        The Ginga canvas on which the region should be plotted.

    r : subclass of `~regions.PixelRegion`
        The region object to be plotted

    tag : str or None (optional, default: None)
        Caller can optionally pass a specific tag for the canvas object

    redraw : bool (optional, default: True)
        True if the viewers of the canvas should be updated immediately

    """
    obj = astropy_region_to_ginga_canvas_object(r)

    if tag is None:
        tag = obj.get_data('name')
    if obj is not None:
        canvas.add(obj, tag=tag, redraw=redraw)
        return obj


def ginga_canvas_object_to_astropy_region(obj):
    """
    Convert a Ginga canvas object to an AstroPy region object.

    Parameters
    ----------
    obj : subclass of `~ginga.canvas.CanvasObject`
        The Ginga canvas object to be converted

    Returns
    -------
    r : subclass of `~regions.PixelRegion`
        The corresponding AstroPy region object

    """
    if not HAVE_REGIONS:
        raise ValueError("Please install the Astropy 'regions' package to use this function")

    dc = get_canvas_types()
    r = None

    if isinstance(obj, (dc.Circle,)):
        r = regions.CirclePixelRegion(center=regions.PixCoord(x=obj.x, y=obj.y),
                                      radius=obj.radius)

    elif isinstance(obj, (dc.Ellipse,)):
        r = regions.EllipsePixelRegion(center=regions.PixCoord(x=obj.x, y=obj.y),
                                       width=obj.xradius * 2,
                                       height=obj.yradius * 2,
                                       angle=obj.rot_deg * u.deg)

    elif isinstance(obj, (dc.Text,)):
        r = regions.TextPixelRegion(center=regions.PixCoord(x=obj.x, y=obj.y),
                                    text=obj.text)
        r.visual['textangle'] = str(obj.rot_deg)

    elif isinstance(obj, (dc.Point,)):
        r = regions.PointPixelRegion(center=regions.PixCoord(x=obj.x, y=obj.y))
        style = pt_ginga.get(obj.style, '*')
        r.visual['symbol'] = style

    elif isinstance(obj, (dc.Line,)):
        r = regions.LinePixelRegion(start=regions.PixCoord(x=obj.x1, y=obj.y1),
                                    end=regions.PixCoord(x=obj.x2, y=obj.y2))

    elif isinstance(obj, (dc.Box,)):
        r = regions.RectanglePixelRegion(center=regions.PixCoord(x=obj.x,
                                                                 y=obj.y),
                                         width=obj.xradius * 2,
                                         height=obj.yradius * 2,
                                         angle=obj.rot_deg * u.deg)

    elif isinstance(obj, (dc.Polygon,)):
        x, y = np.asarray(obj.points).T
        r = regions.PolygonPixelRegion(vertices=regions.PixCoord(x=x, y=y))

    elif isinstance(obj, (dc.Annulus,)) and obj.atype == 'circle':
        rin = obj.radius
        rout = rin + obj.width
        r = regions.CircleAnnulusPixelRegion(center=regions.PixCoord(x=obj.x,
                                                                     y=obj.y),
                                             inner_radius=rin,
                                             outer_radius=rout)

    elif isinstance(obj, (dc.Annulus2R,)) and obj.atype == 'ellipse':
        r = regions.EllipseAnnulusPixelRegion(center=regions.PixCoord(x=obj.x,
                                                                      y=obj.y),
                                              inner_width=obj.xradius * 2,
                                              inner_height=obj.yradius * 2,
                                              outer_width=obj.xradius * 2 + obj.xwidth * 2,
                                              outer_height=obj.yradius * 2 + obj.ywidth * 2,
                                              angle=obj.rot_deg * u.deg)

    elif isinstance(obj, (dc.Annulus2R,)) and obj.atype == 'box':
        r = regions.RectangleAnnulusPixelRegion(center=regions.PixCoord(x=obj.x,
                                                                        y=obj.y),
                                                inner_width=obj.xradius * 2,
                                                inner_height=obj.yradius * 2,
                                                outer_width=obj.xradius * 2 + obj.xwidth * 2,
                                                outer_height=obj.yradius * 2 + obj.ywidth * 2,
                                                angle=obj.rot_deg * u.deg)

    else:
        raise ValueError("Don't know how to convert this object")

    # Set visual styling attributes
    r.visual['color'] = obj.color

    if hasattr(obj, 'font'):
        r.visual['font'] = obj.font
        if obj.fontsize is not None:
            r.visual['fontsize'] = str(obj.fontsize)

    if hasattr(obj, 'linewidth'):
        r.visual['linewidth'] = obj.linewidth

    if hasattr(obj, 'fill'):
        r.visual['fill'] = obj.fill = r.visual.get('fill', False)

    # Limited support for other metadata
    r.meta['edit'] = 1 if obj.editable else 0
    meta = obj.get_data()
    if meta is not None and meta.get('name', None) is not None:
        r.meta['name'] = meta.get('name')

    return r


def import_ds9_regions(ds9_file):
    """
    Convenience function to read a ds9 file containing regions and
    return a list of matching Ginga canvas objects.

    Parameters
    ----------
    ds9_file : str
        Path of a ds9 like regions file

    Returns
    -------
    objs : list
        Returns a list of Ginga canvas objects that can be added
        to a Ginga canvas
    """
    regs = regions.read_ds9(ds9_file)

    return [astropy_region_to_ginga_canvas_object(r)
            for r in regs]
