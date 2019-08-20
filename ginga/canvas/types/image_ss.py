#
# images.py -- classes for images drawn on ginga canvases.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import time
import numpy as np

from ginga.canvas.CanvasObject import (CanvasObjectBase, _bool, _color,
                                       Point, MovePoint,
                                       register_canvas_types,
                                       colors_plus_none, coord_names)
from ginga.misc.ParamSet import Param
from ginga.misc import Bunch
from ginga import trcalc

from .mixins import OnePointMixin


class ImageP(OnePointMixin, CanvasObjectBase):
    """Draws an image on a ImageViewCanvas.
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
        points = np.asarray([pt], dtype=np.float)
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
        self._cache = {}
        self._zorder = 0
        # images are not editable by default
        self.editable = False

        self.enable_callback('image-set')

    def get_zorder(self):
        return self._zorder

    def set_zorder(self, zorder):
        self._zorder = zorder
        for viewer in self._cache:
            viewer.reorder_layers()
            viewer.redraw(whence=2)

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
        handled in `_draw_image()`
        """
        if viewer.renderer._drawing:
            return
        if self.image is None:
            return

        cache = self.get_cache(viewer)

        whence = viewer._whence
        #whence = 3
        self._draw_image(viewer, cache, whence)

        if cache.rgbarr is None:
            return

        cr = viewer.renderer.setup_cr(self)

        cp = self.get_cpoints(viewer)

        # TODO: need an "image id" here that identifies the particular
        # texture to be updated
        image_id = 0
        cr.draw_image(image_id, cp, cache.rgbarr, whence)

        # draw optional border
        if self.linewidth > 0:
            cr.draw_polygon(cp)

        if self.showcap:
            self.draw_caps(cr, self.cap, cp)

    def _draw_image(self, viewer, cache, whence=0.0):
        self._common_draw(viewer, cache, whence)

        cache.rgbarr = trcalc.add_alpha(cache.cutout, alpha=255)

    def _common_draw(self, viewer, cache, whence):
        # internal common drawing phase for all images
        if self.image is None:
            return

        if (whence <= 0.0) or (cache.cutout is None) or (not self.optimize):

            # get destination location in data_coords
            dst_x, dst_y = self.crdmap.to_data((self.x, self.y))

            ## a1, b1, a2, b2 = 0, 0, self.image.width - 1, self.image.height - 1

            ## # scale by our scale
            ## _scale_x, _scale_y = self.scale_x, self.scale_y

            ## interp = self.interpolation
            ## if interp is None:
            ##     t_ = viewer.get_settings()
            ##     interp = t_.get('interpolation', 'basic')

            ## # previous choice might not be available if preferences
            ## # were saved when opencv was being used (and not used now);
            ## # if so, silently default to "basic"
            ## if interp not in trcalc.interpolation_methods:
            ##     interp = 'basic'
            ## res = self.image.get_scaled_cutout2((a1, b1), (a2, b2),
            ##                                     (_scale_x, _scale_y),
            ##                                     method=interp)
            ## data = res.data

            data = self.image.get_data()

            if self.flipy:
                data = np.flipud(data)

            cache.cutout = data

            # calculate our offset
            pan_off = viewer.data_off
            cvs_x, cvs_y = dst_x - pan_off, dst_y - pan_off

            cache.cvs_pos = (cvs_x, cvs_y)

    def _reset_cache(self, cache):
        cache.setvals(cutout=None, drawn=False, cvs_pos=(0, 0))
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
        width = int(self.image.width * self.scale_x)
        height = int(self.image.height * self.scale_y)
        return (width, height)

    def get_coords(self):
        x1, y1 = self.crdmap.to_data((self.x, self.y))
        wd, ht = self.get_scaled_wdht()
        x2, y2 = x1 + wd - 1, y1 + ht - 1
        return (x1, y1, x2, y2)

    def get_llur(self):
        return self.get_coords()

    def get_center_pt(self):
        wd, ht = self.get_scaled_wdht()
        x1, y1, x2, y2 = self.get_coords()
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    def get_points(self):
        x1, y1, x2, y2 = self.get_coords()
        return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]

    def contains_pts(self, pts):
        x_arr, y_arr = np.asarray(pts).T
        x1, y1, x2, y2 = self.get_llur()

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
            scale_x, scale_y = self.calc_dual_scale_from_pt(pt, detail)
            self.scale_x = detail.scale_x * scale_x
        elif i == 2:
            scale_x, scale_y = self.calc_dual_scale_from_pt(pt, detail)
            self.scale_y = detail.scale_y * scale_y
        elif i == 3:
            scale_x, scale_y = self.calc_dual_scale_from_pt(pt, detail)
            self.scale_x = detail.scale_x * scale_x
            self.scale_y = detail.scale_y * scale_y
        else:
            raise ValueError("No point corresponding to index %d" % (i))

        self.reset_optimize()

    def get_edit_points(self, viewer):
        x1, y1, x2, y2 = self.get_coords()
        return [MovePoint(*self.get_center_pt()),    # location
                Point(x2, (y1 + y2) / 2.),   # width scale
                Point((x1 + x2) / 2., y2),   # height scale
                Point(x2, y2),               # both scale
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
    """Draws an image on a ImageViewCanvas.

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
        self.kind = 'normimage'
        super(NormImageP, self).__init__(pt, image, alpha=alpha,
                                         scale_x=scale_x, scale_y=scale_y,
                                         interpolation=interpolation,
                                         linewidth=linewidth, linestyle=linestyle,
                                         color=color,
                                         showcap=showcap, optimize=optimize,
                                         **kwdargs)
        self.rgbmap = rgbmap
        self.cuts = cuts
        self.autocuts = autocuts

    def _draw_image(self, viewer, cache, whence=0.0):
        t1 = t2 = t3 = t4 = time.time()

        self._common_draw(viewer, cache, whence)

        if cache.cutout is None:
            return

        t2 = time.time()
        if self.rgbmap is not None:
            rgbmap = self.rgbmap
        else:
            rgbmap = viewer.get_rgbmap()

        image_order = self.image.get_order()

        if (whence <= 0.0) or (not self.optimize):
            # if image has an alpha channel, then strip it off and save
            # it until it is recombined later with the colorized output
            # this saves us having to deal with an alpha band in the
            # cuts leveling and RGB mapping routines
            img_arr = cache.cutout
            if 'A' not in image_order:
                cache.alpha = None
            else:
                # normalize alpha array to the final output range
                mn, mx = trcalc.get_minmax_dtype(img_arr.dtype)
                a_idx = image_order.index('A')
                cache.alpha = (img_arr[..., a_idx] / mx *
                               rgbmap.maxc).astype(rgbmap.dtype)
                cache.cutout = img_arr[..., 0:a_idx]

        if (whence <= 1.0) or (cache.prergb is None) or (not self.optimize):
            # apply visual changes prior to color mapping (cut levels, etc)
            vmax = rgbmap.get_hash_size() - 1
            newdata = self.apply_visuals(viewer, cache.cutout, 0, vmax)

            # result becomes an index array fed to the RGB mapper
            if not np.issubdtype(newdata.dtype, np.dtype('uint')):
                newdata = newdata.astype(np.uint)
            idx = newdata

            self.logger.debug("shape of index is %s" % (str(idx.shape)))
            cache.prergb = idx

        t3 = time.time()
        dst_order = viewer.get_rgb_order()

        if (whence <= 2.0) or (cache.rgbarr is None) or (not self.optimize):
            # get RGB mapped array
            rgbobj = rgbmap.get_rgbarray(cache.prergb, order=dst_order,
                                         image_order=image_order)
            cache.rgbarr = rgbobj.get_array(dst_order)

            if cache.alpha is not None and 'A' in dst_order:
                a_idx = dst_order.index('A')
                cache.rgbarr[..., a_idx] = cache.alpha

        t4 = time.time()

        #cache.rgbarr = trcalc.add_alpha(cache.rgbarr, alpha=255)

        t5 = time.time()
        self.logger.debug("draw: t2=%.4f t3=%.4f t4=%.4f t5=%.4f total=%.4f" % (
            t2 - t1, t3 - t2, t4 - t3, t5 - t4, t5 - t1))

    def apply_visuals(self, viewer, data, vmin, vmax):
        if self.autocuts is not None:
            autocuts = self.autocuts
        else:
            autocuts = viewer.autocuts

        # Apply cut levels
        if self.cuts is not None:
            loval, hival = self.cuts
        else:
            loval, hival = viewer.t_['cuts']
        newdata = autocuts.cut_levels(data, loval, hival,
                                      vmin=vmin, vmax=vmax)
        return newdata

    def _reset_cache(self, cache):
        cache.setvals(cutout=None, alpha=None, prergb=None, rgbarr=None,
                      drawn=False, cvs_pos=(0, 0))
        return cache

    def set_image(self, image):
        self.image = image
        self.reset_optimize()

        self.make_callback('image-set', image)

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
