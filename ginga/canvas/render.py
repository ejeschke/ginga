#
# render.py -- base class and utilities for Ginga renderers
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

from io import BytesIO

try:
    import PIL.Image as PILimage
    have_PIL = True

except ImportError:
    have_PIL = False

from ginga import trcalc
from ginga.fonts import font_asst


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
        return font_asst.scale_fontsize(self.renderkey, fontsize)


class RendererBase(object):
    """Base class from which all Renderer classes are derived."""

    def __init__(self, viewer):
        self.viewer = viewer
        self.logger = viewer.get_logger()
        self.surface = None

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
        if not have_PIL:
            raise RenderError("Please install PIL to use this method")

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
        image = PILimage.fromarray(arr8)

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
        if not have_PIL:
            raise RenderError("Please install PIL to use this method")

        if self.surface is None:
            raise RenderError("No surface defined")

        with open(filepath, 'w') as out_f:
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

    raise ValueError("Don't know about '%s' renderer type" % (rtype))
