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
        self.path = ""

    def build_gui(self, container):
        fr = Widgets.Frame("Input")

        vbox = Widgets.VBox()
        self.w.lbl = Widgets.TextEntrySet('', editable=True)
        self.w.lbl.set_text(self.path)
        self.w.lbl.set_tooltip("Enter a path to load the data")
        vbox.add_widget(self.w.lbl, stretch=0)
        self.w.lbl.add_callback('activated', self.set_path_cb)

        fr.set_widget(vbox)
        container.set_widget(fr)

    def set_image(self, image):
        self.image = image
        self.path = image.get('path', "")
        if self.gui_up:
            self.w.lbl.set_text(self.path)
        _dir, _fn = None, None
        if len(self.path) > 0:
            _dir, _fn = os.path.split(self.path)
        self.pipeline.set(input_image=image,
                          input_folder=_dir, input_filename=_fn)
        self.pipeline.run_from(self)

    def set_path_cb(self, widget):
        self.path = widget.get_text().strip()
        image = loader.load_data(self.path, logger=self.logger)
        self.set_image(image)

    def run(self, prev_stage):
        assert prev_stage is None, StageError("'input' in wrong location")

        if self._bypass:
            self.pipeline.send(res_np=None)
            return

        data_np = self.image.get_data()
        self.pipeline.send(res_np=data_np)