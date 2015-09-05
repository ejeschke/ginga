#
# Pipeline.py -- Simple data reduction pipeline plugin for Ginga FITS viewer
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from __future__ import print_function
import numpy

from ginga import AstroImage
from ginga.util import dp
from ginga import GingaPlugin
from ginga.gw import Widgets


class Pipeline(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Pipeline, self).__init__(fv, fitsimage)

        # Load preferences
        prefs = self.fv.get_preferences()
        self.settings = prefs.createCategory('plugin_Pipeline')
        self.settings.setDefaults(num_threads=4)
        self.settings.load(onError='silent')

        # For building up an image stack
        self.imglist = []

        # For applying flat fielding
        self.flat  = None
        # For subtracting bias
        self.bias  = None

        self.gui_up = False


    def build_gui(self, container):
        top = Widgets.VBox()
        top.set_border_width(4)

        vbox1, sw, orientation = Widgets.get_oriented_box(container)
        vbox1.set_border_width(4)
        vbox1.set_spacing(2)

        self.msgFont = self.fv.getFont("sansFont", 12)
        tw = Widgets.TextArea(wrap=True, editable=False)
        tw.set_font(self.msgFont)
        self.tw = tw

        fr = Widgets.Frame("Instructions")
        fr.set_widget(tw)
        vbox1.add_widget(fr, stretch=0)

        # Main pipeline control area
        captions = [
            ("Subtract Bias", 'button', "Bias Image:", 'label',
             'bias_image', 'llabel'),
            ("Apply Flat Field", 'button', "Flat Image:", 'label',
             'flat_image', 'llabel'),
            ]
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        fr = Widgets.Frame("Pipeline")
        fr.set_widget(w)
        vbox1.add_widget(fr, stretch=0)

        b.subtract_bias.add_callback('activated', self.subtract_bias_cb)
        b.subtract_bias.set_tooltip("Subtract a bias image")
        bias_name = 'None'
        if self.bias is not None:
            bias_name = self.bias.get('name', "NoName")
        b.bias_image.set_text(bias_name)

        b.apply_flat_field.add_callback('activated', self.apply_flat_cb)
        b.apply_flat_field.set_tooltip("Apply a flat field correction")
        flat_name = 'None'
        if self.flat is not None:
            flat_name = self.flat.get('name', "NoName")
        b.flat_image.set_text(flat_name)

        vbox2 = Widgets.VBox()
        # Pipeline status
        hbox = Widgets.HBox()
        hbox.set_spacing(4)
        hbox.set_border_width(4)
        label = Widgets.Label()
        self.w.eval_status = label
        hbox.add_widget(self.w.eval_status, stretch=0)
        hbox.add_widget(Widgets.Label(''), stretch=1)
        vbox2.add_widget(hbox, stretch=0)

        # progress bar and stop button
        hbox = Widgets.HBox()
        hbox.set_spacing(4)
        hbox.set_border_width(4)
        btn = Widgets.Button("Stop")
        btn.add_callback('activated', lambda w: self.eval_intr())
        btn.set_enabled(False)
        self.w.btn_intr_eval = btn
        hbox.add_widget(btn, stretch=0)

        self.w.eval_pgs = Widgets.ProgressBar()
        hbox.add_widget(self.w.eval_pgs, stretch=1)
        vbox2.add_widget(hbox, stretch=0)
        vbox2.add_widget(Widgets.Label(''), stretch=1)
        vbox1.add_widget(vbox2, stretch=0)

        # Image list
        captions = [
            ("Append", 'button', "Prepend", 'button', "Clear", 'button'),
            ]
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        fr = Widgets.Frame("Image Stack")

        vbox = Widgets.VBox()
        hbox = Widgets.HBox()
        self.w.stack = Widgets.Label('')
        hbox.add_widget(self.w.stack, stretch=0)
        vbox.add_widget(hbox, stretch=0)
        vbox.add_widget(w, stretch=0)
        fr.set_widget(vbox)
        vbox1.add_widget(fr, stretch=0)

        self.update_stack_gui()

        b.append.add_callback('activated', self.append_image_cb)
        b.append.set_tooltip("Append an individual image to the stack")
        b.prepend.add_callback('activated', self.prepend_image_cb)
        b.prepend.set_tooltip("Prepend an individual image to the stack")
        b.clear.add_callback('activated', self.clear_stack_cb)
        b.clear.set_tooltip("Clear the stack of images")

        # Bias
        captions = [
            ("Make Bias", 'button', "Set Bias", 'button'),
            ]
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        fr = Widgets.Frame("Bias Subtraction")
        fr.set_widget(w)
        vbox1.add_widget(fr, stretch=0)

        b.make_bias.add_callback('activated', self.make_bias_cb)
        b.make_bias.set_tooltip("Makes a bias image from a stack of individual images")
        b.set_bias.add_callback('activated', self.set_bias_cb)
        b.set_bias.set_tooltip("Set the currently loaded image as the bias image")

        # Flat fielding
        captions = [
            ("Make Flat Field", 'button', "Set Flat Field", 'button'),
            ]
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        fr = Widgets.Frame("Flat Fielding")
        fr.set_widget(w)
        vbox1.add_widget(fr, stretch=0)

        b.make_flat_field.add_callback('activated', self.make_flat_cb)
        b.make_flat_field.set_tooltip("Makes a flat field from a stack of individual flats")
        b.set_flat_field.add_callback('activated', self.set_flat_cb)
        b.set_flat_field.set_tooltip("Set the currently loaded image as the flat field")

        spacer = Widgets.Label('')
        vbox1.add_widget(spacer, stretch=1)

        top.add_widget(sw, stretch=1)

        btns = Widgets.HBox()
        btns.set_spacing(3)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        top.add_widget(btns, stretch=0)

        container.add_widget(top, stretch=1)
        self.gui_up = True


    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_local_plugin(chname, str(self))
        self.gui_up = False
        return True

    def instructions(self):
        self.tw.set_text("""TBD.""")

    def start(self):
        self.instructions()

    def stop(self):
        self.fv.showStatus("")

    def update_status(self, text):
        self.fv.gui_do(self.w.eval_status.set_text, text)

    def update_stack_gui(self):
        stack = [ image.get('name', "NoName") for image in self.imglist ]
        self.w.stack.set_text(str(stack))

    def append_image_cb(self, w):
        image = self.fitsimage.get_image()
        self.imglist.append(image)
        self.update_stack_gui()
        self.update_status("Appended image #%d to stack." % (len(self.imglist)))

    def prepend_image_cb(self, w):
        image = self.fitsimage.get_image()
        self.imglist.insert(0, image)
        self.update_stack_gui()
        self.update_status("Prepended image #%d to stack." % (len(self.imglist)))

    def clear_stack_cb(self, w):
        self.imglist = []
        self.update_stack_gui()
        self.update_status("Cleared image stack.")

    def show_result(self, image):
        chname = self.fv.get_channelName(self.fitsimage)
        name = dp.get_image_name(image)
        self.imglist.insert(0, image)
        self.update_stack_gui()
        self.fv.add_image(name, image, chname=chname)

    # BIAS

    def _make_bias(self):
        image = dp.make_bias(self.imglist)
        self.imglist = []
        self.fv.gui_do(self.show_result, image)
        self.update_status("Made bias image.")

    def make_bias_cb(self, w):
        self.update_status("Making bias image...")
        self.fv.nongui_do(self.fv.error_wrap, self._make_bias)

    def subtract_bias_cb(self, w):
        image = self.fitsimage.get_image()
        if self.bias is None:
            self.fv.show_error("Please set a bias image first")
        else:
            result = self.fv.error_wrap(dp.subtract, image, self.bias)
            self.fv.gui_do(self.show_result, result)

    def set_bias_cb(self, w):
        # Current image is a bias image we should set
        self.bias = self.fitsimage.get_image()
        biasname = dp.get_image_name(self.bias, pfx='bias')
        self.w.bias_image.set_text(biasname)
        self.update_status("Set bias image.")

    # FLAT FIELDING

    def _make_flat_field(self):
        result = dp.make_flat(self.imglist)
        self.imglist = []
        self.show_result(result)
        self.update_status("Made flat field.")

    def make_flat_cb(self, w):
        self.update_status("Making flat field...")
        self.fv.nongui_do(self.fv.error_wrap, self._make_flat_field)

    def apply_flat_cb(self, w):
        image = self.fitsimage.get_image()
        if self.flat is None:
            self.fv.show_error("Please set a flat field image first")
        else:
            result = self.fv.error_wrap(dp.divide, image, self.flat)
            print(result, image)
            self.fv.gui_do(self.show_result, result)

    def set_flat_cb(self, w):
        # Current image is a flat field we should set
        self.flat = self.fitsimage.get_image()
        flatname = dp.get_image_name(self.flat, pfx='flat')
        self.w.flat_image.set_text(flatname)
        self.update_status("Set flat field.")

    def __str__(self):
        return 'pipeline'


#END
