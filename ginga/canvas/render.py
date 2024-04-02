#
# render.py -- base class and utilities for Ginga renderers
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

from io import BytesIO

import numpy as np
from PIL import Image

from ginga import trcalc, colors
from ginga.fonts import font_asst
from ginga.util import pipeline
from ginga.util.stages import render
from ginga.misc import Bunch


class RenderError(Exception):
    """Base class for exceptions thrown by canvas renderers."""
    pass


class Line:
    def __init__(self, color='black', alpha=1.0, linewidth=1,
                 linestyle='solid'):
        if color is None:
            color = 'black'
        self.color = color
        self.alpha = alpha
        self.linewidth = linewidth
        self.linestyle = linestyle

        # resolve the color to a 4-tuple of (r, g, b, a)
        self._color_4tup = get_color(self.color, self.alpha)

        # attributes in here can be set by the renderer
        self.render = Bunch.Bunch()

    def get_bpp_color(self, bpp):
        r, g, b, a = self._color_4tup
        maxv = 2**bpp - 1
        return (int(r * maxv), int(g * maxv), int(b * maxv), int(a * maxv))


class Fill:
    def __init__(self, color=None, alpha=1.0):
        self.color = color
        self.alpha = alpha

        # resolve the color to a 4-tuple of (r, g, b, a)
        self._color_4tup = get_color(self.color, self.alpha)

        # attributes in here can be set by the renderer
        self.render = Bunch.Bunch()

    def get_bpp_color(self, bpp):
        r, g, b, a = self._color_4tup
        maxv = 2**bpp - 1
        return (int(r * maxv), int(g * maxv), int(b * maxv), int(a * maxv))


class Font:
    def __init__(self, fontname='sans', fontsize=12):
        if fontname is None:
            fontname = 'Sans Serif'
        fontname = font_asst.resolve_alias(fontname, fontname)
        self.fontname = fontname
        if fontsize is None:
            fontsize = 12
        self.fontsize = fontsize
        # scale relative to a 12pt font
        self.scale = fontsize / 12.0

        # attributes in here can be set by the renderer
        self.render = Bunch.Bunch()


class RenderContextBase:
    """Base class from which all RenderContext classes are derived."""

    def __init__(self, renderer, viewer):
        self.renderer = renderer
        self.viewer = viewer
        self.renderkey = renderer.kind

        self.line = None
        self.fill = None
        self.font = None

        # special value that can vary by subclasses to scale the font
        # according to each renderer type
        self._font_scale_factor = 1.0

    def __get_color(self, color, alpha):
        return get_color(color, alpha)

    def get_line(self, color, alpha=1.0, linewidth=1, linestyle='solid'):
        return Line(color=color, linewidth=linewidth,
                    linestyle=linestyle, alpha=alpha)

    def get_fill(self, color, alpha=1.0):
        return Fill(color=color, alpha=alpha)

    def get_font(self, fontname, fontsize=None, fontscale=False,
                 fontsize_min=2, fontsize_max=None):
        fontname = font_asst.resolve_alias(fontname, fontname)
        if fontsize is None:
            fontsize = 12
            fontsize = self.scale_fontsize(fontsize)
        if fontscale:
            # requesting to scale the font according to the viewer zoom level
            scale = self.viewer.get_scale_max()
            n = 1.4
            fontsize = max(fontsize_min, fontsize + np.log(scale) / np.log(n))
            if fontsize_max is not None:
                fontsize = min(fontsize_max, fontsize)

        # apply special scaling factor for this backend
        fontsize = int(round(fontsize * self._font_scale_factor))
        return Font(fontname, fontsize)

    def set_line(self, color, alpha=1.0, linewidth=1, linestyle='solid'):
        self.line = self.get_line(color=color, linewidth=linewidth,
                                  linestyle=linestyle, alpha=alpha)
        return self.line

    def set_fill(self, color, alpha=1.0):
        self.fill = self.get_fill(color=color, alpha=alpha)
        return self.fill

    def set_font(self, fontname, fontsize=None):
        self.font = self.get_font(fontname, fontsize=fontsize)
        return self.font

    def get_line_from_shape(self, shape):
        linewidth = getattr(shape, 'linewidth', 1.0)
        linestyle = getattr(shape, 'linestyle', 'solid')
        alpha = getattr(shape, 'alpha', 1.0)
        color = getattr(shape, 'color', 'black')
        return self.get_line(color, alpha=alpha,
                             linewidth=linewidth, linestyle=linestyle)

    def get_fill_from_shape(self, shape):
        fill = getattr(shape, 'fill', False)
        if fill:
            if hasattr(shape, 'fillcolor') and shape.fillcolor is not None:
                color = shape.fillcolor
            else:
                color = shape.color

            alpha = getattr(shape, 'alpha', None)
            fillalpha = getattr(shape, 'fillalpha', alpha)
            fill = self.get_fill(color, alpha=fillalpha)
        else:
            fill = None
        return fill

    def get_font_from_shape(self, shape):
        if hasattr(shape, 'font'):
            if (hasattr(shape, 'fontsize') and shape.fontsize is not None and
                not getattr(shape, 'fontscale', False)):
                # user specified a font size and no scaling
                fontsize = shape.fontsize
            else:
                # user specified to scale font based on zoom level
                # of viewer
                # TODO: I think we can use the scaling in get_font()
                fontsize = shape.scale_font(self.viewer)

            # render-specific scaling
            #fontsize = self.scale_fontsize(fontsize)
            font = self.get_font(shape.font, fontsize=fontsize)
        else:
            font = None
        return font

    def set_line_from_shape(self, shape):
        self.line = self.get_line_from_shape(shape)
        return self.line

    def set_fill_from_shape(self, shape):
        self.fill = self.get_fill_from_shape(shape)
        return self.fill

    def set_font_from_shape(self, shape):
        self.font = self.get_font_from_shape(shape)
        return self.font

    def initialize_from_shape(self, shape, line=False, fill=False, font=False):
        if line:
            self.set_line_from_shape(shape)
        if fill:
            self.set_fill_from_shape(shape)
        if font:
            self.set_font_from_shape(shape)

    def scale_fontsize(self, fontsize):
        # TO BE EVENTUALLY DEPRECATED
        return self.renderer.scale_fontsize(fontsize)

    ##### DRAWING OPERATIONS #####

    def draw_image(self, cvs_img, cpoints, cache, whence, order='RGBA'):
        pass

    def draw_text(self, cx, cy, text, rot_deg=0.0, font=None, fill=None,
                  line=None):
        pass

    def draw_polygon(self, cpoints, line=None, fill=None):
        pass

    def draw_circle(self, cx, cy, cradius, line=None, fill=None):
        pass

    def draw_line(self, cx1, cy1, cx2, cy2, line=None):
        pass

    def draw_path(self, cpoints, line=None):
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
        self.viewer.redraw(whence=0)

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

    if rtype == 'matplotlib':
        from ginga.mplw import CanvasRenderMpl
        return CanvasRenderMpl.CanvasRenderer

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
                                          name='standard-pipeline-renderer')

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
        self.state = Bunch.Bunch(org_scale=(1.0, 1.0, 1.0),
                                 org_pan=(0.0, 0.0, 0.0),
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
        #self.pipeline.invalidate()
        self.pipeline.run_stage_idx(0)
        self.viewer.redraw(whence=0)

    def calc_const_len(self, clen):
        # For standard pipeline renderer, pixel size is constant
        return clen

    def _resize(self, dims):
        self.dims = dims
        # update window size and center in pipeline
        wd, ht = dims[:2]
        ctr = (wd // 2, ht // 2)
        self.state.setvals(win_dim=dims[:2], ctr=ctr,
                           order=self.std_order)

        # update pan and scale values in pipeline
        pan_x, pan_y = self.viewer.get_pan(coord='data')[:2]
        scale_x, scale_y = self.viewer.get_scale_xy()
        self._update_pan_and_scale(scale_x, scale_y,
                                   pan_x, pan_y, wd, ht)

    def _update_pan_and_scale(self, scale_x, scale_y, pan_x, pan_y,
                              win_wd, win_ht):
        data_off = self.viewer.data_off

        # record location of pan position pixel
        org_x, org_y = pan_x - data_off, pan_y - data_off

        org_scale_x, org_scale_y = scale_x, scale_y
        org_scale_z = (scale_x + scale_y) * 0.5

        self.state.setvals(org_pan=(org_x, org_y, 0.0),
                           org_scale=(org_scale_x, org_scale_y, org_scale_z))

    def _confirm_pan_and_scale(self, scale_x, scale_y, pan_x, pan_y,
                               win_wd, win_ht):
        # Sanity check on the scale
        sx = float(win_wd) / scale_x
        sy = float(win_ht) / scale_y
        if (sx < 1.0) or (sy < 1.0):
            if self.viewer.settings.get('sanity_check_scale', True):
                raise RenderError("new scale would exceed pixel max; scale unchanged")

        self._update_pan_and_scale(scale_x, scale_y, pan_x, pan_y,
                                   win_wd, win_ht)

    def scale_fontsize(self, fontsize):
        return font_asst.scale_fontsize(self.kind, fontsize)


def get_color(color, alpha):
    if color is not None:
        r, g, b = colors.resolve_color(color)
    else:
        r, g, b, alpha = 1.0, 1.0, 1.0, 0.0
    return (r, g, b, alpha)
