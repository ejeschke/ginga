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
        self.settings.addDefaults(columns=columns, always_expand=True)
        self.settings.load(onError='silent')

        # For table-of-contents pane
        self.name_dict = Bunch.caselessDict()
        self.top_index = Bunch.caselessDict()
        # TODO: this ought to be customizable by channel
        self.columns = self.settings.get('columns', columns)
        self.treeview = None

        self.gui_up = False
        fv.set_callback('add-image', self.add_image)
        fv.set_callback('remove-image', self.remove_image)
        fv.set_callback('delete-channel', self.delete_channel)

    def build_gui(self, container):
        # create the Treeview
        always_expand = self.settings.get('always_expand', False)
        treeview = Widgets.TreeView(auto_expand=always_expand,
                                    sortable=True)
        self.treeview = treeview
        headers = [ tup[0] for tup in self.columns ]
        treeview.set_headers(headers)

        treeview.add_callback('selected', self.switch_image)
        container.add_widget(treeview, stretch=1)

        self.gui_up = True


    def switch_image(self, widget, tup):
        chname, imname = tup
        fileDict = self.name_dict[chname]
        key = imname.lower()
        bnch = fileDict[key]
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

        bnch = Bunch.Bunch(CHNAME=chname, path=path,
                           image_future=future)

        # Get header keywords of interest
        header = image.get_header()
        for hdr, key in self.columns:
            bnch[hdr] = str(header.get(key, 'N/A'))
        # name should always be available
        bnch.Name = name
        bnch.__terminal__ = True
        return bnch

    def recreate_toc(self):
        self.logger.debug("Recreating table of contents...")
        self.treeview.set_tree(self.name_dict)

    def add_image(self, viewer, chname, image):
        if not self.gui_up:
            return False

        noname = 'Noname' + str(time.time())
        name = image.get('name', noname)
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
            chitem = self.top_index[chname]

        else:
            # channel does not exist yet in contents--add it
            chitem = self.treeview.add_top_level(chname)

            fileDict = {}
            self.name_dict[chname] = fileDict
            self.top_index[chname] = chitem

        bnch = self.get_info(chname, name, image)
        fileDict[key] = bnch

        l = [ bnch[hdr] for hdr, kwd in self.columns ]
        self.treeview.add_row(chitem, l)
        self.logger.debug("%s added to Contents" % (name))

    def remove_image(self, viewer, chname, name, path):
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

    def delete_channel(self, viewer, chinfo):
        """Called when a channel is deleted from the main interface.
        Parameter is chinfo (a bunch)."""
        chname = chinfo.name
        del self.name_dict[chname]
        if not self.gui_up:
            return False
        if chname in self.top_index:
            del self.top_index[chname]
        self.recreate_toc()

    def stop(self):
        self.gui_up = False

    def __str__(self):
        return 'contents'

#END
