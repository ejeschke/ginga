# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os.path

import numpy as np
from PIL import Image
from astropy.io import fits

from ginga.gw import Widgets
from ginga.util.paths import ginga_home
from ginga.util.action import AttrAction

from .base import Stage


class Output(Stage):

    _stagename = 'output'

    def __init__(self):
        super().__init__()

        self.fv = None
        self.in_image = None
        self._output_folder = '.'
        self._output_filetype = "PNG"
        self._auto_save = False
        self.output_types = ["FITS", "PNG", "JPEG"]
        self.convert_info = dict(FITS=dict(format="fits", ext=".fits"),
                                 PNG=dict(format="png", ext=".png"),
                                 JPEG=dict(format="jpeg", ext=".jpg"))

    def build_gui(self, container):
        self.fv = self.pipeline.get("fv")

        fr = Widgets.Frame("Output")

        captions = [('Output Folder:', 'label', 'output_folder', 'entryset'),
                    ('Output Filename:', 'label', 'output_filename', 'entry'),
                    ('Output Filetype:', 'label', 'output_filetype', 'combobox'),
                    ('Save', 'button', 'Auto Save', 'checkbox'),
                    ]
        w, b = Widgets.build_info(captions, orientation='vertical')
        self.w.update(b)

        b.output_folder.set_text(self._output_folder)
        b.output_folder.set_tooltip("Folder for pipeline output")
        b.output_folder.add_callback('activated', self.set_folder_cb)
        b.output_filename.set_text('')
        b.output_filename.set_tooltip("File for pipeline output")
        #b.output_filename.add_callback('activated', self.set_filename_cb)
        for name in self.output_types:
            b.output_filetype.append_text(name)
        idx = self.output_types.index(self._output_filetype)
        b.output_filetype.set_index(idx)
        b.output_filetype.add_callback('activated', self.set_filetype_cb)
        b.save.add_callback('activated', self.save_as_cb)
        b.auto_save.set_state(self._auto_save)
        b.auto_save.set_tooltip("Automatically save file when clicked")
        b.auto_save.add_callback('activated', self.autosave_cb)

        fr.set_widget(w)
        container.set_widget(fr)

    @property
    def output_folder(self):
        return self._output_folder

    @output_folder.setter
    def output_folder(self, val):
        self._output_folder = val
        if self.gui_up:
            self.w.output_folder.set_text(val)

    @property
    def output_filetype(self):
        return self._output_filetype

    @output_filetype.setter
    def output_filetype(self, val):
        self._output_filetype = val
        if self.gui_up:
            idx = self.output_types.index(self._output_filetype)
            self.w.output_filetype.set_index(idx)

    @property
    def auto_save(self):
        return self._auto_save

    @auto_save.setter
    def auto_save(self, val):
        self._auto_save = val
        if self.gui_up:
            self.w.auto_save.set_state(val)

    def set_folder_cb(self, widget):
        old = dict(output_folder=self._output_folder)
        folder = widget.get_text().strip()
        self.output_folder = folder
        new = dict(output_folder=self._output_folder)
        self.pipeline.push(AttrAction(self, old, new,
                                      descr="output / change output folder"))

    def set_filetype_cb(self, widget, idx):
        old = dict(output_filetype=self._output_filetype)
        self._output_filetype = widget.get_text()
        new = dict(output_filetype=self._output_filetype)
        self.pipeline.push(AttrAction(self, old, new,
                                      descr="output / change output filetype"))

    def autosave_cb(self, widget, tf):
        old = dict(auto_save=self._auto_save)
        self._auto_save = tf
        new = dict(auto_save=self._auto_save)
        self.pipeline.push(AttrAction(self, old, new,
                                      descr="output / change auto save"))

    def run(self, prev_stage):
        data = self.pipeline.get_data(prev_stage)

        self.verify_2d(data)

        if self._bypass or data is None:
            self.pipeline.send(res_np=data)
            return

        output_folder = self._output_folder
        if output_folder is None:
            output_folder = self.pipeline.get('input_folder', '.')
        if self.gui_up:
            self.w.output_folder.set_text(output_folder)

        filename = self.pipeline.get('input_filename', '')
        if len(filename) > 0:
            f_name, f_ext = os.path.splitext(filename)
            # TODO: paramaterize the mangled filename
            output_filename = f_name + '-pipe'
            if self.gui_up:
                self.w.output_filename.set_text(output_filename)

        if self._auto_save:
            self.save_as_cb(self.w.save)

        self.pipeline.send(res_np=data)

    def save_as_cb(self, widget):
        data = self.pipeline.get_data(self)

        dct = self.convert_info[self._output_filetype]
        path = os.path.join(self.w.output_folder.get_text().strip(),
                            self.w.output_filename.get_text().strip() +
                            dct['ext'])
        try:
            self._save_as(path, data, format=dct['format'])

        except Exception as e:
            self.logger.error("Error saving file '{}': {}".format(path, e),
                              exc_info=True)

    def _save_as(self, path, data, format='jpeg', quality=90):
        # get the color profile passed through the pipeline
        output_profile = self.pipeline.get('icc_output_profile', None)
        if output_profile is not None:
            profile_file = os.path.join(ginga_home, "profiles",
                                        output_profile + ".icc")
            with open(profile_file, 'rb') as in_f:
                profile = in_f.read()
        else:
            profile = None

        if format == 'jpeg':
            img = Image.fromarray(data[:, :, 0:3])
            img.save(path, format='jpeg', quality=quality,
                     icc_profile=profile)

        elif format == 'png':
            img = Image.fromarray(data)  # alpha layer OK for PNG
            img.save(path, format='png', quality=quality,
                     icc_profile=profile)

        elif format == 'fits':
            if data.dtype == np.dtype(np.uint8):
                # only if data is RGB--seems to be necessary for FITS
                data = np.moveaxis(data, 2, 0)
            hdu = fits.PrimaryHDU(data)
            # TODO: carry over metadata + some new metadata
            hdu_l = [hdu]
            if profile is not None:
                # save ICC profile as a secondary HDU
                hdu.header.set('HASPROF', True,
                               "Embedded ICC profile in other HDU")
                prof_hdu = fits.ImageHDU(np.frombuffer(profile,
                                                       dtype=np.uint8))
                prof_hdu.header.set('ICCPROF', output_profile,
                                    "Embedded ICC profile in this HDU")
                prof_hdu.name = 'ICCPROF'
                hdu_l.append(prof_hdu)
            img = fits.HDUList(hdu_l)
            img.writeto(path)

    def _get_state(self):
        return dict(output_folder=self._output_folder,
                    output_filetype=self._output_filetype,
                    auto_save=self._auto_save)

    def export_as_dict(self):
        d = super().export_as_dict()
        d.update(self._get_state())
        return d

    def import_from_dict(self, d):
        super().import_from_dict(d)
        self.output_folder = d['output_folder']
        self.output_filetype = d['output_filetype']
        self.auto_save = d['auto_save']
