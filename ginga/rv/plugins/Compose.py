# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
A plugin for composing RGB images from constituent monochrome images.

**Plugin Type: Local**

``Compose`` is a local plugin, which means it is associated with a
channel.  An instance can be opened for each channel.

**Usage**

Start the ``Compose`` plugin from the "Operation->RGB" (below) or
"Plugins->RGB" (above) menu. The tab should show up under the
"Dialogs" tab in the viewer to the right as "IMAGE:Compose".

1. Select the kind of composition you want to make from the "Compose Type"
   drop down: "RGB" for composing three monochrome images into a color
   image, "Alpha" to compose a series of images as layers with different
   alpha values for each layer.
2. Press "New Image" to start composing a new image.

***For RGB composition***

1. Drag your three constituent images that will make up the R, G, and B
   planes to the "Preview" window -- drag them in the order R (red),
   G (green), and B (blue).  Alternatively, you can load the images into
   the channel viewer one by one and after each one pressing "Insert from
   Channel" (similarly, do these in the order of R, G, and B).

In the plugin GUI, the R, G, and B images should show up as three slider
controls in the "Layers" area of the plugin, and the Preview should show
a low resolution version of how the composite image looks with the sliders
set.

.. figure:: figures/compose-rgb.png
   :width: 800px
   :align: center
   :alt: Composing an RGB image

   Composing an RGB Image.

2. Play with the alpha levels of each layer using the sliders in the
   ``Compose`` plugin; as you adjust a slider the preview image should
   update.
3. When you see something you like, you can save it to a file using the
   "Save As" button (use "jpeg" or "png" as the file extension), or insert
   it into the channel using the "Save to Channel" button.

***For Alpha composition***

For Alpha-type composition the images are just combined in the order shown
in the stack, with Layer 0 being the bottom layer, and successive layers
stacked on top.  Each layer's alpha level is adjustible by a slider in the
same manner as discussed above.

.. figure:: figures/compose-alpha.png
   :width: 800px
   :align: center
   :alt: Alpha-composing an image

   Alpha-composing an image.

1. Drag your N constituent images that will make up the layers to the
   "Preview" window, or load the images into the channel viewer one by
   one and after each one pressing "Insert from Channel" (the first image
   will be at the bottom of the stack--layer 0).
2. Play with the alpha levels of each layer using the sliders in the
   ``Compose`` plugin; as you adjust a slider the preview image should
   update.
3. When you see something you like, you can save it to a file using the
   "Save As" button (use "fits" as the file extension), or insert it into
   the channel using the "Save to Channel" button.

***General Notes***

- The preview window is just a ginga widget, so all the usual bindings
  apply; you can set color maps, cut levels, etc. with the mouse and key
  bindings.
"""
import os

from ginga.gw import Widgets, Viewers
from ginga.misc import Bunch
from ginga import RGBImage, LayerImage, AstroImage
from ginga import GingaPlugin

from PIL import Image

__all__ = ['Compose']


class RGBComposeImage(RGBImage.RGBImage, LayerImage.LayerImage):
    def __init__(self, *args, **kwargs):
        RGBImage.RGBImage.__init__(self, *args, **kwargs)
        LayerImage.LayerImage.__init__(self)


class AlphaComposeImage(AstroImage.AstroImage, LayerImage.LayerImage):
    def __init__(self, *args, **kwargs):
        AstroImage.AstroImage.__init__(self, *args, **kwargs)
        LayerImage.LayerImage.__init__(self)


class Compose(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Compose, self).__init__(fv, fitsimage)

        self.limage = None
        self.images = []
        self.count = 0
        self._wd = 300
        self._ht = 200
        self.pct_reduce = 0.1
        self._split_sizes = [600, 200, 200]

        self.layertag = 'compose-canvas'

        self.dc = fv.get_draw_classes()
        canvas = self.dc.DrawingCanvas()
        canvas.set_callback('drag-drop', self.drop_file_cb)
        self.canvas = canvas

        self.gui_up = False

    def build_gui(self, container):
        top = Widgets.VBox()
        top.set_border_width(4)

        vbox = Widgets.VBox()
        vbox.set_border_width(4)
        vbox.set_spacing(2)

        fr = Widgets.Frame("Compositing")

        captions = (("Compose Type:", 'label', "Compose Type", 'combobox'),
                    ("New Image", 'button', "Insert from Channel", 'button'),
                    )
        w, b = Widgets.build_info(captions)
        self.w.update(b)

        fr.set_widget(w)
        vbox.add_widget(fr, stretch=0)

        combobox = b.compose_type
        index = 0
        for name in ('Alpha', 'RGB'):
            combobox.append_text(name)
            index += 1
        combobox.set_index(1)

        b.new_image.add_callback('activated', lambda w: self.new_cb())
        b.new_image.set_tooltip("Start a new composite image")
        b.insert_from_channel.add_callback('activated', lambda w: self.insert_cb())
        b.insert_from_channel.set_tooltip("Insert channel image as layer")

        zi = Viewers.CanvasView(logger=None)
        zi.set_desired_size(self._wd, self._ht)
        zi.enable_autozoom('on')
        zi.enable_autocuts('off')
        zi.cut_levels(0, 255)
        zi.set_bg(0.4, 0.4, 0.4)
        zi.set_name('compose_image')
        self.preview_image = zi

        bd = zi.get_bindings()
        bd.enable_zoom(True)
        bd.enable_pan(True)
        bd.enable_flip(True)
        bd.enable_cuts(True)
        bd.enable_cmap(True)

        iw = Viewers.GingaViewerWidget(zi)
        iw.resize(self._wd, self._ht)

        zi.get_canvas().add(self.canvas)
        self.canvas.set_surface(zi)
        self.canvas.ui_set_active(True, viewer=zi)

        fr = Widgets.Frame("Preview")
        fr.set_widget(iw)

        vpaned = Widgets.Splitter(orientation='vertical')
        self.w.splitter = vpaned
        vpaned.add_widget(fr)
        # spacer
        vpaned.add_widget(Widgets.Label(''))

        fr = Widgets.Frame("Layers")
        self.w.scales = fr
        fr.set_widget(Widgets.VBox())
        vpaned.add_widget(fr)
        vpaned.set_sizes(self._split_sizes)
        vbox.add_widget(vpaned, stretch=1)

        captions = (("Save Image As", 'button', "Save Path", 'entry'),
                    ("Save to Channel", 'button'),
                    )
        w, b = Widgets.build_info(captions)
        self.w.update(b)
        b.save_to_channel.add_callback('activated', lambda w: self.save_to_channel_cb())
        b.save_to_channel.set_tooltip("Save composite image to channel")
        b.save_image_as.add_callback('activated', lambda w: self.save_as_cb())
        b.save_path.add_callback('activated', lambda *args: self.save_as_cb())
        vbox.add_widget(w, stretch=0)

        top.add_widget(vbox, stretch=1)

        btns = Widgets.HBox()
        btns.set_border_width(4)
        btns.set_spacing(4)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn)
        btn = Widgets.Button("Help")
        btn.add_callback('activated', lambda w: self.help())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)

        top.add_widget(btns, stretch=0)

        container.add_widget(top, stretch=1)
        self.gui_up = True

    def _gui_config_layers(self):
        # remove all old scales
        self.logger.debug("removing layer alpha controls")
        self.w.scales.remove_all()

        self.logger.debug("building layer alpha controls")
        # construct a new vbox of alpha controls
        captions = []
        num_layers = self.limage.num_layers()
        for i in range(num_layers):
            layer = self.limage.get_layer(i)
            captions.append((layer.name + ':', 'label', 'layer_%d' % i, 'hscale'))

        w, b = Widgets.build_info(captions)
        self.w.update(b)
        for i in range(num_layers):
            layer = self.limage.get_layer(i)
            adj = b['layer_%d' % (i)]
            lower, upper = 0, 100
            adj.set_limits(lower, upper, incr_value=1)
            #adj.set_decimals(2)
            adj.set_value(int(layer.alpha * 100.0))
            adj.set_tracking(True)
            adj.add_callback('value-changed', self.set_opacity_cb, i)

        self.logger.debug("adding layer alpha controls")
        self.w.scales.set_widget(w)

    def new_cb(self):
        #self.fitsimage.clear()

        name = "composite%d" % (self.count)
        self.limage = RGBComposeImage(logger=self.logger, order='RGB')
        self.images = []

        # Alpha or RGB composition?
        index = self.w.compose_type.get_index()
        if index == 0:
            self.limage.compose = 'alpha'
        else:
            self.limage.compose = 'rgb'
        self._gui_config_layers()
        self.limage.set(name=name, nothumb=True)

    def _get_layer_attributes(self, limage):
        # Get layer name
        idx = limage.num_layers()
        if limage.compose == 'rgb':
            idx = min(idx, 2)
            names = ['Red', 'Green', 'Blue']
            name = names[idx]
        else:
            name = 'layer%d' % (idx)

        # Get alpha
        alpha = 1.0

        bnch = Bunch.Bunch(name=name, alpha=alpha, idx=idx)
        return bnch

    def make_reduced_image(self, image):
        wd, ht = image.get_size()[:2]
        res = image.get_scaled_cutout_basic(0, 0, wd, ht,
                                            self.pct_reduce, self.pct_reduce)
        sm_img = RGBImage.RGBImage(data_np=res.data, order=image.order)
        return sm_img

    def insert_image(self, image):
        if self.limage is None:
            self.new_cb()

        nlayers = self.limage.num_layers()
        if (self.limage.compose == 'rgb') and (nlayers >= 3):
            self.fv.show_error("There are already 3 layers")
            return
        elif nlayers == 0:
            # populate metadata from first layer
            metadata = image.get_metadata()
            self.limage.update_metadata(metadata)

        self.images.append(image)
        sm_img = self.make_reduced_image(image)

        attrs = self._get_layer_attributes(self.limage)
        self.limage.insert_layer(attrs.idx, sm_img, name=attrs.name,
                                 alpha=attrs.alpha)

        self._gui_config_layers()

        self.logger.debug("setting layer image")
        self.preview_image.set_image(self.limage)

    def insert_cb(self):
        image = self.fitsimage.get_image()
        self.insert_image(image)

    def drop_file_cb(self, viewer, paths):
        self.logger.info("dropped files: %s" % str(paths))
        for path in paths[:3]:
            image = self.fv.load_image(path)
            self.insert_image(image)
        return True

    def create_image(self):
        # create new composed image
        if self.limage.compose == 'rgb':
            fimage = RGBComposeImage(logger=self.logger, order='RGB')
        else:
            fimage = AlphaComposeImage(logger=self.logger)
        fimage.compose = self.limage.compose
        name = "composite%d" % (self.count)
        self.count += 1

        # copy metadata
        metadata = self.images[0].get_metadata()
        fimage.update_metadata(metadata)

        # insert original full-size images into new layer image
        # only compose at the end
        for i in range(self.limage.num_layers()):
            layer = self.limage.get_layer(i)
            fimage.insert_layer(i, self.images[i], name=layer.name,
                                alpha=layer.alpha, compose=False)
        fimage.compose_layers()
        fimage.set(name=name)
        return fimage

    def save_to_channel_cb(self):
        fimage = self.create_image()
        # and drop it in the channel
        self.fv.add_image(fimage.get('name'), fimage)

    def set_opacity_cb(self, w, val, idx):
        alpha = val / 100.0
        self.limage.set_alpha(idx, alpha)

    def _alphas_controls_to_layers(self):
        self.logger.debug("updating layers in %s from controls" % self.limage)
        num_layers = self.limage.num_layers()
        vals = []
        for i in range(num_layers):
            alpha = self.w['layer_%d' % i].get_value() / 100.0
            vals.append(alpha)
            self.logger.debug("%d: alpha=%f" % (i, alpha))
            i += 1
        self.limage.set_alphas(vals)

    def _alphas_layers_to_controls(self):
        self.logger.debug("updating controls from %s" % self.limage)
        num_layers = self.limage.num_layers()
        for i in range(num_layers):
            layer = self.limage.get_layer(i)
            self.logger.debug("%d: alpha=%f" % (i, layer.alpha))
            ctrlname = 'layer_%d' % (i)
            if ctrlname in self.w:
                self.w[ctrlname].set_value(layer.alpha * 100.0)
            i += 1

    def save_alpha_as_file(self, path):
        fimage = self.create_image()
        fimage.save_as_file(path)

    def save_rgb_as_file(self, path):
        fimage = self.create_image()
        data = fimage.get_data()
        # Save image using PIL
        p_image = Image.fromarray(data)
        p_image.save(path)

    def save_as_cb(self):
        if self.limage is None:
            self.fv.show_error("Please create a composite image first.")
            return

        path = str(self.w.save_path.get_text()).strip()
        if not path.startswith('/'):
            path = os.path.join('.', path)

        if self.limage.compose == 'rgb':
            self.fv.nongui_do(self.fv.error_wrap, self.save_rgb_as_file, path)

        else:
            self.fv.nongui_do(self.fv.error_wrap, self.save_alpha_as_file, path)

    def close(self):
        self.fv.stop_local_plugin(self.chname, str(self))
        return True

    def start(self):
        self.resume()

    def pause(self):
        pass

    def resume(self):
        pass

    def stop(self):
        self._split_sizes = self.w.splitter.get_sizes()
        self.limage = None
        self.images = []

        self.fv.show_status("")
        self.gui_up = False

    def redo(self):
        pass

    def __str__(self):
        return 'compose'

# END
