#
# HeaderBase.py -- FITS Header plugin base class for fits viewer
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga import GingaPlugin


class HeaderBase(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(HeaderBase, self).__init__(fv)

        self.channel = {}
        self.active = None
        self.info = None
        self.columns = [('Keyword', 'key'),
                        ('Value', 'value'),
                        ('Comment', 'comment'),
                        ]

        prefs = self.fv.get_preferences()
        self.settings = prefs.createCategory('plugin_Header')
        self.settings.addDefaults(sortable=False)
        self.settings.load(onError='silent')

        fv.set_callback('add-channel', self.add_channel)
        fv.set_callback('delete-channel', self.delete_channel)
        fv.set_callback('active-image', self.focus_cb)

    def set_header(self, info, image):
        pass

    def add_channel(self, viewer, chinfo):
        pass

    def delete_channel(self, viewer, chinfo):
        pass

    def focus_cb(self, viewer, fitsimage):
        pass

    def start(self):
        names = self.fv.get_channelNames()
        for name in names:
            chinfo = self.fv.get_channelInfo(name)
            self.add_channel(self.fv, chinfo)

    def new_image_cb(self, fitsimage, image, info):
        self.set_header(info, image)

    def set_sortable_cb(self, info):
        chinfo = self.fv.get_channelInfo(info.chname)
        image = chinfo.fitsimage.get_image()
        self.set_header(info, image)

#END
