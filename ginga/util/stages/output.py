# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os.path

from PIL import Image

from ginga.gw import Widgets
from ginga.util.paths import ginga_home

from .base import Stage

count = 0


class Output(Stage):

    _stagename = 'output'

    def __init__(self):
        super(Output, self).__init__()

        self.fv = None
        self.in_image = None
        self._chname = ""
        self._output_folder = None

    def build_gui(self, container):
        self.fv = self.pipeline.get("fv")

        fr = Widgets.Frame("Output")

        captions = [('Channel:', 'label', 'Channel', 'entryset'),
                    ('Output Folder:', 'label', 'output_folder', 'entryset'),
                    ('Output Filename:', 'label', 'output_filename', 'entry'),
                    ('Save', 'button'),
                    ]
        w, b = Widgets.build_info(captions, orientation='vertical')
        self.w.update(b)

        b.channel.set_tooltip("Channel for output images")
        b.channel.add_callback('activated', self.set_channel_cb)
        b.channel.set_text(self._chname)
        txt = self._output_folder
        if txt is None:
            txt = ''
        b.output_folder.set_text(txt)
        b.output_folder.set_tooltip("Folder for pipeline output")
        b.output_folder.add_callback('activated', self.set_folder_cb)
        b.output_filename.set_text('')
        b.output_filename.set_tooltip("File for pipeline output")
        #b.output_filename.add_callback('activated', self.set_filename_cb)
        b.save.add_callback('activated', self.save_as_cb)
        b.save.set_tooltip("Save file when clicked")

        fr.set_widget(w)
        container.set_widget(fr)

    @property
    def chname(self):
        return self._chname

    @chname.setter
    def chname(self, val):
        self._chname = val
        if self.gui_up:
            self.w.channel.set_text(val)

    @property
    def output_folder(self):
        return self._output_folder

    @output_folder.setter
    def output_folder(self, val):
        self._output_folder = val
        if self.gui_up:
            if val is None:
                val = ""
            self.w.output_folder.set_text(val)

    def set_channel_cb(self, widget):
        self._chname = widget.get_text().strip()
        # TODO: ask user to create channel if it doesn't exist?
        channel = self.fv.get_channel_on_demand(self.chname)

        self.pipeline.run_from(self)

    def set_folder_cb(self, widget):
        folder = widget.get_text().strip()
        self.output_folder = folder

        self.pipeline.run_from(self)

    def run(self, prev_stage):
        global count
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
            #output_filename = f_name + '-pipe' + f_ext
            output_filename = f_name + '-pipe' + '.png'
            if self.gui_up:
                self.w.output_filename.set_text(output_filename)

        if len(self.chname) > 0:
            self.pipeline.logger.info('pipeline output')
            channel = self.fv.get_channel_on_demand(self._chname)

            in_image = self.pipeline.get('input_image')
            if in_image is not self.in_image:
                self.in_image = in_image
                # <-- new image.  Make one of the same type as the input
                # TODO: this needs to be user-selectable
                # TODO: if this is a revisited image, should look
                # up the corresponding previously generated output
                # image, if there is one and load it as the output.
                self.image = in_image.__class__(logger=self.pipeline.logger)

                # copy the header from the input
                in_header = in_image.get_header()
                # TODO: massage header, maybe add some metadata from
                # pipeline?
                self.image.update_keywords(in_header)

                # assign an output image name
                # TODO: name a better output name, that is some kind
                # of modified name of the input image name
                self.image.set(name='P' + str(count))
                count += 1
                self.image.set_data(data)

                channel.add_image(self.image)

            else:
                if self.image is not None:
                    self.image.set_data(data)

            # data has changed so redraw image completely
            channel.fitsimage.redraw(whence=0)

        self.pipeline.send(res_np=data)

    def save_as_cb(self, widget):
        data = self.pipeline.get_data(self)

        path = os.path.join(self.w.output_folder.get_text().strip(),
                            self.w.output_filename.get_text().strip())
        self._save_as(path, data)

    def _save_as(self, path, data, format='jpeg', quality=90):
        # TEMP: need to get the color profile passed through the pipeline
        profile_file = os.path.join(ginga_home, "profiles", "AdobeRGB.icc")
        with open(profile_file, 'rb') as in_f:
            profile = in_f.read()

        img = Image.fromarray(data[:, :, 0:3])
        img.save(path, format=format, quality=quality,
                 icc_profile=profile)

    def get_image(self):
        return self.image

    def _get_state(self):
        return dict(chname=self._chname, output_folder=self._output_folder)

    def export_as_dict(self):
        d = super(Output, self).export_as_dict()
        d.update(self._get_state())
        return d

    def import_from_dict(self, d):
        super(Output, self).import_from_dict(d)
        self.chname = d['chname']
        self.output_folder = d['output_folder']
