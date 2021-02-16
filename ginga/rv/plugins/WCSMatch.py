#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
``WCSMatch`` is a global plugin for the Ginga image viewer that allows
you to roughly align images with different scales and orientations
using the images' World Coordinate System (WCS) for viewing purposes.

**Plugin Type: Global**

``WCSMatch`` is a global plugin.  Only one instance can be opened.

**Usage**

To use, simply start the plugin, and from the plugin GUI select a
channel from the drop-down menu labeled "Reference Channel".  The
image contained in that channel will be used as a reference for
synchronizing the images in the other channels.

The channels will be synchronized in viewing (pan, scale (zoom),
transforms (flips) and rotation.  The checkboxes "Match Pan",
"Match Scale", "Match Transforms" and "Match Rotation" can be
checked or not to control which attributes are synchronized between
channels.

To completely "unlock" the synchronization, simply select "None"
from the "Reference Channel" drop-down menu.

Currently, there is no way to limit the channels that are affected
by the plugin.

"""
from ginga import GingaPlugin
from ginga.gw import Widgets
from ginga.util import wcs
from ginga.misc import Bunch

__all__ = ['WCSMatch']


class WCSMatch(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(WCSMatch, self).__init__(fv)

        self.chnames = []
        self.ref_channel = None
        self.ref_image = None
        self.gui_up = False
        self._cur_opn_viewer = None
        self._match = dict(pan=True, scale=True, transforms=True,
                           rotation=True)

        # get WCSMatch preferences
        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_WCSMatch')
        self.settings.add_defaults(orientation=None)
        self.settings.load(onError='silent')

        fv.add_callback('add-channel', self.add_channel)
        fv.add_callback('delete-channel', self.delete_channel)

    def build_gui(self, container):
        top = Widgets.VBox()
        top.set_border_width(4)

        vbox, sw, orientation = Widgets.get_oriented_box(container,
                                                         orientation=self.settings.get('orientation', None))
        vbox.set_border_width(4)
        vbox.set_spacing(2)

        fr = Widgets.Frame("WCS Match")

        captions = (('Reference Channel:', 'label',
                     'ref channel', 'combobox'),
                    ('Match Pan', 'checkbutton',
                     'Match Scale', 'checkbutton'),
                    ('Match Transforms', 'checkbutton',
                    'Match Rotation', 'checkbutton'),
                    )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w = b

        b.ref_channel.add_callback('activated', self._set_reference_channel_cb)
        self.w.match_pan.set_state(self._match['pan'])
        self.w.match_pan.set_tooltip("Match pan position of reference image")
        self.w.match_pan.add_callback('activated',
                                      self.set_match_cb, 'pan')
        self.w.match_scale.set_state(self._match['scale'])
        self.w.match_scale.add_callback('activated',
                                        self.set_match_cb, 'scale')
        self.w.match_scale.set_tooltip("Match scale of reference image")
        self.w.match_transforms.set_state(self._match['transforms'])
        self.w.match_transforms.add_callback('activated',
                                             self.set_match_cb, 'transforms')
        self.w.match_transforms.set_tooltip("Match transforms of reference image")
        self.w.match_rotation.set_state(self._match['rotation'])
        self.w.match_rotation.add_callback('activated',
                                           self.set_match_cb, 'rotation')
        self.w.match_rotation.set_tooltip("Match rotation of reference image")

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
        btn = Widgets.Button("Help")
        btn.add_callback('activated', lambda w: self.help())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        top.add_widget(btns, stretch=0)

        container.add_widget(top, stretch=1)

        self.gui_up = True
        self._reset_channels_gui()

    def add_channel(self, viewer, channel):
        info = Bunch.Bunch(chinfo=channel)
        channel.extdata._wcsmatch_info = info

        # Add callbacks to the viewer for all the scale, pan, rotation and
        # transform settings changes
        chviewer = channel.fitsimage
        fitssettings = chviewer.get_settings()
        fitssettings.get_setting('scale').add_callback(
            'set', self.zoomset_cb, chviewer, info)
        fitssettings.get_setting('rot_deg').add_callback(
            'set', self.rotset_cb, chviewer, info)
        for name in ('flip_x', 'flip_y', 'swap_xy'):
            fitssettings.get_setting(name).add_callback(
                'set', self.xfmset_cb, chviewer, info)
        fitssettings.get_setting('pan').add_callback(
            'set', self.panset_cb, chviewer, info)
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

    def _update_all(self):
        if self.ref_channel is None:
            return
        chinfo = self.ref_channel
        chviewer = chinfo.fitsimage
        self.zoomset(chviewer, chinfo)
        self.rotset(chviewer, chinfo)
        self.xfmset(chviewer, chinfo)
        self.panset(chviewer, chinfo)

    def _set_reference_channel(self, chname):
        if chname == 'None':
            chname = None
        if chname is None:
            self.ref_image = None
            self.ref_channel = None
            self.logger.info("turning off channel synchronization")
            return

        chinfo = self.fv.get_channel(chname)
        self.ref_channel = chinfo
        chviewer = chinfo.fitsimage
        self.ref_image = chviewer.get_image()

        # reset the scale base to be identical in both axes for the
        # reference image
        chviewer.set_scale_base_xy(1.0, 1.0)

        self._update_all()

        self.logger.info("set reference channel to '%s'" % (chname))

    def _set_reference_channel_cb(self, w, idx):
        """This is the GUI callback for the control that sets the reference
        channel.
        """
        chname = self.chnames[idx]
        self._set_reference_channel(chname)

    def set_reference_channel(self, chname):
        """This is the API call to set the reference channel.
        """
        # change the GUI control to match
        idx = self.chnames.index(str(chname))
        self.w.ref_channel.set_index(idx)
        return self._set_reference_channel(chname)

    def set_match_cb(self, w, tf, key):
        # remember, in case we are closed and reopened
        self._match.update(dict(pan=self.w.match_pan.get_state(),
                                scale=self.w.match_scale.get_state(),
                                transforms=self.w.match_transforms.get_state(),
                                rotation=self.w.match_rotation.get_state()))

        if key == 'scale' and tf is False:
            self.reset_scale_skew()

        self._update_all()

    def close(self):
        self.fv.stop_global_plugin(str(self))
        return True

    def start(self):
        pass

    def stop(self):
        self.ref_channel = None
        self.ref_image = None
        self.fv.show_status("")

    def get_other_channels(self, myname):
        return set(self.fv.get_channel_names()) - set([myname])

    def zoomset_cb(self, setting, value, chviewer, info):
        """This callback is called when a channel window is zoomed.
        """
        return self.zoomset(chviewer, info.chinfo)

    def zoomset(self, chviewer, chinfo):
        # Don't do anything if we are not active
        if not self.gui_up or self.ref_image is None:
            return

        if self._cur_opn_viewer is not None:
            return
        if not self._match['scale']:
            return

        self._cur_opn_viewer = chviewer
        try:
            self.scale_all_relative(chviewer, chinfo)

        finally:
            self._cur_opn_viewer = None

    def scale_all_relative(self, chviewer, chinfo):
        if self.ref_image is None:
            return

        # get native scale relative to reference image
        image = chviewer.get_image()
        ort = wcs.get_relative_orientation(image, self.ref_image)
        self.logger.info("scale for channel '%s' relative to ref image "
                         "%f,%f" % (chinfo.name, ort.rscale_x, ort.rscale_y))

        scale_x, scale_y = chviewer.get_scale_xy()

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

    def reset_scale_skew(self):
        """Set the X/Y scaling factors to be equal in each channel.
        """
        chnames = self.fv.get_channel_names()
        for chname in chnames:
            chinfo = self.fv.get_channel(chname)

            scales = chinfo.fitsimage.get_scale_xy()
            fac = min(*scales)
            chinfo.fitsimage.scale_to(fac, fac)

    def rotset_cb(self, setting, value, chviewer, info):
        """This callback is called when a channel window is rotated.
        """
        return self.rotset(chviewer, info.chinfo)

    def rotset(self, chviewer, chinfo):
        # Don't do anything if we are not active
        if not self.gui_up or self.ref_image is None:
            return

        if self._cur_opn_viewer is not None:
            return
        if not self._match['rotation']:
            return

        self._cur_opn_viewer = chviewer
        try:
            self.rotate_all_relative(chviewer, chinfo)

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
        self.logger.info("rotation for channel '%s' relative to ref image "
                         "%f" % (chinfo.name, ort.rrot_deg))

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
        return self.panset(chviewer, info.chinfo)

    def panset(self, chviewer, chinfo):
        # Don't do anything if we are not active
        if not self.gui_up or self.ref_image is None:
            return

        if self._cur_opn_viewer is not None:
            return
        if not self._match['pan']:
            return

        self._cur_opn_viewer = chviewer
        try:
            self.pan_all_relative(chviewer, chinfo)

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
        return self.xfmset(chviewer, info.chinfo)

    def xfmset(self, chviewer, chinfo):
        # Don't do anything if we are not active
        if not self.gui_up or self.ref_image is None:
            return

        if self._cur_opn_viewer is not None:
            return
        if not self._match['transforms']:
            return

        self._cur_opn_viewer = chviewer
        try:
            self.transform_all_relative(chviewer, chinfo)

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

    def __str__(self):
        return 'wcsmatch'

# END
