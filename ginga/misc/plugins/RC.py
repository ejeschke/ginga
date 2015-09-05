#
# RC.py -- Remote Control plugin for Ginga fits viewer
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
The RC plugin implements a remote control interface for the Ginga FITS
viewer.

 Show example usage:
 $ grc help

 Show help for a specific ginga method:
 $ grc help ginga <method>

 Show help for a specific channel method:
 $ grc help channel <chname> <method>

Ginga methods can be called like this:

 $ grc ginga <method> <arg1> <arg2> ...

Channel methods can be called like this:

 $ grc channel <chname> <method> <arg1> <arg2> ...

Calls can be made from a remote host by adding the options
   --host=<hostname> --port=9000

(in the plugin GUI be sure to remove the 'localhost' prefix
from the addr, but leave the colon and port)

Examples:

 Create a new channel:
 $ grc ginga add_channel FOO

 Load a file into current channel:
 $ grc ginga load_file /home/eric/testdata/SPCAM/SUPA01118797.fits

 Load a file into a specific channel:
 $ grc ginga load_file /home/eric/testdata/SPCAM/SUPA01118797.fits FOO

 Cut levels:
 $ grc channel FOO cut_levels 163 1300

 Auto cut levels:
 $ grc channel FOO auto_levels

 Zoom to a specific level:
 $ grc -- channel FOO zoom_to -7

 Zoom to fit:
 $ grc channel FOO zoom_fit

 Transform (args are boolean triplet: (flipx flipy swapxy)):
 $ grc channel FOO transform 1 0 1

 Rotate:
 $ grc channel FOO rotate 37.5

 Change color map:
 $ grc channel FOO set_color_map rainbow3

 Change color distribution algorithm:
 $ grc channel FOO set_color_algorithm log

 Change intensity map:
 $ grc channel FOO set_intensity_map neg

"""
import sys
import numpy
import binascii
import bz2

from ginga import GingaPlugin
from ginga import AstroImage
from ginga.gw import Widgets
from ginga.util import grc
from ginga.util.six.moves import map, zip

help_msg = sys.modules[__name__].__doc__


class RC(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(RC, self).__init__(fv)

        # What port to listen for requests
        self.port = 9000
        # If blank, listens on all interfaces
        self.host = 'localhost'

        self.ev_quit = fv.ev_quit

    def build_gui(self, container):
        vbox = Widgets.VBox()

        fr = Widgets.Frame("Remote Control")

        captions = [
            ("Addr:", 'label', "Addr", 'llabel', 'Restart', 'button'),
            ("Set Addr:", 'label', "Set Addr", 'entry'),
            ]
        w, b = Widgets.build_info(captions)
        self.w.update(b)

        addr = self.host + ':' + str(self.port)
        b.addr.set_text(addr)
        b.restart.set_tooltip("Restart the server")
        b.restart.add_callback('activated', self.restart_cb)

        b.set_addr.set_length(100)
        b.set_addr.set_text(addr)
        b.set_addr.set_tooltip("Set address to run remote control server")
        b.set_addr.add_callback('activated', self.set_addr_cb)

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
        self.robj = GingaWrapper(self.fv, self.logger)

        self.server = grc.RemoteServer(self.robj, host=self.host, port=self.port,
                                       ev_quit=self.fv.ev_quit)
        self.server.start(thread_pool=self.fv.get_threadPool())

    def stop(self):
        self.server.stop()

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

    def close(self):
        self.fv.stop_global_plugin(str(self))
        return True

    def __str__(self):
        return 'rc'


class GingaWrapper(object):

    def __init__(self, fv, logger):
        self.fv = fv
        self.logger = logger

        # List of XML-RPC acceptable return types
        self.ok_types = list(map(type, [str, int, float, bool, list, tuple]))

    def help(self, *args):
        """Get help for a remote interface method.

        Examples
        --------
        help('ginga', `method`)
           name of the method for which you want help

        help('channel', `chname`, `method`)
           name of the method in the channel for which you want help

        Returns
        -------
        help: string
          a help message
        """
        if len(args) == 0:
            return help_msg

        which = args[0].lower()

        if which == 'ginga':
            method = args[1]
            _method = getattr(self.fv, method)
            return _method.__doc__

        elif which == 'channel':
            chname = args[1]
            method = args[2]
            chinfo = self.fv.get_channelInfo(chname)
            _method = getattr(chinfo.fitsimage, method)
            return _method.__doc__

        else:
            return "Please use 'help ginga <method>' or 'help channel <chname> <method>'"

    def load_buffer(self, imname, chname, data, dims, dtype,
                    header, metadata, compressed):
        """Display a FITS image buffer.

        Parameters
        ----------
        `imname`: string
            a name to use for the image in Ginga
        `chname`: string
            channel in which to load the image
        `data`: string
            the image data, encoded as a base64 ascii encoded string
        `dims`: tuple
            image dimensions in pixels (usually (height, width))
        `dtype`: string
            numpy data type of encoding (e.g. 'float32')
        `header`: dict
            fits file header as a dictionary
        `metadata`: dict
            other metadata about image to attach to image
        `compressed`: boolean
            True if `data` is bz2 compressed before ascii encoding

        Returns
        -------
        0

        Notes
        -----
        * Get array dims: data.shape
        * Get array dtype: str(data.dtype)
        * Make a string from a numpy array: buf = data.tostring()
        * Compress the buffer: buf = bz2.compress(buf)
        * Convert buffer to ascii-encoding: buf = binascii.b2a_base64(buf)
        """

        # Unpack the data
        try:
            # Decode binary data
            data = binascii.a2b_base64(data)

            # Uncompress data if necessary
            if compressed:
                data = bz2.decompress(data)

            if dtype == '':
                dtype = numpy.float32
            else:
                # string to actual type
                dtype = getattr(numpy, dtype)

            # Create image container
            image = AstroImage.AstroImage(logger=self.logger)
            image.load_buffer(data, dims, dtype, byteswap=byteswap,
                              metadata=metadata)
            image.set(name=imname)
            image.update_keywords(header)

        except Exception as e:
            # Some kind of error unpacking the data
            errmsg = "Error creating image data for '%s': %s" % (
                fitsname, str(e))
            self.logger.error(errmsg)
            raise GingaPlugin.PluginError(errmsg)

        # Enqueue image to display datasrc
        self.fv.gui_do(self.fv.add_image, fitsname, image,
                            chname=chname)
        return 0

    def channel(self, chname, method_name, *args, **kwdargs):
        chinfo = self.fv.get_channelInfo(chname)
        _method = getattr(chinfo.fitsimage, method_name)
        return self.fv.gui_call(_method, *args, **kwdargs)

    def ginga(self, method_name, *args, **kwdargs):
        _method = getattr(self.fv, method_name)
        return self.fv.gui_call(_method, *args, **kwdargs)


#END
