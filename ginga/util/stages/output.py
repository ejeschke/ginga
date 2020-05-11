# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.gw import Widgets
from ginga import RGBImage

from .base import Stage

count = 0

class Output(Stage):

    _stagename = 'output'

    def __init__(self, fv):
        super(Output, self).__init__()

        self.fv = fv
        self.in_image = None
        self.chname = ""
        self.path = ""

    def build_gui(self, container):
        fr = Widgets.Frame("Output")

        captions = [('Channel:', 'label', 'Channel', 'entryset'),
                    ('Path:', 'label', 'Path', 'entryset'),
                    ]
        w, b = Widgets.build_info(captions, orientation='vertical')
        self.w.update(b)

        b.channel.set_tooltip("Channel for output images")
        b.channel.add_callback('activated', self.set_channel_cb)
        b.path.set_text(self.path)
        b.path.set_tooltip("Enter a path to save the result")
        b.path.add_callback('activated', self.set_path_cb)

        fr.set_widget(w)
        container.set_widget(fr)

    def set_channel_cb(self, widget):
        self.chname = widget.get_text().strip()
        # TODO: ask user to create channel if it doesn't exist?
        channel = self.fv.get_channel_on_demand(self.chname)
        #self.pipeline.run_from(self)

    def run(self, prev_stage):
        global count
        data = self.pipeline.get_data(prev_stage)

        self.verify_2d(data)

        if self._bypass or data is None:
            self.pipeline.send(res_np=data)
            return

        if len(self.chname) > 0:
            self.pipeline.logger.info('pipeline output')
            channel = self.fv.get_channel(self.chname)

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
                self.image.set(name='P'+str(count))
                count += 1
                self.image.set_data(data)

                channel.add_image(self.image)

            else:
                if self.image is not None:
                    self.image.set_data(data)

        if len(self.path) != 0:
            # TODO: check for overwrite, confirmation?
            # TODO: save quality parameters
            self.image.save_as_file(self.path)

        self.pipeline.send(res_np=data)

    def set_path_cb(self, widget):
        filepath = widget.get_text().strip()
        if len(filepath) > 0:
            self.path = filepath
        else:
            self.path = None

        self.pipeline.run_from(self)

    def get_image(self):
        return self.image

    def __str__(self):
        return self._stagename
