#
# Control.py -- Controller for the Ginga reference viewer.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
# stdlib imports
import sys, os
import traceback
import re, time
import tempfile
import glob
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
import platform
from collections import deque
import atexit, shutil
from datetime import datetime

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
from ginga import cmap, imap
from ginga import AstroImage, RGBImage, BaseImage
from ginga.table import AstroTable
from ginga.misc import Bunch, Datasrc, Callback, Timer, Future
from ginga.util import catalog, iohelper, io_fits
from ginga.canvas.CanvasObject import drawCatalog
from ginga.canvas.types.layer import DrawingCanvas
from ginga.util.six.moves import map, zip

# GUI imports
from ginga.gw import GwHelp, GwMain, PluginManager
from ginga.gw import Widgets, Viewers, Desktop
from ginga import toolkit

# Version
from ginga import __version__

#pluginconfpfx = 'plugins'
pluginconfpfx = None

package_home = os.path.split(sys.modules['ginga.version'].__file__)[0]

## gw_dir = os.path.join(package_home, 'gw')
## sys.path.insert(0, gw_dir)

# pick up plugins specific to our chosen toolkit
tkname = toolkit.get_family()
if tkname is not None:
    # TODO: this relies on a naming convention for widget directories!
    child_dir = os.path.join(package_home, tkname + 'w', 'plugins')
sys.path.insert(0, child_dir)

icon_path = os.path.abspath(os.path.join(package_home, 'icons'))


class ControlError(Exception):
    pass

class GingaViewError(Exception):
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
        self.channel_names = []
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

        # for loading FITS files
        fo = io_fits.fitsLoaderClass(self.logger)
        fo.register_type('image', AstroImage.AstroImage)
        fo.register_type('table', AstroTable.AstroTable)
        self.fits_opener = fo


    def get_server_bank(self):
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
            if (image is None) or not isinstance(image, BaseImage.BaseImage):
                # No compatible image loaded for this channel
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

        # TODO: can this be made more efficient?
        chname = self.get_channel_name(viewer)
        channel = self.get_channel(chname)

        self.make_callback('field-info', channel, info)

        self.update_pending()
        return True

    def motion_cb(self, viewer, button, data_x, data_y):
        """Motion event in the channel viewer window.  Show the pointing
        information under the cursor.
        """
        self.showxy(viewer, data_x, data_y)
        return True

    def keypress(self, viewer, event, data_x, data_y):
        """Key press event in a channel window."""
        keyname = event.key
        chname = self.get_channel_name(viewer)
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
        elif keyname == 'K':
            self.remove_channel_auto()
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
        to_chname = self.get_channel_name(viewer)
        for url in urls:
            ## self.load_file(url)
            self.nongui_do(self.load_file, url, chname=to_chname,
                           wait=False)
        return True

    def force_focus_cb(self, viewer, event, data_x, data_y):
        chname = self.get_channel_name(viewer)
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

    def make_async_gui_callback(self, name, *args, **kwargs):
        # NOTE: asynchronous!
        self.gui_do(self.make_callback, name, *args, **kwargs)

    def make_gui_callback(self, name, *args, **kwargs):
        if self.is_gui_thread():
            return self.make_callback(name, *args, **kwargs)
        else:
            # note: this cannot be "gui_call"--locks viewer.
            # so call becomes async when a non-gui thread invokes it
            self.gui_do(self.make_callback, name, *args, **kwargs)

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
        if hasattr(channel.viewer, 'onscreen_message'):
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

    def error_wrap(self, method, *args, **kwargs):
        try:
            return method(*args, **kwargs)

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

        localDoc = os.path.join(package_home, 'doc', 'help.html')
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

        kwargs = {}

        self.logger.debug("assuming file type: %s/%s'" % (typ, subtyp))
        try:
            if (typ == 'image') and (subtyp not in ('fits', 'x-fits')):
                image = RGBImage.RGBImage(logger=self.logger)
                filepath = filepfx
                image.load_file(filepath, **kwargs)
            else:
                inherit_prihdr = self.settings.get('inherit_primary_header', False)
                kwargs.update(dict(numhdu=idx, inherit_primary_header=inherit_prihdr))

                self.logger.info("Loading object from %s kwargs=%s" % (
                    filepath, str(kwargs)))
                image = self.fits_opener.load_file(filepath, **kwargs)

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

        self.logger.debug("Successfully loaded file into object.")
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

        kwargs = {}
        idx = None
        if info.numhdu is not None:
            kwargs['idx'] = info.numhdu

        try:
            image = image_loader(filepath, **kwargs)

        except Exception as e:
            errmsg = "Failed to load '%s': %s" % (filepath, str(e))
            self.gui_do(self.show_error, errmsg)

        future = Future.Future()
        future.freeze(image_loader, filepath, **kwargs)

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
        """Zoom the view in one zoom step.
        """
        viewer = self.getfocus_viewer()
        viewer.zoom_in()
        return True

    def zoom_out(self):
        """Zoom the view out one zoom step.
        """
        viewer = self.getfocus_viewer()
        viewer.zoom_out()
        return True

    def zoom_1_to_1(self):
        """Zoom the view to a 1 to 1 pixel ratio (100 %%).
        """
        viewer = self.getfocus_viewer()
        viewer.zoom_to(1)
        return True

    def zoom_fit(self):
        """Zoom the view to fit the image entirely in the window.
        """
        viewer = self.getfocus_viewer()
        viewer.zoom_fit()
        return True

    def auto_levels(self):
        """Perform an auto cut levels on the image.
        """
        viewer = self.getfocus_viewer()
        viewer.auto_levels()

    def prev_img(self, loop=True):
        """Go to the previous image in the channel.
        """
        channel = self.get_current_channel()
        if channel is None:
            self.show_error("Please create a channel.", raisetab=True)
            return
        channel.prev_image()
        return True

    def next_img(self, loop=True):
        """Go to the next image in the channel.
        """
        channel = self.get_current_channel()
        if channel is None:
            self.show_error("Please create a channel.", raisetab=True)
            return
        channel.next_image()
        return True

    def get_current_workspace(self):
        channel = self.get_channel_info()
        if channel is None:
            return None
        ws = self.ds.get_ws(channel.workspace)
        return ws

    def prev_channel_ws(self, ws):
        children = list(ws.nb.get_children())
        if len(children) == 0:
            self.show_error("No channels in this workspace.",
                            raisetab=True)
            return
        ws.to_previous()
        idx = ws.nb.get_index()
        child = ws.nb.index_to_widget(idx)
        chname = child.extdata.tab_title
        self.change_channel(chname, raisew=True)

    def prev_channel(self):
        ws = self.get_current_workspace()
        if ws is None:
            self.show_error("Please select or create a workspace",
                            raisetab=True)
            return
        self.prev_channel_ws(ws)

    def next_channel_ws(self, ws):
        children = list(ws.nb.get_children())
        if len(children) == 0:
            self.show_error("No channels in this workspace.",
                            raisetab=True)
            return
        ws.to_next()
        idx = ws.nb.get_index()
        child = ws.nb.index_to_widget(idx)
        chname = child.extdata.tab_title
        self.change_channel(chname, raisew=True)

    def next_channel(self):
        ws = self.get_current_workspace()
        if ws is None:
            self.show_error("Please select or create a workspace",
                            raisetab=True)
            return
        self.next_channel_ws(ws)

    def add_channel_auto_ws(self, ws):
        chpfx = "Image"
        chpfx = ws.extdata.get('chpfx', chpfx)

        chname = self.make_channel_name(chpfx)
        self.add_channel(chname, workspace=ws.name)

    def add_channel_auto(self):
        ws = self.get_current_workspace()
        if ws is None:
            self.show_error("Please select or create a workspace",
                            raisetab=True)
            return

        self.add_channel_auto_ws(ws)

    def remove_channel_auto(self):
        channel = self.get_channel_info()
        if channel is None:
            return
        self.delete_channel(channel.name)

    def configure_workspace(self, wstype):
        ws = self.get_current_workspace()
        ws.configure_wstype(wstype)

    def cycle_workspace_type(self):
        ws = self.get_current_workspace()
        ws.cycle_wstype()

    def add_workspace(self, wsname, wstype, inSpace='channels'):

        ws = self.ds.make_ws(name=wsname, group=1, wstype=wstype,
                             use_toolbar=True)
        if inSpace != 'top level':
            self.ds.add_tab(inSpace, ws.widget, 1, ws.name)
        else:
            #width, height = 700, 800
            #self.ds.create_toplevel_ws(width, height, group=1)
            top_w = self.ds.add_toplevel(ws, ws.name)
            ws.extdata.top_w = top_w

        return ws

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

    def redo_plugins(self, image, channel):
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

    def close_plugins(self, channel):
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
            image.add_callback('modified', self.redo_plugins, channel)

            self.logger.debug("executing redo() in plugins...")
            self.redo_plugins(image, channel)

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
        with self.lock:
            if chname is None:
                return self.cur_channel
            name = chname.lower()
            return self.channel[name]

    def get_current_channel(self):
        with self.lock:
            return self.cur_channel

    def get_channel_info(self, chname=None):
        # TO BE DEPRECATED--please use get_channel()
        return self.get_channel(chname)

    def get_channel_on_demand(self, chname):
        if self.has_channel(chname):
            return self.get_channel(chname)

        return self.gui_call(self.add_channel, chname)

    def get_channel_name(self, viewer):
        with self.lock:
            items = self.channel.items()
        for name, channel in items:
            if viewer in channel.viewers:
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
            bnch.image_viewer.set_name('channel:%s' % (chname))

            opmon = self.getPluginManager(self.logger, self,
                                          self.ds, self.mm)

            channel.widget = bnch.widget
            channel.container = bnch.container
            channel.workspace = bnch.workspace
            channel.connect_viewer(bnch.image_viewer)
            channel.viewer = bnch.image_viewer
            # older name, should eventually be deprecated
            channel.fitsimage = bnch.image_viewer
            channel.opmon = opmon

            name = chname.lower()
            self.channel[name] = channel

            # Update the channels control
            self.channel_names.append(chname)
            self.channel_names.sort()

            if len(self.channel_names) == 1:
                self.cur_channel = channel

        # Prepare local plugins for this channel
        for opname, spec in self.local_plugins.items():
            opmon.loadPlugin(opname, spec, chinfo=channel)

        self.make_gui_callback('add-channel', channel)
        return channel

    def delete_channel(self, chname):
        """Delete a given channel from viewer."""
        name = chname.lower()

        if len(self.channel_names) < 1:
            self.logger.error('Delete channel={0} failed. '
                              'No channels left.'.format(chname))
            return

        with self.lock:
            channel = self.channel[name]

            # Close local plugins open on this channel
            self.close_plugins(channel)

            try:
                idx = self.channel_names.index(chname)
            except ValueError:
                idx = 0

            # Update the channels control
            self.channel_names.remove(channel.name)
            self.channel_names.sort()

            self.ds.remove_tab(chname)
            del self.channel[name]
            self.prefs.remove_settings('channel_'+chname)

            # pick new channel
            num_channels = len(self.channel_names)
            if num_channels > 0:
                if idx >= num_channels:
                    idx = num_channels - 1
                self.change_channel(self.channel_names[idx])
            else:
                self.cur_channel = None

        self.make_gui_callback('delete-channel', channel)

    def get_channel_names(self):
        with self.lock:
            return self.channel_names

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

    def follow_focus(self, tf):
        self.channel_follows_focus = tf

    def show_status(self, text):
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
    ### NON-PEP8 PREDECESSORS: TO BE DEPRECATED

    getDrawClass = get_draw_class
    getDrawClasses = get_draw_classes
    get_channelName = get_channel_name
    get_channelInfo = get_channel_info
    get_channelNames = get_channel_names
    followFocus = follow_focus
    showStatus = show_status
    getfocus_fitsimage = getfocus_viewer
    get_fitsimage = get_viewer
    get_ServerBank = get_server_bank


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
        # this is the image viewer we are connected to
        self.fitsimage = None
        # this is the currently active viewer
        self.viewer = None
        self.viewers = []
        self.viewer_dict = {}
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
        if not viewer in self.viewers:
            self.viewers.append(viewer)
            self.viewer_dict[viewer.vname] = viewer

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

    def get_current_image(self):
        return self.viewer.get_image()

    def view_object(self, dataobj):

        # find available viewers that can view this kind of object
        vnames = self.fv.get_viewer_names(dataobj)
        if len(vnames) == 0:
            raise ValueError("I don't know how to view objects of type '%s'" % (
                str(type(dataobj))))
        self.logger.debug("available viewers are: %s" % (str(vnames)))

        # for now, pick first available viewer that can view this type
        vname = vnames[0]

        # if we don't have this viewer type then install one in the channel
        if not vname in self.viewer_dict:
            self.fv.make_viewer(vname, self)

        self.viewer = self.viewer_dict[vname]
        # find this viewer and raise it
        idx = self.viewers.index(self.viewer)
        self.widget.set_index(idx)

        # and load the data
        self.viewer.set_image(dataobj)


    def switch_image(self, image):

        with self.lock:
            curimage = self.get_current_image()
            if curimage != image:
                self.logger.debug("updating viewer...")
                self.view_object(image)

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


class GingaView(GwMain.GwMain, Widgets.Application):

    def __init__(self, logger, ev_quit, thread_pool):
        GwMain.GwMain.__init__(self, logger=logger, ev_quit=ev_quit,
                               app=self, thread_pool=thread_pool)
        Widgets.Application.__init__(self, logger=logger)

        self.w = Bunch.Bunch()
        self.iconpath = icon_path
        self._lastwsname = 'channels'
        self.layout = None
        self._lsize = None
        self._rsize = None

        self.filesel = None
        self.menubar = None

        # this holds registered viewers
        self.viewer_db = {}

        self.register_viewer(Viewers.CanvasView)
        self.register_viewer(Viewers.TableViewGw)


    def set_layout(self, layout):
        self.layout = layout

    def get_screen_dimensions(self):
        return (self.screen_wd, self.screen_ht)

    def build_toplevel(self):

        self.font = self.getFont('fixedFont', 12)
        self.font11 = self.getFont('fixedFont', 11)
        self.font14 = self.getFont('fixedFont', 14)
        self.font18 = self.getFont('fixedFont', 18)

        self.w.tooltips = None

        self.ds = Desktop.Desktop(self)
        self.ds.make_desktop(self.layout, widgetDict=self.w)
        # TEMP: FIX ME!
        self.gpmon.ds = self.ds

        for win in self.ds.toplevels:
            # add delete/destroy callbacks
            win.add_callback('close', self.quit)
            win.set_title("Ginga")
            root = win
        self.ds.add_callback('all-closed', self.quit)

        self.w.root = root
        self.w.fscreen = None

        # get informed about window closures in existing workspaces
        for wsname in self.ds.get_wsnames():
            ws = self.ds.get_ws(wsname)
            self.init_workspace(ws)

        if 'menu' in self.w:
            menuholder = self.w['menu']
            self.w.menubar = self.add_menus(menuholder)

        self.add_dialogs()

        if 'status' in self.w:
            statusholder = self.w['status']
            self.add_statusbar(statusholder)

        self.w.root.show()

    def get_plugin_manager(self, logger, fitsview, ds, mm):
        return PluginManager.PluginManager(logger, fitsview, ds, mm)

    def _name_mangle(self, name, pfx=''):
        newname = []
        for c in name.lower():
            if not (c.isalpha() or c.isdigit() or (c == '_')):
                newname.append('_')
            else:
                newname.append(c)
        return pfx + ''.join(newname)

    def add_menus(self, holder):

        menubar = Widgets.Menubar()
        self.menubar = menubar

        # NOTE: Special hack for Mac OS X. From the Qt documentation:
        # "If you want all windows in a Mac application to share one
        #  menu bar, you must create a menu bar that does not have a
        #  parent."
        macos_ver = platform.mac_ver()[0]
        if len(macos_ver) > 0:
            pass
        else:
            holder.add_widget(menubar, stretch=1)

        # create a File pulldown menu, and add it to the menu bar
        filemenu = menubar.add_name("File")

        item = filemenu.add_name("Load Image")
        item.add_callback('activated', lambda *args: self.gui_load_file())

        item = filemenu.add_name("Remove Image")
        item.add_callback("activated", lambda *args: self.remove_current_image())

        filemenu.add_separator()

        item = filemenu.add_name("Quit")
        item.add_callback('activated', lambda *args: self.window_close())

        # create a Channel pulldown menu, and add it to the menu bar
        chmenu = menubar.add_name("Channel")

        item = chmenu.add_name("Add Channel")
        item.add_callback('activated', lambda *args: self.gui_add_channel())

        item = chmenu.add_name("Add Channels")
        item.add_callback('activated', lambda *args: self.gui_add_channels())

        item = chmenu.add_name("Delete Channel")
        item.add_callback('activated', lambda *args: self.gui_delete_channel())

        # create a Window pulldown menu, and add it to the menu bar
        wsmenu = menubar.add_name("Workspace")

        item = wsmenu.add_name("Add Workspace")
        item.add_callback('activated', lambda *args: self.gui_add_ws())

        # # create a Option pulldown menu, and add it to the menu bar
        # optionmenu = menubar.add_name("Option")

        # create a Plugins pulldown menu, and add it to the menu bar
        plugmenu = menubar.add_name("Plugins")
        self.w.menu_plug = plugmenu

        # create a Help pulldown menu, and add it to the menu bar
        helpmenu = menubar.add_name("Help")

        item = helpmenu.add_name("About")
        item.add_callback('activated', lambda *args: self.banner(raiseTab=True))

        item = helpmenu.add_name("Documentation")
        item.add_callback('activated', lambda *args: self.help())

        return menubar

    def add_menu(self, name):
        """Add a menu with name `name` to the global menu bar.
        Returns a menu widget.
        """
        if self.menubar is None:
            raise ValueError("No menu bar configured")
        return self.menubar.add_name(name)

    def get_menu(self, name):
        """Get the menu with name `name` from the global menu bar.
        Returns a menu widget.
        """
        if self.menubar is None:
            raise ValueError("No menu bar configured")
        return self.menubar.get_menu(name)

    def add_dialogs(self):
        if hasattr(GwHelp, 'FileSelection'):
            self.filesel = GwHelp.FileSelection(self.w.root.get_widget())

    def add_plugin_menu(self, name):
        # NOTE: self.w.menu_plug is a ginga.Widgets wrapper
        if 'menu_plug' in self.w:
            item = self.w.menu_plug.add_name("Start %s" % (name))
            item.add_callback('activated',
                              lambda *args: self.start_global_plugin(name))

    def add_statusbar(self, holder):
        self.w.status = Widgets.StatusBar()
        holder.add_widget(self.w.status, stretch=1)

    def fullscreen(self):
        self.w.root.fullscreen()

    def normalsize(self):
        self.w.root.unfullscreen()

    def maximize(self):
        self.w.root.maximize()

    def toggle_fullscreen(self):
        if not self.w.root.is_fullscreen():
            self.w.root.fullscreen()
        else:
            self.w.root.unfullscreen()

    def build_fullscreen(self):
        w = self.w.fscreen
        self.w.fscreen = None
        if w is not None:
            w.delete()
            return

        # Get image from current focused channel
        channel = self.get_current_channel()
        viewer = channel.fitsimage
        settings = viewer.get_settings()
        rgbmap = viewer.get_rgbmap()

        root = Widgets.TopLevel()
        vbox = Widgets.VBox()
        vbox.set_border_width(0)
        vbox.set_spacing(0)
        root.add_widget(vbox, stretch=1)

        fi = self.build_viewpane(settings, rgbmap=rgbmap)
        iw = fi.get_widget()
        vbox.add_widget(iw, stretch=1)

        # Get image from current focused channel
        image = viewer.get_image()
        if image is None:
            return
        fi.set_image(image)

        # Copy attributes of the frame
        viewer.copy_attributes(fi,
                                  [#'transforms',
                                   #'cutlevels',
                                   'rgbmap'])

        root.fullscreen()
        self.w.fscreen = root

    def register_viewer(self, vclass):
        """Register a channel viewer with the reference viewer.
        `vclass` is the class of the viewer.
        """
        self.viewer_db[vclass.vname] = Bunch.Bunch(vname=vclass.vname,
                                                   vclass=vclass,
                                                   vtypes=vclass.vtypes)

    def get_viewer_names(self, dataobj):
        """Returns a list of viewer names that are registered that
        can view `dataobj`.
        """
        res = []
        for bnch in self.viewer_db.values():
            for vtype in bnch.vtypes:
                if isinstance(dataobj, vtype):
                    res.append(bnch.vname)
        return res

    def make_viewer(self, vname, channel):
        """Make a viewer whose type name is `vname` and add it to `channel`.
        """
        if not vname in self.viewer_db:
            raise ValueError("I don't know how to build a '%s' viewer" % (
                vname))

        stk_w = channel.widget
        settings = channel.settings

        bnch = self.viewer_db[vname]

        viewer = bnch.vclass(logger=self.logger,
                             settings=channel.settings)
        stk_w.add_widget(viewer.get_widget(), title=vname)

        # let the GUI respond to this widget addition
        self.update_pending()

        # let the channel object do any necessary initialization
        channel.connect_viewer(viewer)

        # finally, let the viewer do any viewer-side initialization
        viewer.initialize_channel(self, channel)

    ####################################################
    # THESE METHODS ARE CALLED FROM OTHER MODULES & OBJECTS
    ####################################################

    def set_titlebar(self, text):
        self.w.root.set_title("Ginga: %s" % text)

    def build_viewpane(self, settings, rgbmap=None, size=(1, 1)):
        # instantiate bindings loaded with users preferences
        bclass = Viewers.ImageViewCanvas.bindingsClass
        bindprefs = self.prefs.createCategory('bindings')
        bd = bclass(self.logger, settings=bindprefs)

        fi = Viewers.ImageViewCanvas(logger=self.logger,
                                     rgbmap=rgbmap,
                                     settings=settings,
                                     bindings=bd)
        fi.set_desired_size(size[0], size[1])

        canvas = DrawingCanvas()
        canvas.enable_draw(False)
        fi.set_canvas(canvas)

        fi.set_enter_focus(settings.get('enter_focus', False))
        fi.enable_auto_orient(True)

        fi.add_callback('motion', self.motion_cb)
        fi.add_callback('cursor-down', self.force_focus_cb)
        fi.set_callback('keydown-none', self.keypress)
        fi.add_callback('drag-drop', self.dragdrop)
        fi.ui_setActive(True)

        bd = fi.get_bindings()
        bd.enable_all(True)

        fi.set_bg(0.2, 0.2, 0.2)
        return fi

    def add_viewer(self, name, settings, workspace=None):

        vbox = Widgets.VBox()
        vbox.set_border_width(1)
        vbox.set_spacing(0)

        if not workspace:
            workspace = 'channels'
        w = self.ds.get_nb(workspace)

        size = (1, 1)
        if isinstance(w, Widgets.MDIWidget) and w.true_mdi:
            size = (300, 300)

        # build image viewer & widget
        fi = self.build_viewpane(settings, size=size)

        # add scrollbar interface around this viewer
        scr = settings.get('scrollbars', 'off')
        si = Viewers.ScrolledView(fi)
        si.scroll_bars(horizontal=scr, vertical=scr)
        iw = Widgets.wrap(si)

        stk_w = Widgets.StackWidget()
        stk_w.add_widget(iw, title='image')

        fi.add_callback('focus', self.focus_cb, name)
        vbox.add_widget(stk_w, stretch=1)
        fi.set_name(name)

        # Add the viewer to the specified workspace
        self.ds.add_tab(workspace, vbox, 1, name)

        self.update_pending()

        bnch = Bunch.Bunch(image_viewer=fi,
                           widget=stk_w, container=vbox,
                           workspace=workspace)
        return bnch


    def gui_add_channel(self, chname=None):
        chpfx = "Image"
        ws = self.get_current_workspace()
        if ws is not None:
            chpfx = ws.extdata.get('chpfx', chpfx)

        if not chname:
            chname = self.make_channel_name(chpfx)

        captions = (('New channel name:', 'label', 'channel_name', 'entry'),
                    ('In workspace:', 'label', 'workspace', 'combobox'),
                    )

        w, b = Widgets.build_info(captions, orientation='vertical')

        # populate values
        b.channel_name.set_text(chname)
        names = self.ds.get_wsnames()
        try:
            idx = names.index(self._lastwsname)
        except:
            idx = 0
        for name in names:
            b.workspace.append_text(name)
        b.workspace.set_index(idx)

        # build dialog
        dialog = Widgets.Dialog(title="Add Channel",
                                flags=0,
                                buttons=[['Cancel', 0], ['Ok', 1]],
                                parent=self.w.root)
        dialog.add_callback('activated',
                            lambda w, rsp: self.add_channel_cb(w, rsp, b, names))
        box = dialog.get_content_area()
        box.add_widget(w, stretch=0)

        self.ds.show_dialog(dialog)

    def gui_add_channels(self):

        chpfx = "Image"
        ws = self.get_current_workspace()
        if ws is not None:
            chpfx = ws.extdata.get('chpfx', chpfx)

        captions = (('Prefix:', 'label', 'Prefix', 'entry'),
                    ('Number:', 'label', 'Number', 'spinbutton'),
                    ('In workspace:', 'label', 'workspace', 'combobox'),
                    )

        w, b = Widgets.build_info(captions)
        b.prefix.set_text(chpfx)
        b.number.set_limits(1, 12, incr_value=1)
        b.number.set_value(1)

        cbox = b.workspace
        names = self.ds.get_wsnames()
        try:
            idx = names.index('channels')
        except:
            idx = 0
        for name in names:
            b.workspace.append_text(name)
        b.workspace.set_index(idx)
        dialog = Widgets.Dialog(title="Add Channels",
                                flags=0,
                                buttons=[['Cancel', 0], ['Ok', 1]],
                                parent=self.w.root)
        dialog.add_callback('activated',
                            lambda w, rsp: self.add_channels_cb(w, rsp, b, names))
        box = dialog.get_content_area()
        box.add_widget(w, stretch=0)

        self.ds.show_dialog(dialog)

    def gui_delete_channel(self, chname=None):
        if chname is None:
            channel = self.get_channel(chname)
            if (len(self.get_channel_names()) == 0) or (channel is None):
                self.show_error("There are no more channels to delete.",
                                raisetab=True)
                return

            chname = channel.name

        lbl = Widgets.Label("Really delete channel '%s' ?" % (chname))
        dialog = Widgets.Dialog(title="Delete Channel",
                                flags=0,
                                buttons=[['Cancel', 0], ['Ok', 1]],
                                parent=self.w.root)
        dialog.add_callback('activated',
                            lambda w, rsp: self.delete_channel_cb(w, rsp, chname))

        box = dialog.get_content_area()
        box.add_widget(lbl, stretch=0)

        self.ds.show_dialog(dialog)

    def gui_delete_window(self, tabname):
        lbl = Widgets.Label("Really delete window '%s' ?" % (tabname))
        dialog = Widgets.Dialog(title="Delete Window",
                                flags=0,
                                buttons=[['Cancel', 0], ['Ok', 1]],
                                parent=self.w.root)
        dialog.add_callback('activated',
                            lambda w, rsp: self.delete_tab_cb(w, rsp, tabname))

        box = dialog.get_content_area()
        box.add_widget(lbl, stretch=0)

        self.ds.show_dialog(dialog)

    def gui_delete_channel_ws(self, ws):
        children = list(ws.nb.get_children())
        if len(children) == 0:
            self.show_error("No channels in this workspace to delete.",
                            raisetab=True)
            return
        idx = ws.nb.get_index()
        child = ws.nb.index_to_widget(idx)
        chname = child.extdata.tab_title

        if self.has_channel(chname):
            self.gui_delete_channel(chname)
        else:
            self.gui_delete_window(chname)


    def gui_add_ws(self):

        chpfx = "Image"
        ws = self.get_current_workspace()
        if ws is not None:
            chpfx = ws.extdata.get('chpfx', chpfx)

        captions = (('Workspace name:', 'label', 'Workspace name', 'entry'),
                    ('Workspace type:', 'label', 'Workspace type', 'combobox'),
                    ('In workspace:', 'label', 'workspace', 'combobox'),
                    ('Channel prefix:', 'label', 'Channel prefix', 'entry'),
                    ('Number of channels:', 'label', 'num_channels', 'spinbutton'),
                    ('Share settings:', 'label', 'Share settings', 'entry'),
                    )
        w, b = Widgets.build_info(captions)

        self.wscount += 1
        wsname = "ws%d" % (self.wscount)
        b.workspace_name.set_text(wsname)
        #b.share_settings.set_length(60)

        cbox = b.workspace_type
        cbox.append_text("Grid")
        cbox.append_text("Tabs")
        cbox.append_text("MDI")
        cbox.append_text("Stack")
        cbox.set_index(0)

        cbox = b.workspace
        names = self.ds.get_wsnames()
        names.insert(0, 'top level')
        try:
            idx = names.index('channels')
        except:
            idx = 0
        for name in names:
            cbox.append_text(name)
        cbox.set_index(idx)

        b.channel_prefix.set_text(chpfx)
        spnbtn = b.num_channels
        spnbtn.set_limits(0, 36, incr_value=1)
        spnbtn.set_value(4)

        dialog = Widgets.Dialog(title="Add Workspace",
                                flags=0,
                                buttons=[['Cancel', 0], ['Ok', 1]],
                                parent=self.w.root)
        dialog.add_callback('activated',
                            lambda w, rsp: self.add_ws_cb(w, rsp, b, names))
        box = dialog.get_content_area()
        box.add_widget(w, stretch=1)
        self.ds.show_dialog(dialog)

    def gui_load_file(self, initialdir=None):
        #self.start_operation('FBrowser')
        self.filesel.popup("Load File", self.load_file,
                           initialdir=initialdir)

    def status_msg(self, format, *args):
        if not format:
            s = ''
        else:
            s = format % args

        if 'status' in self.w:
            self.w.status.set_message(s)

    def set_pos(self, x, y):
        self.w.root.move(x, y)

    def set_size(self, wd, ht):
        self.w.root.resize(wd, ht)

    def set_geometry(self, geometry):
        # translation of X window geometry specification WxH+X+Y
        coords = geometry.replace('+', ' +')
        coords = coords.replace('-', ' -')
        coords = coords.split()
        if 'x' in coords[0]:
            # spec includes dimensions
            dim = coords[0]
            coords = coords[1:]
        else:
            # spec is position only
            dim = None

        if dim is not None:
            # user specified dimensions
            dim = list(map(int, dim.split('x')))
            self.set_size(*dim)

        if len(coords) > 0:
            # user specified position
            coords = list(map(int, coords))
            self.set_pos(*coords)


    def collapse_pane(self, side):
        """
        Toggle collapsing the left or right panes.
        """
        # TODO: this is too tied to one configuration, need to figure
        # out how to generalize this
        hsplit = self.w['hpnl']
        sizes = hsplit.get_sizes()
        lsize, msize, rsize = sizes
        if self._lsize is None:
            self._lsize, self._rsize = lsize, rsize
        self.logger.debug("left=%d mid=%d right=%d" % (
            lsize, msize, rsize))
        if side == 'right':
            if rsize < 10:
                # restore pane
                rsize = self._rsize
                msize -= rsize
            else:
                # minimize pane
                self._rsize = rsize
                msize += rsize
                rsize = 0
        elif side == 'left':
            if lsize < 10:
                # restore pane
                lsize = self._lsize
                msize -= lsize
            else:
                # minimize pane
                self._lsize = lsize
                msize += lsize
                lsize = 0
        hsplit.set_sizes([lsize, msize, rsize])

    def get_font(self, font_family, point_size):
        return GwHelp.get_font(font_family, point_size)

    def get_icon(self, icondir, filename):
        iconpath = os.path.join(icondir, filename)
        icon = GwHelp.get_icon(iconpath)
        return icon

    ####################################################
    # CALLBACKS
    ####################################################

    def window_close(self, *args):
        """Quit the application.
        """
        self.quit()

    def quit(self, *args):
        """Quit the application.
        """
        self.logger.info("Attempting to shut down the application...")
        self.stop()

        root = self.w.root
        self.w.root = None
        while len(self.ds.toplevels) > 0:
            w = self.ds.toplevels.pop()
            w.delete()

    def add_channel_cb(self, w, rsp, b, names):
        chname = str(b.channel_name.get_text())
        idx = b.workspace.get_index()
        if idx < 0:
            idx = 0
        wsname = names[idx]
        self.ds.remove_dialog(w)
        # save name for next add
        self._lastwsname = wsname
        if rsp == 0:
            return

        if self.has_channel(chname):
            self.show_error("Channel name already in use: '%s'" % (chname))
            return True

        self.add_channel(chname, workspace=wsname)
        return True

    def add_channels_cb(self, w, rsp, b, names):
        chpfx = b.prefix.get_text()
        idx = b.workspace.get_index()
        wsname = names[idx]
        num = int(b.number.get_value())
        self.ds.remove_dialog(w)
        if (rsp == 0) or (num <= 0):
            return

        for i in range(num):
            chname = self.make_channel_name(chpfx)
            self.add_channel(chname, workspace=wsname)
        return True

    def delete_channel_cb(self, w, rsp, chname):
        self.ds.remove_dialog(w)
        if rsp == 0:
            return
        self.delete_channel(chname)
        return True

    def delete_tab_cb(self, w, rsp, tabname):
        self.ds.remove_dialog(w)
        if rsp == 0:
            return
        self.ds.remove_tab(tabname)
        return True

    def init_workspace(self, ws):

        # add close handlers
        ws.add_callback('ws-close', self.workspace_closed_cb)

        if ws.nb.has_callback('page-closed'):
            ws.nb.add_callback('page-closed', self.page_closed_cb,
                                   ws.name)
        if ws.nb.has_callback('page-switch'):
            ws.nb.add_callback('page-switch', self.page_switch_cb)

        if ws.toolbar is not None:
            tb = ws.toolbar
            tb.add_separator()

            # add toolbar buttons for navigating images in the channel
            iconpath = os.path.join(self.iconpath, "up_48.png")
            btn = tb.add_action(None, iconpath=iconpath, iconsize=(18, 18))
            btn.set_tooltip("Previous object in current channel")
            btn.add_callback('activated', lambda w: self.prev_img())
            iconpath = os.path.join(self.iconpath, "down_48.png")
            btn = tb.add_action(None, iconpath=iconpath, iconsize=(18, 18))
            btn.set_tooltip("Next object in current channel")
            btn.add_callback('activated', lambda w: self.next_img())

            tb.add_separator()

            # add toolbar buttons for navigating between channels
            iconpath = os.path.join(self.iconpath, "prev_48.png")
            btn = tb.add_action(None, iconpath=iconpath, iconsize=(18, 18))
            btn.set_tooltip("Focus previous channel in this workspace")
            btn.add_callback('activated', lambda w: self.prev_channel_ws(ws))
            iconpath = os.path.join(self.iconpath, "next_48.png")
            btn = tb.add_action(None, iconpath=iconpath, iconsize=(18, 18))
            btn.set_tooltip("Focus next channel in this workspace")
            btn.add_callback('activated', lambda w: self.next_channel_ws(ws))

            tb.add_separator()

            # add toolbar buttons adding and deleting channels
            iconpath = os.path.join(self.iconpath, "plus_48.png")
            btn = tb.add_action(None, iconpath=iconpath, iconsize=(18, 18))
            btn.set_tooltip("Add a channel to this workspace")
            btn.add_callback('activated',
                             lambda w: self.add_channel_auto_ws(ws))
            iconpath = os.path.join(self.iconpath, "minus_48.png")
            btn = tb.add_action(None, iconpath=iconpath, iconsize=(18, 18))
            btn.set_tooltip("Delete current channel from this workspace")
            btn.add_callback('activated',
                             lambda w: self.gui_delete_channel_ws(ws))

    def add_ws_cb(self, w, rsp, b, names):
        try:
            wsname = str(b.workspace_name.get_text())
            idx = b.workspace_type.get_index()
            if rsp == 0:
                self.ds.remove_dialog(w)
                return

            try:
                nb = self.ds.get_nb(wsname)
                self.show_error("Workspace name '%s' cannot be used, sorry." % (
                    wsname))
                self.ds.remove_dialog(w)
                return

            except KeyError:
                pass

            d = { 0: 'grid', 1: 'tabs', 2: 'mdi', 3: 'stack' }
            wstype = d[idx]
            idx = b.workspace.get_index()
            in_space = names[idx]

            chpfx = b.channel_prefix.get_text().strip()
            num = int(b.num_channels.get_value())
            share_list = b.share_settings.get_text().split()

            self.ds.remove_dialog(w)

            ws = self.error_wrap(self.add_workspace, wsname, wstype,
                                 inSpace=in_space)
            ws.extdata.chpfx = chpfx

            self.init_workspace(ws)

            if num <= 0:
                return

            # Create a settings template to copy settings from
            name = "channel_template_%f" % (time.time())
            settings = self.prefs.createCategory(name)
            try:
                settings_template = self.prefs.getSettings('channel_Image')
                settings_template.copySettings(settings)
            except KeyError:
                settings_template = None

            for i in range(num):
                chname = self.make_channel_name(chpfx)
                self.add_channel(chname, workspace=wsname,
                                 settings_template=settings_template,
                                 settings_share=settings,
                                 share_keylist=share_list)
        except Exception as e:
            self.logger.error("Exception building workspace: %s" % (str(e)))

        return True

    def load_file_cb(self, w, rsp):
        w.hide()
        if rsp == 0:
            return

        filename = w.selected_files()[0]

        # Normal load
        if os.path.isfile(filename):
            self.logger.debug('Loading {0}'.format(filename))
            self.load_file(filename)

        # Fancy load (first file only)
        # TODO: If load all the matches, might get (Qt) QPainter errors
        else:
            info = iohelper.get_fileinfo(filename)
            ext = iohelper.get_hdu_suffix(info.numhdu)
            paths = ['{0}{1}'.format(fname, ext)
                     for fname in glob.iglob(info.filepath)]
            self.logger.debug(
                'Found {0} and only loading {1}'.format(paths, paths[0]))
            self.load_file(paths[0])

    def _get_channel_by_container(self, child):
        for chname in self.get_channel_names():
            channel = self.get_channel(chname)
            if channel.container == child:
                return channel
        return None

    def page_switch_cb(self, tab_w, child):
        self.logger.debug("page switched to %s" % (str(child)))

        # Find the channel that contains this widget
        channel = self._get_channel_by_container(child)
        self.logger.debug("channel: %s" % (str(channel)))
        if channel is not None:
            viewer = channel.viewer
            if viewer != self.getfocus_viewer():
                chname = channel.name
                self.logger.debug("Active channel switch to '%s'" % (
                    chname))
                self.change_channel(chname, raisew=False)

        return True

    def workspace_closed_cb(self, ws):
        self.logger.debug("workspace requests close")
        children = list(ws.nb.get_children())
        if len(children) > 0:
            self.show_error("Please close all windows in this workspace first!",
                            raisetab=True)
            return

        # TODO: this will prompt the user if we should close the workspace
        lbl = Widgets.Label("Really delete workspace '%s' ?" % (ws.name))
        dialog = Widgets.Dialog(title="Delete Workspace",
                                flags=0,
                                buttons=[['Cancel', 0], ['Ok', 1]],
                                parent=self.w.root)
        dialog.add_callback('activated',
                            lambda w, rsp: self.delete_workspace_cb(w, rsp,
                                                                    ws))
        box = dialog.get_content_area()
        box.add_widget(lbl, stretch=0)

        self.ds.show_dialog(dialog)

    def delete_workspace_cb(self, w, rsp, ws):
        self.ds.remove_dialog(w)
        if rsp == 0:
            return

        top_w = ws.extdata.get('top_w', None)
        if top_w is None:
            self.ds.remove_tab(ws.name)
        else:
            # this is a top-level window
            self.ds.remove_toplevel(top_w)

        # inform desktop we are no longer tracking this
        self.ds.delete_ws(ws.name)

        return True

    def page_closed_cb(self, widget, child, wsname):
        self.logger.debug("page closed in %s: '%s'" % (wsname, str(child)))

        channel = self._get_channel_by_container(child)
        if channel is not None:
            self.gui_delete_channel(channel.name)


    ########################################################
    ### NON-PEP8 PREDECESSORS: TO BE DEPRECATED

    getFont = get_font
    getPluginManager = get_plugin_manager
    statusMsg = status_msg


class GuiLogHandler(logging.Handler):
    """Logs to a pane in the GUI."""

    def __init__(self, fv, level=logging.NOTSET):
        self.fv = fv
        logging.Handler.__init__(self, level=level)

    def emit(self, record):
        text = self.format(record)
        self.fv.logit(text)


def _rmtmpdir(tmpdir):
    if os.path.isdir(tmpdir):
        shutil.rmtree(tmpdir)


# END
