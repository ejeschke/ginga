#
# Contents.py -- Table of Contents plugin for fits viewer
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga import GingaPlugin
from ginga.misc import Bunch

from ginga.gw import Widgets
import time

class Contents(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Contents, self).__init__(fv)

        columns = [ ('Name', 'NAME'), ('Object', 'OBJECT'),
                    ('Date', 'DATE-OBS'), ('Time UT', 'UT'),
                     ]

        prefs = self.fv.get_preferences()
        self.settings = prefs.createCategory('plugin_Contents')
        self.settings.addDefaults(columns=columns,
                                  always_expand=True,
                                  highlight_tracks_keyboard_focus=True,
                                  color_alternate_rows=True,
                                  row_font_color='green')
        self.settings.load(onError='silent')

        # For table-of-contents pane
        self.name_dict = Bunch.caselessDict()
        # TODO: this ought to be customizable by channel
        self.columns = self.settings.get('columns', columns)
        self.treeview = None
        # paths of highlighted entries, by channel
        self.highlight_tracks_keyboard_focus = self.settings.get(
            'highlight_tracks_keyboard_focus', True)
        self._hl_path = set([])

        fv.add_callback('add-image', self.add_image_cb)
        fv.set_callback('add-image-info', self.add_image_info_cb)
        fv.add_callback('remove-image', self.remove_image_cb)
        fv.add_callback('add-channel', self.add_channel_cb)
        fv.add_callback('delete-channel', self.delete_channel_cb)
        fv.add_callback('active-image', self.focus_cb)

        self.gui_up = False

    def build_gui(self, container):
        # create the Treeview
        always_expand = self.settings.get('always_expand', False)
        color_alternate = self.settings.get('color_alternate_rows', True)
        treeview = Widgets.TreeView(auto_expand=always_expand,
                                    sortable=True,
                                    use_alt_row_color=color_alternate)
        self.treeview = treeview
        treeview.setup_table(self.columns, 2, 'NAME')

        treeview.add_callback('selected', self.switch_image)
        container.add_widget(treeview, stretch=1)

        self.gui_up = True

    def stop(self):
        self.gui_up = False

    def switch_image(self, widget, res_dict):
        chname = list(res_dict.keys())[0]
        img_dict = res_dict[chname]
        imname = list(img_dict.keys())[0]
        bnch = img_dict[imname]
        path = bnch.path
        self.logger.debug("chname=%s name=%s path=%s" % (
            chname, imname, path))

        self.fv.switch_name(chname, imname, path=path,
                            image_future=bnch.image_future)

    def get_info(self, chname, name, image, info):
        path = info.get('path', None)
        future = info.get('image_future', None)

        bnch = Bunch.Bunch(CHNAME=chname, imname=name, path=path,
                           image_future=future)

        # Get header keywords of interest
        header = image.get_header()
        for hdr, key in self.columns:
            bnch[key] = str(header.get(key, 'N/A'))
        # name should always be available
        bnch.NAME = name
        return bnch

    def recreate_toc(self):
        self.logger.debug("Recreating table of contents...")
        self.treeview.set_tree(self.name_dict)

        # re-highlight as necessary
        if self.highlight_tracks_keyboard_focus:
            new_highlight = self._hl_path
        else:
            new_highlight = set([])
            for chname in self.name_dict:
                channel = self.fv.get_channelInfo(chname)
                new_highlight |= channel.extdata.contents_old_highlight
        self.update_highlights(set([]), new_highlight)

    def add_image_cb(self, viewer, chname, image, image_info):
        if not self.gui_up:
            return False

        name = image_info.name
        self.logger.debug("name=%s" % (name))

        nothumb = image.get('nothumb', False)
        if nothumb:
            return

        key = name

        if chname in self.name_dict:
            fileDict = self.name_dict[chname]
            if key in fileDict:
                # there is already an entry
                return
        else:
            # channel does not exist yet in contents
            fileDict = {}
            self.name_dict[chname] = fileDict

        bnch = self.get_info(chname, name, image, image_info)
        fileDict[key] = bnch

        tree_dict = { chname: { name: bnch } }
        self.treeview.add_tree(tree_dict)
        self.logger.debug("%s added to Contents" % (name))

    def remove_image_cb(self, viewer, chname, name, path):
        if not self.gui_up:
            return False

        if chname not in self.name_dict:
            return

        fileDict = self.name_dict[chname]

        key = name
        if key not in fileDict:
            return

        del fileDict[key]

        # Unhighlight
        channel = self.fv.get_channelInfo(chname)
        key = (chname, name)
        self._hl_path.discard(key)
        channel.extdata.contents_old_highlight.discard(key)

        self.recreate_toc()
        self.logger.debug("%s removed from Contents" % (name))

    def clear(self):
        self.name_dict = Bunch.caselessDict()
        self._hl_path = set([])
        self.recreate_toc()

    def add_channel_cb(self, viewer, chinfo):
        """Called when a channel is added from the main interface.
        Parameter is chinfo (a bunch)."""
        chname = chinfo.name
        chinfo.fitsimage.add_callback('image-set', self.set_image_cb, chname)

        # add old highlight set to channel external data
        chinfo.extdata.setdefault('contents_old_highlight', set([]))

        if not self.gui_up:
            return False

        # Add the channel to the treeview
        fileDict = {}
        self.name_dict.setdefault(chname, fileDict)

        tree_dict = { chname: { } }
        self.treeview.add_tree(tree_dict)

    def delete_channel_cb(self, viewer, chinfo):
        """Called when a channel is deleted from the main interface.
        Parameter is chinfo (a bunch)."""
        chname = chinfo.name
        del self.name_dict[chname]

        # Unhighlight
        un_hilite_set = set([])
        for path in self._hl_path:
            if path[0] == chname:
                un_hilite_set.add(path)
        self._hl_path -= un_hilite_set

        if not self.gui_up:
            return False
        self.recreate_toc()

    def _get_hl_key(self, chname, image):
        return (chname, image.get('name', 'none'))

    def _highlight_path(self, hl_path, tf):
        """Highlight or unhighlight a single entry.

        Examples
        --------
        >>> hl_path = self._get_hl_key(chname, image)
        >>> self._highlight_path(hl_path, True)

        """
        fc = self.settings.get('row_font_color', 'green')

        try:
            self.treeview.highlight_path(hl_path, tf, font_color=fc)
        except Exception as e:
            self.logger.error('Error changing highlight on treeview path '
                              '({0}): {1}'.format(hl_path, str(e)))

    def update_highlights(self, old_highlight_set, new_highlight_set):
        """Unhighlight the entries represented by ``old_highlight_set``
        and highlight the ones represented by ``new_highlight_set``.

        Both are sets of keys.

        """
        un_hilite_set = old_highlight_set - new_highlight_set
        re_hilite_set = new_highlight_set - old_highlight_set

        # unhighlight entries that should NOT be highlighted any more
        for key in un_hilite_set:
            self._highlight_path(key, False)

        # highlight new entries that should be
        for key in re_hilite_set:
            self._highlight_path(key, True)

    def set_image_cb(self, fitsimage, image, chname):
        """This method is called when an image is set in a channel."""

        # get old highlighted entries for this channel -- will be
        # an empty set or one key
        channel = self.fv.get_channelInfo(chname)
        old_highlight = channel.extdata.contents_old_highlight

        # calculate new highlight keys -- again, an empty set or one key
        if image is not None:
            key = self._get_hl_key(chname, image)
            new_highlight = set([key])
        else:
            # no image has the focus
            new_highlight = set([])

        # Only highlights active image in the current channel
        if self.highlight_tracks_keyboard_focus:
            self.update_highlights(self._hl_path, new_highlight)
            self._hl_path = new_highlight

        # Highlight all active images in all channels
        else:
            self.update_highlights(old_highlight, new_highlight)
            channel.extdata.contents_old_highlight = new_highlight

        return True

    def focus_cb(self, viewer, fitsimage):
        chname = self.fv.get_channelName(fitsimage)
        chinfo = self.fv.get_channelInfo(chname)
        chname = chinfo.name
        image = fitsimage.get_image()

        if image is not None:
            key = self._get_hl_key(chname, image)
            new_highlight = set([key])
        else:
            # no image has the focus
            new_highlight = set([])

        if self.highlight_tracks_keyboard_focus:
            self.update_highlights(self._hl_path, new_highlight)
            self._hl_path = new_highlight

    def add_image_info_cb(self, viewer, channel, image_info):
        chname = channel.name
        image = None

        # TODO: figure out what information to show for an image
        # that is not yet been loaded
        ## self.fv.gui_do(self.add_image_cb, viewer, chname, image,
        ##                  image_info)

    def __str__(self):
        return 'contents'

#END
