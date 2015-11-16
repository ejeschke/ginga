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
from ginga.misc import Bunch, Future

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
        self.settings.addDefaults(columns=columns, always_expand=True,
                                  highlight_tracks_keyboard_focus=False,
                                  color_alternate_rows=True)
        self.settings.load(onError='silent')

        # For table-of-contents pane
        self.name_dict = Bunch.caselessDict()
        # TODO: this ought to be customizable by channel
        self.columns = self.settings.get('columns', columns)
        self.treeview = None
        # paths of highlighted entries, by channel
        self._hl_path = {}
        self.highlight_tracks_keyboard_focus = self.settings.get(
            'highlight_tracks_keyboard_focus', False)

        self.gui_up = False
        fv.add_callback('add-image', self.add_image_cb)
        fv.add_callback('remove-image', self.remove_image_cb)
        fv.add_callback('add-channel', self.add_channel_cb)
        fv.add_callback('delete-channel', self.delete_channel_cb)
        if self.highlight_tracks_keyboard_focus:
            fv.add_callback('active-image', self.focus_cb)
            self._hl_path['none'] = None


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


    def switch_image(self, widget, res_dict):
        chname = res_dict.keys()[0]
        img_dict = res_dict[chname]
        imname = img_dict.keys()[0]
        bnch = img_dict[imname]
        path = bnch.path
        self.logger.debug("chname=%s name=%s path=%s" % (
            chname, imname, path))

        self.fv.switch_name(chname, imname, path=path,
                            image_future=bnch.image_future)

    def get_info(self, chname, name, image):
        path = image.get('path', None)
        future = image.get('image_future', None)
        if future is None:
            image_loader = image.get('loader', self.fv.load_image)
            future = Future.Future()
            future.freeze(image_loader, path)

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
        hl_items = list(self._hl_path.items())
        for chname, hl_path in hl_items:
            self._highlight_path(chname, hl_path, True)

    def add_image_cb(self, viewer, chname, image, image_info):
        if not self.gui_up:
            return False

        name = image_info.name
        self.logger.debug("name=%s" % (name))

        nothumb = image.get('nothumb', False)
        if nothumb:
            return

        key = name.lower()

        if chname in self.name_dict:
            fileDict = self.name_dict[chname]
            if key in fileDict:
                # there is already an entry
                return
        else:
            # channel does not exist yet in contents
            fileDict = {}
            self.name_dict[chname] = fileDict

        bnch = self.get_info(chname, name, image)
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

        key = name.lower()
        if key not in fileDict:
            return

        del fileDict[key]
        self.recreate_toc()
        self.logger.debug("%s removed from Contents" % (name))

    def clear(self):
        self.name_dict = Bunch.caselessDict()
        self.recreate_toc()

    def add_channel_cb(self, viewer, chinfo):
        """Called when a channel is added from the main interface.
        Parameter is chinfo (a bunch)."""
        chname = chinfo.name

        if not self.highlight_tracks_keyboard_focus:
            chinfo.fitsimage.add_callback('image-set',
                                          self.set_image_cb, chname)

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
        if chname in self._hl_path:
            del self._hl_path[chname]
        if not self.gui_up:
            return False
        self.recreate_toc()

    def _highlight_path(self, chname, path, tf):
        try:
            self.treeview.highlight_path(path, tf)

        except Exception as e:
            self.logger.warn("Error changing highlight on treeview path (%s): %s" % (
                str(path), str(e)))
            path = None

        self._hl_path[chname] = path

    def set_image_cb(self, fitsimage, image, chname):
        if chname in self._hl_path:
            # if there is already a path highlighted for this channel
            # then unhighlight it
            path = self._hl_path[chname]
            if path is not None:
                self._highlight_path(chname, path, False)

        if image is None:
            return
        # create path of this image in treeview
        hl_path = [chname, image.get('name', 'none')]

        # note and highlight the new path
        self._highlight_path(chname, hl_path, True)
        return True

    def focus_cb(self, viewer, fitsimage):
        chname = self.fv.get_channelName(fitsimage)
        chinfo = self.fv.get_channelInfo(chname)
        chname = chinfo.name

        # if there is already a path highlighted for this channel
        # then unhighlight it
        path = self._hl_path['none']
        if path is not None:
            self._highlight_path('none', path, False)

        image = fitsimage.get_image()
        if image is None:
            return

        # create path of this image in treeview
        hl_path = [chname, image.get('name', 'none')]

        # note and highlight the new path
        self._highlight_path('none', hl_path, True)

    def stop(self):
        self.gui_up = False

    def __str__(self):
        return 'contents'

#END
