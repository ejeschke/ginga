#
# render.py -- base class and utilities for Ginga renderers
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

from io import BytesIO

import numpy as np
from PIL import Image

from ginga import trcalc, RGBMap
from ginga.fonts import font_asst
from ginga.util import pipeline, rgb_cms
from ginga.util.stages import render
from ginga.misc import Bunch


class RenderError(Exception):
    """Base class for exceptions thrown by canvas renderers."""
    pass


class RenderContextBase(object):
    """Base class from which all RenderContext classes are derived."""

    def __init__(self, renderer, viewer):
        self.renderer = renderer
        self.viewer = viewer
        self.renderkey = renderer.kind

    def scale_fontsize(self, fontsize):
        # TO BE EVENTUALLY DEPRECATED
        return self.renderer.scale_fontsize(fontsize)

    def draw_image(self, cvs_img, cpoints, cache, whence, order='RGBA'):
        pass


class RendererBase(object):
    """Base class from which all Renderer classes are derived."""

    def __init__(self, viewer):
        self.viewer = viewer
        self.logger = viewer.get_logger()
        self.surface = None

    def initialize(self):
        #raise RenderError("subclass should override this method!")
        pass

    def render_whence(self, whence):
        """Called in eventual response to a redraw request in the viewer.

        Causes the rendering pipeline to be partially or completely
        re-executed, depending on `whence`.

        Parameters
        ----------
        whence : `float` or `int`
            A number indicating at what level things need to be redrawn.

        """
        raise RenderError("subclass should override this method!")

    def finalize(self):
        #raise RenderError("subclass should override this method!")
        pass

    def prepare_image(self, cvs_img, cache, whence):
        """Prepare an image to be displayed somewhere in the viewer.

        Called at a point in the rendering process when it is known
        that an image will need to be displayed.  In this renderer,
        it is called via the "overlays" stage, and it creates an RGB
        image in the cache which is then merged into the background.

        Parameters
        ----------
        cvs_img : instance of `~ginga.canvas.types.image.Image`
            The canvas object for the image to be displayed

        cache : `~ginga.misc.Bunch.Bunch`
            A cache of items used by the renderer for a particular viewer

        whence : `float` or `int`
            A number indicating at what level things need to be redrawn.
        """
        raise RenderError("subclass should override this method!")

    def getwin_array(self, order='RGBA', alpha=1.0, dtype=None):
        """Get Numpy data array representing the viewer window.

        Parameters
        ----------
        order : str
            The desired order of RGB color layers.

        alpha : float
            Opacity.

        dtype : numpy dtype
            Numpy data type desired; defaults to the renderer default.

        Returns
        -------
        outarr : ndarray
            Numpy data array for display window.

        """
        raise RenderError("subclass should override this method!")

    def get_surface_as_array(self, order=None):
        raise RenderError("subclass should override this method!")

    def get_surface_as_bytes(self, order=None):
        """Returns the surface area as a bytes encoded RGB image buffer.
        Subclass should override if there is a more efficient conversion
        than from generating a numpy array first.
        """
        arr8 = self.get_surface_as_array(order=order)
        return arr8.tobytes(order='C')

    def get_surface_as_buffer(self, output=None, order=None):
        obuf = output
        if obuf is None:
            obuf = BytesIO()

        obuf.write(self.get_surface_as_bytes(order=order))
        return obuf

    def get_surface_as_rgb_format_buffer(self, output=None, format='png',
                                         quality=90):
        if self.surface is None:
            raise RenderError("No surface defined")

        # Get current surface as an array
        # note: use format 'RGB' because PIL cannot write JPEG with
        #  4 band images
        arr8 = self.get_surface_as_array(order='RGB')

        obuf = output
        if obuf is None:
            obuf = BytesIO()

        # make a PIL image
        image = Image.fromarray(arr8)

        image.save(obuf, format=format, quality=quality)
        if output is not None:
            return None
        return obuf

    def get_surface_as_rgb_format_bytes(self, format='png', quality=90):
        buf = self.get_surface_as_rgb_format_buffer(format=format,
                                                    quality=quality)
        return buf.getvalue()

    def save_surface_as_rgb_format_file(self, filepath, format='png',
                                        quality=90):
        if self.surface is None:
            raise RenderError("No surface defined")

        with open(filepath, 'wb') as out_f:
            self.get_surface_as_rgb_format_buffer(output=out_f, format=format,
                                                  quality=quality)
        self.logger.debug("wrote %s file '%s'" % (format, filepath))

    def reorder(self, dst_order, arr, src_order=None):
        """Reorder the output array to match that needed by the viewer."""
        if dst_order is None:
            dst_order = self.viewer.rgb_order
        if src_order is None:
            src_order = self.rgb_order
        if src_order != dst_order:
            arr = trcalc.reorder_image(dst_order, arr, src_order)

        return arr

    def scale(self, scales):
        self.viewer.redraw(whence=0)

    def pan(self, pos):
        self.viewer.redraw(whence=0)

    def rotate_2d(self, rot_deg):
        self.viewer.redraw(whence=2.6)

    def transform_2d(self, state):
        self.viewer.redraw(whence=2.5)

    def rgbmap_change(self, rgbmap):
        self.viewer.redraw(whence=2)

    def levels_change(self, levels):
        self.viewer.redraw(whence=1)

    def bg_change(self, bg):
        self.viewer.redraw(whence=3)

    def fg_change(self, fg):
        self.viewer.redraw(whence=3)

    def icc_profile_change(self):
        self.viewer.redraw(whence=2.3)

    def interpolation_change(self, interp):
        self.viewer.redraw(whence=0)

    def limits_change(self, limits):
        self.viewer.redraw(whence=3)

    def get_scale(self):
        """Return the scale currently set in the renderer."""
        raise RenderError("subclass should override this method!")

    def get_origin(self):
        """Return the point in data coordinates that is supposed to
        be at the pan position (center of the window)."""
        raise RenderError("subclass should override this method!")

    def get_window_center(self):
        """Return the point in pixel coordinates at the center
        of the window."""
        raise RenderError("subclass should override this method!")

    def get_window_size(self):
        """Return the window dimensions."""
        raise RenderError("subclass should override this method!")

    def resize(self, dims):
        raise RenderError("subclass should override this method!")

    def calc_const_len(self, clen):
        # For standard pixel renderer, pixel size is constant
        raise RenderError("subclass should override this method!")

    def _confirm_pan_and_scale(self, scale_x, scale_y, pan_x, pan_y,
                               win_wd, win_ht):
        raise RenderError("subclass should override this method!")

    def scale_fontsize(self, fontsize):
        raise RenderError("subclass should override this method!")


def get_render_class(rtype):

    rtype = rtype.lower()
    if rtype == 'pil':
        from ginga.pilw import CanvasRenderPil
        return CanvasRenderPil.CanvasRenderer

    if rtype == 'agg':
        from ginga.aggw import CanvasRenderAgg
        return CanvasRenderAgg.CanvasRenderer

    if rtype == 'opencv':
        from ginga.cvw import CanvasRenderCv
        return CanvasRenderCv.CanvasRenderer

    if rtype == 'cairo':
        from ginga.cairow import CanvasRenderCairo
        return CanvasRenderCairo.CanvasRenderer

    if rtype == 'opengl':
        from ginga.opengl import CanvasRenderGL
        return CanvasRenderGL.CanvasRenderer

    if rtype == 'qt':
        from ginga.qtw import CanvasRenderQt
        return CanvasRenderQt.CanvasRenderer

    if rtype == 'vqt':
        from ginga.qtw import CanvasRenderQt
        return CanvasRenderQt.VectorCanvasRenderer

    raise ValueError("Don't know about '%s' renderer type" % (rtype))


class StandardPixelRenderer(RendererBase):
    """Standard renderer for generating bitmap-based image that can be
    copied to an RGB image type-widget or a canvas.
    """

    def __init__(self, viewer):
        super(StandardPixelRenderer, self).__init__(viewer)

        # center (and reference) pixel in the screen image (in pixel coords)
        self._ctr_x = 1
        self._ctr_y = 1

        # data indexes at the reference pixel (in data coords)
        self._org_x = 0
        self._org_y = 0
        self._org_z = 0

        # offset from pan position (at center) in this array
        self._org_xoff = 0
        self._org_yoff = 0

        # actual scale factors produced from desired ones
        self._org_scale_x = 1.0
        self._org_scale_y = 1.0
        self._org_scale_z = 1.0

        # see _apply_transforms() and _apply_rotation()
        self._xoff = 0
        self._yoff = 0

        # offsets in the screen image for drawing (in screen coords)
        self._dst_x = 0
        self._dst_y = 0

        # last known dimensions of rendering window
        self.dims = (0, 0)

        # order of RGBA channels that renderer needs to work in
        self.rgb_order = 'RGBA'

        self.invalidate()

    def get_rgb_order(self):
        return self.rgb_order

    def invalidate(self):
        # handles to various intermediate arrays
        self._rgbarr = None
        self._rgbarr2 = None
        self._rgbarr3 = None
        self._rgbarr4 = None
        self._rgbobj = None

    def create_bg_array(self, width, height, order):
        # calculate dimensions of window RGB backing image
        wd, ht = self._calc_bg_dimensions(width, height)

        # create backing image
        depth = len(order)
        rgbmap = self.viewer.get_rgbmap()

        # make backing image with the background color
        r, g, b = self.viewer.get_bg()
        rgba = trcalc.make_filled_array((ht, wd, depth), rgbmap.dtype,
                                        order, r, g, b, 1.0)

        self._rgbarr = rgba

        #self.viewer.redraw(whence=0)

    def get_rgb_object(self, whence=0):
        """Create and return RGB slices representing the data
        that should be rendered at the current zoom level and pan settings.

        Parameters
        ----------
        whence : {0, 1, 2, 3}
            Optimization flag that reduces the time to create
            the RGB object by only recalculating what is necessary:

                0: New image, pan/scale has changed
                1: Cut levels or similar has changed
                2: Color mapping has changed
                2.3: ICC profile has changed
                2.5: Transforms have changed
                2.6: Rotation has changed
                3: Graphical overlays have changed

        Returns
        -------
        rgbobj : `~ginga.RGBMap.RGBPlanes`
            RGB object.

        """
        win_wd, win_ht = self.viewer.get_window_size()
        order = self.get_rgb_order()
        # NOTE: need to have an alpha channel in place to do overlay_image()
        if 'A' not in order:
            order = order + 'A'

        if whence <= 0.0:
            # confirm and record pan and scale
            pan_x, pan_y = self.viewer.get_pan(coord='data')[:2]
            scale_x, scale_y = self.viewer.get_scale_xy()
            self._confirm_pan_and_scale(scale_x, scale_y,
                                        pan_x, pan_y,
                                        win_wd, win_ht)

        if self._rgbarr is None:
            self.create_bg_array(win_wd, win_ht, order)

        if (whence <= 2.0) or (self._rgbarr2 is None):
            # Apply any RGB image overlays
            self._rgbarr2 = np.copy(self._rgbarr)
            p_canvas = self.viewer.get_private_canvas()
            self._overlay_images(p_canvas, whence=whence)

        output_profile = self.viewer.t_.get('icc_output_profile', None)
        if output_profile is None:
            self._rgbarr3 = self._rgbarr2

        elif (whence <= 2.3) or (self._rgbarr3 is None):
            self._rgbarr3 = np.copy(self._rgbarr2)

            # convert to output ICC profile, if one is specified
            working_profile = rgb_cms.working_profile
            if (working_profile is not None) and (output_profile is not None):
                self.convert_via_profile(self._rgbarr3, order,
                                         working_profile, output_profile)

        if (whence <= 2.5) or (self._rgbarr4 is None):
            data = np.copy(self._rgbarr3)

            # Apply any viewing transformations
            self._rgbarr4 = self._apply_transforms(data)

        if (whence <= 2.6) or (self._rgbobj is None):
            rotimg = np.copy(self._rgbarr4)

            # Apply any viewing rotations
            rot_deg = self.viewer.get_rotation()
            rotimg = self._apply_rotation(rotimg, rot_deg)
            rotimg = np.ascontiguousarray(rotimg)

            self._rgbobj = RGBMap.RGBPlanes(rotimg, order)

        return self._rgbobj

    def render_whence(self, whence):
        rgbobj = self.get_rgb_object(whence=whence)

        dst_order = self.rgb_order
        #rgbarr = rgbobj.get_array(dst_order, dtype=np.uint8)
        #self.render_image(rgbarr, dst_order, (self._dst_x, self._dst_y))

        rgbarr = self.getwin_array(order=dst_order, alpha=1.0,
                                   dtype=np.uint8)
        self.render_image(rgbarr, dst_order, (0, 0))

    def _calc_bg_dimensions(self, win_wd, win_ht):
        """Calculate background image size necessary for rendering.

        This is an internal method, called during viewer window size
        configuration.

        Parameters
        ----------
        win_wd, win_ht : int
            window dimensions in pixels
        """
        # calc minimum size of pixel image we will generate
        # necessary to fit the window in the desired size

        # Make a square from the scaled cutout, with room to rotate
        slop = 20
        side = int(np.sqrt(win_wd**2 + win_ht**2) + slop)
        wd = ht = side

        # Find center of new array
        ncx, ncy = wd // 2, ht // 2
        self._org_xoff, self._org_yoff = ncx, ncy

        return (wd, ht)

    def _confirm_pan_and_scale(self, scale_x, scale_y,
                               pan_x, pan_y, win_wd, win_ht):
        """Check and record the desired pan and scale factors.

        This is an internal method, called during viewer rendering.

        Parameters
        ----------
        scale_x, scale_y : float
            desired scale of viewer in each axis.

        pan_x, pan_y : float
            pan position in data coordinates.

        win_wd, win_ht : int
            window dimensions in pixels
        """
        data_off = self.viewer.data_off

        # Sanity check on the scale
        sx = float(win_wd) / scale_x
        sy = float(win_ht) / scale_y
        if (sx < 1.0) or (sy < 1.0):
            if self.viewer.settings.get('sanity_check_scale', True):
                raise RenderError("new scale would exceed pixel max; scale unchanged")

        # record location of pan position pixel
        self._org_x, self._org_y = pan_x - data_off, pan_y - data_off
        self._org_scale_x, self._org_scale_y = scale_x, scale_y
        self._org_scale_z = (scale_x + scale_y) / 2.0

    def _apply_transforms(self, data):
        """Apply transformations to the given data.
        These include flipping on axis and swapping X/Y axes.

        This is an internal method, called during viewer rendering.

        Parameters
        ----------
        data : ndarray
            Data to be transformed.

        Returns
        -------
        data : ndarray
            Transformed data.

        """
        ht, wd = data.shape[:2]
        xoff, yoff = self._org_xoff, self._org_yoff

        # Do transforms as necessary
        flip_x, flip_y, swap_xy = self.viewer.get_transforms()

        data = trcalc.transform(data, flip_x=flip_x, flip_y=flip_y,
                                swap_xy=swap_xy)
        if flip_y:
            yoff = ht - yoff
        if flip_x:
            xoff = wd - xoff
        if swap_xy:
            xoff, yoff = yoff, xoff

        self._xoff, self._yoff = xoff, yoff

        return data

    def _apply_rotation(self, data, rot_deg):
        """Apply transformations to the given data.
        These include rotation and invert Y.

        This is an internal method, called during viewer rendering.

        Parameters
        ----------
        data : ndarray
            Data to be rotated.

        rot_deg : float
            Rotate the data by the given degrees.

        Returns
        -------
        data : ndarray
            Rotated data.

        """
        xoff, yoff = self._xoff, self._yoff

        # Rotate the image as necessary
        if rot_deg != 0:
            # This is the slowest part of the rendering--
            # install the OpenCv or Pillow packages to speed it up
            data = np.ascontiguousarray(data)
            pre_y, pre_x = data.shape[:2]
            data = trcalc.rotate_clip(data, -rot_deg, out=data,
                                      logger=self.logger)

        # apply other transforms
        if self.viewer._invert_y:
            # Flip Y for natural Y-axis inversion between FITS coords
            # and screen coords
            data = np.flipud(data)

        # dimensions may have changed in transformations
        ht, wd = data.shape[:2]

        ctr_x, ctr_y = self._ctr_x, self._ctr_y
        dst_x, dst_y = ctr_x - xoff, ctr_y - (ht - yoff)
        self._dst_x, self._dst_y = dst_x, dst_y
        self.logger.debug("ctr=%d,%d off=%d,%d dst=%d,%d cutout=%dx%d" % (
            ctr_x, ctr_y, xoff, yoff, dst_x, dst_y, wd, ht))

        win_wd, win_ht = self.viewer.get_window_size()
        self.logger.debug("win=%d,%d coverage=%d,%d" % (
            win_wd, win_ht, dst_x + wd, dst_y + ht))

        return data

    def _overlay_images(self, canvas, whence=0.0):
        """Overlay data from any canvas image objects.

        Parameters
        ----------
        canvas : `~ginga.canvas.types.layer.DrawingCanvas`
            Canvas containing possible images to overlay.

        data : ndarray
            Output array on which to overlay image data.

        whence
             See :meth:`get_rgb_object`.

        """
        #if not canvas.is_compound():
        if not hasattr(canvas, 'objects'):
            return

        for obj in canvas.get_objects():
            if hasattr(obj, 'prepare_image'):
                obj.prepare_image(self.viewer, whence)
            elif obj.is_compound() and (obj != canvas):
                self._overlay_images(obj, whence=whence)

    def _common_draw(self, cvs_img, cache, whence):
        # internal common drawing phase for all images
        image = cvs_img.image
        if image is None:
            return
        dstarr = self._rgbarr2

        if (whence <= 0.0) or (cache.cutout is None) or (not cvs_img.optimize):
            # get extent of our data coverage in the window
            # TODO: get rid of padding by fixing get_draw_rect() which
            # doesn't quite get the coverage right at high magnifications
            pad = 1.0
            pts = np.asarray(self.viewer.get_draw_rect()).T
            xmin = int(np.min(pts[0])) - pad
            ymin = int(np.min(pts[1])) - pad
            xmax = int(np.ceil(np.max(pts[0]))) + pad
            ymax = int(np.ceil(np.max(pts[1]))) + pad

            # get destination location in data_coords
            dst_x, dst_y = cvs_img.crdmap.to_data((cvs_img.x, cvs_img.y))

            a1, b1, a2, b2 = 0, 0, cvs_img.image.width - 1, cvs_img.image.height - 1

            # calculate the cutout that we can make and scale to merge
            # onto the final image--by only cutting out what is necessary
            # this speeds scaling greatly at zoomed in sizes
            ((dst_x, dst_y), (a1, b1), (a2, b2)) = \
                trcalc.calc_image_merge_clip((xmin, ymin), (xmax, ymax),
                                             (dst_x, dst_y),
                                             (a1, b1), (a2, b2))

            # is image completely off the screen?
            if (a2 - a1 <= 0) or (b2 - b1 <= 0):
                # no overlay needed
                cache.cutout = None
                return

            # cutout and scale the piece appropriately by the viewer scale
            scale_x, scale_y = self.viewer.get_scale_xy()
            # scale additionally by our scale
            _scale_x, _scale_y = (scale_x * cvs_img.scale_x,
                                  scale_y * cvs_img.scale_y)

            interp = cvs_img.interpolation
            if interp is None:
                t_ = self.viewer.get_settings()
                interp = t_.get('interpolation', 'basic')

            # previous choice might not be available if preferences
            # were saved when opencv was being used (and not used now);
            # if so, silently default to "basic"
            if interp not in trcalc.interpolation_methods:
                interp = 'basic'
            res = image.get_scaled_cutout2((a1, b1), (a2, b2),
                                           (_scale_x, _scale_y),
                                           method=interp)
            data = res.data

            if cvs_img.flipy:
                data = np.flipud(data)
            cache.cutout = data

            # calculate our offset from the pan position
            pan_x, pan_y = self.viewer.get_pan()
            pan_off = self.viewer.data_off
            pan_x, pan_y = pan_x + pan_off, pan_y + pan_off
            off_x, off_y = dst_x - pan_x, dst_y - pan_y
            # scale offset
            off_x *= scale_x
            off_y *= scale_y

            # dst position in the pre-transformed array should be calculated
            # from the center of the array plus offsets
            ht, wd, dp = dstarr.shape
            cvs_x = int(np.round(wd / 2.0 + off_x))
            cvs_y = int(np.round(ht / 2.0 + off_y))
            cache.cvs_pos = (cvs_x, cvs_y)

    def _prepare_image(self, cvs_img, cache, whence):
        if whence > 2.3 and cache.rgbarr is not None:
            return
        dstarr = self._rgbarr2

        self._common_draw(cvs_img, cache, whence)

        if cache.cutout is None:
            return

        cache.rgbarr = cache.cutout

        # should this be self.get_rgb_order() ?
        dst_order = self.viewer.get_rgb_order()
        image_order = cvs_img.image.get_order()

        # composite the image into the destination array at the
        # calculated position
        trcalc.overlay_image(dstarr, cache.cvs_pos, cache.rgbarr,
                             dst_order=dst_order, src_order=image_order,
                             alpha=cvs_img.alpha, fill=True, flipy=False)

        cache.drawn = True

    def _prepare_norm_image(self, cvs_img, cache, whence):
        if whence > 2.3 and cache.rgbarr is not None:
            return
        dstarr = self._rgbarr2

        self._common_draw(cvs_img, cache, whence)

        if cache.cutout is None:
            return

        if cvs_img.rgbmap is not None:
            rgbmap = cvs_img.rgbmap
        else:
            rgbmap = self.viewer.get_rgbmap()

        image_order = cvs_img.image.get_order()

        if (whence <= 0.0) or (not cvs_img.optimize):
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

        if (whence <= 1.0) or (cache.prergb is None) or (not cvs_img.optimize):
            # apply visual changes prior to color mapping (cut levels, etc)
            vmax = rgbmap.get_hash_size() - 1
            newdata = self._apply_visuals(cvs_img, cache.cutout, 0, vmax)

            # result becomes an index array fed to the RGB mapper
            if not np.issubdtype(newdata.dtype, np.dtype('uint')):
                newdata = newdata.astype(np.uint)
            idx = newdata

            self.logger.debug("shape of index is %s" % (str(idx.shape)))
            cache.prergb = idx

        dst_order = self.get_rgb_order()

        if (whence <= 2.0) or (cache.rgbarr is None) or (not cvs_img.optimize):
            # get RGB mapped array
            rgbobj = rgbmap.get_rgbarray(cache.prergb, order=dst_order,
                                         image_order=image_order)
            cache.rgbarr = rgbobj.get_array(dst_order)

            if cache.alpha is not None and 'A' in dst_order:
                a_idx = dst_order.index('A')
                cache.rgbarr[..., a_idx] = cache.alpha

        # composite the image into the destination array at the
        # calculated position
        trcalc.overlay_image(dstarr, cache.cvs_pos, cache.rgbarr,
                             dst_order=dst_order, src_order=dst_order,
                             alpha=cvs_img.alpha, fill=True, flipy=False)

        cache.drawn = True

    def _apply_visuals(self, cvs_img, data, vmin, vmax):
        if cvs_img.autocuts is not None:
            autocuts = cvs_img.autocuts
        else:
            autocuts = self.viewer.autocuts

        # Apply cut levels
        if cvs_img.cuts is not None:
            loval, hival = cvs_img.cuts
        else:
            loval, hival = self.viewer.t_['cuts']
        newdata = autocuts.cut_levels(data, loval, hival,
                                      vmin=vmin, vmax=vmax)
        return newdata

    def prepare_image(self, cvs_img, cache, whence):
        if cvs_img.kind == 'image':
            self._prepare_image(cvs_img, cache, whence)
        elif cvs_img.kind == 'normimage':
            self._prepare_norm_image(cvs_img, cache, whence)
        else:
            raise RenderError("I don't know how to render canvas type '{}'".format(cvs_img.kind))

    def convert_via_profile(self, data_np, order, inprof_name, outprof_name):
        """Convert the given RGB data from the working ICC profile
        to the output profile in-place.

        Parameters
        ----------
        data_np : ndarray
            RGB image data to be displayed.

        order : str
            Order of channels in the data (e.g. "BGRA").

        inprof_name, outprof_name : str
            ICC profile names (see :func:`ginga.util.rgb_cms.get_profiles`).

        """
        t_ = self.viewer.get_settings()
        # get rest of necessary conversion parameters
        to_intent = t_.get('icc_output_intent', 'perceptual')
        proofprof_name = t_.get('icc_proof_profile', None)
        proof_intent = t_.get('icc_proof_intent', 'perceptual')
        use_black_pt = t_.get('icc_black_point_compensation', False)

        try:
            rgbobj = RGBMap.RGBPlanes(data_np, order)
            arr_np = rgbobj.get_array('RGB')

            arr = rgb_cms.convert_profile_fromto(arr_np, inprof_name, outprof_name,
                                                 to_intent=to_intent,
                                                 proof_name=proofprof_name,
                                                 proof_intent=proof_intent,
                                                 use_black_pt=use_black_pt,
                                                 logger=self.logger)
            ri, gi, bi = rgbobj.get_order_indexes('RGB')

            out = data_np
            out[..., ri] = arr[..., 0]
            out[..., gi] = arr[..., 1]
            out[..., bi] = arr[..., 2]

            self.logger.debug("Converted from '%s' to '%s' profile" % (
                inprof_name, outprof_name))

        except Exception as e:
            self.logger.warning("Error converting output from working profile: %s" % (str(e)))
            # TODO: maybe should have a traceback here
            self.logger.info("Output left unprofiled")

    def getwin_array(self, order='RGBA', alpha=1.0, dtype=None):
        """Get Numpy data array for display window.

        Parameters
        ----------
        order : str
            The desired order of RGB color layers.

        alpha : float
            Opacity.

        dtype : numpy dtype
            Numpy data type desired; defaults to rgb mapper setting.

        Returns
        -------
        outarr : ndarray
            Numpy data array for display window.

        """
        dst_order = order.upper()
        src_order = self.get_rgb_order()
        # NOTE: need to have an alpha channel in place to do overlay_image()
        if 'A' not in src_order:
            src_order = src_order + 'A'

        if dtype is None:
            rgbmap = self.viewer.get_rgbmap()
            dtype = rgbmap.dtype

        # Prepare data array for rendering
        data = self._rgbobj.get_array(src_order, dtype=dtype)

        # NOTE [A]
        height, width, depth = data.shape

        win_wd, win_ht = self.viewer.get_window_size()

        # create RGBA image array with the background color for output
        r, g, b = self.viewer.get_bg()
        outarr = trcalc.make_filled_array((win_ht, win_wd, depth),
                                          dtype, src_order, r, g, b, alpha)

        # overlay our data
        trcalc.overlay_image(outarr, (self._dst_x, self._dst_y),
                             data, dst_order=src_order, src_order=src_order,
                             flipy=False, fill=False, copy=False)

        outarr = self.reorder(dst_order, outarr, src_order=src_order)
        return outarr

    def render_image(self, rgbobj, win_x, win_y):
        """Render image.
        This must be implemented by subclasses.

        Parameters
        ----------
        rgbobj : `~ginga.RGBMap.RGBPlanes`
            RGB object.

        win_x, win_y : float
            Offsets in screen coordinates.

        """
        self.logger.warning("Subclass should override this abstract method!")

    def get_scale(self):
        return (self._org_scale_x, self._org_scale_y, self._org_scale_z)

    def get_origin(self):
        return (self._org_x, self._org_y, self._org_z)

    def get_window_center(self):
        return (self._ctr_x, self._ctr_y)

    def get_window_size(self):
        return self.dims[:2]

    def _resize(self, dims):
        self.dims = dims
        width, height = dims[:2]

        self._ctr_x = width // 2
        self._ctr_y = height // 2

    def resize(self, dims):
        self._resize(dims)

        self.invalidate()
        self.viewer.redraw(whence=0)

    def get_center(self):
        return (self._ctr_x, self._ctr_y)

    def calc_const_len(self, clen):
        # For standard pixel renderer, pixel size is constant
        return clen

    def scale_fontsize(self, fontsize):
        return font_asst.scale_fontsize(self.kind, fontsize)


class StandardPipelineRenderer(RendererBase):
    """Standard renderer for generating bitmap-based image that can be
    copied to an RGB image type-widget or a canvas.

    This renderer has a pipeline that looks like:

    [createbg] => [overlays] => [iccprof] => [flipswap] => [rotate] => [output]

    """

    def __init__(self, viewer):
        super(StandardPipelineRenderer, self).__init__(viewer)

        # stages making up the rendering pipeline
        self.stage = Bunch.Bunch(createbg=render.CreateBg(viewer),
                                 overlays=render.Overlays(viewer),
                                 iccprofile=render.ICCProf(viewer),
                                 flipswap=render.FlipSwap(viewer),
                                 rotate=render.Rotate(viewer),
                                 output=render.Output(viewer))
        # build the pipeline
        self.pipeline = pipeline.Pipeline(self.logger,
                                          [self.stage.createbg,
                                           self.stage.overlays,
                                           self.stage.iccprofile,
                                           self.stage.flipswap,
                                           self.stage.rotate,
                                           self.stage.output],
                                          name='standard-pixel-renderer')

        # A table of (threshold, stage) tuples. See render_whence()
        self.tbl = [(2.0, self.stage.overlays),
                    (2.3, self.stage.iccprofile),
                    (2.5, self.stage.flipswap),
                    (2.6, self.stage.rotate),
                    ]

        # order of RGBA channels that renderer needs to work in
        self.rgb_order = 'RGBA'
        self.std_order = 'RGBA'
        self.dims = (0, 0)
        self.state = Bunch.Bunch(org_scale=(1.0, 1.0),
                                 org_pan=(0.0, 0.0),
                                 ctr=(0, 0),
                                 win_dim=(0, 0),
                                 order=self.std_order)
        self.pipeline.set(state=self.state)
        # initialize pipeline
        self.pipeline.invalidate()

    def get_rgb_order(self):
        return self.rgb_order

    def invalidate(self):
        self.pipeline.invalidate()

    def initialize(self):
        # not currently used by this renderer
        pass

    def render_whence(self, whence):
        if whence < 3.0:
            # Search the table and stop at the first stage whose threshold
            # is <= whence. Run the pipeline from that stage.
            for thr, stage in self.tbl:
                if whence <= thr:
                    self.pipeline.set(whence=whence)
                    self.pipeline.run_from(stage)
                    break

        # TODO: what are options for high bit depth under the backend?
        last_stage = self.pipeline[-1]
        rgbarr = self.pipeline.get_data(last_stage)

        # NOTE: we assume Output stage has rendered according to the
        # RGB order needed by the renderer
        dst_order = self.get_rgb_order()
        out_order = self.pipeline.get('out_order')
        if dst_order != out_order:
            raise RenderError("RGB order of pipeline output ({}) "
                              "does not match renderer expected ({})".format(
                                  out_order, dst_order))

        self.render_image(rgbarr, dst_order, (0, 0))

    def finalize(self):
        # not currently used by this renderer
        pass

    def prepare_image(self, cvs_img, cache, whence):
        stage = self.pipeline[1]
        if cvs_img.kind == 'image':
            stage._prepare_image(cvs_img, cache, whence)
        elif cvs_img.kind == 'normimage':
            stage._prepare_norm_image(cvs_img, cache, whence)
        else:
            raise RenderError("I don't know how to render canvas type '{}'".format(cvs_img.kind))

    def getwin_array(self, order='RGBA', alpha=1.0, dtype=None):
        # NOTE: alpha parameter temporarily ignored for now
        dst_order = order.upper()
        #src_order = self.std_order
        src_order = self.get_rgb_order()

        last_stage = self.pipeline[-1]
        outarr = self.pipeline.get_data(last_stage)

        # reorder as caller needs it
        outarr = self.reorder(dst_order, outarr, src_order=src_order)
        outarr = np.ascontiguousarray(outarr)
        if dtype is not None:
            outarr = outarr.astype(dtype, copy=False)
        return outarr

    def get_scale(self):
        return self.state.org_scale

    def get_origin(self):
        return self.state.org_pan

    def get_window_center(self):
        return self.state.ctr

    def get_window_size(self):
        return self.state.win_dim

    def resize(self, dims):
        self._resize(dims)
        self.pipeline.run_stage_idx(0)
        self.viewer.redraw(whence=0)

    def calc_const_len(self, clen):
        # For standard pixel renderer, pixel size is constant
        return clen

    def _resize(self, dims):
        self.dims = dims
        wd, ht = dims[:2]
        ctr = (wd // 2, ht // 2)
        self.state.setvals(win_dim=dims[:2], ctr=ctr,
                           order=self.std_order)

    def _confirm_pan_and_scale(self, scale_x, scale_y, pan_x, pan_y,
                               win_wd, win_ht):
        # Sanity check on the scale
        sx = float(win_wd) / scale_x
        sy = float(win_ht) / scale_y
        if (sx < 1.0) or (sy < 1.0):
            if self.viewer.settings.get('sanity_check_scale', True):
                raise RenderError("new scale would exceed pixel max; scale unchanged")

        data_off = self.viewer.data_off

        # record location of pan position pixel
        org_x, org_y = pan_x - data_off, pan_y - data_off

        org_scale_x, org_scale_y = scale_x, scale_y
        org_scale_z = (scale_x + scale_y) / 2.0

        self.state.setvals(org_pan=(org_x, org_y, 0.0),
                           org_scale=(org_scale_x, org_scale_y, org_scale_z))

    def scale_fontsize(self, fontsize):
        return font_asst.scale_fontsize(self.kind, fontsize)
