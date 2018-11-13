#
# contour.py -- Support for drawing contours on ginga canvases
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#

# THIRD-PARTY
import numpy as np

have_skimage = False
try:
    from skimage import measure
    have_skimage = True
except ImportError:
    pass


def get_contours(data, levels):
    """Get sets of contour points for numpy array `data`.
    `levels` is a sequence of values around which to calculate the
    contours.  Returns a list of numpy arrays of points--each array
    makes a polygon if plotted as such.
    """
    if not have_skimage:
        raise Exception("Please install scikit-image > 0.13"
                        "to use this function")
    res = [filter(lambda arr: len(arr) >= 3,
                  measure.find_contours(data, level))
           for level in levels]
    res = [map(lambda arr: np.roll(arr, 1, axis=1),
               arrs) for arrs in res]
    return res


def calc_contours(data, num_contours):
    """Get sets of contour points for numpy array `data`.
    `num_contours` specifies the number (int) of contours to make.
    Returns a list of numpy arrays of points--each array makes a polygon
    if plotted as such.
    """
    mn = np.nanmean(data)
    top = np.nanmax(data)
    levels = np.linspace(mn, top, num_contours)
    return get_contours(data, levels)


def create_contours_obj(canvas, contour_groups, colors=None, **kwargs):
    """Create and return a compound object for ginga `canvas`, consisting
    of a number of contour polygons.  `contour_groups` is a list of
    numpy arrays of points representing polygons, such as returned by
    calc_contours() or get_contours().
    `colors` (if provided) is a list of colors for each polygon.
    Any other keyword parameters are passed on to the Polygon class.
    """
    if colors is None:
        colors = ['black']
    Polygon = canvas.get_draw_class('polygon')
    Compound = canvas.get_draw_class('compoundobject')
    objs = [Polygon(contour, color=colors[i % len(colors)], **kwargs)
            for i, contours in enumerate(contour_groups)
            for n, contour in enumerate(contours)
            ]
    contours_obj = Compound(*objs)
    return contours_obj

# END
