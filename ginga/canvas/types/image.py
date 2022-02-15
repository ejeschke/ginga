#
# image.py -- classes for images drawn on Ginga canvases.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import uuid
import weakref
import numpy as np

from ginga.canvas.CanvasObject import (CanvasObjectBase, _bool, _color,
                                       Point, MovePoint,
                                       register_canvas_types,
                                       colors_plus_none, coord_names)
from ginga.misc.ParamSet import Param
from ginga.misc import Bunch

from .mixins import OnePointMixin


class ImageP(OnePointMixin, CanvasObjectBase):
    """Draws an image on a Ginga canvas.
    Parameters are:
    x, y: 0-based coordinates of one corner in the data space
    image: the image, which must be an RGBImage object
    """

    @classmethod
    def get_params_metadata(cls):
        return [
            Param(name='coord', type=str, default='data',
                  valid=coord_names,
                  description="Set type of coordinates"),
            Param(name='x', type=float, default=0.0, argpos=0,
                  description="X coordinate of corner of object"),
            Param(name='y', type=float, default=0.0, argpos=1,
                  description="Y coordinate of corner of object"),
            ## Param(name='image', type=?, argpos=2,
            ##       description="Image to be displayed on canvas"),
            Param(name='scale_x', type=float, default=1.0,
                  description="Scaling factor for X dimension of object"),
            Param(name='scale_y', type=float, default=1.0,
                  description="Scaling factor for Y dimension of object"),
            Param(name='interpolation', type=str, default=None,
                  description="Interpolation method for scaling pixels"),
            Param(name='linewidth', type=int, default=0,
                  min=0, max=20, widget='spinbutton', incr=1,
                  description="Width of outline"),
            Param(name='linestyle', type=str, default='solid',
                  valid=['solid', 'dash'],
                  description="Style of outline (default: solid)"),
            Param(name='color',
                  valid=colors_plus_none, type=_color, default='lightgreen',
                  description="Color of outline"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of outline"),
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
            Param(name='flipy', type=_bool,
                  default=False, valid=[False, True],
                  description="Flip image in Y direction"),
            Param(name='optimize', type=_bool,
                  default=True, valid=[False, True],
                  description="Optimize rendering for this object"),
        ]

    def __init__(self, pt, image, alpha=1.0, scale_x=1.0, scale_y=1.0,
                 interpolation=None,
                 linewidth=0, linestyle='solid', color='lightgreen',
                 showcap=False, flipy=False, optimize=True,
                 **kwdargs):
        self.kind = 'image'
        points = np.asarray([pt], dtype=float)
        CanvasObjectBase.__init__(self, points=points, image=image, alpha=alpha,
                                  scale_x=scale_x, scale_y=scale_y,
                                  interpolation=interpolation,
                                  linewidth=linewidth, linestyle=linestyle,
                                  color=color, showcap=showcap,
                                  flipy=flipy, optimize=optimize,
                                  **kwdargs)
        OnePointMixin.__init__(self)

        # The cache holds intermediate step results by viewer.
        # Depending on value of `whence` they may not need to be recomputed.
        self._cache = weakref.WeakKeyDictionary()
        self.image_id = str(uuid.uuid4())
        # images are not editable by default
        self.editable = False
        # is this image "data" or something else
        self.is_data = False

        self.enable_callback('image-set')

    def in_cache(self, viewer):
        return viewer in self._cache

    def get_cache(self, viewer):
        if viewer in self._cache:
            cache = self._cache[viewer]
        else:
            cache = self._reset_cache(Bunch.Bunch())
            self._cache[viewer] = cache
        return cache

    def invalidate_cache(self, viewer):
        cache = self.get_cache(viewer)
        self._reset_cache(cache)
        return cache

    def draw(self, viewer):
        """General draw method for RGB image types.
        Note that actual insertion of the image into the output is
        handled in `draw_image()`
        """
        if self.image is None:
            return
        whence = viewer._whence
        cache = self.get_cache(viewer)

        if not cache.drawn:
            # Normally, prepare_image() will be called earlier, and
            # cache.drawn will be true.  This catches the case for
            # some renderers where that might not happen
            viewer.prepare_image(self, cache, whence)

        cpoints = self.get_cpoints(viewer)
        cr = viewer.renderer.setup_cr(self)

        cr.draw_image(self, cpoints, cache, whence)

        # draw optional border
        if self.linewidth > 0:
            cr.draw_polygon(cpoints)

        if self.showcap:
            self.draw_caps(cr, self.cap, cpoints)

    def prepare_image(self, viewer, whence):
        cache = self.get_cache(viewer)
        viewer.prepare_image(self, cache, whence)

    def _reset_cache(self, cache):
        cache.setvals(cutout=None, rgbarr=None, drawn=False, cvs_pos=(0, 0))
        return cache

    def reset_optimize(self):
        for cache in self._cache.values():
            self._reset_cache(cache)

    def get_image(self):
        return self.image

    def set_image(self, image):
        self.image = image
        self.reset_optimize()

        self.make_callback('image-set', image)

    def get_scaled_wdht(self):
        if self.image is None:
            return (0, 0)
        width = self.image.width * self.scale_x
        height = self.image.height * self.scale_y
        return (width, height)

    def get_coords(self):
        x1, y1 = self.crdmap.to_data((self.x, self.y))
        # TODO: this should be viewer.data_off instead of hard-coded,
        # but we don't have a handle to the viewer here.
        x1, y1 = x1 - 0.5, y1 - 0.5
        wd, ht = self.get_scaled_wdht()
        x2, y2 = x1 + wd, y1 + ht
        return (x1, y1, x2, y2)

    def get_llur(self):
        return self.get_coords()

    def get_center_pt(self):
        x1, y1, x2, y2 = self.get_coords()
        return ((x1 + x2) * 0.5, (y1 + y2) * 0.5)

    def get_points(self):
        x1, y1, x2, y2 = self.get_coords()
        return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]

    def contains_pts(self, pts):
        x_arr, y_arr = np.asarray(pts).T
        x1, y1, x2, y2 = self.get_coords()

        contains = np.logical_and(
            np.logical_and(x1 <= x_arr, x_arr <= x2),
            np.logical_and(y1 <= y_arr, y_arr <= y2))
        return contains

    def rotate(self, theta, xoff=0, yoff=0):
        raise ValueError("Images cannot be rotated")

    def setup_edit(self, detail):
        detail.center_pos = self.get_center_pt()
        detail.scale_x = self.scale_x
        detail.scale_y = self.scale_y

    def set_edit_point(self, i, pt, detail):
        if i == 0:
            self.move_to_pt(pt)
        elif i == 1:
            scale_x = self.calc_scale_from_pt(pt, detail)
            self.scale_x = detail.scale_x * scale_x
        elif i == 2:
            scale_y = self.calc_scale_from_pt(pt, detail)
            self.scale_y = detail.scale_y * scale_y
        elif i == 3:
            scale_x, scale_y = self.calc_dual_scale_from_pt(pt, detail)
            self.scale_x = detail.scale_x * scale_x
            self.scale_y = detail.scale_y * scale_y
        else:
            raise ValueError("No point corresponding to index %d" % (i))

        self.reset_optimize()
        detail.viewer.redraw(whence=0)

    def get_edit_points(self, viewer):
        x1, y1, x2, y2 = self.get_coords()
        return [MovePoint(*self.get_center_pt()),    # location
                Point(x2, (y1 + y2) * 0.5),          # width scale
                Point((x1 + x2) * 0.5, y2),          # height scale
                Point(x2, y2),                       # both scale
                ]

    def scale_by_factors(self, factors):
        scale_x, scale_y = factors[:2]
        self.scale_x *= scale_x
        self.scale_y *= scale_y
        self.reset_optimize()

    def set_scale(self, scale_x, scale_y):
        self.scale_x = scale_x
        self.scale_y = scale_y
        self.reset_optimize()

    def set_origin(self, x, y):
        self.x, self.y = x, y
        self.reset_optimize()


class Image(ImageP):

    def __init__(self, x, y, image, alpha=1.0, scale_x=1.0, scale_y=1.0,
                 interpolation=None,
                 linewidth=0, linestyle='solid', color='lightgreen',
                 showcap=False, flipy=False, optimize=True,
                 **kwdargs):
        ImageP.__init__(self, (x, y), image, alpha=alpha,
                        scale_x=scale_x, scale_y=scale_y,
                        interpolation=interpolation,
                        linewidth=linewidth, linestyle=linestyle,
                        color=color, showcap=showcap,
                        flipy=flipy, optimize=optimize,
                        **kwdargs)


class NormImageP(ImageP):
    """Draws an image on a Ginga canvas.

    Parameters are:
    x, y: 0-based coordinates of one corner in the data space
    image: the image, which must be an RGBImage object
    """

    @classmethod
    def get_params_metadata(cls):
        return [
            Param(name='coord', type=str, default='data',
                  valid=coord_names,
                  description="Set type of coordinates"),
            Param(name='x', type=float, default=0.0, argpos=0,
                  description="X coordinate of corner of object"),
            Param(name='y', type=float, default=0.0, argpos=1,
                  description="Y coordinate of corner of object"),
            ## Param(name='image', type=?, argpos=2,
            ##       description="Image to be displayed on canvas"),
            Param(name='scale_x', type=float, default=1.0,
                  description="Scaling factor for X dimension of object"),
            Param(name='scale_y', type=float, default=1.0,
                  description="Scaling factor for Y dimension of object"),
            Param(name='interpolation', type=str, default=None,
                  description="Interpolation method for scaling pixels"),
            Param(name='linewidth', type=int, default=0,
                  min=0, max=20, widget='spinbutton', incr=1,
                  description="Width of outline"),
            Param(name='linestyle', type=str, default='solid',
                  valid=['solid', 'dash'],
                  description="Style of outline (default: solid)"),
            Param(name='color',
                  valid=colors_plus_none, type=_color, default='lightgreen',
                  description="Color of outline"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of outline"),
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
            ## Param(name='flipy', type=_bool,
            ##       default=False, valid=[False, True],
            ##       description="Flip image in Y direction"),
            Param(name='optimize', type=_bool,
                  default=True, valid=[False, True],
                  description="Optimize rendering for this object"),
            ## Param(name='cuts', type=tuple, default=None,
            ##       description="Tuple of (lo, hi) cut levels for image"),
            ## Param(name='rgbmap', type=?,
            ##       description="RGB mapper for the image"),
            ## Param(name='autocuts', type=?,
            ##       description="Cuts manager for the image"),
        ]

    def __init__(self, pt, image, alpha=1.0, scale_x=1.0, scale_y=1.0,
                 interpolation=None, cuts=None, linewidth=0, linestyle='solid',
                 color='lightgreen', showcap=False,
                 optimize=True, rgbmap=None, autocuts=None, **kwdargs):
        super(NormImageP, self).__init__(pt, image, alpha=alpha,
                                         scale_x=scale_x, scale_y=scale_y,
                                         interpolation=interpolation,
                                         linewidth=linewidth, linestyle=linestyle,
                                         color=color,
                                         showcap=showcap, optimize=optimize,
                                         **kwdargs)
        self.kind = 'normimage'
        self.rgbmap = rgbmap
        self.cuts = cuts
        self.autocuts = autocuts

    def _reset_cache(self, cache):
        cache.setvals(cutout=None, alpha=None, prergb=None, rgbarr=None,
                      drawn=False, cvs_pos=(0, 0))
        return cache

    def scale_by(self, scale_x, scale_y):
        self.scale_x *= scale_x
        self.scale_y *= scale_y
        self.reset_optimize()


class NormImage(NormImageP):

    def __init__(self, x, y, image, alpha=1.0, scale_x=1.0, scale_y=1.0,
                 interpolation=None, cuts=None, linewidth=0, linestyle='solid',
                 color='lightgreen', showcap=False,
                 optimize=True, rgbmap=None, autocuts=None, **kwdargs):
        NormImageP.__init__(self, (x, y), image, alpha=alpha,
                            scale_x=scale_x, scale_y=scale_y,
                            interpolation=interpolation,
                            linewidth=linewidth, linestyle=linestyle,
                            color=color, showcap=showcap, optimize=optimize,
                            **kwdargs)


# register our types
register_canvas_types(dict(image=Image, normimage=NormImage))

#END
