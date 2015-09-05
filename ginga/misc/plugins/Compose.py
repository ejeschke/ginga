#
# Compose.py -- Compose plugin for Ginga reference viewer
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os

from ginga.gw import Widgets
from ginga.misc import Bunch
from ginga import RGBImage, LayerImage
from ginga import GingaPlugin

import numpy
try:
    from PIL import Image
    have_PIL = True
except ImportError:
    have_PIL = False


class ComposeImage(RGBImage.RGBImage, LayerImage.LayerImage):
    def __init__(self, *args, **kwdargs):
        RGBImage.RGBImage.__init__(self, *args, **kwdargs)
        LayerImage.LayerImage.__init__(self)

class Compose(GingaPlugin.LocalPlugin):
    """
    Usage:
    Start the Compose plugin from the Operation menu--the tab should
    show up under "Dialogs"

    - Press "New Image" to start composing a new RGB image.

    - drag your three constituent images that will make up the R, G and B
    planes to the main viewer window--drag them in the order R (red),
    G (green) and B (blue).

    In the plugin, the R, G and B iamges should show up as three slider
    controls in the Layers area of the plugin.

    You should now have a composite three color image in the Compose preview
    window.  Most likely the image does not have good cut levels set, so you
    may want to set cut levels on the image using any of the usual cut levels
    controls.

    - Play with the alpha levels of each layer using the sliders in the
    Compose plugin, when you release a slider the image should update.

    - When you see something you like you can save it to a file using the
    "Save As" button.
    """
    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Compose, self).__init__(fv, fitsimage)

        self.limage = None
        self.count = 0

        self.layertag = 'compose-canvas'

        self.dc = fv.getDrawClasses()
        canvas = self.dc.DrawingCanvas()
        canvas.set_callback('drag-drop', self.drop_file_cb)
        canvas.setSurface(self.fitsimage)
        self.canvas = canvas

        self.gui_up = False

    def build_gui(self, container):
        top = Widgets.VBox()
        top.set_border_width(4)

        vbox, sw, orientation = Widgets.get_oriented_box(container)
        vbox.set_border_width(4)
        vbox.set_spacing(2)

        self.msgFont = self.fv.getFont("sansFont", 12)
        tw = Widgets.TextArea(wrap=True, editable=False)
        tw.set_font(self.msgFont)
        self.tw = tw

        fr = Widgets.Expander("Instructions")
        fr.set_widget(tw)
        vbox.add_widget(fr, stretch=0)

        fr = Widgets.Frame("Compositing")

        captions = (("Compose Type:", 'label', "Compose Type", 'combobox'),
                    ("New Image", 'button', "Insert Layer", 'button'),
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
        #combobox.add_callback('activated', self.set_combine_cb)

        b.new_image.add_callback('activated', lambda w: self.new_cb())
        b.new_image.set_tooltip("Start a new composite image")
        b.insert_layer.add_callback('activated', lambda w: self.insert_cb())
        b.insert_layer.set_tooltip("Insert channel image as layer")

        fr = Widgets.Frame("Layers")
        self.w.scales = fr
        vbox.add_widget(fr, stretch=0)

        hbox = Widgets.HBox()
        hbox.set_border_width(4)
        hbox.set_spacing(4)
        btn = Widgets.Button("Save Image As")
        btn.add_callback('activated', lambda w: self.save_as_cb())
        hbox.add_widget(btn, stretch=0)
        self.entry2 = Widgets.TextEntry()
        hbox.add_widget(self.entry2, stretch=1)
        self.entry2.add_callback('activated', lambda *args: self.save_as_cb())

        vbox.add_widget(hbox, stretch=0)

        # spacer
        vbox.add_widget(Widgets.Label(''), stretch=1)

        top.add_widget(sw, stretch=1)

        btns = Widgets.HBox()
        btns.set_border_width(4)
        btns.set_spacing(4)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn)
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
            captions.append((layer.name+':', 'label', 'layer_%d' % i, 'hscale'))

        w, b = Widgets.build_info(captions)
        self.w.update(b)
        for i in range(num_layers):
            layer = self.limage.get_layer(i)
            adj = b['layer_%d' % (i)]
            lower, upper = 0, 100
            adj.set_limits(lower, upper, incr_value=1)
            #adj.set_decimals(2)
            adj.set_value(int(layer.alpha * 100.0))
            #adj.set_tracking(True)
            adj.add_callback('value-changed', self.set_opacity_cb, i)

        self.logger.debug("adding layer alpha controls")
        self.w.scales.set_widget(w)

    def new_cb(self):
        #self.fitsimage.clear()

        name = "composite%d" % (self.count)
        self.limage = ComposeImage(logger=self.logger, order='RGB')

        # Alpha or RGB composition?
        index = self.w.compose_type.get_index()
        if index == 0:
            self.limage.compose = 'alpha'
        else:
            self.limage.compose = 'rgb'
        self._gui_config_layers()
        self.limage.set(name=name, nothumb=True)

    def _get_layer_attributes(self):
        # Get layer name
        idx = self.limage.num_layers()
        if self.limage.compose == 'rgb':
            idx = min(idx, 2)
            names = ['Red', 'Green', 'Blue']
            name = names[idx]
        else:
            name = 'layer%d' % (idx)

        # Get alpha
        alpha = 1.0

        bnch = Bunch.Bunch(name=name, alpha=alpha, idx=idx)
        return bnch

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

        attrs = self._get_layer_attributes()
        self.limage.insert_layer(attrs.idx, image, name=attrs.name,
                                alpha=attrs.alpha)

        self._gui_config_layers()

        self.logger.debug("setting layer image")
        self.fitsimage.set_image(self.limage)

    def insert_cb(self):
        image = self.fitsimage.get_image()
        self.insert_image(image)

    def drop_file_cb(self, viewer, paths):
        self.logger.info("dropped files: %s" % str(paths))
        for path in paths[:3]:
            image = self.fv.load_image(path)
            self.insert_image(image)
        return True

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

    def add_to_channel_cb(self):
        image = self.limage.copy()
        name = "composite%d" % (self.count)
        self.count += 1
        image.set(name=name)
        self.fv.add_image(name, image)

    def save_as_file(self, path, image, order='RGB'):
        if not have_PIL:
            raise Exception("You need to install PIL or pillow to save images")

        data = image.get_data()
        viewer = self.fitsimage

        rgbmap = viewer.get_rgbmap()
        vmin, vmax = 0, rgbmap.get_hash_size() - 1

        # Cut levels on the full image, with settings from viewer
        autocuts = viewer.autocuts
        loval, hival = viewer.get_cut_levels()
        data = autocuts.cut_levels(data, loval, hival,
                                   vmin=vmin, vmax=vmax)

        # result becomes an index array fed to the RGB mapper
        if not numpy.issubdtype(data.dtype, numpy.dtype('uint')):
            data = data.astype(numpy.uint)

        # get RGB array using settings from viewer
        rgbobj = rgbmap.get_rgbarray(data, order=order,
                                     image_order='RGB')
        data = rgbobj.get_array(order)

        # Save image using PIL
        p_image = Image.fromarray(data)
        p_image.save(path)

    def save_as_cb(self):
        path = str(self.entry2.get_text()).strip()
        if not path.startswith('/'):
            path = os.path.join('.', path)

        image = self.fitsimage.get_image()
        self.fv.nongui_do(self.fv.error_wrap, self.save_as_file, path, image)

    def instructions(self):
        self.tw.set_text("""Drag R, then G then B images to the window. Adjust cut levels and contrast as desired.

Then manipulate channel mix using the sliders.""")

    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_local_plugin(chname, str(self))
        return True

    def start(self):
        self.instructions()
        # start ruler drawing operation
        p_canvas = self.fitsimage.get_canvas()
        try:
            obj = p_canvas.getObjectByTag(self.layertag)

        except KeyError:
            # Add ruler layer
            p_canvas.add(self.canvas, tag=self.layertag)

        self.resume()

    def pause(self):
        self.canvas.ui_setActive(False)

    def resume(self):
        self.canvas.ui_setActive(True)

    def stop(self):
        # remove the canvas from the image
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.deleteObjectByTag(self.layertag)
        except:
            pass
        self.canvas.ui_setActive(False)
        self.fv.showStatus("")
        self.gui_up = False

    def redo(self):
        pass

    def __str__(self):
        return 'compose'

#END
