#
# ap_region.py -- astropy-regions support
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
This module provides Ginga support for DS9 type region files and objects via
the ``astropy-regions`` package.
"""
import numpy as np

from astropy import units as u
from astropy.coordinates import SkyCoord

from ginga.canvas.CanvasObject import get_canvas_types

HAVE_REGIONS = False
try:
    import regions
    HAVE_REGIONS = True
except ImportError:
    pass


__all__ = ['astropy_region_to_ginga_canvas_object', 'add_region',
           'ginga_canvas_object_to_astropy_region']


# mappings of point styles
pt_ginga = {'*': 'square', 'x': 'cross', '+': 'plus', 'D': 'diamond'}
pt_regions = {v: k for k, v in pt_ginga.items()}
# mappings of arrow styles
arr_ginga = {'0 0': 'none', '1 0': 'start', '0 1': 'end', '1 1': 'both'}
arr_regions = {v: k for k, v in arr_ginga.items()}


def astropy_region_to_ginga_canvas_object(r, logger=None):
    """
    Convert an astropy-region object to a Ginga canvas object.

    Parameters
    ----------
    r : subclass of `~regions.PixelRegion`
        The region object to be converted

    logger : a Python logger (optional, default: None)
        A logger to which errors will be written

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

    elif isinstance(r, (regions.CircleSkyRegion,)):
        obj = dc.Circle(r.center.ra.deg, r.center.dec.deg,
                        r.radius.to(u.deg).value, coord='wcs')

    elif isinstance(r, (regions.EllipsePixelRegion,)):
        obj = dc.Ellipse(r.center.x, r.center.y, r.width * 0.5, r.height * 0.5,
                         rot_deg=r.angle.to(u.deg).value)

    elif isinstance(r, (regions.EllipseSkyRegion,)):
        obj = dc.Ellipse(r.center.ra.deg, r.center.dec.deg,
                         (r.width * 0.5).to(u.deg).value,
                         (r.height * 0.5).to(u.deg).value,
                         rot_deg=r.angle.to(u.deg).value, coord='wcs')

    # NOTE: need to check for Text before Point, because Text seems to be
    # a subclass of Point in regions
    elif isinstance(r, (regions.TextPixelRegion,)):
        # NOTE: font needed here, but will be overridden later if specified
        # in the region's visuals
        obj = dc.Text(r.center.x, r.center.y, text=r.text, font='sans',
                      rot_deg=float(r.visual.get('textangle', 0.0)))

    elif isinstance(r, (regions.TextSkyRegion,)):
        # NOTE: font needed here, but will be overridden later if specified
        # in the region's visuals
        obj = dc.Text(r.center.ra.deg, r.center.dec.deg, text=r.text,
                      font='sans',
                      rot_deg=float(r.visual.get('textangle', 0.0)),
                      coord='wcs')

    elif isinstance(r, (regions.PointPixelRegion,)):
        # what is a reasonable default radius?
        radius = 15   # pixels

        # convert the regions-encoded style for a point into the
        # corresponding ginga style for a point, defaulting to "diamond"
        # if there is no direct match.
        style = r.visual.get('symbol', '*')
        style = pt_ginga.get(style, 'diamond')
        obj = dc.Point(r.center.x, r.center.y, radius, style=style)

    elif isinstance(r, (regions.PointSkyRegion,)):
        # what is a reasonable default radius?
        radius = 0.001   # degrees

        # see comment for PointPixelRegion
        style = r.visual.get('symbol', '*')
        style = pt_ginga.get(style, 'diamond')
        obj = dc.Point(r.center.ra.deg, r.center.dec.deg, radius, style=style,
                       coord='wcs')

    elif isinstance(r, (regions.LinePixelRegion,)):
        obj = dc.Line(r.start.x, r.start.y, r.end.x, r.end.y)
        obj.arrow = arr_ginga[r.meta.get('line', '0 0')]

    elif isinstance(r, (regions.LineSkyRegion,)):
        obj = dc.Line(r.start.ra.deg, r.start.dec.deg,
                      r.end.ra.deg, r.end.dec.deg, coord='wcs')
        obj.arrow = arr_ginga[r.meta.get('line', '0 0')]

    elif isinstance(r, (regions.RectanglePixelRegion,)):
        obj = dc.Box(r.center.x, r.center.y, r.width * 0.5, r.height * 0.5,
                     rot_deg=r.angle.to(u.deg).value)

    elif isinstance(r, (regions.RectangleSkyRegion,)):
        obj = dc.Box(r.center.ra.deg, r.center.dec.deg,
                     (r.width * 0.5).to(u.deg).value,
                     (r.height * 0.5).to(u.deg).value,
                     rot_deg=r.angle.to(u.deg).value, coord='wcs')

    elif isinstance(r, (regions.PolygonPixelRegion,)):
        points = np.array(r.vertices.xy).T
        obj = dc.Polygon(points)

    elif isinstance(r, (regions.PolygonSkyRegion,)):
        points = np.array((r.vertices.ra.deg, r.vertices.dec.deg)).T
        obj = dc.Polygon(points, coord='wcs')

    elif isinstance(r, (regions.CircleAnnulusPixelRegion,)):
        rin = r.inner_radius
        rout = r.outer_radius
        wd = rout - rin
        obj = dc.Annulus(r.center.x, r.center.y, rin, width=wd,
                         atype='circle')

    elif isinstance(r, (regions.CircleAnnulusSkyRegion,)):
        rin = r.inner_radius.to(u.deg).value
        rout = r.outer_radius.to(u.deg).value
        wd = rout - rin
        obj = dc.Annulus(r.center.ra.deg, r.center.dec.deg, rin, width=wd,
                         atype='circle', coord='wcs')

    elif isinstance(r, (regions.EllipseAnnulusPixelRegion,)):
        xwd = (r.outer_width - r.inner_width) * 0.5
        ywd = (r.outer_height - r.inner_height) * 0.5
        obj = dc.Annulus2R(r.center.x, r.center.y,
                           r.inner_width * 0.5, r.inner_height * 0.5,
                           xwidth=xwd, ywidth=ywd,
                           atype='ellipse',
                           rot_deg=r.angle.to(u.deg).value)

    elif isinstance(r, (regions.EllipseAnnulusSkyRegion,)):
        xwd = ((r.outer_width - r.inner_width) * 0.5).to(u.deg).value
        ywd = ((r.outer_height - r.inner_height) * 0.5).to(u.deg).value
        obj = dc.Annulus2R(r.center.ra.deg, r.center.dec.deg,
                           (r.inner_width * 0.5).to(u.deg).value,
                           (r.inner_height * 0.5).to(u.deg).value,
                           xwidth=xwd, ywidth=ywd,
                           atype='ellipse',
                           rot_deg=r.angle.to(u.deg).value, coord='wcs')

    elif isinstance(r, (regions.RectangleAnnulusPixelRegion,)):
        xwd = (r.outer_width - r.inner_width) * 0.5
        ywd = (r.outer_height - r.inner_height) * 0.5
        obj = dc.Annulus2R(r.center.x, r.center.y,
                           r.inner_width * 0.5, r.inner_height * 0.5,
                           xwidth=xwd, ywidth=ywd,
                           atype='box',
                           rot_deg=r.angle.to(u.deg).value)

    elif isinstance(r, (regions.RectangleAnnulusSkyRegion,)):
        xwd = ((r.outer_width - r.inner_width) * 0.5).to(u.deg).value
        ywd = ((r.outer_height - r.inner_height) * 0.5).to(u.deg).value
        obj = dc.Annulus2R(r.center.ra.deg, r.center.dec.deg,
                           (r.inner_width * 0.5).to(u.deg).value,
                           (r.inner_height * 0.5).to(u.deg).value,
                           xwidth=xwd, ywidth=ywd,
                           atype='box',
                           rot_deg=r.angle.to(u.deg).value, coord='wcs')

    else:
        errmsg = "Don't know how to convert this object of type: {}".format(str(type(r)))
        if logger is not None:
            # if a logger is passed, simply note the error message in the
            # log and convert the object to a Text with the error message
            logger.error(errmsg, exc_info=True)
            obj = dc.Text(0, 0, text=errmsg, font='sans')
        else:
            raise ValueError(errmsg)

    # Set visual styling attributes
    obj.color = r.visual.get('edgecolor', r.visual.get('color', 'green'))
    if hasattr(obj, 'font'):
        obj.font = r.visual.get('fontname', 'Sans')
        if 'fontsize' in r.visual:
            obj.fontsize = int(r.visual['fontsize'])

    if hasattr(obj, 'linewidth'):
        obj.linewidth = r.visual.get('linewidth', 1)

    if hasattr(obj, 'fill'):
        obj.fill = r.visual.get('fill', False)
        obj.fillcolor = r.visual.get('facecolor', obj.color)

    # Limited support for other metadata
    obj.editable = r.meta.get('edit', True)
    obj.set_data(name=r.meta.get('name', None))

    # needed for compound objects like annulus
    obj.sync_state()

    return obj


def add_region(canvas, r, tag=None, redraw=True):
    """
    Convenience function to plot an astropy-regions object on a Ginga
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


def ginga_canvas_object_to_astropy_region(obj, frame='icrs', logger=None):
    """
    Convert a Ginga canvas object to an astropy-region object.

    Parameters
    ----------
    obj : subclass of `~ginga.canvas.CanvasObject.CanvasObjectBase`
        The Ginga canvas object to be converted

    frame : str (optional, default: 'icrs')
        The type of astropy frame that should be generated for Sky regions

    logger : a Python logger (optional, default: None)
        A logger to which errors will be written

    Returns
    -------
    r : subclass of `~regions.PixelRegion` or `~regions.SkyRegion`
        The corresponding astropy-region object

    """
    if not HAVE_REGIONS:
        raise ValueError("Please install the Astropy 'regions' package to use this function")

    dc = get_canvas_types()
    r = None

    if isinstance(obj, (dc.Circle,)):
        if obj.coord == 'data':
            center = regions.PixCoord(x=obj.x, y=obj.y)
            r = regions.CirclePixelRegion(center=center,
                                          radius=obj.radius)
        elif obj.coord == 'wcs':
            center = SkyCoord(obj.x, obj.y, unit='deg', frame=frame)
            r = regions.CircleSkyRegion(center=center,
                                        radius=obj.radius * u.deg)

    elif isinstance(obj, (dc.Ellipse,)):
        if obj.coord == 'data':
            center = regions.PixCoord(x=obj.x, y=obj.y)
            r = regions.EllipsePixelRegion(center=center,
                                           width=obj.xradius * 2,
                                           height=obj.yradius * 2,
                                           angle=obj.rot_deg * u.deg)
        elif obj.coord == 'wcs':
            center = SkyCoord(obj.x, obj.y, unit='deg', frame=frame)
            r = regions.EllipseSkyRegion(center=center,
                                         width=obj.xradius * 2 * u.deg,
                                         height=obj.yradius * 2 * u.deg,
                                         angle=obj.rot_deg * u.deg)

    elif isinstance(obj, (dc.Text,)):
        if obj.coord == 'data':
            center = regions.PixCoord(x=obj.x, y=obj.y)
            r = regions.TextPixelRegion(center=center, text=obj.text)
            r.visual['textangle'] = str(obj.rot_deg)
        elif obj.coord == 'wcs':
            center = SkyCoord(obj.x, obj.y, unit='deg', frame=frame)
            r = regions.TextSkyRegion(center=center, text=obj.text)
            r.visual['textangle'] = str(obj.rot_deg)

    elif isinstance(obj, (dc.Point,)):
        style = pt_regions.get(obj.style, '*')
        if obj.coord == 'data':
            center = regions.PixCoord(x=obj.x, y=obj.y)
            r = regions.PointPixelRegion(center=center)
        elif obj.coord == 'wcs':
            center = SkyCoord(obj.x, obj.y, unit='deg', frame=frame)
            r = regions.PointSkyRegion(center=center)
        r.visual['symbol'] = style

    elif isinstance(obj, (dc.Line,)):
        if obj.coord == 'data':
            start = regions.PixCoord(x=obj.x1, y=obj.y1)
            end = regions.PixCoord(x=obj.x2, y=obj.y2)
            r = regions.LinePixelRegion(start=start, end=end)
        elif obj.coord == 'wcs':
            start = SkyCoord(obj.x1, obj.y1, unit='deg', frame=frame)
            end = SkyCoord(obj.x2, obj.y2, unit='deg', frame=frame)
            r = regions.LineSkyRegion(start=start, end=end)
        r.meta['line'] = arr_regions.get(obj.arrow, '0 0')

    elif isinstance(obj, (dc.Box,)):
        if obj.coord == 'data':
            center = regions.PixCoord(x=obj.x, y=obj.y)
            r = regions.RectanglePixelRegion(center=center,
                                             width=obj.xradius * 2,
                                             height=obj.yradius * 2,
                                             angle=obj.rot_deg * u.deg)
        elif obj.coord == 'wcs':
            center = SkyCoord(obj.x, obj.y, unit='deg', frame=frame)
            r = regions.RectangleSkyRegion(center=center,
                                           width=obj.xradius * 2 * u.deg,
                                           height=obj.yradius * 2 * u.deg,
                                           angle=obj.rot_deg * u.deg)

    elif isinstance(obj, (dc.Polygon,)):
        x, y = np.asarray(obj.points).T
        if obj.coord == 'data':
            vertices = regions.PixCoord(x=x, y=y)
            r = regions.PolygonPixelRegion(vertices=vertices)
        elif obj.coord == 'wcs':
            vertices = SkyCoord(x, y, unit='deg', frame=frame)
            r = regions.PolygonSkyRegion(vertices=vertices)

    elif isinstance(obj, (dc.Annulus,)) and obj.atype == 'circle':
        if obj.coord == 'data':
            rin = obj.radius
            rout = rin + obj.width
            center = regions.PixCoord(x=obj.x, y=obj.y)
            r = regions.CircleAnnulusPixelRegion(center=center,
                                                 inner_radius=rin,
                                                 outer_radius=rout)
        elif obj.coord == 'wcs':
            rin = obj.radius * u.deg
            rout = rin + obj.width * u.deg
            center = SkyCoord(obj.x, obj.y, unit='deg', frame=frame)
            r = regions.CircleAnnulusSkyRegion(center=center,
                                               inner_radius=rin,
                                               outer_radius=rout)

    elif isinstance(obj, (dc.Annulus2R,)) and obj.atype == 'ellipse':
        if obj.coord == 'data':
            center = regions.PixCoord(x=obj.x, y=obj.y)
            r = regions.EllipseAnnulusPixelRegion(center=center,
                                                  inner_width=obj.xradius * 2,
                                                  inner_height=obj.yradius * 2,
                                                  outer_width=obj.xradius * 2 + obj.xwidth * 2,
                                                  outer_height=obj.yradius * 2 + obj.ywidth * 2,
                                                  angle=obj.rot_deg * u.deg)
        elif obj.coord == 'wcs':
            center = SkyCoord(obj.x, obj.y, unit='deg', frame=frame)
            r = regions.EllipseAnnulusSkyRegion(center=center,
                                                inner_width=obj.xradius * 2 * u.deg,
                                                inner_height=obj.yradius * 2 * u.deg,
                                                outer_width=obj.xradius * 2 * u.deg + obj.xwidth * 2 * u.deg,
                                                outer_height=obj.yradius * 2 * u.deg + obj.ywidth * 2 * u.deg,
                                                angle=obj.rot_deg * u.deg)

    elif isinstance(obj, (dc.Annulus2R,)) and obj.atype == 'box':
        if obj.coord == 'data':
            center = regions.PixCoord(x=obj.x, y=obj.y)
            r = regions.RectangleAnnulusPixelRegion(center=center,
                                                    inner_width=obj.xradius * 2,
                                                    inner_height=obj.yradius * 2,
                                                    outer_width=obj.xradius * 2 + obj.xwidth * 2,
                                                    outer_height=obj.yradius * 2 + obj.ywidth * 2,
                                                    angle=obj.rot_deg * u.deg)
        elif obj.coord == 'wcs':
            center = SkyCoord(obj.x, obj.y, unit='deg', frame=frame)
            r = regions.RectangleAnnulusSkyRegion(center=center,
                                                  inner_width=obj.xradius * 2 * u.deg,
                                                  inner_height=obj.yradius * 2 * u.deg,
                                                  outer_width=obj.xradius * 2 * u.deg + obj.xwidth * 2 * u.deg,
                                                  outer_height=obj.yradius * 2 * u.deg + obj.ywidth * 2 * u.deg,
                                                  angle=obj.rot_deg * u.deg)

    else:
        errmsg = "Don't know how to convert this kind of object: {}".format(obj.kind)
        if logger is not None:
            # if a logger is passed, simply note the error message in the
            # log and convert the object to a TextPixelRegion with the
            # error message
            logger.error(errmsg, exc_info=True)
            r = regions.TextPixelRegion(center=regions.PixCoord(x=0, y=0),
                                        text=errmsg)
        else:
            raise ValueError(errmsg)

    # Set visual styling attributes
    r.visual['color'] = obj.color
    r.visual['edgecolor'] = obj.color

    if hasattr(obj, 'font'):
        r.visual['fontname'] = obj.font
        if obj.fontsize is not None:
            r.visual['fontsize'] = str(obj.fontsize)

    if hasattr(obj, 'linewidth'):
        r.visual['linewidth'] = obj.linewidth

    if hasattr(obj, 'fill'):
        r.visual['fill'] = 1 if obj.fill else 0
        r.visual['facecolor'] = obj.fillcolor

    # Limited support for other metadata
    r.meta['edit'] = 1 if obj.editable else 0
    meta = obj.get_data()
    if meta is not None and meta.get('name', None) is not None:
        r.meta['name'] = meta.get('name')

    return r


def import_regions(regions_file, format='ds9', logger=None):
    """
    Convenience function to read a file containing regions and
    return a list of matching Ginga canvas objects.

    Parameters
    ----------
    regions_file : str
        Path of a astropy-regions compatible file

    format : str (optional, default: 'ds9')
        Format of the astropy-regions compatible file

    logger : a Python logger (optional, default: None)
        A logger to which errors will be written

    Returns
    -------
    objs : list
        Returns a list of Ginga canvas objects that can be added
        to a Ginga canvas
    """
    regs = regions.Regions.read(regions_file, format=format)

    return [astropy_region_to_ginga_canvas_object(r, logger=logger)
            for r in regs]


def export_regions(objs, logger=None):
    """
    Convenience function to convert a sequence of Ginga canvas objects
    to a ds9 file containing regions and return a list of matching
    astropy-regions shapes.

    Parameters
    ----------
    objs : seq of subclasses of `~ginga.canvas.CanvasObject.CanvasObjectBase`
        Sequence of Ginga canvas objects compatible with Regions

    logger : a Python logger (optional, default: None)
        A logger to which errors will be written

    Returns
    -------
    regions : `~regions.Regions` object
        Returns an astropy-regions object
    """
    def _g2r(obj):
        return ginga_canvas_object_to_astropy_region(obj, logger=logger)
    regs = regions.Regions(map(_g2r, objs))
    return regs


def export_regions_canvas(canvas, logger=None):
    """
    Convenience function to convert a Ginga canvas's collection of objects
    to a ds9 file containing regions and return a list of matching
    astropy-regions shapes.

    Parameters
    ----------
    canvas : a `~ginga.canvas.types.layer.Canvas` object or subclass thereof
        a Ginga canvas object

    logger : a Python logger (optional, default: None)
        A logger to which errors will be written

    Returns
    -------
    regions : `~regions.Regions` object
        Returns an astropy-regions object
    """
    # TODO: support nested canvases, etc?
    def _g2r(obj):
        return ginga_canvas_object_to_astropy_region(obj, logger=logger)
    objs = canvas.objects
    return regions.Regions(map(_g2r, objs))
