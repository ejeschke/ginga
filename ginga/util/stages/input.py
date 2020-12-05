# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os.path

from ginga.util import loader
from ginga.gw import Widgets

from .base import Stage, StageError


class Input(Stage):

    _stagename = 'input'

    def __init__(self):
        super(Input, self).__init__()

        self.image = None
        self._path = ""

    def build_gui(self, container):
        fr = Widgets.Frame("Input")

        vbox = Widgets.VBox()
        self.w.lbl = Widgets.TextEntrySet('', editable=True)
        self.w.lbl.set_text(self._path)
        self.w.lbl.set_tooltip("Enter a path to load the data")
        vbox.add_widget(self.w.lbl, stretch=0)
        self.w.lbl.add_callback('activated', self.set_path_cb)

        fr.set_widget(vbox)
        container.set_widget(fr)

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, val):
        self._path = val
        if self.gui_up:
            self.w.lbl.set_text(val)

    def _set_image(self, image):
        self.image = image
        self.path = image.get('path', "")
        _dir, _fn = None, None
        if len(self._path) > 0:
            _dir, _fn = os.path.split(self._path)
        self.pipeline.set(input_image=image,
                          input_folder=_dir, input_filename=_fn)

    def set_image(self, image):
        self._set_image(image)
        self.pipeline.run_from(self)

    def _set_path(self, path):
        image = loader.load_data(path, logger=self.logger)
        self._set_image(image)

    def set_path_cb(self, widget):
        path = widget.get_text().strip()
        self._set_path(path)
        self.pipeline.run_from(self)

    def run(self, prev_stage):
        assert prev_stage is None, StageError("'input' in wrong location")

        if self._bypass:
            self.pipeline.send(res_np=None)
            return

        data_np = self.image.get_data()
        self.pipeline.send(res_np=data_np)

    def _get_state(self):
        return dict(path=self._path)

    def export_as_dict(self):
        d = super(Input, self).export_as_dict()
        d.update(self._get_state())
        return d

    def import_from_dict(self, d):
        super(Input, self).import_from_dict(d)
        self._set_path(d['path'])

        # TODO: load image into channel?
