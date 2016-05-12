#
# RemoteData.py -- Remote Data plugin for Ginga image viewer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
"""
import sys

from ginga import GingaPlugin
from ginga.util.grc import RemoteClient
from ginga.gw import Widgets

from RemoteImage import RemoteImage

help_msg = sys.modules[__name__].__doc__


class RemoteData(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(RemoteData, self).__init__(fv, fitsimage)

        # What port to connect to for requests
        self.port = 9909
        # What host to connect to
        self.host = 'localhost'

        self.ev_quit = fv.ev_quit

    def build_gui(self, container):
        vbox = Widgets.VBox()

        fr = Widgets.Frame("Remote Control")

        captions = [
            ("Addr:", 'label', "Addr", 'llabel'),
            ("Set Addr:", 'label', "Set Addr", 'entryset'),
            ("Remote Path:", 'label', "Remote Path", 'entry'),
            ]
        w, b = Widgets.build_info(captions)
        self.w.update(b)

        addr = self.host + ':' + str(self.port)
        b.addr.set_text(addr)

        b.set_addr.set_length(100)
        b.set_addr.set_text(addr)
        b.set_addr.set_tooltip("Set address to connect to remote server")
        b.set_addr.add_callback('activated', self.set_addr_cb)
        b.remote_path.add_callback('activated', self.load_cb)

        fr.set_widget(w)
        vbox.add_widget(fr, stretch=0)

        # stretch
        vbox.add_widget(Widgets.Label(''), stretch=1)

        btns = Widgets.HBox()
        btns.set_spacing(4)
        btns.set_border_width(4)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn)
        btns.add_widget(Widgets.Label(''), stretch=1)
        vbox.add_widget(btns)

        container.add_widget(vbox, stretch=1)


    def start(self):
        pass

    def stop(self):
        pass

    def restart_cb(self, w):
        # restart server
        self.server.stop()
        self.start()

    def set_addr_cb(self, w):
        # get and parse address
        addr = w.get_text()
        host, port = addr.split(':')
        self.host = host
        self.port = int(port)
        self.w.addr.set_text(addr)

        self.proxy = RemoteClient(self.host, self.port)

    def load_cb(self, w):
        path = w.get_text().strip()

        try:
            image = RemoteImage(self.proxy, logger=self.logger)
            image.load_file(path)

            chname = self.fv.get_channelName(self.fitsimage)
            imname = image.get('name', None)
            if imname is None:
                imname = self.fv.name_image_from_path(path)
                image.set(name=imname)

            self.logger.debug("Adding image '%s'" % (imname))
            self.fv.add_image(imname, image, chname=chname)

        except Exception as e:
            self.fv.show_error("Error loading remote image: %s" % (str(e)))

    def close(self):
        self.fv.stop_local_plugin(str(self))
        return True

    def __str__(self):
        return 'remotedata'


#END
