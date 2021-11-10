#
# vip.py -- data extraction operations on mixed, plotted images.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import time
import numpy as np
# for debugging
#np.set_printoptions(threshold=np.inf)

from ginga import trcalc
from ginga.canvas.types.image import ImageP
from ginga.canvas.types.layer import Canvas
from ginga.misc import Bunch


class ViewerImageProxy:
    """This class can be used in lieu of a `~ginga.BaseImage`-subclassed
    object (such as `~ginga.AstroImage` to handle cases where either an
    image has been loaded into a viewer in the conventional way, OR multiple
    images have been plotted onto the viewer canvas.  It has a subset of the
    API for an image wrapper object, and can be substituted for that in cases
    that only use the subset.

    Every `ImageView`-based viewer has one already constructed inside it.

    Example. Previously, one might do:

       image = viewer.get_image()
       data, x1, y1, x2, y2 = image.cutout_radius(data_x, data_y, radius)

    Alternative, using the already built vip:

        image = viewer.get_vip()
        data, x1, y1, x2, y2 = image.cutout_radius(data_x, data_y, radius)

    Here are the methods that are supported:
    * cutout_data
    * cutout_adjust
    * cutout_radius
    * cutout_cross
    * get_pixels_on_line
    * get_pixels_on_curve
    * get_shape_view
    * cutout_shape
    * get_size
    * get_depth
    * get_center
    * get_minmax
    * get_data_xy
    * info_xy
    * pixtoradec
    * has_valid_wcs
    * _slice

    Supported properties:
    * shape
    * width
    * height
    * depth
    * ndim
    """

    def __init__(self, viewer):
        """Constructor for a ViewerImageProxy object.

        Parameters
        ----------
        viewer : `~ginga.ImageView` (or subclass thereof)
            Ginga viewer object

        """
        self.viewer = viewer
        self.logger = viewer.get_logger()

        self.limit_cutout = 5000

    def get_canvas_images_at_pt(self, pt):
        """Extract the canvas Image-based objects under the point.

        Parameters
        ----------
        pt : tuple of int
            Point in data coordinates; e.g. (data_x, data_y)

        Returns
        -------
        obj : `~ginga.canvas.types.image.Image` (or subclass thereof)
            The top canvas image object found under this point

        """
        # get first canvas image object found under the cursor
        data_x, data_y = pt[:2]
        canvas = self.viewer.get_canvas()
        objs = canvas.get_items_at(pt)
        objs = list(filter(lambda obj: isinstance(obj, ImageP), objs))
        # top most objects are farther down
        objs.reverse()
        return objs

    def get_image_at_pt(self, pt):
        """Extract the image wrapper object under the point.

        Parameters
        ----------
        pt : tuple of int
            Point in data coordinates; e.g. (data_x, data_y)

        Returns
        -------
        (image, pt2) : tuple
            `image` is a `~ginga.BaseImage.BaseImage` (or subclass thereof)
            and `pt2` is a modified version of `pt` with the plotted location
            subtracted.

        """
        objs = self.get_canvas_images_at_pt(pt)
        data_x, data_y = pt[:2]
        off = self.viewer.data_off

        for obj in objs:
            image = obj.get_image()
            # adjust data coords for where this image is plotted
            _x, _y = data_x - obj.x, data_y - obj.y
            order = image.get_order()
            if 'A' not in order:
                # no alpha channel, so this image's data is valid
                return (image, (_x, _y))

            aix = order.index('A')
            data = image.get_data()
            _d_x, _d_y = int(np.floor(_x + off)), int(np.floor(_y + off))
            val = data[_d_y, _d_x]
            if np.isclose(val[aix], 0.0):
                # alpha value is 0
                continue

            return (image, (_x, _y))

        return None, pt

    def getval_pt(self, pt):
        """Extract the data value from an image under the point.

        The value will be NaN if the point does not refer to a valid
        location within a plotted image.

        Parameters
        ----------
        pt : tuple of int
            Point in data coordinates; e.g. (data_x, data_y)

        Returns
        -------
        val : `numpy` value
            The value for the image object found under this point

        """
        val = self.get_data_xy(pt[0], pt[1])
        if val is None:
            return np.NaN
        return val

    ## def extend_view(self, image, view):
    ##     if len(image.shape) <= 2:
    ##         return view
    ##     order = image.get_order()
    ##     if 'M' in order:
    ##         idx = order.index('M')
    ##     else:
    ##         idx = 0
    ##     return view + (idx:idx+1,)

    def get_images(self, res, canvas):
        for obj in canvas.objects:
            if isinstance(obj, ImageP) and obj.is_data:
                res.append(obj)
            elif isinstance(obj, Canvas):
                self.get_images(res, obj)
        return res

    # ----- for compatibility with BaseImage objects -----

    def cutout_data(self, x1, y1, x2, y2, xstep=1, ystep=1, z=0,
                    astype=float, fill_value=np.NaN):
        """Cut out data area based on rectangular coordinates.

        Parameters
        ----------
        x1 : int
            Starting X coordinate

        y1 : int
            Starting Y coordinate

        x2 : int
            (One more than) Ending X coordinate

        y2 : int
            (one more than) Ending Y coordinate

        xstep : int (optional, default: 1)
            Step in X direction

        ystep : int (optional, default: 1)
            Step in Y direction

        z : None or int (optional, default: 0)
            Index of a Z slice, if cutout array has three dimensions

        astype : None, str or `numpy.dtype` (optional, default: None)
            Optional type to coerce the result array to

        Returns
        -------
        arr : `numpy.ndarray`
            The cut out array

        """
        t1 = time.time()

        if astype is None:
            astype = float
        if fill_value is None:
            fill_value = np.NaN

        # coerce to int values, just in case
        x1, y1, x2, y2 = trcalc.sort_xy(x1, y1, x2, y2)
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        xstep, ystep = int(xstep), int(ystep)

        # output size
        x_len = len(range(x1, x2, xstep))
        y_len = len(range(y1, y2, ystep))

        # create result array, filled with fill value
        data_np = np.full((y_len, x_len), fill_value, dtype=astype)

        # calculate pixel containment indexes in cutout bbox
        yi, xi = np.mgrid[y1:y2:ystep, x1:x2:xstep]
        pts = np.asarray((xi, yi)).T

        canvas = self.viewer.get_canvas()
        images = self.get_images([], canvas)

        # iterate through images on this canvas, filling the result
        # array with pixels that overlap in each image
        for cv_img in images:
            # quick check for images overlapping our bbox;
            # skip those that do not overlap
            _x1, _y1, _x2, _y2 = cv_img.get_llur()
            dx = min(x2, _x2) - max(x1, _x1)
            dy = min(y2, _y2) - max(y1, _y1)
            if not (dx >= 0 and dy >= 0):
                continue

            # make a dst mask to assign only those pixels in this image
            # overlapping the cutout bbox.
            mask = cv_img.contains_pts(pts)
            # now form indices into this image's array to extract
            # the overlapping pixels
            xpos, ypos = cv_img.crdmap.to_data((cv_img.x, cv_img.y))
            xpos, ypos = int(xpos), int(ypos)
            xstart, ystart = x1 - xpos, y1 - ypos
            xstop, ystop = x2 - xpos, y2 - ypos
            yii, xii = np.mgrid[ystart:ystop:ystep, xstart:xstop:xstep]
            yi, xi = yii[mask].ravel(), xii[mask].ravel()

            image = cv_img.get_image()
            src_data = image.get_data()
            # check if this image has an alpha mask; if so, then we need
            # to further modify the dst mask to ignore the alpha masked pixels
            # NOTE: currently treatment of alpha channel is binary--
            # you get it or you don't; but it may be possible to do some
            # kind of blending in the future
            if len(src_data.shape) > 2:
                img_data = src_data[..., z][yi, xi]
                order = image.get_order()
                if 'A' in order:
                    ai = order.index('A')
                    a_arr = src_data[..., ai][yi, xi]
                    amask = np.logical_not(np.isclose(a_arr, 0))
                    mask[np.nonzero(mask)] = amask
                    data_np[mask] = img_data[amask]
                else:
                    data_np[mask] = img_data
            else:
                data_np[mask] = src_data[yi, xi]

        self.logger.debug("time to cutout_data %.4f sec" % (time.time() - t1))
        return data_np

    def cutout_adjust(self, x1, y1, x2, y2, xstep=1, ystep=1, z=0,
                      astype=None):
        """Like cutout_data(), but modifies the coordinates to remain within
        the boundaries of plotted data.

        Returns the cutout data slice and (possibly modified) bounding box.
        """
        dx = x2 - x1
        dy = y2 - y1

        xy_mn, xy_mx = self.viewer.get_limits()

        if x2 >= xy_mx[0]:
            x2 = xy_mx[0]
            x1 = x2 - dx

        if x1 < xy_mn[0]:
            x1 = xy_mn[0]

        if y2 >= xy_mx[1]:
            y2 = xy_mx[1]
            y1 = y2 - dy

        if y1 < xy_mn[1]:
            y1 = xy_mn[1]

        data = self.cutout_data(x1, y1, x2, y2, xstep=xstep, ystep=ystep,
                                z=z, astype=astype)
        return (data, x1, y1, x2, y2)

    def cutout_radius(self, x, y, radius, xstep=1, ystep=1, astype=None):
        return self.cutout_adjust(x - radius, y - radius,
                                  x + radius + 1, y + radius + 1,
                                  xstep=xstep, ystep=ystep, z=0,
                                  astype=astype)

    def cutout_cross(self, x, y, radius):
        """Cut two data subarrays that have a center at (x, y) and with
        radius (radius) from (image).  Returns the starting pixel (x0, y0)
        of each cut and the respective arrays (xarr, yarr).
        """
        x, y, radius = int(x), int(y), int(radius)
        x1, x2 = x - radius, x + radius
        y1, y2 = y - radius, y + radius
        data_np = self.cutout_data(x1, y1, x2 + 1, y2 + 1)

        xarr = data_np[y - y1, :]
        yarr = data_np[:, x - x1]

        return (x1, y1, xarr, yarr)

    ## def get_shape_mask(self, shape_obj):
    ##     """
    ##     Return full mask where True marks pixels within the given shape.
    ##     """
    ##     xy_mn, xy_mx = self.viewer.get_limits()
    ##     yi = np.mgrid[xy_mn[1]:xy_mx[1]].reshape(-1, 1)
    ##     xi = np.mgrid[xy_mn[0]:xy_mx[0]].reshape(1, -1)
    ##     pts = np.asarray((xi, yi)).T
    ##     contains = shape_obj.contains_pts(pts)
    ##     return contains

    def cutout_shape(self, shape_obj):
        view, mask = self.get_shape_view(shape_obj)

        data = self._slice(view)

        # mask non-containing members
        mdata = np.ma.array(data, mask=np.logical_not(mask))
        return mdata

    def get_shape_view(self, shape_obj, avoid_oob=True):
        """
        Calculate a bounding box in the data enclosing `shape_obj` and
        return a view that accesses it and a mask that is True only for
        pixels enclosed in the region.

        If `avoid_oob` is True (default) then the bounding box is clipped
        to avoid coordinates outside of the actual data.
        """
        x1, y1, x2, y2 = [int(np.round(n)) for n in shape_obj.get_llur()]

        if avoid_oob:
            # avoid out of bounds indexes
            xy_mn, xy_mx = self.viewer.get_limits()
            x1, x2 = max(xy_mn[0], x1), min(x2, xy_mx[0] - 1)
            y1, y2 = max(xy_mn[1], y1), min(y2, xy_mx[1] - 1)

        # calculate pixel containment mask in bbox
        xi, yi = np.meshgrid(range(x1, x2 + 1), range(y1, y2 + 1))
        pts = np.array((xi, yi)).T

        contains = shape_obj.contains_pts(pts)

        view = np.s_[y1:y2 + 1, x1:x2 + 1]
        return (view, contains)

    def get_pixels_on_line(self, x1, y1, x2, y2, getvalues=True):
        """Uses Bresenham's line algorithm to enumerate the pixels along
        a line.
        (see http://en.wikipedia.org/wiki/Bresenham%27s_line_algorithm)

        If `getvalues`==False then it will return tuples of (x, y) coordinates
        instead of pixel values.
        """
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        if x1 < x2:
            sx = 1
        else:
            sx = -1
        if y1 < y2:
            sy = 1
        else:
            sy = -1
        err = dx - dy

        res = []
        x, y = x1, y1
        while True:
            res.append((x, y))
            if (x == x2) and (y == y2):
                break
            e2 = 2 * err
            if e2 > -dy:
                err = err - dy
                x += sx
            if e2 < dx:
                err = err + dx
                y += sy

        if getvalues:
            if np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2) > self.limit_cutout:
                return [self.getval_pt((x, y)) for x, y in res]

            x1, y1, x2, y2 = trcalc.sort_xy(x1, y1, x2, y2)
            data_np = self.cutout_data(x1, y1, x2 + 1, y2 + 1)
            res = [data_np[y - y1, x - x1] for x, y in res]

        return res

    def get_pixels_on_curve(self, curve_obj, getvalues=True):
        res = [(int(x), int(y))
               for x, y in curve_obj.get_points_on_curve(None)]

        if getvalues:
            ## x1, y1, x2, y2 = curve_obj.get_llur()
            ## x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            ## data_np = self.cutout_data(x1, y1, x2 + 1, y2 + 1)
            ## return [data_np[y - y1, x - x1] for x, y in res]
            return [self.getval_pt((x, y)) for x, y in res]

        return res

    def _slice(self, view):
        # cutout our enclosing (possibly shortened) bbox
        x1, x2 = view[1].start, view[1].stop
        y1, y2 = view[0].start, view[0].stop
        xs = view[1].step
        if xs is None:
            xs = 1
        ys = view[0].step
        if ys is None:
            ys = 1

        data = self.cutout_data(x1, y1, x2, y2, xstep=xs, ystep=ys)
        return data

    @property
    def shape(self):
        wd, ht = self.get_size()[:2]
        return (ht, wd)

    @property
    def width(self):
        return self.get_size()[0]

    @property
    def height(self):
        return self.get_size()[1]

    @property
    def depth(self):
        return self.get_depth()

    @property
    def ndim(self):
        return len(self.shape)

    def get_size(self):
        xy_mn, xy_mx = self.viewer.get_limits()
        wd = int(abs(xy_mx[0] - xy_mn[0]))
        ht = int(abs(xy_mx[1] - xy_mn[1]))
        return (wd, ht)

    def get_depth(self):
        image = self.viewer.get_image()
        if image is not None:
            return image.get_depth()
        shape = self.shape
        if len(shape) > 2:
            return shape[-1]
        return 1

    def get_minmax(self, noinf=False):
        canvas = self.viewer.get_canvas()
        cvs_imgs = list(self.get_images([], canvas))
        if len(cvs_imgs) == 0:
            return (0, 0)
        mn, mx = cvs_imgs[0].get_image().get_minmax(noinf=noinf)
        for cvs_img in cvs_imgs[1:]:
            _mn, _mx = cvs_img.get_image().get_minmax(noinf=noinf)
            mn, mx = min(mn, _mn), max(mx, _mx)
        return (mn, mx)

    def get_shape(self):
        return self.shape

    def get_center(self):
        wd, ht = self.get_size()
        ctr_x, ctr_y = wd // 2, ht // 2
        return (ctr_x, ctr_y)

    def get_data_xy(self, x, y):
        x1, y1 = int(x), int(y)
        data = self.cutout_data(x1, y1, x1 + 1, y1 + 1)
        val = data[0, 0]
        if np.isnan(val):
            return None
        return val

    def info_xy(self, data_x, data_y, settings):

        image, pt = self.get_image_at_pt((data_x, data_y))
        ld_image = self.viewer.get_image()
        data_off = self.viewer.data_off

        if ld_image is not None:
            info = ld_image.info_xy(data_x, data_y, settings)

            if image is not None and image is not ld_image:
                info.image_x, info.image_y = pt
                _b_x, _b_y = pt[:2]
                _d_x, _d_y = (int(np.floor(_b_x + data_off)),
                              int(np.floor(_b_y + data_off)))
                info.value = image.get_data_xy(_d_x, _d_y)

        elif image is not None:
            info = image.info_xy(pt[0], pt[1], settings)
            info.x, info.y = data_x, data_y
            info.data_x, info.data_y = data_x, data_y

        else:
            info = Bunch.Bunch(itype='base', data_x=data_x, data_y=data_y,
                               x=data_x, y=data_y, value=None)

        return info

    def pixtoradec(self, data_x, data_y, format='deg', coords='data'):
        ld_image = self.viewer.get_image()
        if ld_image is not None:
            # if there is a loaded image, then use it for WCS
            return ld_image.pixtoradec(data_x, data_y, format=format,
                                       coords=coords)

        # otherwise, look to see if there is an image under the data
        # point and use it's WCS if it has one
        image, pt = self.get_image_at_pt((data_x, data_y))
        if image is not None:
            return image.pixtoradec(pt[0], pt[1], format=format, coords=coords)

        raise ValueError("No image found for WCS conversion")

    def has_valid_wcs(self):
        ld_image = self.viewer.get_image()
        if ld_image is not None:
            return ld_image.has_valid_wcs()
        return False
