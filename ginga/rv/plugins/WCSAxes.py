#
# WCSAxes.py -- WCS axes overlay plugin for Ginga reference viewer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from __future__ import division

import math

import numpy as np

from ginga import colors
from ginga.AstroImage import AstroImage
from ginga.GingaPlugin import LocalPlugin
from ginga.gw import Widgets
from ginga.util.wcs import raDegToString, decDegToString
from ginga.util.wcsmod import AstropyWCS


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
        image = self.fitsimage.get_image()
        if not isinstance(image, AstroImage) or not image.has_valid_wcs():
            return True

        # TODO: Support all WCS packages?
        if not isinstance(image.wcs, AstropyWCS):
            return True

        try:
            obj = self.canvas.get_object_by_tag(self.overlaytag)
        except Exception:
            pass
        else:
            if obj.kind != 'compound':
                return True
        try:
            self.canvas.delete_object_by_tag(self.overlaytag)
        except Exception:
            pass

        # TODO: Support data cube
        # Approximate bounding box in RA/DEC space
        xmax = image.width - 1
        ymax = image.height - 1
        radec = image.wcs.wcs.all_pix2world(
            [[0, 0], [0, ymax], [xmax, 0], [xmax, ymax]], 0)
        ra_min, dec_min = radec.min(axis=0)
        ra_max, dec_max = radec.max(axis=0)
        ra_size = ra_max - ra_min
        dec_size = dec_max - dec_min

        # Calculate positions of RA/DEC lines
        d_ra = ra_size / (self.num_ra + 1)
        d_dec = dec_size / (self.num_dec + 1)
        ra_arr = np.arange(ra_min + d_ra, ra_max - d_ra * 0.5, d_ra)
        dec_arr = np.arange(dec_min + d_dec, dec_max - d_ra * 0.5, d_dec)

        # RA/DEC step size for each vector
        min_imsize = min(image.width, image.height)
        d_ra_step = ra_size * self._pix_res / min_imsize
        d_dec_step = dec_size * self._pix_res / min_imsize

        # Create Path objects
        objs = []

        for cur_ra in ra_arr:
            crds = [[cur_ra, cur_dec] for cur_dec in
                    np.arange(dec_min, dec_max + d_dec_step, d_dec_step)]
            lbl = raDegToString(cur_ra)
            objs += self._get_path(image, crds, lbl, self.ra_angle)
        for cur_dec in dec_arr:
            crds = [[cur_ra, cur_dec] for cur_ra in
                    np.arange(ra_min, ra_max + d_ra_step, d_ra_step)]
            lbl = decDegToString(cur_dec)
            objs += self._get_path(image, crds, lbl, self.dec_angle)

        self.overlaytag = self.canvas.add(self.dc.CompoundObject(*objs))
        self.canvas.redraw(whence=3)

    def _get_path(self, image, crds, lbl, rot):
        pts = image.wcs.wcs.all_world2pix(crds, 0)

        # Don't draw outside image area
        mask = ((pts[:, 0] >= 0) & (pts[:, 0] < image.width) &
                (pts[:, 1] >= 0) & (pts[:, 1] < image.height))
        pts = pts[mask]

        path_obj = self.dc.Path(
            points=pts, coords='data', linewidth=self.linewidth,
            linestyle=self.linestyle, color=self.linecolor,
            alpha=self.alpha)

        if self.show_label:
            # Calculate label orientation
            if rot is None:
                x1, y1 = pts[0]
                x2, y2 = pts[-1]
                try:
                    rot = math.asin((y2 - y1) / (x2 - x1)) * 180 / math.pi
                except ValueError:
                    rot = 90

            text_obj = self.dc.Text(
                4, 4, lbl, fontsize=self.fontsize, color=self.linecolor,
                alpha=self.alpha, rot_deg=rot, coord='offset',
                ref_obj=path_obj)
            return [path_obj, text_obj]
        else:
            return [path_obj]

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
