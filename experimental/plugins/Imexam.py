#
# Imexam.py -- Imexam plugin for Ginga reference viewer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys
import inspect
import traceback
import logging
from io import StringIO

from ginga import GingaPlugin
from ginga.gw import Widgets
from ginga.gw import Plot
from ginga.util import plots
from ginga.misc import Bunch

have_imexam = False
try:
    from imexam.imexamine import Imexamine
    have_imexam = True

except ImportError:
    pass


class Imexam(GingaPlugin.LocalPlugin):
    """
    This is an experimental Ginga plugin for the "imexam" package.
    To use it you will need to install the "imexam" package:

        https://github.com/spacetelescope/imexam

    To install this plugin:
      $ mkdir $HOME/.ginga/plugins
      $ cp Imexam.py $HOME/.ginga/plugins/.

    To use:
      $ ginga ... --plugins=Imexam

      Then from the "Operations" menu, choose "Imexam".

    KNOWN ISSUES:
    - You need ginga v2.6.0.dev

    - When a plot is created for the first time, it will force the
      focus away from the channel viewer.  This means that keystrokes
      will not be recognized in the viewer again until you give it the
      focus back (by say, clicking in the window)

    - It makes the most sense to use the plugin with the channels
      workspace in "MDI" mode, although it works fine in other
      configurations.

    - Closing the plot windows is only possible currently by making
      sure the window has the focus and then using the workspace toolbar
      "-" button to delete it.

    - If you close an active plot window, you will need to press the
      "Detach Plot" button before plotting will work again--it doesn't
      recognize that the window has been closed.

    """

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Imexam, self).__init__(fv, fitsimage)

        # get Imexam preferences
        prefs = self.fv.get_preferences()
        self.settings = prefs.createCategory('plugin_Imexam')
        self.settings.addDefaults(font='Courier', fontsize=12,
                                  plots_in_workspace=False)
        self.settings.load(onError='silent')

        self.layertag = 'imexam-canvas'
        self.imexam_active = False

        # this is our imexamine object
        self.imex = Imexamine()

        # capture the stdout logger from imexam
        self.log_capture_string = StringIO()
        self.stream_handler = logging.StreamHandler(self.log_capture_string)
        self.stream_handler.setLevel(logging.INFO)
        self.imex.log.addHandler(self.stream_handler)

        self.dc = fv.get_draw_classes()
        canvas = self.dc.DrawingCanvas()
        canvas.set_callback('key-press', self.key_press_cb)
        canvas.set_surface(self.fitsimage)
        canvas.register_for_cursor_drawing(self.fitsimage)
        canvas.enable_draw(False)
        canvas.name = 'Imexam-canvas'
        self.canvas = canvas

        self._plot = None
        self._plot_w = None
        self._plot_idx = 0
        self._plots_in_ws = self.settings.get('plots_in_workspace', False)
        self.w = Bunch.Bunch()

    def build_gui(self, container):
        if not have_imexam:
            raise Exception("Please install 'imexam' to use this plugin")

        top = Widgets.VBox()
        top.set_border_width(4)

        fontsize = self.settings.get('fontsize', 12)

        msg_font = self.fv.get_font('sans', fontsize)
        tw = Widgets.TextArea(wrap=False, editable=False)
        tw.set_font(msg_font)
        self.tw = tw

        fr = Widgets.Expander("Instructions")
        fr.set_widget(tw)
        top.add_widget(fr, stretch=0)

        fr = Widgets.Frame("Imexam output:")

        if not self._plots_in_ws:
            splitter = Widgets.Splitter(orientation='vertical')

            self.nb = Widgets.TabWidget()
            splitter.add_widget(self.nb)

        # this holds the messages returned from imexamine
        tw = Widgets.TextArea(wrap=False, editable=False)
        font = self.settings.get('font', 'Courier')
        fixed_font = self.fv.get_font(font, fontsize)
        tw.set_font(fixed_font)
        self.msg_res = tw

        if not self._plots_in_ws:
            splitter.add_widget(tw)
            fr.set_widget(splitter)
        else:
            fr.set_widget(tw)

        top.add_widget(fr, stretch=1)

        hbox = Widgets.HBox()
        btn = Widgets.Button('Detach Plot')
        btn.add_callback('activated', self.detach_plot_cb)
        btn.set_tooltip("Detach current plot and start a new one")
        hbox.add_widget(btn, stretch=0)
        btn = Widgets.Button('Clear Text')
        btn.add_callback('activated', self.clear_text_cb)
        btn.set_tooltip("Clear the imexam output")
        hbox.add_widget(btn, stretch=0)
        hbox.add_widget(Widgets.Label(''), stretch=1)
        top.add_widget(hbox, stretch=0)

        hbox = Widgets.HBox()
        lbl = Widgets.Label("Keys active:")
        hbox.add_widget(lbl)
        btn1 = Widgets.RadioButton("On")
        btn1.set_state(self.imexam_active)
        btn1.add_callback('activated', lambda w, val: self.set_active_cb(True, val))
        btn1.set_tooltip("Enable imexam keys")
        self.w.btn_on = btn1
        hbox.add_widget(btn1)

        btn2 = Widgets.RadioButton("Off", group=btn1)
        btn2.set_state(not self.imexam_active)
        btn2.add_callback('activated', lambda w, val: self.set_active_cb(False, val))
        btn2.set_tooltip("Disable imexam keys")
        self.w.btn_off = btn2
        hbox.add_widget(btn2)

        hbox.add_widget(Widgets.Label(''), stretch=1)
        top.add_widget(hbox, stretch=0)

        btns = Widgets.HBox()
        btns.set_spacing(3)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        top.add_widget(btns, stretch=0)

        self._plot = None
        self._plot_w = None
        self._plot_idx = 0
        self.make_new_figure()

        container.add_widget(top, stretch=1)

    def close(self):
        self.fv.stop_local_plugin(self.chname, str(self))
        return True

    def set_active(self, onoff, update_ui=False):
        self.imexam_active = onoff
        self.canvas.ui_setActive(onoff)

        if update_ui and 'btn_on' in self.w:
            if onoff:
                self.w.btn_on.set_state(True)
            else:
                self.w.btn_off.set_state(True)

        if onoff:
            msg = "Imexam keys are active"
        else:
            msg = "Imexam keys deactivated"

        self.fitsimage.onscreen_message(msg, delay=1.0)
        self.fv.show_status(msg)

    def set_active_cb(self, tf, onoff):
        if tf:
            self.set_active(onoff, update_ui=False)

    def detach_plot_cb(self, w):
        self._plot = None
        self._plot_w = None
        self.make_new_figure()

    def clear_text_cb(self, w):
        self.msg_res.clear()

    def instructions(self):
        lines = ["Key bindings:"]
        for key, tup in self.imex.imexam_option_funcs.items():
            func, descr = tup
            lines.append("  %s : %s" % (key, descr))

        text = '\n'.join(lines)
        self.tw.set_text(text)

    def start(self):
        self.instructions()
        p_canvas = self.fitsimage.get_canvas()
        if not p_canvas.has_object(self.canvas):
            p_canvas.add(self.canvas, tag=self.layertag)

        self.clear()
        self.resume()

    def pause(self):
        self.set_active(False, update_ui=True)

    def resume(self):
        self.set_active(True, update_ui=True)

    def stop(self):
        self.pause()

        # remove the canvas from the image
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.delete_object_by_tag(self.layertag)
        except Exception:
            pass
        self.fv.show_status("")

    def redo(self):
        pass

    def make_new_figure(self):
        chname = self.fv.get_channel_name(self.fitsimage)

        wd, ht = 400, 300
        self._plot_idx += 1
        self._plot = plots.Plot(logger=self.logger,
                                width=wd, height=ht)

        name = "%s: Fig %d" % (chname, self._plot_idx)
        group = 10

        pw = Plot.PlotWidget(self._plot)

        vbox = Widgets.VBox()
        vbox.add_widget(pw, stretch=1)
        hbox = Widgets.HBox()
        hbox.add_widget(Widgets.Label(''), stretch=1)
        btn = Widgets.Button('Close Plot')
        btn.add_callback('activated', lambda w: self.close_plot(name, vbox))
        hbox.add_widget(btn, stretch=0)
        vbox.add_widget(hbox, stretch=0)

        # vbox.resize(wd, ht)
        self._plot_w = vbox

        if self._plots_in_ws:
            ws = self.fv.get_current_workspace()
            tab = self.fv.ds.add_tab(ws.name, vbox, group, name, name,
                                     data=dict(plot=self._plot))
        else:
            self.nb.add_widget(vbox, name)

        # imexam should get a clean figure
        fig = self._plot.get_figure()
        fig.clf()

    def close_plot(self, name, child):
        if child == self._plot_w:
            self.make_new_figure()

        if not self._plots_in_ws:
            self.nb.remove(child)

        return True

    def imexam_cmd(self, canvas, keyname, data_x, data_y, func):
        if not self.imexam_active:
            return False
        self.logger.debug("imexam_cb")

        # keyname = event.key
        self.logger.debug("key pressed: %s" % (keyname))

        image = self.fitsimage.get_image()
        if image is None:
            return False

        # inspect func to see what kind of things we can pass in
        args, varargs, varkw, defaults = inspect.getargspec(func)

        kwargs = dict()

        if 'data' in args:
            # pass the data array
            data_np = image.get_data()
            kwargs['data'] = data_np

        if 'fig' in args:
            # Make a new figure if we don't have one
            if self._plot is None:
                self.make_new_figure()
            kwargs['fig'] = self._plot.get_figure()
        self.log_capture_string.seek(0)
        self.log_capture_string.truncate()
        self.msg_res.append_text("----\ncmd: '%s'\n" % keyname)
        try:
            func(data_x, data_y, **kwargs)
            self.msg_res.append_text(self.log_capture_string.getvalue(),
                                     autoscroll=True)
        except Exception as e:
            self.msg_res.append_text(self.log_capture_string.getvalue(),
                                     autoscroll=True)
            # get any partial output
            errmsg = ("Error calling imexam function: %s" % (
                str(e)))
            self.msg_res.append_text(errmsg)

            # show traceback
            try:
                (type, value, tb) = sys.exc_info()
                tb_str = "\n".join(traceback.format_tb(tb))
            except Exception as e:
                tb_str = "Traceback information unavailable."

            self.msg_res.append_text(tb_str, autoscroll=True)

        return True

    def key_press_cb(self, canvas, keyname):

        # some keys that we explicitly can't handle from imexamine
        if keyname == '2':
            self.detach_plot_cb(None)
            return True

        try:
            # lookup imexamine function
            func, descr = self.imex.imexam_option_funcs[keyname]

        except KeyError:
            # no key binding for this in imexam
            return False

        data_x, data_y = self.fitsimage.get_last_data_xy()
        return self.imexam_cmd(self.canvas, keyname, data_x, data_y, func)


    def clear(self):
        self.canvas.delete_all_objects()
        return False

    def __str__(self):
        return 'imexam'

# END
