#
# Contents.py -- Table of Contents plugin for fits viewer
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.util.six import itervalues
from ginga.util.six.moves import map

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
                    ('Modified', 'MODIFIED')
                    ]

        prefs = self.fv.get_preferences()
        self.settings = prefs.createCategory('plugin_Contents')
        self.settings.addDefaults(columns=columns,
                                  always_expand=True,
                                  highlight_tracks_keyboard_focus=True,
                                  color_alternate_rows=True,
                                  row_font_color='green',
                                  max_rows_for_col_resize=100)
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
        fv.add_callback('add-image-info', self.add_image_info_cb)
        fv.add_callback('remove-image', self.remove_image_cb)
        fv.add_callback('add-channel', self.add_channel_cb)
        fv.add_callback('delete-channel', self.delete_channel_cb)
        fv.add_callback('channel-change', self.focus_cb)

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
        if image is not None:
            header = image.get_header()
        else:
            header = {}

        for hdr, key in self.columns:
            bnch[key] = str(header.get(key, 'N/A'))

        # name should always be available
        bnch.NAME = name

        # Modified timestamp will be set if image data is modified
        timestamp = info.time_modified
        if timestamp is not None:
            # Z: Zulu time, GMT, UTC
            timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%SZ')
        bnch.MODIFIED = timestamp

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

        # Resize column widths
        n_rows = sum(map(len, self.name_dict.values()))
        if n_rows < self.settings.get('max_rows_for_col_resize', 100):
            self.treeview.set_optimal_column_widths()
            self.logger.debug("Resized columns for {0} row(s)".format(n_rows))

    def is_in_contents(self, chname, imname):
        if not chname in self.name_dict:
            return False

        file_dict = self.name_dict[chname]
        if not imname in file_dict:
            return False

        return True

    def add_image_cb(self, viewer, chname, image, image_info):
        if not self.gui_up:
            return False

        name = image_info.name
        self.logger.debug("name=%s" % (name))

        if image is not None:
            nothumb = image.get('nothumb', False)
            if nothumb:
                return

        bnch = self.get_info(chname, name, image, image_info)

        if not chname in self.name_dict:
            # channel does not exist yet in contents
            # Note: this typically shouldn't happen, because add_channel_cb()
            # will have added an empty dict
            file_dict = {}
            self.name_dict[chname] = file_dict
        else:
            file_dict = self.name_dict[chname]

        if not name in file_dict:
            # new image
            file_dict[name] = bnch
        else:
            # old image
            file_dict[name].update(bnch)

        # TODO: either make add_tree() merge updates or make an
        #    update_tree() method--shouldn't need to recreate entire
        #    tree, just add new entry and possibly rehighlight
        ## tree_dict = { chname: { name: bnch } }
        ## self.treeview.add_tree(tree_dict)
        self.recreate_toc()

        self.logger.debug("%s added to Contents" % (name))

    def add_image_info_cb(self, viewer, channel, image_info):
        """Almost the same as add_image_info(), except that the image
        may not be loaded in memory.
        """
        chname = channel.name
        name = image_info.name
        self.logger.debug("name=%s" % (name))

        # Updates of any extant information
        try:
            image = channel.get_loaded_image(name)
        except KeyError:
            # images that are not yet loaded will show "N/A" for keywords
            image = None

        self.add_image_cb(viewer, chname, image, image_info)

    def remove_image_cb(self, viewer, chname, name, path):
        if not self.gui_up:
            return False

        if chname not in self.name_dict:
            return

        file_dict = self.name_dict[chname]

        if name not in file_dict:
            return

        del file_dict[name]

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

    def add_channel_cb(self, viewer, channel):
        """Called when a channel is added from the main interface.
        Parameter is a channel (a Channel object)."""
        chname = channel.name

        # add old highlight set to channel external data
        channel.extdata.setdefault('contents_old_highlight', set([]))

        # Add the channel to the treeview
        file_dict = {}
        self.name_dict.setdefault(chname, file_dict)

        if not self.gui_up:
            return False

        tree_dict = { chname: { } }
        self.treeview.add_tree(tree_dict)

    def delete_channel_cb(self, viewer, channel):
        """Called when a channel is deleted from the main interface.
        Parameter is a channel (a Channel object)."""
        chname = channel.name
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

    def redo(self, channel, image):
        """This method is called when an image is set in a channel."""

        imname = image.get('name', 'none')
        chname = channel.name
        # is image in contents tree yet?
        in_contents = self.is_in_contents(chname, imname)

        # get old highlighted entries for this channel -- will be
        # an empty set or one key
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
            if in_contents:
                self.update_highlights(self._hl_path, new_highlight)
            self._hl_path = new_highlight

        # Highlight all active images in all channels
        else:
            if in_contents:
                self.update_highlights(old_highlight, new_highlight)
            channel.extdata.contents_old_highlight = new_highlight

        return True

    def focus_cb(self, viewer, channel):
        chname = channel.name
        image = channel.fitsimage.get_image()

        if image is not None:
            key = self._get_hl_key(chname, image)
            new_highlight = set([key])
        else:
            # no image has the focus
            new_highlight = set([])

        if self.highlight_tracks_keyboard_focus:
            self.update_highlights(self._hl_path, new_highlight)
            self._hl_path = new_highlight

    def __str__(self):
        return 'contents'

#END
