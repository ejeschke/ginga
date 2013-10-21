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

Examples:

 Create a new channel:
 $ grc ginga add_channel FOO
 
 Load a file:
 $ grc ginga load_file FOO /home/eric/testdata/SPCAM/SUPA01118797.fits

 Cut levels:
 $ grc channel FOO cut_levels 163 1300

 Auto cut levels:
 $ grc channel FOO auto_levels

 Zoom to a specific level:
 $ grc -- channel FOO zoom -7
 
 Zoom to fit:
 $ grc channel FOO zoom_fit
 
 Transform:
 $ grc channel FOO transform 1 0 1

 
"""
import sys
import numpy
import SimpleXMLRPCServer
import binascii
import bz2

from ginga import GingaPlugin
from ginga import AstroImage
from ginga import cmap

help_msg = sys.modules[__name__].__doc__


class RC(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(RC, self).__init__(fv)

        # What port to listen for requests
        self.port = 9000
        # If blank, listens on all interfaces
        self.host = ''

        self.ev_quit = fv.ev_quit

    # NO GUI...yet
    #def build_gui(self, container):
    #    pass
    
    def start(self):
        self.robj = GingaWrapper(self.fv, self.logger)
        
        self.server = SimpleXMLRPCServer.SimpleXMLRPCServer((self.host,
                                                             self.port))
        self.server.register_instance(self.robj)
        self.fv.nongui_do(self.monitor_shutdown)
        self.fv.nongui_do(self.server.serve_forever, poll_interval=0.1)
        
    def stop(self):
        self.server.shutdown()

    def monitor_shutdown(self):
        # the thread running this method waits until the entire viewer
        # is exiting and then shuts down the XML-RPC server which is
        # running in a different thread
        self.ev_quit.wait()
        self.server.shutdown()

    def __str__(self):
        return 'rc'

    
class GingaWrapper(object):

    def __init__(self, fv, logger):
        self.fv = fv
        self.logger = logger

        # List of XML-RPC acceptable return types
        self.ok_types = map(type, [str, int, float, bool, list, tuple])
        
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
        
        except Exception, e:
            # Some kind of error unpacking the data
            errmsg = "Error creating image data for '%s': %s" % (
                fitsname, str(e))
            self.logger.error(errmsg)
            raise GingaPlugin.PluginError(errmsg)

        # Enqueue image to display datasrc
        self.fv.gui_do(self.fv.add_image, fitsname, image,
                            chname=chname)
        return 0

    def _cleanse(self, res):
        """Transform results into XML-RPC friendy ones.
        """
        ptype = type(res)
        
        if ptype in self.ok_types:
            return res

        return str(res)
        
    def _prep_arg(self, arg):
        try:
            return float(arg)
        except ValueError:
            try:
                return int(arg)
            except ValueError:
                return arg
        
    def _prep_args(self, args):
        return map(self._prep_arg, args)
    
    def channel(self, chname, method, *args):
        chinfo = self.fv.get_channelInfo(chname)
        _method = getattr(chinfo.fitsimage, method)
        res = self.fv.gui_call(_method, *self._prep_args(args))
        return self._cleanse(res)
    
    def ginga(self, method, *args):
        _method = getattr(self.fv, method)
        res = self.fv.gui_call(_method, *self._prep_args(args))
        return self._cleanse(res)
    
#END
                                
