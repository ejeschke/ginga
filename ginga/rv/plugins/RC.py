#
# RC.py -- Remote Control plugin for Ginga fits viewer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys
import numpy
import bz2
from io import BytesIO

from ginga import GingaPlugin
from ginga import AstroImage
from ginga.gw import Widgets
from ginga.util import grc
from ginga.util.six.moves import map, zip

help_msg = sys.modules[__name__].__doc__


class RC(GingaPlugin.GlobalPlugin):
    """
    RC
    ==
    The RC plugin implements a remote control interface for the Ginga FITS
    viewer.

    Plugin Type: Global
    -------------------
    RC is a global plugin.  Only one instance can be opened.

    Usage
    -----
    Start the plugin.  The remote interface is not up and listening unless
    you do.

    Usage from the Command-Line Client
    ----------------------------------
    Show example usage:

      $ ggrc help

    Show help for a specific ginga method:

      $ ggrc help ginga <method>

    Show help for a specific channel method:

      $ ggrc help channel <chname> <method>

    Ginga methods can be called like this:

      $ ggrc ginga <method> <arg1> <arg2> ...

    Channel methods can be called like this:

      $ ggrc channel <chname> <method> <arg1> <arg2> ...

    Calls can be made from a remote host by adding the options:

       --host=<hostname> --port=9000

    (in the plugin GUI be sure to remove the 'localhost' prefix
    from the addr, but leave the colon and port)

    Examples
    --------

    Create a new channel:

      $ ggrc ginga add_channel FOO

    Load a file into current channel:

      $ ggrc ginga load_file /home/eric/testdata/SPCAM/SUPA01118797.fits

    Load a file into a specific channel:

      $ ggrc ginga load_file /home/eric/testdata/SPCAM/SUPA01118797.fits FOO

    Cut levels:

      $ ggrc channel FOO cut_levels 163 1300

    Auto cut levels:

      $ ggrc channel FOO auto_levels

    Zoom to a specific level:

      $ ggrc -- channel FOO zoom_to -7

    Zoom to fit:

      $ ggrc channel FOO zoom_fit

    Transform (args are boolean triplet: (flipx flipy swapxy)):

      $ ggrc channel FOO transform 1 0 1

    Rotate:

      $ ggrc channel FOO rotate 37.5

    Change color map:

      $ ggrc channel FOO set_color_map rainbow3

    Change color distribution algorithm:

      $ ggrc channel FOO set_color_algorithm log

    Change intensity map:

      $ ggrc channel FOO set_intensity_map neg

    """
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
        btn = Widgets.Button("Help")
        btn.add_callback('activated', lambda w: self.help())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        vbox.add_widget(btns)

        container.add_widget(vbox, stretch=1)


    def start(self):
        self.robj = GingaWrapper(self.fv, self.logger)

        self.server = grc.RemoteServer(self.robj,
                                       host=self.host, port=self.port,
                                       ev_quit=self.fv.ev_quit,
                                       logger=self.logger)
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
            chinfo = self.fv.get_channel(chname)
            _method = getattr(chinfo.viewer, method)
            return _method.__doc__

        else:
            return "Please use 'help ginga <method>' or 'help channel <chname> <method>'"

    def load_buffer(self, imname, chname, img_buf, dims, dtype,
                    header, metadata, compressed):
        """Display a FITS image buffer.

        Parameters
        ----------
        `imname`: string
            a name to use for the image in Ginga
        `chname`: string
            channel in which to load the image
        `img_buf`: string
            the image data, as a bytes object
        `dims`: tuple
            image dimensions in pixels (usually (height, width))
        `dtype`: string
            numpy data type of encoding (e.g. 'float32')
        `header`: dict
            fits file header as a dictionary
        `metadata`: dict
            other metadata about image to attach to image
        `compressed`: bool
            decompress buffer using "bz2"

        Returns
        -------
        0

        Notes
        -----
        * Get array dims: data.shape
        * Get array dtype: str(data.dtype)
        * Make a string from a numpy array: buf = data.tostring()
        * Compress the buffer: buf = bz2.compress(buf)
        """
        self.logger.info("received image data len=%d" % (len(img_buf)))

        # Unpack the data
        try:
            # Uncompress data if necessary
            decompress = metadata.get('decompress', None)
            if compressed  or (decompress == 'bz2'):
                img_buf = bz2.decompress(img_buf)

            # dtype string works for most instances
            if dtype == '':
                dtype = numpy.float32

            byteswap = metadata.get('byteswap', False)

            # WCS?
            if 'WCS-XIMG' in header.keys():
                from ginga.util import wcsmod
                from ginga.util.wcsmod.common import register_wcs
                from ginga.util.wcsmod.wcs_img import ImgWCS
                register_wcs('img', ImgWCS, ['pixel'])
                wcsmod.use('img')
                metadata = header.copy()

            # Create image container
            image = AstroImage.AstroImage(logger=self.logger)
            image.load_buffer(img_buf, dims, dtype, byteswap=byteswap,
                              metadata=metadata)
            image.update_keywords(header)
            image.set(name=imname, path=None)

        except Exception as e:
            # Some kind of error unpacking the data
            errmsg = "Error creating image data for '%s': %s" % (
                imname, str(e))
            self.logger.error(errmsg)
            raise GingaPlugin.PluginError(errmsg)

        # Display the image
        channel = self.fv.gui_call(self.fv.get_channel_on_demand, chname)

        # Note: this little hack needed to let window resize in time for
        # file to auto-size properly
        self.fv.gui_do(self.fv.change_channel, channel.name)

        self.fv.gui_do(self.fv.add_image, imname, image,
                       chname=channel.name)
        return 0

    def load_fits_buffer(self, imname, chname, file_buf, num_hdu,
                         metadata):
        from astropy.io import fits

        # Unpack the data
        try:
            # Uncompress data if necessary
            decompress = metadata.get('decompress', None)
            if decompress == 'bz2':
                file_buf = bz2.decompress(file_buf)

            self.logger.info("received data: len=%d num_hdu=%d" % (
                len(file_buf), num_hdu))

            in_f = BytesIO(file_buf)

            # Create image container
            with fits.open(in_f, 'readonly') as fits_f:
                image = AstroImage.AstroImage(metadata=metadata,
                                              logger=self.logger)
                image.load_hdu(fits_f[num_hdu], fobj=fits_f)
            image.set(name=imname, path=None, idx=num_hdu)

        except Exception as e:
            # Some kind of error unpacking the data
            errmsg = "Error creating image data for '%s': %s" % (
                imname, str(e))
            self.logger.error(errmsg)
            raise GingaPlugin.PluginError(errmsg)

        # Display the image
        channel = self.fv.gui_call(self.fv.get_channel_on_demand, chname)

        # Note: this little hack needed to let window resize in time for
        # file to auto-size properly
        self.fv.gui_do(self.fv.change_channel, channel.name)

        self.fv.gui_do(self.fv.add_image, imname, image,
                       chname=channel.name)
        return 0

    def channel(self, chname, method_name, *args, **kwdargs):
        chinfo = self.fv.get_channel(chname)
        _method = getattr(chinfo.viewer, method_name)
        return self.fv.gui_call(_method, *args, **kwdargs)

    def ginga(self, method_name, *args, **kwdargs):
        _method = getattr(self.fv, method_name)
        return self.fv.gui_call(_method, *args, **kwdargs)

    def canvas(self, chname, command, *args, **kwargs):
        chinfo = self.fv.get_channel(chname)
        canvas = chinfo.viewer.get_canvas()
        if command == 'add':
            klass = canvas.get_draw_class(args[0])
            newargs = args[1:]
            obj = klass(*newargs, **kwargs)
            return self.fv.gui_call(canvas.add, obj)
        elif command == 'clear':  # Clear only drawn objects, not the image
            nobj = len(canvas.objects)
            if nobj == 0:
                return
            elif nobj == 1:  # Assume it is the image, don't remove
                return
            else:
                canvas.objects = canvas.objects[0:1]
        elif command == 'nobj':
            return len(canvas.objects)
        else:
            print("Canvas RC command not recognized")
            return

#END
