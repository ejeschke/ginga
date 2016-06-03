#
# Control.py -- Controller for the Ginga FITS viewer.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
# stdlib imports
import sys, os
import traceback
import re, time
import tempfile
import ginga.util.six as six
if six.PY2:
    import thread
    import Queue
else:
    import _thread as thread
    import queue as Queue
import threading
import logging
import mimetypes
from collections import deque
import atexit, shutil
from datetime import datetime

import numpy
magic_tester = None
try:
    import magic
    have_magic = True
    # it seems there are conflicting versions of a 'magic'
    # module for python floating around...*sigh*
    if not hasattr(magic, 'from_file'):
        # TODO: do this at program start only
        magic_tester = magic.open(magic.DEFAULT_MODE)
        magic_tester.load()

except (ImportError, Exception):
    have_magic = False

# Local application imports
from ginga import cmap, imap, AstroImage, RGBImage, ImageView
from ginga.misc import Bunch, Datasrc, Callback, Timer, Task, Future
from ginga.util import catalog, iohelper
from ginga.canvas.CanvasObject import drawCatalog

# Version
from ginga import __version__

#pluginconfpfx = 'plugins'
pluginconfpfx = None

packageHome = os.path.split(sys.modules[__name__].__file__)[0]


class ControlError(Exception):
    pass


class GingaControl(Callback.Callbacks):
    """Main Ginga control.

    """
    def __init__(self, logger, threadPool, module_manager, preferences,
                 ev_quit=None):
        Callback.Callbacks.__init__(self)

        self.logger = logger
        self.mm = module_manager
        self.prefs = preferences
        # event for controlling termination of threads executing in this
        # object
        if not ev_quit:
            self.ev_quit = threading.Event()
        else:
            self.ev_quit = ev_quit

        self.tmpdir = tempfile.mkdtemp()
        # remove temporary directory on exit
        atexit.register(_rmtmpdir, self.tmpdir)

        # For callbacks
        for name in ('add-image', 'channel-change', 'remove-image',
                     'add-channel', 'delete-channel', 'field-info',
                     'add-image-info', 'add-operation'):
            self.enable_callback(name)

        # Initialize the timer factory
        self.timer_factory = Timer.TimerFactory(ev_quit=self.ev_quit,
                                                logger=self.logger)
        self.timer_factory.wind()

        self.lock = threading.RLock()
        self.channel = {}
        self.channelNames = []
        self.cur_channel = None
        self.wscount = 0
        self.statustask = None
        self.preload_lock = threading.RLock()
        self.preload_list = deque([], 4)

        # Create general preferences
        self.settings = self.prefs.createCategory('general')
        self.settings.load(onError='silent')
        # Load bindings preferences
        bindprefs = self.prefs.createCategory('bindings')
        bindprefs.load(onError='silent')

        self.settings.addDefaults(fixedFont='Monospace',
                                  sansFont='Sans',
                                  channel_follows_focus=False,
                                  share_readout=True,
                                  numImages=10,
                                  # Offset to add to numpy-based coords
                                  pixel_coords_offset=1.0,
                                  # inherit from primary header
                                  inherit_primary_header=False,
                                  cursor_interval=0.050)

        # Should channel change as mouse moves between windows
        self.channel_follows_focus = self.settings['channel_follows_focus']

        self.global_plugins = {}
        self.local_plugins = {}

        # some default colormap info
        self.cm = cmap.get_cmap("gray")
        self.im = imap.get_imap("ramp")

        # This plugin manager handles "global" (aka standard) plug ins
        # (unique instances, not per channel)
        self.gpmon = self.getPluginManager(self.logger, self,
                                           None, self.mm)

        # Initialize catalog and image server bank
        self.imgsrv = catalog.ServerBank(self.logger)

        self.operations = []

        # state for implementing field-info callback
        self._cursor_task = self.get_timer()
        self._cursor_task.set_callback('expired', self._cursor_timer_cb)
        self._cursor_last_update = time.time()
        self.cursor_interval = self.settings.get('cursor_interval', 0.050)


    def get_ServerBank(self):
        return self.imgsrv

    def get_preferences(self):
        return self.prefs

    def get_timer(self):
        return self.timer_factory.timer()

    ####################################################
    # CALLBACKS
    ####################################################

    def showxy(self, viewer, data_x, data_y):
        """Called by the mouse-tracking callback to handle reporting of
        cursor position to various plugins that subscribe to the
        'field-info' callback.
        """
        # This is an optimization to get around slow coordinate
        # transformation by astropy and possibly other WCS packages,
        # which causes delay for other mouse tracking events, e.g.
        # the zoom plugin.
        # We only update the under cursor information every period
        # defined by (self.cursor_interval) sec.
        #
        # If the refresh interval has expired then update the info;
        # otherwise (re)set the timer until the end of the interval.
        cur_time = time.time()
        elapsed = cur_time - self._cursor_last_update
        if elapsed > self.cursor_interval:
            # cancel timer
            self._cursor_task.clear()
            self._showxy(viewer, data_x, data_y)
        else:
            # store needed data into the timer data area
            self._cursor_task.data.setvals(viewer=viewer,
                                           data_x=data_x, data_y=data_y)
            # calculate delta until end of refresh interval
            period = self.cursor_interval - elapsed
            # set timer conditionally (only if it hasn't yet been set)
            self._cursor_task.cond_set(period)
        return True

    def _cursor_timer_cb(self, timer):
        """Callback when the cursor timer expires.
        """
        data = timer.data
        self.gui_do(self._showxy, data.viewer, data.data_x, data.data_y)

    def _showxy(self, viewer, data_x, data_y):
        """Update the info from the last position recorded under the cursor.
        """
        self._cursor_last_update = time.time()
        try:
            image = viewer.get_image()
            if image is None:
                # No image loaded for this channel
                return

            settings = viewer.get_settings()
            info = image.info_xy(data_x, data_y, settings)

            # Are we reporting in data or FITS coordinates?
            off = self.settings.get('pixel_coords_offset', 0.0)
            info.x += off
            info.y += off

        except Exception as e:
            self.logger.warning("Can't get info under the cursor: %s" % (str(e)))
            return

        self.make_callback('field-info', viewer, info)

        self.update_pending()
        return True

    def motion_cb(self, viewer, button, data_x, data_y):
        """Motion event in the big fits window.  Show the pointing
        information under the cursor.
        """
        ## if button == 0:
        ##     self.showxy(viewer, data_x, data_y)
        self.showxy(viewer, data_x, data_y)
        return True

    def keypress(self, viewer, keyname):
        """Key press event in a channel window."""
        chname = self.get_channelName(viewer)
        self.logger.debug("key press (%s) in channel %s" % (
            keyname, chname))
        # TODO: keyboard accelerators to raise tabs need to be integrated into
        #   the desktop object
        if keyname == 'Z':
            self.ds.raise_tab('Zoom')
        ## elif keyname == 'T':
        ##     self.ds.raise_tab('Thumbs')
        elif keyname == 'I':
            self.ds.raise_tab('Info')
        elif keyname == 'H':
            self.ds.raise_tab('Header')
        elif keyname == 'C':
            self.ds.raise_tab('Contents')
        elif keyname == 'D':
            self.ds.raise_tab('Dialogs')
        elif keyname == 'F':
            self.build_fullscreen()
        elif keyname == 'f':
            self.toggle_fullscreen()
        elif keyname == 'm':
            self.maximize()
        elif keyname == '<':
            self.collapse_pane('left')
        elif keyname == '>':
            self.collapse_pane('right')
        elif keyname == 'n':
            self.next_channel()
        elif keyname == 'j':
            self.cycle_workspace_type()
        elif keyname == 'k':
            self.add_channel_auto()
        ## elif keyname == 'escape':
        ##     self.reset_viewer()
        elif keyname in ('up',):
            self.prev_img()
        elif keyname in ('down',):
            self.next_img()
        elif keyname in ('left',):
            self.prev_channel()
        elif keyname in ('right',):
            self.next_channel()
        return True

    def dragdrop(self, viewer, urls):
        """Called when a drop operation is performed on our main window.
        We are called back with a URL and we attempt to load it if it
        names a file.
        """
        for url in urls:
            to_chname = self.get_channelName(viewer)

            ## self.load_file(url)
            self.nongui_do(self.load_file, url, chname=to_chname,
                           wait=False)
        return True

    def force_focus_cb(self, viewer, event, data_x, data_y):
        chname = self.get_channelName(viewer)
        self.change_channel(chname, raisew=True)
        return True

    def focus_cb(self, viewer, tf, name):
        """Called when ``viewer`` gets ``(tf==True)`` or loses
        ``(tf==False)`` the focus.
        """
        if not self.channel_follows_focus:
            return True
        self.logger.debug("Focus %s=%s" % (name, tf))
        if tf:
            if viewer != self.getfocus_viewer():
                self.change_channel(name, raisew=False)

        return True

    def stop(self):
        self.logger.info("shutting down Ginga...")
        self.timer_factory.quit()
        self.ev_quit.set()
        self.logger.debug("should be exiting now")

    def reset_viewer(self):
        channel = self.get_current_channel()
        opmon = channel.opmon
        opmon.deactivate_focused()
        self.normalsize()

    def get_draw_class(self, drawtype):
        drawtype = drawtype.lower()
        return drawCatalog[drawtype]

    def get_draw_classes(self):
        return drawCatalog

    def make_async_gui_callback(self, name, *args, **kwdargs):
        # NOTE: asynchronous!
        self.gui_do(self.make_callback, name, *args, **kwdargs)

    def make_gui_callback(self, name, *args, **kwdargs):
        if self.is_gui_thread():
            return self.make_callback(name, *args, **kwdargs)
        else:
            # note: this cannot be "gui_call"--locks viewer.
            # so call becomes async when a non-gui thread invokes it
            self.gui_do(self.make_callback, name, *args, **kwdargs)

    # PLUGIN MANAGEMENT

    def start_operation(self, opname):
        return self.start_local_plugin(None, opname, None)

    def stop_operation_channel(self, chname, opname):
        self.logger.warning("Do not use this method name--it will be deprecated!")
        return self.stop_local_plugin(chname, opname)

    def start_local_plugin(self, chname, opname, future):
        channel = self.get_channel(chname)
        opmon = channel.opmon
        opmon.start_plugin_future(channel.name, opname, future)
        channel.viewer.onscreen_message(opname, delay=1.0)

    def stop_local_plugin(self, chname, opname):
        channel = self.get_channel(chname)
        opmon = channel.opmon
        opmon.deactivate(opname)

    def start_global_plugin(self, pluginName, raise_tab=False):
        self.gpmon.start_plugin_future(None, pluginName, None)
        if raise_tab:
            pInfo = self.gpmon.getPluginInfo(pluginName)
            self.ds.raise_tab(pInfo.tabname)

    def stop_global_plugin(self, pluginName):
        self.gpmon.deactivate(pluginName)

    def add_local_plugin(self, spec):
        try:
            name = spec.setdefault('name', spec.get('klass', spec.module))
            self.local_plugins[name] = spec

            pfx = spec.get('pfx', pluginconfpfx)
            self.mm.loadModule(spec.module, pfx=pfx)

            hidden = spec.get('hidden', False)
            if not hidden:
                self.add_operation(name)

        except Exception as e:
            self.logger.error("Unable to load local plugin '%s': %s" % (
                name, str(e)))

    def add_operation(self, opname):
        self.operations.append(opname)
        self.make_callback('add-operation', opname)

    def get_operations(self):
        return self.operations

    def add_global_plugin(self, spec):
        try:
            name = spec.setdefault('name', spec.get('klass', spec.module))
            self.global_plugins[name] = spec

            pfx = spec.get('pfx', pluginconfpfx)
            self.mm.loadModule(spec.module, pfx=pfx)

            self.gpmon.loadPlugin(name, spec)
            self.add_plugin_menu(name)

            start = spec.get('start', True)
            if start:
                self.start_global_plugin(name, raise_tab=False)

        except Exception as e:
            self.logger.error("Unable to load global plugin '%s': %s" % (
                name, str(e)))

    def show_error(self, errmsg, raisetab=True):
        if self.gpmon.has_plugin('Errors'):
            obj = self.gpmon.getPlugin('Errors')
            obj.add_error(errmsg)
            if raisetab:
                self.ds.raise_tab('Errors')

    def error_wrap(self, method, *args, **kwdargs):
        try:
            return method(*args, **kwdargs)

        except Exception as e:
            errmsg = "\n".join([e.__class__.__name__, str(e)])
            try:
                (type, value, tb) = sys.exc_info()
                tb_str = "\n".join(traceback.format_tb(tb))
            except Exception as e:
                tb_str = "Traceback information unavailable."
            errmsg += tb_str
            self.logger.error(errmsg)
            self.gui_do(self.show_error, errmsg, raisetab=True)

    def help(self):
        if not self.gpmon.has_plugin('WBrowser'):
            self.logger.error("help() requires 'WBrowser' plugin")
            return

        self.start_global_plugin('WBrowser')

        localDoc = os.path.join(packageHome, 'doc', 'help.html')
        if not os.path.exists(localDoc):
            url = "https://ginga.readthedocs.io/en/latest"
        else:
            url = "file:%s" % (os.path.abspath(localDoc))

        # TODO: need to let GUI finish processing, it seems
        self.update_pending()

        obj = self.gpmon.getPlugin('WBrowser')
        obj.browse(url)

    # BASIC IMAGE OPERATIONS

    def guess_filetype(self, filepath):
        # If we have python-magic, use it to determine file type
        typ = None
        if have_magic:
            try:
                # it seems there are conflicting versions of a 'magic'
                # module for python floating around...*sigh*
                if hasattr(magic, 'from_file'):
                    typ = magic.from_file(filepath, mime=True)

                elif magic_tester is not None:
                    descrip = magic_tester.file(filepath)
                    if descrip.startswith("FITS image data"):
                        return ('image', 'fits')

            except Exception as e:
                self.logger.warning("python-magic error: %s; falling back "
                                    "to 'mimetypes'" % (str(e)))

        if typ is None:
            try:
                typ, enc = mimetypes.guess_type(filepath)
            except Exception as e:
                self.logger.warning("mimetypes error: %s; can't determine "
                                    "file type" % (str(e)))

        if typ:
            typ, subtyp = typ.split('/')
            self.logger.debug("MIME type is %s/%s" % (typ, subtyp))
            return (typ, subtyp)

        raise ControlError("Can't determine file type of '%s'" % (filepath))

    def load_image(self, filepath, idx=None):

        info = iohelper.get_fileinfo(filepath, cache_dir=self.tmpdir)
        filepfx = info.filepath
        if idx is None:
            idx = info.numhdu

        # Create an image.  Assume type to be an AstroImage unless
        # the MIME association says it is something different.
        try:
            typ, subtyp = self.guess_filetype(filepfx)

        except Exception as e:
            self.logger.warning("error determining file type: %s; "
                                "assuming 'image/fits'" % (str(e)))
            # Can't determine file type: assume and attempt FITS
            typ, subtyp = 'image', 'fits'

        kwdargs = {}

        self.logger.debug("assuming file type: %s/%s'" % (typ, subtyp))
        if (typ == 'image') and (subtyp not in ('fits', 'x-fits')):
            image = RGBImage.RGBImage(logger=self.logger)
            filepath = filepfx
        else:
            inherit_prihdr = self.settings.get('inherit_primary_header', False)
            image = AstroImage.AstroImage(logger=self.logger,
                                          inherit_primary_header=inherit_prihdr)
            kwdargs.update(dict(numhdu=idx))

        try:
            self.logger.info("Loading image from %s kwdargs=%s" % (
                filepath, str(kwdargs)))
            image.load_file(filepath, **kwdargs)

        except Exception as e:
            errmsg = "Failed to load file '%s': %s" % (
                filepath, str(e))
            self.logger.error(errmsg)
            try:
                (type, value, tb) = sys.exc_info()
                tb_str = "\n".join(traceback.format_tb(tb))
            except Exception as e:
                tb_str = "Traceback information unavailable."
            self.gui_do(self.show_error, errmsg + '\n' + tb_str)
            #channel.viewer.onscreen_message("Failed to load file", delay=1.0)
            raise ControlError(errmsg)

        self.logger.debug("Successfully loaded file into image object.")
        return image

    def get_fileinfo(self, filespec, dldir=None):
        """Break down a file specification into its components.

        Parameters
        ----------
        filespec : str
            The path of the file to load (can be a URL).

        dldir

        Returns
        -------
        res : `~ginga.misc.Bunch.Bunch`

        """
        if dldir is None:
            dldir = self.tmpdir

        # Get information about this file/URL
        info = iohelper.get_fileinfo(filespec, cache_dir=dldir)

        if (not info.ondisk) and (info.url is not None) and \
               (not info.url.startswith('file:')):
            # Download the file if a URL was passed
            def  _dl_indicator(count, blksize, totalsize):
                pct = float(count * blksize) / float(totalsize)
                msg = "Downloading: %%%.2f complete" % (pct*100.0)
                self.gui_do(self.showStatus, msg)

            # Try to download the URL.  We press our generic URL server
            # into use as a generic file downloader.
            try:
                dl = catalog.URLServer(self.logger, "downloader", "dl",
                                       info.url, "")
                filepath = dl.retrieve(info.url, filepath=info.filepath,
                                       cb_fn=_dl_indicator)
            finally:
                self.gui_do(self.showStatus, "")

        return info

    def name_image_from_path(self, path, idx=None):
        return iohelper.name_image_from_path(path, idx=idx)

    def load_file(self, filepath, chname=None, wait=True,
                  create_channel=True, display_image=True,
                  image_loader=None):
        """Load a file from filesystem and display it.

        Parameters
        ----------
        filepath : str
            The path of the file to load (can be a URL).

        chname : str, optional
            The name of the channel in which to display the image.

        wait : bool, optional
            If `True`, then wait for the file to be displayed before returning
            (synchronous behavior).

        create_channel : bool, optional
            Create channel.

        display_image : bool, optional
            If not `False`, then will load the image.

        image_loader : func, optional
            A special image loader, if provided.

        Returns
        -------
        image
            The image object that was loaded.

        """
        if not chname:
            channel = self.get_current_channel()
            chname = channel.name
        else:
            if not self.has_channel(chname) and create_channel:
                self.gui_call(self.add_channel, chname)
            channel = self.get_channel(chname)
            chname = channel.name

        if image_loader is None:
            image_loader = self.load_image

        info = self.get_fileinfo(filepath)
        filepath = info.filepath

        kwdargs = {}
        idx = None
        if info.numhdu is not None:
            kwdargs['idx'] = info.numhdu

        try:
            image = image_loader(filepath, **kwdargs)

        except Exception as e:
            errmsg = "Failed to load '%s': %s" % (filepath, str(e))
            self.gui_do(self.show_error, errmsg)

        future = Future.Future()
        future.freeze(image_loader, filepath, **kwdargs)

        # Save a future for this image to reload it later if we
        # have to remove it from memory
        image.set(loader=image_loader, image_future=future)

        if image.get('path', None) is None:
            image.set(path=filepath)

        # Assign a name to the image if the loader did not.
        name = image.get('name', None)
        if name is None:
            name = self.name_image_from_path(filepath, idx=idx)
            image.set(name=name)

        if display_image:
            # Display image.  If the wait parameter is False then don't wait
            # for the image to load into the viewer
            if wait:
                self.gui_call(self.add_image, name, image, chname=chname)
            else:
                self.gui_do(self.bulk_add_image, name, image, chname)
                #self.gui_do(self.add_image, name, image, chname=chname)

        # Return the image
        return image

    def add_preload(self, chname, image_info):
        bnch = Bunch.Bunch(chname=chname, info=image_info)
        with self.preload_lock:
            self.preload_list.append(bnch)
        self.nongui_do(self.preload_scan)

    def preload_scan(self):
        # preload any pending files
        # TODO: do we need any throttling of loading here?
        with self.preload_lock:
            while len(self.preload_list) > 0:
                bnch = self.preload_list.pop()
                self.nongui_do(self.preload_file, bnch.chname,
                               bnch.info.name, bnch.info.path,
                               image_future=bnch.info.image_future)

    def preload_file(self, chname, imname, path, image_future=None):
        # sanity check to see if the file is already in memory
        self.logger.debug("preload: checking %s in %s" % (imname, chname))
        channel = self.get_channel(chname)
        datasrc = channel.datasrc

        if not channel.datasrc.has_key(imname):
            # not there--load image in a non-gui thread, then have the
            # gui add it to the channel silently
            self.logger.info("preloading image %s" % (path))
            if image_future is None:
                # TODO: need index info?
                image = self.load_image(path)
            else:
                image = image_future.thaw()

            self.gui_do(self.add_image, imname, image,
                           chname=chname, silent=True)
        self.logger.debug("end preload")

    def zoom_in(self):
        viewer = self.getfocus_viewer()
        viewer.zoom_in()
        return True

    def zoom_out(self):
        viewer = self.getfocus_viewer()
        viewer.zoom_out()
        return True

    def zoom_1_to_1(self):
        viewer = self.getfocus_viewer()
        viewer.zoom_to(1)
        return True

    def zoom_fit(self):
        viewer = self.getfocus_viewer()
        viewer.zoom_fit()
        return True

    def auto_levels(self):
        viewer = self.getfocus_viewer()
        viewer.auto_levels()

    def prev_img(self, loop=True):
        channel = self.get_current_channel()
        channel.prev_image()
        return True

    def next_img(self, loop=True):
        channel = self.get_current_channel()
        channel.next_image()
        return True

    def get_current_workspace(self):
        # TODO: track current workspace
        return self.ds.get_ws('channels')

    def prev_channel(self):
        ws = self.get_current_workspace()
        ws.to_previous()
        idx = ws.nb.get_index()
        child = ws.nb.index_to_widget(idx)
        chname = child.extdata.tab_title
        self.change_channel(chname, raisew=True)

    def next_channel(self):
        ws = self.get_current_workspace()
        ws.to_next()
        idx = ws.nb.get_index()
        child = ws.nb.index_to_widget(idx)
        chname = child.extdata.tab_title
        self.change_channel(chname, raisew=True)

    def add_channel_auto(self):
        ws = self.get_current_workspace()
        chname = self.make_channel_name('Image')
        self.add_channel(chname, workspace=ws.name)

    def configure_workspace(self, wstype):
        ws = self.get_current_workspace()
        ws.configure_wstype(wstype)

    def cycle_workspace_type(self):
        ws = self.get_current_workspace()
        ws.cycle_wstype()

    def add_workspace(self, wsname, wstype, inSpace='channels'):

        ws = self.ds.make_ws(name=wsname, group=1, wstype=wstype)
        if inSpace != 'top level':
            self.ds.add_tab(inSpace, ws.widget, 1, ws.name)
        else:
            #width, height = 700, 800
            #self.ds.create_toplevel_ws(width, height, group=1)
            self.ds.add_toplevel(ws, ws.name)

        if ws.widget.has_callback('page-closed'):
            ws.widget.add_callback('page-closed', self.page_closed_cb, wsname)

        return True

    # CHANNEL MANAGEMENT

    def add_image(self, imname, image, chname=None, silent=False):
        if chname is None:
            channel = self.get_current_channel()
            if channel is None:
                raise ValueError("Need to provide a channel name to add "
                                 "the image")
            chname = channel.name

        # add image to named channel
        channel = self.get_channel_on_demand(chname)
        channel.add_image(image, silent=silent)

    def advertise_image(self, chname, image):
        channel = self.get_channel(chname)
        info = channel.get_image_info(image.get('name'))

        self.make_gui_callback('add-image', chname, image, info)

    def bulk_add_image(self, imname, image, chname):
        channel = self.get_channel_on_demand(chname)
        channel.add_image(image, bulk_add=True)

    def get_image(self, chname, imname):
        channel = self.get_channel(chname)
        if channel is None:
            return None
        return channel.get_loaded_image(imname)

    def getfocus_viewer(self):
        channel = self.get_current_channel()
        if channel is None:
            return None
        return channel.viewer

    def get_viewer(self, chname):
        channel = self.get_channel(chname)
        if channel is None:
            return None
        return channel.viewer

    # TO BE DEPRECATED EVENTUALLY
    getfocus_fitsimage = getfocus_viewer
    get_fitsimage = get_viewer

    def switch_name(self, chname, imname, path=None,
                    image_future=None):

        try:
            # create channel if it doesn't exist already
            channel = self.get_channel_on_demand(chname)
            channel.switch_name(imname)

            self.change_channel(channel.name)
        except Exception as e:
            self.logger.error("Couldn't switch to image '%s': %s" % (
                str(imname), str(e)))

    def _redo_plugins(self, image, channel):
        # New data in channel
        # update active global plugins
        opmon = self.gpmon
        for key in opmon.get_active():
            obj = opmon.getPlugin(key)
            try:
                self.gui_do(obj.redo, channel, image)

            except Exception as e:
                self.logger.error("Failed to continue operation: %s" % (str(e)))
                # TODO: log traceback?

        # update active local plugins
        opmon = channel.opmon
        for key in opmon.get_active():
            obj = opmon.getPlugin(key)
            try:
                self.gui_do(obj.redo)

            except Exception as e:
                self.logger.error("Failed to continue operation: %s" % (str(e)))
                # TODO: log traceback?

    def _close_plugins(self, channel):
        """Close all plugins associated with the channel."""
        opmon = channel.opmon
        for key in opmon.get_active():
            obj = opmon.getPlugin(key)
            try:
                self.gui_do(obj.close)

            except Exception as e:
                self.logger.error("Failed to continue operation: %s" % (str(e)))
                # TODO: log traceback?

    def channel_image_updated(self, channel, image):

        with self.lock:
            self.logger.debug("Update image start")
            start_time = time.time()

            # add cb so that if image is modified internally
            #  our plugins get updated
            image.add_callback('modified', self._redo_plugins, channel)

            self.logger.debug("executing redo() in plugins...")
            self._redo_plugins(image, channel)

            split_time1 = time.time()
            self.logger.info("Large image update: %.4f sec" % (
                split_time1 - start_time))

    def change_channel(self, chname, image=None, raisew=True):
        self.logger.debug("change channel: %s" % (chname))
        name = chname.lower()
        if self.cur_channel is None:
            oldchname = None
        else:
            oldchname = self.cur_channel.name.lower()

        channel = self.get_channel(name)

        if name != oldchname:
            with self.lock:
                self.cur_channel = channel

        if name != oldchname:
            # raise tab
            if raisew:
                #self.ds.raise_tab(channel.workspace)
                self.ds.raise_tab(name)

            if oldchname is not None:
                try:
                    self.ds.highlight_tab(oldchname, False)
                except:
                    # old channel may not exist!
                    pass
            self.ds.highlight_tab(name, True)

            ## # Update title bar
            title = channel.name
            ## if image is not None:
            ##     name = image.get('name', 'Noname')
            ##     title += ": %s" % (name)
            self.set_titlebar(title)

        if image:
            channel.switch_image(image)

        self.make_gui_callback('channel-change', channel)

        self.update_pending()
        return True

    def has_channel(self, chname):
        name = chname.lower()
        with self.lock:
            return name in self.channel

    def get_channel(self, chname):
        return self.get_channelInfo(chname=chname)

    def get_current_channel(self):
        with self.lock:
            return self.cur_channel

    def get_channelInfo(self, chname=None):
        with self.lock:
            if not chname:
                return self.cur_channel
            name = chname.lower()
            return self.channel[name]

    def get_channel_on_demand(self, chname):
        if self.has_channel(chname):
            return self.get_channel(chname)

        return self.gui_call(self.add_channel, chname)

    def get_channelName(self, viewer):
        with self.lock:
            items = self.channel.items()
        for name, channel in items:
            if channel.viewer == viewer:
                return channel.name
        return None

    def make_channel_name(self, pfx):
        i = 0
        while i < 10000:
            chname = pfx + str(i)
            if not self.has_channel(chname):
                return chname
            i += 1
        return pfx + str(time.time())

    def add_channel(self, chname, workspace=None,
                    num_images=None, settings=None,
                    settings_template=None,
                    settings_share=None, share_keylist=None):
        """Create a new Ginga channel.

        Parameters
        ----------
        chname : str
            The name of the channel to create.

        workspace

        num_images

        settings

        settings_template

        settings_share

        share_keylist

        Returns
        -------
        channel : `~ginga.misc.Bunch.Bunch`
            The channel info bunch.

        """
        if self.has_channel(chname):
            return self.get_channel(chname)

        name = chname
        if settings is None:
            settings = self.prefs.createCategory('channel_'+name)
            try:
                settings.load(onError='raise')

            except Exception as e:
                self.logger.warning("no saved preferences found for channel "
                                    "'%s': %s" % (name, str(e)))

                # copy template settings to new channel
                if settings_template is not None:
                    osettings = settings_template
                    osettings.copySettings(settings)
                else:
                    try:
                        # use channel_Image as a template if one was not
                        # provided
                        osettings = self.prefs.getSettings('channel_Image')
                        self.logger.debug("Copying settings from 'Image' to "
                                          "'%s'" % (name))
                        osettings.copySettings(settings)
                    except KeyError:
                        pass

        if (share_keylist is not None) and (settings_share is not None):
            # caller wants us to share settings with another viewer
            settings_share.shareSettings(settings, keylist=share_keylist)

        # Make sure these preferences are at least defined
        if num_images is None:
            num_images = settings.get('numImages',
                                      self.settings.get('numImages', 1))
        settings.setDefaults(switchnew=True, numImages=num_images,
                             raisenew=True, genthumb=True,
                             preload_images=False, sort_order='loadtime')

        with self.lock:
            self.logger.debug("Adding channel '%s'" % (chname))
            channel = Channel(chname, self, datasrc=None,
                              settings=settings)

            bnch = self.add_viewer(chname, settings,
                                   workspace=workspace)
            # for debugging
            bnch.viewer.set_name('channel:%s' % (chname))

            opmon = self.getPluginManager(self.logger, self,
                                          self.ds, self.mm)

            channel.widget = bnch.view
            channel.container = bnch.container
            channel.workspace = bnch.workspace
            channel.viewer = bnch.viewer
            # older name, should eventually be deprecated
            channel.fitsimage = bnch.viewer
            channel.opmon = opmon

            name = chname.lower()
            self.channel[name] = channel

            # Update the channels control
            self.channelNames.append(chname)
            self.channelNames.sort()

            if len(self.channelNames) == 1:
                self.cur_channel = channel

        # Prepare local plugins for this channel
        for opname, spec in self.local_plugins.items():
            opmon.loadPlugin(opname, spec, chinfo=channel)

        self.make_gui_callback('add-channel', channel)
        return channel

    def delete_channel(self, chname):
        """Delete a given channel from viewer."""
        name = chname.lower()

        if len(self.channelNames) < 1:
            self.logger.error('Delete channel={0} failed. '
                              'No channels left.'.format(chname))
            return

        with self.lock:
            channel = self.channel[name]

            # Close local plugins open on this channel
            self._close_plugins(channel)

            # Update the channels control
            self.channelNames.remove(chname)
            self.channelNames.sort()

            self.ds.remove_tab(chname)
            del self.channel[name]
            self.prefs.remove_settings('channel_'+chname)

            # pick new channel
            if len(self.channelNames) > 0:
                self.change_channel(self.channelNames[0])
            else:
                self.cur_channel = None

        self.make_gui_callback('delete-channel', channel)

    def get_channelNames(self):
        with self.lock:
            return self.channelNames

    def scale2text(self, scalefactor):
        if scalefactor >= 1.0:
            #text = '%dx' % (int(scalefactor))
            text = '%.2fx' % (scalefactor)
        else:
            #text = '1/%dx' % (int(1.0/scalefactor))
            text = '1/%.2fx' % (1.0/scalefactor)
        return text

    def banner(self, raiseTab=False):
        bannerFile = os.path.join(self.iconpath, 'ginga-splash.ppm')
        chname = 'Ginga'
        self.add_channel(chname)
        channel = self.get_channel(chname)
        viewer = channel.viewer
        viewer.enable_autocuts('off')
        viewer.enable_autozoom('on')
        viewer.cut_levels(0, 255)

        #self.nongui_do(self.load_file, bannerFile, chname=chname)
        image = self.load_file(bannerFile, chname=chname, wait=False)

        # Insert Ginga version info
        header = image.get_header()
        header['VERSION'] = __version__

        if raiseTab:
            self.change_channel(chname)
            viewer.zoom_fit()

    def remove_image_by_name(self, chname, imname, impath=None):
        channel = self.get_channel(chname)
        viewer = channel.viewer
        self.logger.info("removing image %s" % (imname))
        # If this is the current image in the viewer, clear the viewer
        image = viewer.get_image()
        if image is not None:
            curname = image.get('name', 'NONAME')
            if curname == imname:
                viewer.clear()

        bnch = channel.remove_image(imname)
        self.make_async_gui_callback('remove-image', channel.name, imname, impath)

    def move_image_by_name(self, from_chname, imname, to_chname, impath=None):

        channel_from = self.get_channel(from_chname)
        channel_to = self.get_channel(to_chname)
        channel_from.move_image_to(imname, channel_to)

    def remove_current_image(self):
        channel = self.get_current_channel()
        viewer = channel.viewer
        image = viewer.get_image()
        if image is None:
            return
        imname = image.get('name', 'NONAME')
        impath = image.get('path', None)
        self.remove_image_by_name(channel.name, imname, impath=impath)

    def followFocus(self, tf):
        self.channel_follows_focus = tf

    def showStatus(self, text):
        """Write a message to the status bar.

        Parameters
        ----------
        text : str
            The message.

        """
        self.statusMsg("%s", text)

    def error(self, text):
        self.logger.error(text)
        self.statusMsg("%s", text)
        # TODO: turn bar red

    def logit(self, text):
        try:
            obj = self.gpmon.getPlugin('Log')
            self.gui_do(obj.log, text)
        except:
            pass

    def set_loglevel(self, level):
        handlers = self.logger.handlers
        for hdlr in handlers:
            hdlr.setLevel(level)

    def play_soundfile(self, filepath, format=None, priority=20):
        self.logger.debug("Subclass could override this to play sound file "
                          "'%s'" % (filepath))

    def get_color_maps(self):
        """Get the list of named color maps.

        Returns
        -------
        names : list
            A list of all named colormaps installed.

        """
        return cmap.get_names()

    def get_intensity_maps(self):
        """Get the list of named intensity maps.

        Returns
        -------
        names : list
            A list of all named intensity maps installed.

        """
        return imap.get_names()


    ########################################################
    ### TO BE DEPRECATED

    def getDrawClass(self, drawtype):
        #self.logger.warning("This method to be deprecated--use 'get_draw_class' instead")
        return self.get_draw_class(drawtype)

    def getDrawClasses(self):
        #self.logger.warning("This method to be deprecated--use 'get_draw_classes' instead")
        return self.get_draw_classes()


def _rmtmpdir(tmpdir):
    if os.path.isdir(tmpdir):
        shutil.rmtree(tmpdir)


class GuiLogHandler(logging.Handler):
    """Logs to a pane in the GUI."""

    def __init__(self, fv, level=logging.NOTSET):
        self.fv = fv
        logging.Handler.__init__(self, level=level)

    def emit(self, record):
        text = self.format(record)
        self.fv.logit(text)


class Channel(Callback.Callbacks):
    """Class to manage a channel.

    Parameters
    ----------
    name : str
        Name of the channel.

    fv
        Parent viewer.

    settings
        Channel settings.

    datasrc : `~ginga.misc.Datasrc.Datasrc`
        Data cache.

    """
    def __init__(self, name, fv, settings, datasrc=None):
        super(Channel, self).__init__()

        self.logger = fv.logger
        self.fv = fv
        self.settings = settings
        self.logger = fv.logger
        self.lock = threading.RLock()

        # CHANNEL ATTRIBUTES
        self.name = name
        self.widget = None
        self.container = None
        self.workspace = None
        self.opmon = None
        # this is the viewer we are connected to
        self.fitsimage = None
        if datasrc is None:
            num_images = self.settings.get('numImages', 1)
            datasrc = Datasrc.Datasrc(num_images)
        self.datasrc = datasrc
        self.cursor = -1
        self.history = []
        self.image_index = {}
        # external entities can attach stuff via this attribute
        self.extdata = Bunch.Bunch()

        self._configure_sort()
        self.settings.getSetting('sort_order').add_callback(
            'set', self._sort_changed_ext_cb)

    def connect_viewer(self, viewer):
        self.viewer = viewer

        # redraw top image
        self.refresh_cursor_image()

    def move_image_to(self, imname, channel):
        if self == channel:
            return

        self.copy_image_to(imname, channel)
        self.remove_image(imname)

    def copy_image_to(self, imname, channel, silent=False):
        if self == channel:
            return

        try:
            # copy image to other channel's datasrc if still
            # in memory
            image = self.datasrc[imname]

        except KeyError:
            # transfer image info
            info = self.image_index[imname]
            channel._add_info(info)
            return

        #channel.datasrc[imname] = image
        channel.add_image(image, silent=silent)

    def remove_image(self, imname):
        if self.datasrc.has_key(imname):
            self.datasrc.remove(imname)

        info = self.remove_history(imname)
        return info

    def get_image_names(self):
        return [ info.name for info in self.history ]

    def get_loaded_image(self, imname):
        """Get an image from memory.

        Parameters
        ----------
        imname : str
            Key, usually image name and extension.

        Returns
        -------
        image
            Image object.

        Raises
        ------
        KeyError
            Image is not in memory.

        """
        image = self.datasrc[imname]
        return image

    def add_image(self, image, silent=False, bulk_add=False):

        imname = image.get('name', None)
        assert imname is not None, \
               ValueError("image has no name")

        self.logger.debug("Adding image '%s' in channel %s" % (
            imname, self.name))

        self.datasrc[imname] = image

        idx = image.get('idx', None)
        path = image.get('path', None)
        image_loader = image.get('image_loader', None)
        image_future = image.get('image_future', None)
        info = self.add_history(imname, path,
                                image_loader=image_loader,
                                image_future=image_future,
                                idx=idx)

        # we'll get notified if an image changes and can update
        # metadata and make a chained callback
        image.add_callback('modified', self._image_modified_cb)

        if not silent:
            if not bulk_add:
                self._add_image_update(image, info)
                return

            # By using gui_do() here, more images may be bulk added
            # before the _add_image_update executes--it will then
            # only update the gui for the latest image, which saves
            # work
            self.fv.gui_do(self._add_image_update, image, info)

    def add_image_info(self, info):

        image_loader = info.get('image_loader', self.fv.load_image)

        # create an image_future if one does not exist
        image_future = info.get('image_future', None)
        if (image_future is None) and (info.path is not None):
            image_future = Future.Future()
            image_future.freeze(image_loader, info.path)

        info = self.add_history(info.name, info.path,
                                image_loader=image_loader,
                                image_future=image_future)
        self.fv.make_async_gui_callback('add-image-info', self, info)

    def get_image_info(self, imname):
        return self.image_index[imname]

    def _add_image_update(self, image, info):
        self.fv.make_async_gui_callback('add-image', self.name, image, info)

        current = self.datasrc.youngest()
        curname = current.get('name')
        self.logger.debug("image=%s youngest=%s" % (image.get('name'), curname))
        if current != image:
            return

        # switch to current image?
        if self.settings['switchnew']:
            self.logger.debug("switching to new image '%s'" % (curname))
            self.switch_image(image)

        if self.settings['raisenew']:
            channel = self.fv.get_current_channel()
            if channel != self:
                self.fv.change_channel(self.name)

    def _image_modified_cb(self, image):
        imname = image.get('name')
        info = self.image_index[imname]
        info.time_modified = datetime.utcnow()
        self.logger.debug("image modified; making chained callback")

        self.fv.make_async_gui_callback('add-image-info', self, info)

    def get_current_image(self):
        return self.fitsimage.get_image()

    def refresh_cursor_image(self):
        info = self.history[self.cursor]
        if self.datasrc.has_key(info.name):
            # image still in memory
            image = self.datasrc[info.name]
            self.switch_image(image)

        else:
            self.switch_name(info.name)

    def prev_image(self, loop=True):
        with self.lock:
            self.logger.debug("Previous image")
            if self.cursor <= 0:
                n = len(self.history) - 1
                if (not loop) or (n < 0):
                    self.logger.error("No previous image!")
                    return True
                self.cursor = n
            else:
                self.cursor -= 1

            self.refresh_cursor_image()

        return True

    def next_image(self, loop=True):
        with self.lock:
            self.logger.debug("Next image")
            n = len(self.history) - 1
            if self.cursor >= n:
                if (not loop) or (n < 0):
                    self.logger.error("No next image!")
                    return True
                self.cursor = 0
            else:
                self.cursor += 1

            self.refresh_cursor_image()

        return True

    def _add_info(self, info):
        if not info in self.image_index:
            self.history.append(info)
            self.image_index[info.name] = info

            if self.hist_sort is not None:
                self.history.sort(key=self.hist_sort)

    def add_history(self, imname, path, idx=None,
                    image_loader=None, image_future=None):

        if not (imname in self.image_index):

            if image_loader is None:
                image_loader = self.fv.load_image
            # create an image_future if one does not exist
            if (image_future is None) and (path is not None):
                image_future = Future.Future()
                image_future.freeze(image_loader, path)

            info = Bunch.Bunch(name=imname, path=path,
                               idx=idx,
                               image_loader=image_loader,
                               image_future=image_future,
                               time_added=time.time(),
                               time_modified=None)
            self._add_info(info)
        else:
            # already in history
            info = self.image_index[imname]
        return info

    def remove_history(self, imname):
        if imname in self.image_index:
            info = self.image_index[imname]
            del self.image_index[imname]
            self.history.remove(info)
            return info
        return None

    def switch_image(self, image):

        with self.lock:
            curimage = self.fitsimage.get_image()
            if curimage != image:
                self.logger.debug("Setting image...")
                self.fitsimage.set_image(image)

                # update cursor to match image
                imname = image.get('name')
                if imname in self.image_index:
                    info = self.image_index[imname]
                    if info in self.history:
                        self.cursor = self.history.index(info)

                self.fv.channel_image_updated(self, image)

                # Check for preloading any images into memory
                preload = self.settings.get('preload_images', False)
                if not preload:
                    return

                # queue next and previous files for preloading
                index = self.cursor
                if index < len(self.history)-1:
                    info = self.history[index+1]
                    if info.path is not None:
                        self.fv.add_preload(self.name, info)

                if index > 0:
                    info = self.history[index-1]
                    if info.path is not None:
                        self.fv.add_preload(self.name, info)

            else:
                self.logger.debug("Apparently no need to set image.")

    def switch_name(self, imname):

        if self.datasrc.has_key(imname):
            # Image is still in the heap
            image = self.datasrc[imname]
            self.switch_image(image)
            return

        if not (imname in self.image_index):
            errmsg = "No image by the name '%s' found" % (imname)
            self.logger.error("Can't switch to image '%s': %s" % (
                imname, errmsg))
            raise ControlError(errmsg)

        # Do we have a way to reconstruct this image from a future?
        info = self.image_index[imname]
        if info.image_future is not None:
            self.logger.info("Image '%s' is no longer in memory; attempting "
                             "reloader" % (imname))
            # TODO: recode this--it's a bit messy
            def _switch(image):
                # this will be executed in the gui thread
                self.add_image(image, silent=True)
                self.switch_image(image)

                # reset modified timestamp
                info.time_modified = None
                self.fv.make_async_gui_callback('add-image-info', self, info)

            def _load_n_switch(imname, path, image_future):
                # this will be executed in a non-gui thread
                # reconstitute the image
                image = self.fv.error_wrap(image_future.thaw)
                if isinstance(image, Exception):
                    errmsg = "Error reconstituting image: %s" % (str(image))
                    self.logger.error(errmsg)
                    raise image

                # perpetuate the image_future
                image.set(image_future=image_future, name=imname, path=path)

                self.fv.gui_do(_switch, image)

            self.fv.nongui_do(_load_n_switch, imname, info.path,
                              info.image_future)

        elif info.path is not None:
            # Do we have a path? We can try to reload it
            self.logger.debug("Image '%s' is no longer in memory; attempting "
                              "to load from %s" % (imname, info.path))

            #self.fv.load_file(path, chname=chname)
            self.fv.nongui_do(self.load_file, info.path, chname=self.name)

        else:
            raise ControlError("No way to recreate image '%s'" % (imname))

    def _configure_sort(self):
        self.hist_sort = lambda info: info.time_added
        # set sorting function
        sort_order = self.settings.get('sort_order', 'loadtime')
        if sort_order == 'alpha':
            # sort history alphabetically
            self.hist_sort = lambda info: info.name

    def _sort_changed_ext_cb(self, setting, value):
        self._configure_sort()

        self.history.sort(key=self.hist_sort)

# END
