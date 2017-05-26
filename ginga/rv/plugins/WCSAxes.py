#
# WCSAxes.py -- WCS axes overlay plugin for Ginga reference viewer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from __future__ import division

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
        self.overlaytag = None

        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_WCSAxes')
        self.settings.add_defaults(linecolor='cyan', alpha=1,
                                   linestyle='solid', linewidth=1,
                                   n_ra_lines=10, n_dec_lines=10,
                                   show_label=True, fontsize=8,
                                   ra_angle=None, dec_angle=None)
        self.settings.load(onError='silent')

        self.colornames = colors.get_colors()
        self.linestyles = ['solid', 'dash']
        self.linecolor = self.settings.get('linecolor', 'cyan')
        self.alpha = self.settings.get('alpha', 1)
        self.linestyle = self.settings.get('linestyle', 'solid')
        self.linewidth = self.settings.get('linewidth', 1)
        self.num_ra = self.settings.get('n_ra_lines', 10)
        self.num_dec = self.settings.get('n_dec_lines', 10)
        self.show_label = self.settings.get('show_label', True)
        self.fontsize = self.settings.get('fontsize', 8)
        self.ra_angle = self.settings.get('ra_angle', None)
        self.dec_angle = self.settings.get('dec_angle', None)
        self._pix_res = 10

        self.dc = fv.get_draw_classes()

        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(False)
        canvas.set_surface(self.fitsimage)
        self.canvas = canvas

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
        combobox.set_index(self.colornames.index(self.linecolor))
        combobox.add_callback('activated', self.set_linecolor_cb)

        b.alpha.set_text(str(self.alpha))
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
        combobox.set_index(self.linestyles.index(self.linestyle))
        combobox.add_callback('activated', self.set_linestyle_cb)

        b.num_ra.set_text(str(self.num_ra))
        b.num_ra.set_tooltip('Number of lines drawn for RA')
        b.num_ra.add_callback('activated', lambda *args: self.set_num_ra())

        b.num_dec.set_text(str(self.num_dec))
        b.num_dec.set_tooltip('Number of lines drawn for DEC')
        b.num_dec.add_callback('activated', lambda *args: self.set_num_dec())

        fr.set_widget(w)
        vbox.add_widget(fr, stretch=0)

        fr = Widgets.Frame('Labels')
        captions = (('Show label', 'checkbutton'),
                    ('Font size:', 'label', 'Font size', 'entryset'),
                    ('RA angle:', 'label', 'RA angle', 'entryset'),
                    ('DEC angle:', 'label', 'DEC angle', 'entryset'))
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        b.show_label.set_state(self.show_label)
        b.show_label.set_tooltip('Show/hide label')
        b.show_label.add_callback('activated', self.toggle_label_cb)

        b.font_size.set_text(str(self.fontsize))
        b.font_size.set_tooltip('Labels font size')
        b.font_size.add_callback(
            'activated', lambda *args: self.set_fontsize())

        b.ra_angle.set_text(str(self.ra_angle))
        b.ra_angle.set_tooltip('Orientation in deg of RA labels')
        b.ra_angle.add_callback('activated', lambda *args: self.set_ra_angle())

        b.dec_angle.set_text(str(self.dec_angle))
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
        self.redo()

    def redo(self):
        try:
            obj = self.canvas.get_object_by_tag(self.overlaytag)
        except Exception:
            pass
        else:
            if obj.kind != 'wcsaxes':
                return True
        try:
            self.canvas.delete_object_by_tag(self.overlaytag)
        except Exception:
            pass

        # dc.WCSAxes will pick up image under the hood.
        # UNTIL HERE - what about other params to adjust?
        obj = self.dc.WCSAxes(
            linewidth=self.linewidth, linestyle=self.linestyle,
            color=self.linecolor, alpha=self.alpha, fontsize=self.fontsize)
        self.overlaytag = self.canvas.add(obj)
        self.canvas.redraw(whence=3)

    def set_linecolor_cb(self, w, index):
        self.linecolor = self.colornames[index]
        self.redo()
        return True

    def set_alpha(self):
        try:
            a = float(self.w.alpha.get_text())
        except ValueError:
            self.w.alpha.set_text(str(self.alpha))
        else:
            self.alpha = a
            self.redo()
        return True

    def set_linestyle_cb(self, w, index):
        self.linestyle = self.linestyles[index]
        self.redo()
        return True

    def set_num_ra(self):
        try:
            n = int(self.w.num_ra.get_text())
        except ValueError:
            self.w.num_ra.set_text(str(self.num_ra))
        else:
            self.num_ra = n
            self.redo()
        return True

    def set_num_dec(self):
        try:
            n = int(self.w.num_dec.get_text())
        except ValueError:
            self.w.num_dec.set_text(str(self.num_dec))
        else:
            self.num_dec = n
            self.redo()
        return True

    def toggle_label_cb(self, w, val):
        self.show_label = val
        self.redo()

    def set_fontsize(self):
        try:
            val = float(self.w.font_size.get_text())
        except ValueError:
            self.w.font_size.set_text(str(self.fontsize))
        else:
            self.fontsize = val
            self.redo()
        return True

    def set_ra_angle(self):
        try:
            a = float(self.w.ra_angle.get_text())
        except ValueError:
            self.ra_angle = None
            self.w.ra_angle.set_text(str(self.ra_angle))
        else:
            self.ra_angle = a
        self.redo()
        return True

    def set_dec_angle(self):
        try:
            a = float(self.w.dec_angle.get_text())
        except ValueError:
            self.dec_angle = None
            self.w.dec_angle.set_text(str(self.dec_angle))
        else:
            self.dec_angle = a
        self.redo()
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

    def pause(self):
        self.canvas.ui_set_active(False)

    def resume(self):
        # turn off any mode user may be in
        self.modes_off()

        self.canvas.ui_set_active(True)
        self.fv.show_status("Overlaying WCS axes if available")

    def stop(self):
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
