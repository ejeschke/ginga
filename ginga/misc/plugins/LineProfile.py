from ginga import GingaPlugin
from ginga.misc import Widgets, Plot

import numpy as np

class LineProfile(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        super(LineProfile, self).__init__(fv, fitsimage)

        self.layertag = 'lineprofile-canvas'
        self.raster_file = False

        self.dc = self.fv.getDrawClasses()
        canvas = self.dc.DrawingCanvas()
        canvas.add_callback('motion', self.motion_cb)
        canvas.setSurface(self.fitsimage)
        self.canvas = canvas

        self.gui_up = False

    def build_gui(self, container):
        top = Widgets.VBox()
        top.set_border_width(4)

        vbox, sw, orientation = Widgets.get_oriented_box(container)
        vbox.set_margins(4, 4, 4, 4)
        vbox.set_spacing(2)

        self.msgFont = self.fv.getFont("sansFont", 12)
        tw = Widgets.TextArea(wrap=True, editable=False)
        tw.set_font(self.msgFont)
        self.tw = tw

        fr = Widgets.Expander("Instructions")
        vbox2 = Widgets.VBox()
        vbox2.add_widget(tw)
        vbox2.add_widget(Widgets.Label(''), stretch=1)
        fr.set_widget(vbox2)
        vbox.add_widget(fr, stretch=0)

        self.plot = Plot.Plot(self.logger, width=2, height=4, dpi=100)
        ax = self.plot.add_axis()
        ax.grid(False)

        w = Widgets.wrap(self.plot.get_widget())
        vbox.add_widget(w, stretch=1)

        fr = Widgets.Frame("Axes controls")
        self.hbox_axes = Widgets.HBox()
        self.hbox_axes.set_border_width(4)
        self.hbox_axes.set_spacing(1)
        fr.set_widget(self.hbox_axes)

        vbox.add_widget(fr, stretch=0)
        self.build_axes()

        # scroll bars will allow lots of content to be accessed
        top.add_widget(sw, stretch=1)

        # A button box that is always visible at the bottom
        btns = Widgets.HBox()
        btns.set_spacing(3)

        # Add a close button for the convenience of the user
        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        top.add_widget(btns, stretch=0)

        # Add our GUI to the container
        container.add_widget(top, stretch=1)
        self.gui_up = True

    def build_axes(self):
        self.hbox_axes.remove_all()
        image = self.fitsimage.get_image()
        if image is not None:
            self.axes_states = []
            # For easier mapping of indices with the axes
            self.axes_states.append(None)

            # Add Checkbox widgets
            for i in xrange(1, len(image.get_mddata().shape)+1):
                name = 'NAXIS%d' % i
                chkbox = Widgets.CheckBox(name)
                self.axes_states.append(False)
                self.hbox_axes.add_widget(chkbox)

                # Add callback
                self.axes_callback_handler(chkbox, i)

    def axes_callback_handler(self, chkbox, pos):
        chkbox.add_callback('activated', lambda w, tf: self.axis_toggle_cb(w, tf, pos))

    def axis_toggle_cb(self, w, tf, pos):
        # Deactivate other checkboxes
        children = self.hbox_axes.get_children()
        for p, val in enumerate(self.axes_states):
            if val is None:
                continue
            elif val is True:
                self.axes_states[p] = False
                children[p-1].set_state(False)

        self.axes_states[pos] = tf
        self.logger.info('Axes states : %s ' % self.axes_states)

    def instructions(self):
        self.tw.set_text("""Pick a point using the cursor""")

    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_local_plugin(chname, str(self))
        self.gui_up = False
        return True

    def start(self):
        self.instructions()

        # insert layer if it is not already
        try:
            obj = self.fitsimage.getObjectByTag(self.layertag)

        except KeyError:
            # Add canvas layer
            self.fitsimage.add(self.canvas, tag=self.layertag)

        self.resume()

    def pause(self):
        self.canvas.ui_setActive(False)

    def resume(self):
        self.canvas.ui_setActive(True)
        self.redo()

    def stop(self):
        self.canvas.ui_setActive(False)
        try:
            self.fitsimage.deleteObjectByTag(self.layertag)
        except:
            pass

    def redo(self):
        # Get image being shown
        self.image = self.fitsimage.get_image()

        try:
            curr_axis = self.axes_states
            self.build_axes()

            # Restore axis state
            children = self.hbox_axes.get_children()
            for p, val in enumerate(curr_axis):
                if val is True:
                    children[p-1].set_state(True)
        except AttributeError:
            self.build_axes()

    def motion_cb(self, canvas, button, data_x, data_y):
        if self.image is None:
            return

        self.xcoord = int(data_x)
        self.ycoord = int(data_y)

        # Exclude points outside boundaries
        wd, ht = self.image.get_size()
        if 0 <= self.xcoord < wd and 0 <= self.ycoord < ht:
            self._plot()
        else:
            self.plot.clear()
            self.plot.fig.canvas.draw()
        return False

    def _plot(self):
        # Transpose array for easier slicing
        mddata = self.image.get_mddata().T
        naxes = mddata.ndim

        self.enabled_axes = [pos for pos, val in enumerate(self.axes_states) if val is True]

        if self.enabled_axes:
            axis_data = self.get_axis(self.enabled_axes[0])
            axes_slice = self._slice(naxes)

            self.plot.clear()
            self.plot.plot(axis_data, mddata[axes_slice])

    def _slice(self, naxes):
        header = self.image.get_header()

        # Build N-dim slice
        axes_slice = [0] * naxes

        t_step = self.image.revnaxis[-1] + 1

        axes_slice[0] = self.xcoord
        axes_slice[1] = self.ycoord
        axes_slice[2] = t_step

        # Slice enabled axis
        for ea in self.enabled_axes:
            axes_slice[ea-1] = slice(None, None, None)

        return axes_slice

    def get_axis(self, i):
        try:
            header = self.image.get_header()
            axis = header.get('CRVAL%d' % i) + \
                   np.arange(0, header.get('NAXIS%d' % i), 1) * \
                   header.get('CDELT%d' % i)
            return axis
        except Exception as e:
            errmsg = "Error loading axis %d: %s" % (i, str(e))
            self.logger.error(errmsg)
            self.fv.error(errmsg)

    def __str__(self):
        return 'lineprofile'
