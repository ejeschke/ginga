#
# WCSMatch.py -- WCSMatch plugin for Ginga reference viewer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga import GingaPlugin
from ginga.gw import Widgets
from ginga.util import wcs
from ginga.misc import Bunch


class WCSMatch(GingaPlugin.GlobalPlugin):
    """
    *** This plugin is experimental/alpha/testing/preview ***

    WCSMatch is a global plugin for the Ginga image viewer that allows
    you to roughly align images with different scales and orientations
    using WCS for viewing purposes.

    To use, simply start the plugin, and from the plugin GUI select a
    channel from the drop-down menu labeled "Reference Channel".  The
    image contained in that channel will be used as a reference for
    zooming and orienting the images in the other channels.

    The channels will be synchronized in viewing (zoom, pan, rotate,
    transform).  To "unlock" the synchronization, simply select "None"
    from the "Reference Channel" drop-down menu.

    Currently there is no way to limit the channels that are affected
    by the plugin.
    """

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(WCSMatch, self).__init__(fv)

        self.chnames = []
        self.ref_channel = None
        self.ref_image = None
        self.gui_up = False
        self._cur_opn_viewer = None

        fv.add_callback('add-channel', self.add_channel)
        fv.add_callback('delete-channel', self.delete_channel)

    def build_gui(self, container):
        top = Widgets.VBox()
        top.set_border_width(4)

        vbox, sw, orientation = Widgets.get_oriented_box(container)
        vbox.set_border_width(4)
        vbox.set_spacing(2)

        self.msg_font = self.fv.get_font("sansFont", 12)
        tw = Widgets.TextArea(wrap=True, editable=False)
        tw.set_font(self.msg_font)
        self.tw = tw

        fr = Widgets.Expander("Instructions")
        fr.set_widget(tw)
        vbox.add_widget(fr, stretch=0)

        fr = Widgets.Frame("WCS Match")

        captions = ((' Reference Channel:', 'label',
                     'ref channel', 'combobox'),
                    )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w = b

        b.ref_channel.add_callback('activated', self.set_reference_channel_cb)

        fr.set_widget(w)
        vbox.add_widget(fr, stretch=0)

        spacer = Widgets.Label('')
        vbox.add_widget(spacer, stretch=1)

        top.add_widget(sw, stretch=1)

        btns = Widgets.HBox()
        btns.set_spacing(3)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        top.add_widget(btns, stretch=0)

        container.add_widget(top, stretch=1)

        self.gui_up = True
        self._reset_channels_gui()

    def add_channel(self, viewer, channel):
        chname = channel.name
        info = Bunch.Bunch(chinfo=channel)
        channel.extdata._wcsmatch_info = info

        # Add callbacks to the viewer for all the scale, pan, rotation and
        # transform settings changes
        chviewer = channel.fitsimage
        fitssettings = chviewer.get_settings()
        fitssettings.getSetting('scale').add_callback('set',
                                                   self.zoomset_cb, chviewer, info)
        fitssettings.getSetting('rot_deg').add_callback('set',
                                                        self.rotset_cb, chviewer, info)
        for name in ('flip_x', 'flip_y', 'swap_xy'):
            fitssettings.getSetting(name).add_callback('set',
                                                       self.xfmset_cb, chviewer, info)
        fitssettings.getSetting('pan').add_callback('set',
                                                    self.panset_cb, chviewer, info)
        self.fv.gui_do(self._reset_channels_gui)


    def delete_channel(self, viewer, channel):
        chname = channel.name
        self.logger.debug("deleting channel %s" % (chname))
        self.active = None
        self.info = None
        self.fv.gui_do(self._reset_channels_gui)

    def _reset_channels_gui(self):
        self.chnames = list(self.fv.get_channel_names())
        self.chnames.sort()
        self.chnames.insert(0, "None")
        if not self.gui_up:
            return
        self.w.ref_channel.clear()
        for chname in self.chnames:
            self.w.ref_channel.append_text(chname)

    # CALLBACKS

    def redo(self, channel, image):
        info = channel.extdata._wcsmatch_info

        self.logger.info("Channel '%s' setting image" % (info.chinfo.name))
        if info.chinfo == self.ref_channel:
            self.ref_image = image
        return True

    def set_reference_channel_cb(self, w, idx):
        chname = self.chnames[idx]
        if chname == 'None':
            self.ref_image = None
            self.ref_channel = None

        chinfo = self.fv.get_channel(chname)
        self.ref_channel = chinfo
        chviewer = chinfo.fitsimage
        self.ref_image = chviewer.get_image()

        # reset the scale base to be identical in both axes for the
        # reference image
        chviewer.set_scale_base_xy(1.0, 1.0)

        self.scale_all_relative(chviewer, chinfo)
        self.rotate_all_relative(chviewer, chinfo)
        self.transform_all_relative(chviewer, chinfo)
        self.pan_all_relative(chviewer, chinfo)

        self.logger.info("set reference channel to '%s'" % (chname))

    def close(self):
        self.fv.stop_global_plugin(str(self))
        return True

    def instructions(self):
        self.tw.set_text(WCSMatch.__doc__)

    def start(self):
        self.instructions()

    def stop(self):
        self.ref_channel = None
        self.ref_image = None
        self.fv.showStatus("")

    def get_other_channels(self, myname):
        return set(self.fv.get_channel_names()) - set([myname])

    def zoomset_cb(self, setting, value, chviewer, info):
        """This callback is called when a channel window is zoomed.
        """
        # Don't do anything if we are not active
        if not self.gui_up or self.ref_image is None:
            return

        # if this is not a zoom event from the focus window then
        # don't do anything
        ## focus_chviewer = self.fv.getfocus_viewer()
        ## if chviewer != focus_chviewer:
        ##     return
        if self._cur_opn_viewer is not None:
            return

        self._cur_opn_viewer = chviewer
        try:
            self.scale_all_relative(chviewer, info.chinfo)

        finally:
            self._cur_opn_viewer = None

    def scale_all_relative(self, chviewer, chinfo):
        if self.ref_image is None:
            return

        # get native scale relative to reference image
        image = chviewer.get_image()
        ort = wcs.get_relative_orientation(image, self.ref_image)
        self.logger.info("scale for channel '%s' relative to ref image %f,%f" % (
            chinfo.name, ort.rscale_x, ort.rscale_y))

        scale_x, scale_y = chviewer.get_scale_xy()
        #scale_x, scale_y = value

        chg_x, chg_y = scale_x / ort.rscale_x, scale_y / ort.rscale_y
        self.logger.info("scale changed for channel '%s' by %f,%f" % (
            chinfo.name, chg_x, chg_y))

        # for all other channels except ours
        chnames = self.get_other_channels(chinfo.name)
        for chname in chnames:
            chinfo2 = self.fv.get_channel(chname)

            # calculate scale from orientation to reference image
            image = chinfo2.fitsimage.get_image()
            if image is None:
                continue
            ort = wcs.get_relative_orientation(image, self.ref_image)

            new_scale_x, new_scale_y = (ort.rscale_x * chg_x,
                                        ort.rscale_y * chg_y)
            # apply that scale
            self.logger.info("changing scale for channel '%s' to %f,%f" % (
                chinfo2.name, new_scale_x, new_scale_y))
            chinfo2.fitsimage.scale_to(new_scale_x, new_scale_y)


    def rotset_cb(self, setting, value, chviewer, info):
        """This callback is called when a channel window is rotated.
        """
        # Don't do anything if we are not active
        if not self.gui_up or self.ref_image is None:
            return

        # if this is not a zoom event from the focus window then
        # don't do anything
        ## focus_chviewer = self.fv.getfocus_viewer()
        ## if chviewer != focus_chviewer:
        ##     return
        if self._cur_opn_viewer is not None:
            return

        self._cur_opn_viewer = chviewer
        try:
            self.rotate_all_relative(chviewer, info.chinfo)

        finally:
            self._cur_opn_viewer = None

    def rotate_all_relative(self, chviewer, chinfo):
        if self.ref_image is None:
            return

        # get native scale relative to reference image
        image = chviewer.get_image()
        if self.ref_image is None:
            return
        ort = wcs.get_relative_orientation(image, self.ref_image)
        self.logger.info("rotation for channel '%s' relative to ref image %f" % (
            chinfo.name, ort.rrot_deg))

        rot_deg = chviewer.get_rotation()

        chg_rot_deg = rot_deg + ort.rrot_deg
        self.logger.info("rotation changed for channel '%s' by %f" % (
            chinfo.name, chg_rot_deg))

        # for all other channels except ours
        chnames = self.get_other_channels(chinfo.name)
        for chname in chnames:
            chinfo2 = self.fv.get_channel(chname)

            # Get relative rotation of their image
            image = chinfo2.fitsimage.get_image()
            if image is None:
                continue
            ort = wcs.get_relative_orientation(image, self.ref_image)

            # Apply that rotation
            new_rot_deg = ort.rrot_deg + chg_rot_deg
            self.logger.info("changing rot for channel '%s' to %f" % (
                chinfo2.name, new_rot_deg))
            chinfo2.fitsimage.rotate(new_rot_deg)


    def panset_cb(self, setting, value, chviewer, info):
        """This callback is called when a channel window is panned.
        """
        # Don't do anything if we are not active
        if not self.gui_up or self.ref_image is None:
            return

        # if this is not a zoom event from the focus window then
        # don't do anything
        ## focus_chviewer = self.fv.getfocus_viewer()
        ## if chviewer != focus_chviewer:
        ##     return
        if self._cur_opn_viewer is not None:
            return

        self._cur_opn_viewer = chviewer
        try:
            self.pan_all_relative(chviewer, info.chinfo)

        finally:
            self._cur_opn_viewer = None


    def pan_all_relative(self, chviewer, chinfo):
        if self.ref_image is None:
            return

        image = chviewer.get_image()
        if self.ref_image is None:
            return

        pan_ra, pan_dec = chviewer.get_pan(coord='wcs')

        # for all other channels except ours
        chnames = self.get_other_channels(chinfo.name)
        for chname in chnames:
            chinfo2 = self.fv.get_channel(chname)

            # set pan position on their viewer
            image = chinfo2.fitsimage.get_image()
            if image is None:
                continue
            data_x, data_y = image.radectopix(pan_ra, pan_dec)
            chinfo2.fitsimage.panset_xy(data_x, data_y)


    def xfmset_cb(self, setting, value, chviewer, info):
        """This callback is called when a channel window is transformed
        (flipped, or swap axes).
        """
        # Don't do anything if we are not active
        if not self.gui_up or self.ref_image is None:
            return

        # if this is not a zoom event from the focus window then
        # don't do anything
        ## focus_chviewer = self.fv.getfocus_chviewer()
        ## if chviewer != focus_chviewer:
        ##     return
        if self._cur_opn_viewer is not None:
            return

        self._cur_opn_viewer = chviewer
        try:
            self.transform_all_relative(chviewer, info.chinfo)

        finally:
            self._cur_opn_viewer = None


    def transform_all_relative(self, chviewer, chinfo):
        if self.ref_image is None:
            return

        image = chviewer.get_image()
        if self.ref_image is None:
            return

        flip_x, flip_y, swap_xy = chviewer.get_transforms()

        # for all other channels except ours
        chnames = self.get_other_channels(chinfo.name)
        for chname in chnames:
            chinfo2 = self.fv.get_channel(chname)

            # set our pan position on their viewer
            image = chinfo2.fitsimage.get_image()
            if image is None:
                continue
            chinfo2.fitsimage.transform(flip_x, flip_y, swap_xy)


    def redo(self):
        if self.ref_image is None:
            # no reference image
            return

        chinfo = self.fv.get_channel_info()
        viewer = chinfo.fitsimage

        image = viewer.get_image()
        ## if image == self.ref_image:
        ##     # current image is same as reference image
        ##     return

        info = wcs.get_relative_orientation(image, self.ref_image)
        self.logger.info("rscale_x=%f rscale_y=%f rrot_deg=%f" % (
            info.rscale_x, info.rscale_y, info.rrot_deg))

    def __str__(self):
        return 'wcsmatch'

#END
