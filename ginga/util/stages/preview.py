# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga import RGBMap, AutoCuts
from ginga.gw import Widgets

from .base import Stage, StageAction

count = 0


class Preview(Stage):

    _stagename = 'preview'

    def __init__(self):
        super().__init__()

        self.fv = None
        self.in_image = None
        self.image = None
        self._chname = ""

    def build_gui(self, container):
        self.fv = self.pipeline.get("fv")

        fr = Widgets.Frame("Preview")

        captions = [('Preview Channel:', 'label', 'Channel', 'entryset'),
                    ('Detach Image', 'button'),
                    ]
        w, b = Widgets.build_info(captions, orientation='vertical')
        self.w.update(b)

        b.channel.set_tooltip("Channel for preview image")
        b.channel.add_callback('activated', self.set_channel_cb)
        b.channel.set_text(self._chname)

        b.detach_image.set_tooltip("Detach the current image")
        b.detach_image.add_callback('activated', self.insert_image_cb)

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

    def get_channel(self, chname):
        channel = self.fv.get_channel_on_demand(chname)
        viewer = channel.viewer

        # PassThruRGBMapper does not do any RGB mapping
        rgbmap = RGBMap.PassThruRGBMapper(self.logger)
        viewer.set_rgbmap(rgbmap)

        # Clip cuts assumes data does not need to be scaled in cut levels--
        # only clipped
        viewer.set_autocuts(AutoCuts.Clip(logger=self.logger))

        return channel

    def set_channel_cb(self, widget):
        old = dict(chname=self._chname)
        self._chname = widget.get_text().strip()
        new = dict(chname=self._chname)
        self.pipeline.push(StageAction(self, old, new,
                                       descr="preview / change channel"))

        self.get_channel(self._chname)

        self.pipeline.run_from(self)

    def insert_image_cb(self, widget):
        image, self.image = self.image, None
        self.in_image = None

        self.pipeline.run_from(self)

    def run(self, prev_stage):
        global count
        data = self.pipeline.get_data(prev_stage)

        self.verify_2d(data)

        if self._bypass or data is None:
            self.pipeline.send(res_np=data)
            return

        if len(self.chname) > 0:
            self.pipeline.logger.info('pipeline preview')
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

    def get_image(self):
        return self.image

    def _get_state(self):
        return dict(chname=self._chname)

    def export_as_dict(self):
        d = super().export_as_dict()
        d.update(self._get_state())
        return d

    def import_from_dict(self, d):
        super().import_from_dict(d)
        self.chname = d['chname']
