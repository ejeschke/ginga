#
# ImageViewGtkGL.py -- a backend for Ginga using Gtk's GLArea widget
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from io import BytesIO

#from ginga.gtk3w import GtkHelp
from ginga.gtk3w import ImageViewGtk
from ginga import Mixins, Bindings

from gi.repository import Gtk

# Local imports
from .CanvasRenderGL import CanvasRenderer
from .GlHelp import get_transforms


class ImageViewGtkGLError(ImageViewGtk.ImageViewGtkError):
    pass


class ImageViewGtkGL(ImageViewGtk.ImageViewGtk):

    def __init__(self, logger=None, rgbmap=None, settings=None):
        ImageViewGtk.ImageViewGtk.__init__(self, logger=logger,
                                           rgbmap=rgbmap, settings=settings)

        self.imgwin = Gtk.GLArea()
        self.imgwin.connect('realize', self.on_realize_cb)
        self.imgwin.connect('render', self.on_render_cb)
        self.imgwin.set_has_depth_buffer(False)
        self.imgwin.set_has_stencil_buffer(False)
        self.imgwin.set_auto_render(False)

        # Gtk expects 32bit RGBA data for color images
        self.rgb_order = 'RGBA'

        # we replace some transforms in the catalog for OpenGL rendering
        self.tform = get_transforms(self)

        self.choose_best_renderer()

    def choose_renderer(self, name):
        if name != 'gtkgl':
            raise ImageViewGtkGLError("Only the 'gtkgl' renderer can be used with this viewer")
        self.renderer = CanvasRenderer(self)

    def choose_best_renderer(self):
        self.choose_renderer('gtkgl')

    def configure_window(self, width, height):
        self.logger.info("window size reconfigured to %dx%d" % (
            width, height))
        self.renderer.resize((width, height))

        self.configure(width, height)

    def get_rgb_image_as_widget(self):
        return self.imgwin.grabFrameBuffer()

    def get_rgb_image_as_buffer(self, output=None, format='png',
                                quality=90):
        ibuf = output
        if ibuf is None:
            ibuf = BytesIO()

        qimg = self.get_rgb_image_as_widget()
        qimg.save(ibuf, format=format, quality=quality)
        return ibuf

    def prepare_image(self, image_id, cp, rgb_arr, whence):
        # NOTE: parameters `cp` and `whence` unused for now; possible future use
        if whence >= 2.5:
            return

        #<-- image has changed, need to update texture
        self.imgwin.make_current()

        self.renderer.gl_set_image(image_id, rgb_arr)

    def update_image(self):
        if self.imgwin is None:
            return

        self.logger.debug("updating window")
        self.imgwin.queue_render()

    def on_realize_cb(self, area):
        ctx = self.imgwin.get_context()
        ctx.make_current()

        #wd = area.get_allocated_width()
        #ht = area.get_allocated_height()
        #self.renderer.gl_resize(wd, ht)
        ## gl.glViewport(0, 0, wd, ht)

        self.renderer.gl_initialize()
        print("realized", ctx)

    def on_render_cb(self, area, ctx):
        ctx.make_current()

        self.renderer.gl_paint()

    def gl_update(self):
        self.imgwin.queue_render()
        print('gl_update!')


class ImageViewEvent(ImageViewGtkGL, ImageViewGtk.GtkEventMixin):

    def __init__(self, logger=None, rgbmap=None, settings=None):
        ImageViewGtkGL.__init__(self, logger=logger, rgbmap=rgbmap,
                                settings=settings)

        ImageViewGtk.GtkEventMixin.__init__(self)


class ImageViewZoom(Mixins.UIMixin, ImageViewEvent):

    # class variables for binding map and bindings can be set
    bindmapClass = Bindings.BindingMapper
    bindingsClass = Bindings.ImageViewBindings

    @classmethod
    def set_bindingsClass(cls, klass):
        cls.bindingsClass = klass

    @classmethod
    def set_bindmapClass(cls, klass):
        cls.bindmapClass = klass

    def __init__(self, logger=None, settings=None, rgbmap=None,
                 bindmap=None, bindings=None):
        ImageViewEvent.__init__(self, logger=logger, settings=settings,
                                rgbmap=rgbmap)
        Mixins.UIMixin.__init__(self)

        self.ui_set_active(True)

        if bindmap is None:
            bindmap = ImageViewZoom.bindmapClass(self.logger)
        self.bindmap = bindmap
        bindmap.register_for_events(self)

        if bindings is None:
            bindings = ImageViewZoom.bindingsClass(self.logger)
        self.set_bindings(bindings)

    def get_bindmap(self):
        return self.bindmap

    def get_bindings(self):
        return self.bindings

    def set_bindings(self, bindings):
        self.bindings = bindings
        bindings.set_bindings(self)


class CanvasView(ImageViewZoom):

    def __init__(self, logger=None, settings=None, rgbmap=None,
                 bindmap=None, bindings=None):
        ImageViewZoom.__init__(self, logger=logger, settings=settings,
                               rgbmap=rgbmap,
                               bindmap=bindmap, bindings=bindings)

        # Needed for UIMixin to propagate events correctly
        self.objects = [self.private_canvas]

    def set_canvas(self, canvas, private_canvas=None):
        super(CanvasView, self).set_canvas(canvas,
                                           private_canvas=private_canvas)

        self.objects[0] = self.private_canvas


#END
