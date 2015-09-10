#
# images.py -- classes for images drawn on ginga canvases.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy

from ginga.canvas.CanvasObject import (CanvasObjectBase, _bool, _color,
                                       register_canvas_types,
                                       colors_plus_none)
from ginga.misc.ParamSet import Param
from ginga.misc import Bunch
from ginga import trcalc

class Image(CanvasObjectBase):
    """Draws an image on a ImageViewCanvas.
    Parameters are:
    x, y: 0-based coordinates of one corner in the data space
    image: the image, which must be an RGBImage object
    """

    @classmethod
    def get_params_metadata(cls):
        return [
            ## Param(name='coord', type=str, default='data',
            ##       valid=['data'],
            ##       description="Set type of coordinates"),
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
            Param(name='interpolation', type=str, default='basic',
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
            ##       default=True, valid=[False, True],
            ##       description="Flip image in Y direction"),
            Param(name='optimize', type=_bool,
                  default=True, valid=[False, True],
                  description="Optimize rendering for this object"),
            ]

    def __init__(self, x, y, image, alpha=1.0, scale_x=1.0, scale_y=1.0,
                 interpolation='basic',
                 linewidth=0, linestyle='solid', color='lightgreen',
                 showcap=False, flipy=False, optimize=True,
                 **kwdargs):
        self.kind = 'image'
        super(Image, self).__init__(x=x, y=y, image=image, alpha=alpha,
                                        scale_x=scale_x, scale_y=scale_y,
                                        interpolation=interpolation,
                                        linewidth=linewidth, linestyle=linestyle,
                                        color=color, showcap=showcap,
                                        flipy=flipy, optimize=optimize,
                                        **kwdargs)

        # The cache holds intermediate step results by viewer.
        # Depending on value of `whence` they may not need to be recomputed.
        self._cache = {}
        self._zorder = 0
        # images are not editable by default
        self.editable = False

    def get_zorder(self):
        return self._zorder

    def set_zorder(self, zorder):
        self._zorder = zorder
        for viewer in self._cache:
            viewer.reorder_layers()
            viewer.redraw(whence=2)

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
        cache = self.get_cache(viewer)

        if not cache.drawn:
            cache.drawn = True
            viewer.redraw(whence=2)

        cpoints = self.get_cpoints(viewer)
        cr = viewer.renderer.setup_cr(self)

        # draw optional border
        if self.linewidth > 0:
            cr.draw_polygon(cpoints)

        if self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


    def draw_image(self, viewer, dstarr, whence=0.0):
        if self.image is None:
            return

        cache = self.get_cache(viewer)

        #print("redraw whence=%f" % (whence))
        dst_order = viewer.get_rgb_order()
        image_order = self.image.get_order()

        if (whence <= 0.0) or (cache.cutout is None) or (not self.optimize):
            # get extent of our data coverage in the window
            ((x0, y0), (x1, y1), (x2, y2), (x3, y3)) = viewer.get_pan_rect()
            xmin = int(min(x0, x1, x2, x3))
            ymin = int(min(y0, y1, y2, y3))
            xmax = int(max(x0, x1, x2, x3))
            ymax = int(max(y0, y1, y2, y3))

            # destination location in data_coords
            #dst_x, dst_y = self.x, self.y + ht
            dst_x, dst_y = self.x, self.y

            a1, b1, a2, b2 = 0, 0, self.image.width, self.image.height

            # calculate the cutout that we can make and scale to merge
            # onto the final image--by only cutting out what is necessary
            # this speeds scaling greatly at zoomed in sizes
            dst_x, dst_y, a1, b1, a2, b2 = \
                   trcalc.calc_image_merge_clip(xmin, ymin, xmax, ymax,
                                                dst_x, dst_y, a1, b1, a2, b2)

            # is image completely off the screen?
            if (a2 - a1 <= 0) or (b2 - b1 <= 0):
                # no overlay needed
                #print "no overlay needed"
                return

            # cutout and scale the piece appropriately by the viewer scale
            scale_x, scale_y = viewer.get_scale_xy()
            # scale additionally by our scale
            _scale_x, _scale_y = scale_x * self.scale_x, scale_y * self.scale_y

            res = self.image.get_scaled_cutout(a1, b1, a2, b2,
                                               _scale_x, _scale_y,
                                               #flipy=self.flipy,
                                               method=self.interpolation)

            # don't ask for an alpha channel from overlaid image if it
            # doesn't have one
            dst_order = viewer.get_rgb_order()
            image_order = self.image.get_order()
            ## if ('A' in dst_order) and not ('A' in image_order):
            ##     dst_order = dst_order.replace('A', '')

            ## if dst_order != image_order:
            ##     # reorder result to match desired rgb_order by backend
            ##     cache.cutout = trcalc.reorder_image(dst_order, res.data,
            ##                                          image_order)
            ## else:
            ##     cache.cutout = res.data
            cache.cutout = res.data

            # calculate our offset from the pan position
            pan_x, pan_y = viewer.get_pan()
            pan_off = viewer.data_off
            pan_x, pan_y = pan_x + pan_off, pan_y + pan_off
            #print "pan x,y=%f,%f" % (pan_x, pan_y)
            off_x, off_y = dst_x - pan_x, dst_y - pan_y
            # scale offset
            off_x *= scale_x
            off_y *= scale_y
            #print "off_x,y=%f,%f" % (off_x, off_y)

            # dst position in the pre-transformed array should be calculated
            # from the center of the array plus offsets
            ht, wd, dp = dstarr.shape
            cache.cvs_x = int(round(wd / 2.0  + off_x))
            cache.cvs_y = int(round(ht / 2.0  + off_y))

        # composite the image into the destination array at the
        # calculated position
        trcalc.overlay_image(dstarr, cache.cvs_x, cache.cvs_y, cache.cutout,
                             dst_order=dst_order, src_order=image_order,
                             alpha=self.alpha, flipy=False)

    def _reset_cache(self, cache):
        cache.setvals(cutout=None, drawn=False, cvs_x=0, cvs_y=0)
        return cache

    def reset_optimize(self):
        for cache in self._cache.values():
            self._reset_cache(cache)

    def set_image(self, image):
        self.image = image
        self.reset_optimize()

    def get_scaled_wdht(self):
        width = int(self.image.width * self.scale_x)
        height = int(self.image.height * self.scale_y)
        return (width, height)

    def get_coords(self):
        x1, y1 = self.x, self.y
        wd, ht = self.get_scaled_wdht()
        x2, y2 = x1 + wd, y1 + ht
        return (x1, y1, x2, y2)

    def get_center_pt(self):
        wd, ht = self.get_scaled_wdht()
        return (self.x + wd / 2.0, self.y + ht / 2.0)

    def get_points(self):
        x1, y1, x2, y2 = self.get_coords()
        return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]

    def contains(self, data_x, data_y):
        width, height = self.get_scaled_wdht()
        x2, y2 = self.x + width, self.y + height
        if ((self.x <= data_x < x2) and (self.y <= data_y < y2)):
            return True
        return False

    def rotate(self, theta, xoff=0, yoff=0):
        raise ValueError("Images cannot be rotated")

    def set_edit_point(self, i, pt):
        if i == 0:
            x, y = pt
            self.move_to(x, y)
        elif i == 1:
            x, y = pt
            self.scale_x = abs(x - self.x) / float(self.image.width)
        elif i == 2:
            x, y = pt
            self.scale_y = abs(y - self.y) / float(self.image.height)
        elif i == 3:
            x, y = pt
            self.scale_x = abs(x - self.x) / float(self.image.width)
            self.scale_y = abs(y - self.y) / float(self.image.height)
        else:
            raise ValueError("No point corresponding to index %d" % (i))

        self.reset_optimize()

    def get_edit_points(self):
        width, height = self.get_scaled_wdht()
        return [self.get_center_pt(),    # location
                (self.x + width, self.y + height / 2.),
                (self.x + width / 2., self.y + height),
                (self.x + width, self.y + height)
                ]

    def scale_by(self, scale_x, scale_y):
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


class NormImage(Image):
    """Draws an image on a ImageViewCanvas.

    Parameters are:
    x, y: 0-based coordinates of one corner in the data space
    image: the image, which must be an RGBImage object
    """

    @classmethod
    def get_params_metadata(cls):
        return [
            ## Param(name='coord', type=str, default='data',
            ##       valid=['data'],
            ##       description="Set type of coordinates"),
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
            Param(name='interpolation', type=str, default='basic',
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
            ##       default=True, valid=[False, True],
            ##       description="Flip image in Y direction"),
            Param(name='optimize', type=_bool,
                  default=True, valid=[False, True],
                  description="Optimize rendering for this object"),
            ## Param(name='rgbmap', type=?,
            ##       description="RGB mapper for the image"),
            ## Param(name='autocuts', type=?,
            ##       description="Cuts manager for the image"),
            ]

    def __init__(self, x, y, image, alpha=1.0, scale_x=1.0, scale_y=1.0,
                 interpolation='basic',
                 linewidth=0, linestyle='solid', color='lightgreen', showcap=False,
                 optimize=True, rgbmap=None, autocuts=None, **kwdargs):
        self.kind = 'normimage'
        super(NormImage, self).__init__(x=x, y=y, image=image, alpha=alpha,
                                            scale_x=scale_x, scale_y=scale_y,
                                            interpolation=interpolation,
                                            linewidth=linewidth, linestyle=linestyle,
                                            color=color,
                                            showcap=showcap, optimize=optimize,
                                            **kwdargs)
        self.rgbmap = rgbmap
        self.autocuts = autocuts


    def draw_image(self, viewer, dstarr, whence=0.0):
        if self.image is None:
            return

        #print("redraw whence=%f" % (whence))
        cache = self.get_cache(viewer)

        if (whence <= 0.0) or (cache.cutout is None) or (not self.optimize):
            # get extent of our data coverage in the window
            ((x0, y0), (x1, y1), (x2, y2), (x3, y3)) = viewer.get_pan_rect()
            xmin = int(min(x0, x1, x2, x3))
            ymin = int(min(y0, y1, y2, y3))
            xmax = int(max(x0, x1, x2, x3))
            ymax = int(max(y0, y1, y2, y3))

            # destination location in data_coords
            dst_x, dst_y = self.x, self.y

            a1, b1, a2, b2 = 0, 0, self.image.width, self.image.height

            # calculate the cutout that we can make and scale to merge
            # onto the final image--by only cutting out what is necessary
            # this speeds scaling greatly at zoomed in sizes
            dst_x, dst_y, a1, b1, a2, b2 = \
                   trcalc.calc_image_merge_clip(xmin, ymin, xmax, ymax,
                                                dst_x, dst_y, a1, b1, a2, b2)

            # is image completely off the screen?
            if (a2 - a1 <= 0) or (b2 - b1 <= 0):
                # no overlay needed
                #print "no overlay needed"
                return

            # cutout and scale the piece appropriately by viewer scale
            scale_x, scale_y = viewer.get_scale_xy()
            # scale additionally by our scale
            _scale_x, _scale_y = scale_x * self.scale_x, scale_y * self.scale_y

            res = self.image.get_scaled_cutout(a1, b1, a2, b2,
                                               _scale_x, _scale_y,
                                               method=self.interpolation)
            cache.cutout = res.data

            # calculate our offset from the pan position
            pan_x, pan_y = viewer.get_pan()
            pan_off = viewer.data_off
            pan_x, pan_y = pan_x + pan_off, pan_y + pan_off
            #print "pan x,y=%f,%f" % (pan_x, pan_y)
            off_x, off_y = dst_x - pan_x, dst_y - pan_y
            # scale offset
            off_x *= scale_x
            off_y *= scale_y
            #print "off_x,y=%f,%f" % (off_x, off_y)

            # dst position in the pre-transformed array should be calculated
            # from the center of the array plus offsets
            ht, wd, dp = dstarr.shape
            cache.cvs_x = int(round(wd / 2.0  + off_x))
            cache.cvs_y = int(round(ht / 2.0  + off_y))

        if self.rgbmap is not None:
            rgbmap = self.rgbmap
        else:
            rgbmap = viewer.get_rgbmap()

        if (whence <= 1.0) or (cache.prergb is None) or (not self.optimize):
            # apply visual changes prior to color mapping (cut levels, etc)
            vmax = rgbmap.get_hash_size() - 1
            newdata = self.apply_visuals(viewer, cache.cutout, 0, vmax)

            # result becomes an index array fed to the RGB mapper
            if not numpy.issubdtype(newdata.dtype, numpy.dtype('uint')):
                newdata = newdata.astype(numpy.uint)
            idx = newdata

            self.logger.debug("shape of index is %s" % (str(idx.shape)))
            cache.prergb = idx

        dst_order = viewer.get_rgb_order()
        image_order = self.image.get_order()
        get_order = dst_order
        if ('A' in dst_order) and not ('A' in image_order):
            get_order = dst_order.replace('A', '')

        if (whence <= 2.5) or (cache.rgbarr is None) or (not self.optimize):
            # get RGB mapped array
            rgbobj = rgbmap.get_rgbarray(cache.prergb, order=dst_order,
                                         image_order=image_order)
            cache.rgbarr = rgbobj.get_array(get_order)

        # composite the image into the destination array at the
        # calculated position
        trcalc.overlay_image(dstarr, cache.cvs_x, cache.cvs_y, cache.rgbarr,
                             dst_order=dst_order, src_order=get_order,
                             alpha=self.alpha, flipy=False)

    def apply_visuals(self, viewer, data, vmin, vmax):
        if self.autocuts is not None:
            autocuts = self.autocuts
        else:
            autocuts = viewer.autocuts

        # Apply cut levels
        loval, hival = viewer.t_['cuts']
        newdata = autocuts.cut_levels(data, loval, hival,
                                      vmin=vmin, vmax=vmax)
        return newdata

    def _reset_cache(self, cache):
        cache.setvals(cutout=None, prergb=None, rgbarr=None,
                      drawn=False, cvs_x=0, cvs_y=0)
        return cache

    def set_image(self, image):
        self.image = image
        self.reset_optimize()

    def scale_by(self, scale_x, scale_y):
        #print("scaling image")
        self.scale_x *= scale_x
        self.scale_y *= scale_y
        self.reset_optimize()
        #print("image scale_x=%f scale_y=%f" % (self.scale_x, self.scale_y))


# register our types
register_canvas_types(dict(image=Image, normimage=NormImage))

#END
