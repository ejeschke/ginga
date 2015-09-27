from ginga import GingaPlugin
from ginga.misc import Widgets, Plot

import numpy as np


class LineProfile(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        super(LineProfile, self).__init__(fv, fitsimage)

        self.image = None
        self.layertag = 'lineprofile-canvas'
        self.raster_file = False
        self.pan2mark = False
        self.wd = None
        self.ht = None

        self.dc = self.fv.getDrawClasses()
        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(True)
        canvas.add_draw_mode('move', move=self.drag, up=self.update, down=self.btndown_cb)
        canvas.register_for_cursor_drawing(self.fitsimage)
        canvas.set_draw_mode('move')
        canvas.add_callback('motion', self.motion_cb)
        canvas.setSurface(self.fitsimage)
        self.canvas = canvas

        # For "marks" feature
        self.mark_radius = 10
        self.mark_style = 'cross'
        self.mark_color = 'purple'
        self.select_color = 'cyan'
        self.marks = ['None']
        self.mark_index = 0
        self.mark_selected = None
        self.tw = None
        self.mark_data_x = [None]
        self.mark_data_y = [None]

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
        vbox.add_widget(w, stretch=0)

        fr = Widgets.Frame("Axes controls")
        self.hbox_axes = Widgets.HBox()
        self.hbox_axes.set_border_width(4)
        self.hbox_axes.set_spacing(1)
        fr.set_widget(self.hbox_axes)

        vbox.add_widget(fr, stretch=0)
        self.build_axes()

        btns = Widgets.HBox()
        btns.set_border_width(4)
        btns.set_spacing(4)

        # control for selecting a mark
        cbox2 = Widgets.ComboBox()
        for tag in self.marks:
            cbox2.append_text(tag)
        if self.mark_selected is None:
            cbox2.set_index(0)
        else:
            cbox2.show_text(self.mark_selected)
        cbox2.add_callback('activated', self.mark_select_cb)
        self.w.marks = cbox2
        cbox2.set_tooltip("Select a mark")
        btns.add_widget(cbox2, stretch=0)

        btn1 = Widgets.CheckBox("Pan to mark")
        btn1.set_state(self.pan2mark)
        btn1.add_callback('activated', self.pan2mark_cb)
        btn1.set_tooltip("Pan follows selected mark")
        btns.add_widget(btn1)
        btns.add_widget(Widgets.Label(''), stretch=1)

        btn2 = Widgets.Button("Delete")
        self.del_btn = btn2
        btn2.add_callback('activated', lambda w: self.clear_mark_cb())
        btn2.set_tooltip("Delete selected mark")
        btn2.set_enabled(False)
        btns.add_widget(btn2, stretch=0)

        btn3 = Widgets.Button("Delete All")
        self.del_all_btn = btn3
        btn3.add_callback('activated', lambda w: self.clear_all())
        btn3.set_tooltip("Clear all marks")
        btn3.set_enabled(False)
        btns.add_widget(btn3, stretch=0)

        vbox2 = Widgets.VBox()
        vbox2.add_widget(btns, stretch=0)
        vbox2.add_widget(Widgets.Label(''), stretch=1)

        fr = Widgets.Frame("Mark controls")
        fr.set_widget(vbox2)
        vbox.add_widget(fr, stretch=1)

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

        # Clear plot if no axis is enabled
        if True not in self.axes_states:
            self.clear_plot()
        else:
            self.redraw_mark()

    def instructions(self):
        self.tw.set_text("""Select an axis and pick a point using the cursor. Left-click to mark position.
Use MultiDim to change step values of axes.""")

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
        if self.image is None:
            return
        self.wd, self.ht = self.image.get_size()

        try:
            curr_axis = self.axes_states
            self.build_axes()

            # Restore axis state
            children = self.hbox_axes.get_children()
            for p, val in enumerate(curr_axis):
                if val is True:
                    children[p-1].set_state(True)

            if len(self.marks) > 1:
                self.del_all_btn.set_enabled(True)
        except AttributeError:
            self.build_axes()

    def motion_cb(self, canvas, button, data_x, data_y):
        if self.mark_selected is None:
            if not 0 <= data_x < self.wd or not 0 <= data_y < self.ht:
                self.clear_plot()
            else:
                self._plot(data_x, data_y, mark=None)
        return False

    def _plot(self, data_x, data_y, mark=None):
        # Exclude points outside boundaries
        if not 0 <= data_x < self.wd or not 0 <= data_y < self.ht:
            self.clear_plot()
            return

        # Transpose array for easier slicing
        mddata = self.image.get_mddata().T
        naxes = mddata.ndim

        self.enabled_axes = [pos for pos, val in enumerate(self.axes_states) if val is True]

        if self.enabled_axes:
            axis_data = self.get_axis(self.enabled_axes[0])
            axes_slice = self._slice(naxes, data_x, data_y, mk=mark)

            self.clear_plot()
            self.plot.plot(axis_data, mddata[axes_slice])

    def _slice(self, naxes, data_x, data_y, mk):
        # Build N-dim slice
        axes_slice = [0] * naxes

        # For axes 1 and 2
        if mk is not None:
            axes_slice[0] = self.mark_data_x[mk]
            axes_slice[1] = self.mark_data_y[mk]
        else:
            axes_slice[0] = data_x
            axes_slice[1] = data_y

        # For axis > 3
        for i in xrange(2, naxes):
            axes_slice[i] = self.image.revnaxis[i-2] + 1

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

    def clear_plot(self):
        self.plot.clear()
        self.plot.fig.canvas.draw()

    ### MARK FEATURE LOGIC ###

    def btndown_cb(self, canvas, event, data_x, data_y, viewer):
        if self.image is None or self.mark_selected:
            return

        self.mark_data_x.append(data_x)
        self.mark_data_y.append(data_y)
        self.add_mark(data_x, data_y)

        self.del_btn.set_enabled(True)
        self.del_all_btn.set_enabled(True)
        return True

    def drag(self, canvas, event, data_x, data_y, viewer):
        tag = self.mark_selected
        if tag is None:
            return
        obj = self.canvas.getObjectByTag(tag)
        obj.move_to(data_x, data_y)

        canvas.redraw(whence=3)
        return True

    def update(self, canvas, event, data_x, data_y, viewer):
        tag = self.mark_selected
        if tag is None:
            return
        idx = int(tag.strip('mark'))
        obj = self.canvas.getObjectByTag(tag)
        obj.move_to(data_x, data_y)

        canvas.redraw(whence=3)

        self.mark_data_x[idx] = data_x
        self.mark_data_y[idx] = data_y

        self.redraw_mark()
        return True

    def add_mark(self, data_x, data_y, radius=None, color=None, style=None):
        if not radius:
            radius = self.mark_radius
        if not color:
            color = self.mark_color
        if not style:
            style = self.mark_style

        self.logger.debug("Setting mark at %d,%d" % (data_x, data_y))
        self.mark_index += 1
        tag = 'mark%d' % (self.mark_index)
        tag = self.canvas.add(self.dc.CompoundObject(
            self.dc.Point(data_x, data_y, self.mark_radius,
                          style=style, color=color,
                          linestyle='solid'),
            self.dc.Text(data_x + 10, data_y, "%d" % (self.mark_index),
                         color=color)),
                              tag=tag)
        self.marks.append(tag)
        self.w.marks.append_text(tag)
        self.select_mark(tag, pan=False)

    def select_mark(self, tag, pan=True):
        # deselect the current selected mark, if there is one
        if self.mark_selected is not None:
            try:
                obj = self.canvas.getObjectByTag(self.mark_selected)
                obj.setAttrAll(color=self.mark_color)
            except:
                # old object may have been deleted
                pass

        self.mark_selected = tag
        if tag is None:
            self.w.marks.show_text('None')
            self.canvas.redraw(whence=3)
            return

        self.w.marks.show_text(tag)
        obj = self.canvas.getObjectByTag(tag)
        obj.setAttrAll(color=self.select_color)
        if self.pan2mark and pan:
            self.fitsimage.panset_xy(obj.objects[0].x, obj.objects[0].y)
        self.canvas.redraw(whence=3)

        self.redraw_mark()

    def redraw_mark(self):
        if self.mark_selected is None:
            return
        idx = int(self.mark_selected.strip('mark'))
        self._plot(self.mark_data_x[idx], self.mark_data_y[idx], mark=idx)

    def mark_select_cb(self, w, index):
        tag = self.marks[index]
        if index == 0:
            tag = None
            self.clear_plot()
            self.del_btn.set_enabled(False)
        else:
            self.del_btn.set_enabled(True)

        self.select_mark(tag)

    def pan2mark_cb(self, w, val):
        self.pan2mark = val

    def clear_mark_cb(self):
        tag = self.mark_selected
        if tag is None:
            return
        idx = int(tag.strip('mark'))
        self.canvas.deleteObjectByTag(tag)
        self.w.marks.delete_alpha(tag)
        self.marks.remove(tag)
        self.w.marks.set_index(0)
        self.mark_selected = None

        self.clear_plot()

        self.mark_data_x[idx] = None
        self.mark_data_y[idx] = None
        self.del_btn.set_enabled(False)
        if len(self.marks) == 1:
            self.del_all_btn.set_enabled(False)

    def clear_all(self):
        self.canvas.deleteAllObjects()
        for name in self.marks:
            self.w.marks.delete_alpha(name)
        self.marks = ['None']
        self.w.marks.append_text('None')
        self.w.marks.set_index(0)
        self.mark_index = 0
        self.mark_selected = None
        self.mark_data_x = [None]
        self.mark_data_y = [None]

        self.clear_plot()

        self.del_btn.set_enabled(False)
        self.del_all_btn.set_enabled(False)

    def __str__(self):
        return 'lineprofile'
