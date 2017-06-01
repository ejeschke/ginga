#
# WCSAxes.py -- WCS axes overlay plugin for Ginga reference viewer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from __future__ import division

import numpy as np

from ginga import colors
from ginga.GingaPlugin import LocalPlugin
from ginga.gw import Widgets


class WCSAxes(LocalPlugin):
    """
    WCSAxes
    =======
    A plugin for generating WCS axes overlay in the loaded image.

    Plugin Type: Local
    ------------------
    WCSAxes is a local plugin, which means it is associated with a channel.
    An instance can be opened for each channel.

    Usage
    -----
    As long as image as a valid WCS, WCS axes will be displayed.
    Use plugin GUI or configuration file to customize axes display.

    """
    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(WCSAxes, self).__init__(fv, fitsimage)

        self.layertag = 'wcsaxes-canvas'
        self.colornames = colors.get_colors()
        self.linestyles = ['solid', 'dash']

        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_WCSAxes')
        self.settings.add_defaults(linecolor='cyan', alpha=1,
                                   linestyle='solid', linewidth=1,
                                   n_ra_lines=10, n_dec_lines=10,
                                   show_label=True, fontsize=8, label_offset=4)
        self.settings.load(onError='silent')

        linecolor = self.settings.get('linecolor', 'cyan')
        alpha = self.settings.get('alpha', 1)
        linestyle = self.settings.get('linestyle', 'solid')
        linewidth = self.settings.get('linewidth', 1)
        num_ra = self.settings.get('n_ra_lines', 10)
        num_dec = self.settings.get('n_dec_lines', 10)
        show_label = self.settings.get('show_label', True)
        fontsize = self.settings.get('fontsize', 8)
        txt_off = self.settings.get('label_offset', 4)

        self.dc = fv.get_draw_classes()

        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(False)
        canvas.set_surface(self.fitsimage)
        self.canvas = canvas

        self.axes = self.dc.WCSAxes(
            linewidth=linewidth, linestyle=linestyle, color=linecolor,
            alpha=alpha, fontsize=fontsize)
        self.axes.num_ra = num_ra
        self.axes.num_dec = num_dec
        self.axes.show_label = show_label
        self.axes.txt_off = txt_off
        self.canvas.add(self.axes)

        self.gui_up = False

    def build_gui(self, container):
        top = Widgets.VBox()
        top.set_border_width(4)

        vbox, sw, orientation = Widgets.get_oriented_box(container)
        vbox.set_border_width(4)
        vbox.set_spacing(2)

        fr = Widgets.Frame('General')
        captions = (('Line color:', 'label', 'Line colors', 'combobox'),
                    ('Alpha:', 'label', 'Alpha', 'entryset'))
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        combobox = b.line_colors
        for name in self.colornames:
            combobox.append_text(name)
        combobox.set_index(self.colornames.index(self.axes.color))
        combobox.add_callback('activated', self.set_linecolor_cb)

        b.alpha.set_text(str(self.axes.alpha))
        b.alpha.set_tooltip('Line transparency (alpha)')
        b.alpha.add_callback('activated', lambda *args: self.set_alpha())

        fr.set_widget(w)
        vbox.add_widget(fr, stretch=0)

        fr = Widgets.Frame('Lines')
        captions = (('Line style:', 'label', 'Line styles', 'combobox'),
                    ('# RA lines:', 'label', 'Num RA', 'entryset'),
                    ('# DEC lines:', 'label', 'Num DEC', 'entryset'))
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        combobox = b.line_styles
        for name in self.linestyles:
            combobox.append_text(name)
        combobox.set_index(self.linestyles.index(self.axes.linestyle))
        combobox.add_callback('activated', self.set_linestyle_cb)

        b.num_ra.set_text(str(self.axes.num_ra))
        b.num_ra.set_tooltip('Number of lines drawn for RA')
        b.num_ra.add_callback('activated', lambda *args: self.set_num_ra())

        b.num_dec.set_text(str(self.axes.num_dec))
        b.num_dec.set_tooltip('Number of lines drawn for DEC')
        b.num_dec.add_callback('activated', lambda *args: self.set_num_dec())

        fr.set_widget(w)
        vbox.add_widget(fr, stretch=0)

        fr = Widgets.Frame('Labels')
        captions = (('Show label', 'checkbutton'),
                    ('Font size:', 'label', 'Font size', 'entryset'),
                    ('Text offset:', 'label', 'Text offset', 'entryset'),
                    ('RA angle:', 'label', 'RA angle', 'entryset'),
                    ('DEC angle:', 'label', 'DEC angle', 'entryset'))
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        b.show_label.set_state(self.axes.show_label)
        b.show_label.set_tooltip('Show/hide label')
        b.show_label.add_callback('activated', self.toggle_label_cb)

        b.font_size.set_text(str(self.axes.fontsize))
        b.font_size.set_tooltip('Labels font size')
        b.font_size.add_callback(
            'activated', lambda *args: self.set_fontsize())

        b.text_offset.set_text(str(self.axes.txt_off))
        b.text_offset.set_tooltip('Labels text offset in pixels')
        b.text_offset.add_callback(
            'activated', lambda *args: self.set_txt_off())

        b.ra_angle.set_text(str(self.axes.ra_angle))
        b.ra_angle.set_tooltip('Orientation in deg of RA labels')
        b.ra_angle.add_callback('activated', lambda *args: self.set_ra_angle())

        b.dec_angle.set_text(str(self.axes.dec_angle))
        b.dec_angle.set_tooltip('Orientation in deg of DEC labels')
        b.dec_angle.add_callback(
            'activated', lambda *args: self.set_dec_angle())

        fr.set_widget(w)
        vbox.add_widget(fr, stretch=0)

        top.add_widget(sw, stretch=1)

        btns = Widgets.HBox()
        btns.set_spacing(3)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=0)
        btn = Widgets.Button("Help")
        btn.add_callback('activated', lambda w: self.help())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        top.add_widget(btns, stretch=0)

        container.add_widget(top, stretch=1)

        self.gui_up = True

    def redo(self):
        if not self.gui_up:
            return

        # Need this here so GUI accurately updates values from drawing.
        self.w.ra_angle.set_text(str(self.axes.ra_angle))
        self.w.dec_angle.set_text(str(self.axes.dec_angle))

    def set_linecolor_cb(self, w, index):
        self.axes.color = self.colornames[index]
        self.axes.sync_state()
        self.canvas.update_canvas()
        return True

    def set_alpha(self):
        try:
            a = float(self.w.alpha.get_text())
            if (a < 0) or (a > 1):
                raise ValueError
        except ValueError:
            self.w.alpha.set_text(str(self.axes.alpha))
        else:
            self.axes.alpha = a
            self.axes.sync_state()
            self.canvas.update_canvas()
        return True

    def set_linestyle_cb(self, w, index):
        self.axes.linestyle = self.linestyles[index]
        self.axes.sync_state()
        self.canvas.update_canvas()
        return True

    def set_num_ra(self):
        try:
            n = int(self.w.num_ra.get_text())
            if n < 1 or n > 50:
                raise ValueError
        except ValueError:
            self.w.num_ra.set_text(str(self.axes.num_ra))
        else:
            self.axes.num_ra = n
            self.axes._cur_image = None  # Force redraw
            self.canvas.update_canvas()
        return True

    def set_num_dec(self):
        try:
            n = int(self.w.num_dec.get_text())
            if n < 1 or n > 50:
                raise ValueError
        except ValueError:
            self.w.num_dec.set_text(str(self.axes.num_dec))
        else:
            self.axes.num_dec = n
            self.axes._cur_image = None  # Force redraw
            self.canvas.update_canvas()
        return True

    def toggle_label_cb(self, w, val):
        self.axes.show_label = val

        # Toggling label off and switch image causes axes not to have labels
        # at all, which causes toggling it back on to not work without complete
        # rebuild.
        if (val and not np.any([obj.kind == 'text'
                                for obj in self.axes.objects])):
            self.axes._cur_image = None  # Force redraw
        else:
            self.axes.sync_state()

        self.canvas.update_canvas()

    def set_fontsize(self):
        try:
            val = int(self.w.font_size.get_text())
            if val < 8 or val > 72:
                raise ValueError
        except ValueError:
            self.w.font_size.set_text(str(self.axes.fontsize))
        else:
            self.axes.fontsize = val
            self.axes.sync_state()
            self.canvas.update_canvas()
        return True

    def set_txt_off(self):
        try:
            val = int(self.w.text_offset.get_text())
            if abs(val) > 50:  # No point putting the label so far away
                raise ValueError
        except ValueError:
            self.w.text_offset.set_text(str(self.axes.txt_off))
        else:
            self.axes.txt_off = val
            self.axes._cur_image = None  # Force redraw
            self.canvas.update_canvas()
        return True

    def set_ra_angle(self):
        s = self.w.ra_angle.get_text()
        if s.lower() == 'none':
            a = None
        else:
            try:
                a = float(s)
            except ValueError:
                self.w.ra_angle.set_text(str(self.axes.ra_angle))
                return

        self.axes.ra_angle = a
        self.axes.sync_state()
        self.canvas.update_canvas()
        return True

    def set_dec_angle(self):
        s = self.w.dec_angle.get_text()
        if s.lower() == 'none':
            a = None
        else:
            try:
                a = float(s)
            except ValueError:
                self.w.dec_angle.set_text(str(self.axes.dec_angle))
                return

        self.axes.dec_angle = a
        self.axes.sync_state()
        self.canvas.update_canvas()
        return True

    def close(self):
        self.fv.stop_local_plugin(self.chname, str(self))
        return True

    def start(self):
        # insert canvas, if not already
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.get_object_by_tag(self.layertag)
        except KeyError:
            # Add ruler layer
            p_canvas.add(self.canvas, tag=self.layertag)

        self.resume()

    def stop(self):
        # so we don't hang on to a large image
        self.axes._cur_image = None

        # remove the canvas from the image
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.delete_object_by_tag(self.layertag)
        except:
            pass

        self.gui_up = False
        self.fv.show_status("")

    def __str__(self):
        return 'wcsaxes'

# END
