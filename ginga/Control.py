#
# Control.py -- Controller for the Ginga FITS viewer.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
# stdlib imports
import sys, os
import traceback
import re, time
import thread, threading
import logging
import Queue
import mimetypes

import numpy
try:
    import magic
    have_magic = True

except ImportError:
    have_magic = False

# Local application imports
from ginga import cmap, imap, Catalog, AstroImage, RGBImage, ImageView
from ginga.misc import Bunch, Datasrc, Callback, Timer, Task

#pluginconfpfx = 'plugins'
pluginconfpfx = None


class ControlError(Exception):
    pass

class GingaControl(Callback.Callbacks):
     
    def __init__(self, logger, threadPool, module_manager, preferences,
                 ev_quit=None):
        Callback.Callbacks.__init__(self)

        self.logger = logger
        self.threadPool = threadPool
        self.mm = module_manager
        self.prefs = preferences
        # event for controlling termination of threads executing in this
        # object
        if not ev_quit:
            self.ev_quit = threading.Event()
        else:
            self.ev_quit = ev_quit

        # For callbacks
        for name in ('add-image', 'active-image', 'add-channel',
                     'delete-channel', 'field-info'):
            self.enable_callback(name)

        self.gui_queue = Queue.Queue()
        self.gui_thread_id = None
        # For asynchronous tasks on the thread pool
        self.tag = 'master'
        self.shares = ['threadPool', 'logger']

        # Initialize the timer factory
        self.timer_factory = Timer.TimerFactory(ev_quit=self.ev_quit)
        task = Task.FuncTask2(self.timer_factory.mainloop)
        task.init_and_start(self)
        
        self.lock = threading.RLock()
        self.channel = {}
        self.channelNames = []
        self.chinfo = None
        self.chncnt = 0
        self.wscount = 0
        self.statustask = None
        self.preloadLock = threading.RLock()
        self.preloadList = []

        # Create general preferences
        self.settings = self.prefs.createCategory('general')
        self.settings.load(onError='silent')

        self.settings.addDefaults(fixedFont='Monospace',
                                  sansFont='Sans',
                                  channelFollowsFocus=False,
                                  shareReadout=True,
                                  numImages=10)

        # Should channel change as mouse moves between windows
        self.channel_follows_focus = self.settings['channelFollowsFocus']

        self.cm = cmap.get_cmap("ramp")
        self.im = imap.get_imap("ramp")

        self.fn_keys = ('f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8',
                        'f9', 'f10', 'f11', 'f12')
        
        self.global_plugins = {}
        self.local_plugins = {}
        self.operations  = []

        # This plugin manager handles "global" (aka standard) plug ins
        # (unique instances, not per channel)
        self.gpmon = self.getPluginManager(self.logger, self,
                                           None, self.mm)

        # Initialize image server bank
        self.imgsrv = Catalog.ServerBank(self.logger)
        self.dsscnt = 0


    def get_ServerBank(self):
        return self.imgsrv

    def get_threadPool(self):
        return self.threadPool

    def get_preferences(self):
        return self.prefs

    def get_timer(self):
        return self.timer_factory.timer()

    ####################################################
    # CALLBACKS
    ####################################################
    
    def showxy(self, fitsimage, data_x, data_y):
        try:
            image = fitsimage.get_image()
            if image == None:
                # No image loaded for this channel
                return

            prefs = fitsimage.get_settings()
            info = image.info_xy(data_x, data_y, prefs)

        except Exception, e:
            self.logger.warn("Can't get info under the cursor: %s" % (
                str(e)))
            return

        self.make_callback('field-info', fitsimage, info)
        
        self.update_pending()
        return True

    def readout_config(self, fitsimage, image, readout):
        # A new image has come into fitsimage. Get and store the sizes of
        # the fields necessary to display all X, Y coords as well as values.
        width, height = fitsimage.get_data_size()
        # Set size of coordinate areas (4 is "." + precision 3)
        readout.maxx = len(str(width)) + 4
        readout.maxy = len(str(height)) + 4
        minval, maxval = image.get_minmax()
        readout.maxv = max(len(str(minval)), len(str(maxval)))
        return True

    def readout_cb(self, viewer, fitsimage, info, readout, name):
        # TEMP: hack
        if readout.fitsimage != fitsimage:
            return

        # If this is a multiband image, then average the values for the readout
        value = info.value
        if isinstance(value, numpy.ndarray):
            avg = numpy.average(value)
            value = avg
            
        # Update the readout
        maxx = readout.maxx
        maxy = readout.maxy
        maxv = readout.maxv
        fits_x = "%.3f" % info.x
        fits_y = "%.3f" % info.y
        if info.has_key('ra_txt'):
            text = "%1.1s: %-14.14s  %1.1s: %-14.14s  X: %-*.*s  Y: %-*.*s  Value: %-*.*s" % (
                info.ra_lbl, info.ra_txt, info.dec_lbl, info.dec_txt,
                maxx, maxx, fits_x, maxy, maxy, fits_y, maxv, maxv, value)
        else:
            text = "%1.1s: %-14.14s  %1.1s: %-14.14s  X: %-*.*s  Y: %-*.*s  Value: %-*.*s" % (
                '', '', '', '',
                maxx, maxx, fits_x, maxy, maxy, fits_y, maxv, maxv, value)
        readout.set_text(text)

        # Draw colorbar value wedge
        #self.colorbar.set_current_value(value)

    def motion_cb(self, fitsimage, button, data_x, data_y):
        """Motion event in the big fits window.  Show the pointing
        information under the cursor.
        """
        ## if button == 0:
        ##     self.showxy(fitsimage, data_x, data_y)
        self.showxy(fitsimage, data_x, data_y)
        return True

    def keypress(self, fitsimage, keyname):
        """Key press event in the big FITS window."""
        chname = self.get_channelName(fitsimage)
        self.logger.debug("key press (%s) in channel %s" % (
            keyname, chname))
        # TODO: keyboard accelerators to raise tabs need to be integrated into
        #   the desktop object
        if keyname == 'T':
            self.ds.raise_tab('Thumbs')
        elif keyname == 'Z':
            self.ds.raise_tab('Zoom')
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
        elif keyname == 'v':
            self.build_view()
        elif keyname == 'm':
            self.maximize()
        elif keyname == 'escape':
            self.reset_viewer()
        elif keyname in self.fn_keys:
            index = self.fn_keys.index(keyname)
            if (index >= 0) and (index < len(self.operations)):
                opname = self.operations[index]
                self.start_operation_channel(chname, opname, None)
        return True

    def dragdrop(self, fitsimage, urls):
        """Called when a drop operation is performed on our main window.
        We are called back with a URL and we attempt to load it if it
        names a file.
        """
        for url in urls:
            match = re.match(r"^file://(.+)$", url)
            if match:
                fitspath = match.group(1).strip()
                #self.load_file(fitspath)
                chname = self.get_channelName(fitsimage)
                self.nongui_do(self.load_file, fitspath, chname=chname,
                               wait=False)
        return True

    def _match_cmap(self, fitsimage, colorbar):
        rgbmap = fitsimage.get_rgbmap()
        loval, hival = fitsimage.get_cut_levels()
        colorbar.set_range(loval, hival, redraw=False)
        colorbar.set_rgbmap(rgbmap)
        
    def change_cbar(self, viewer, fitsimage, cbar):
        self._match_cmap(fitsimage, cbar)
        
    def change_range_cb(self, setting, value, fitsimage, cbar):
        if fitsimage != self.getfocus_fitsimage():
            return False
        loval, hival = value
        cbar.set_range(loval, hival)
        
    def cbar_value_cb(self, cbar, value, event):
        #print "CBAR VALUE = %f" % (value)
        chinfo = self.get_channelInfo()
        readout = chinfo.readout
        if readout != None:
            maxv = readout.maxv
            text = "Value: %-*.*s" % (maxv, maxv, value)
            readout.set_text(text)
        
    def rgbmap_cb(self, rgbmap, fitsimage):
        if fitsimage != self.getfocus_fitsimage():
            return False
        self.change_cbar(self, fitsimage, self.colorbar)
        
    def force_focus_cb(self, fitsimage, action, data_x, data_y):
        chname = self.get_channelName(fitsimage)
        self.change_channel(chname, raisew=True)
        return True

    def focus_cb(self, fitsimage, tf, name):
        """Called when _fitsimage_ gets (tf==True) or loses (tf==False)
        the focus."""
        if tf:
            self.readout.fitsimage = fitsimage
            image = fitsimage.get_image()
            self.readout_config(fitsimage, image, self.readout)

        if not self.channel_follows_focus:
            return True
        self.logger.debug("Focus %s=%s" % (name, tf))
        if tf:
            if fitsimage != self.getfocus_fitsimage():
                self.change_channel(name, raisew=False)

        return True

    def stop(self):
        self.ev_quit.set()

    def reset_viewer(self):
        chinfo = self.get_channelInfo()
        opmon = chinfo.opmon
        opmon.deactivate_focused()
        self.normalsize()
        
    # PLUGIN MANAGEMENT

    def start_operation(self, opname):
        return self.start_operation_channel(None, opname, None)

    def start_operation_channel(self, chname, opname, future):
        chinfo = self.get_channelInfo(chname)
        opmon = chinfo.opmon
        opmon.start_plugin_future(chinfo.name, opname, future)
        chinfo.fitsimage.onscreen_message(opname, delay=1.0)
            
    def stop_operation_channel(self, chname, opname):
        chinfo = self.get_channelInfo(chname)
        opmon = chinfo.opmon
        opmon.deactivate(opname)
            
    def add_local_plugin(self, spec):
        try:
            name = spec.setdefault('name', spec.get('klass', spec.module))
            self.local_plugins[name] = spec

            self.mm.loadModule(spec.module, pfx=pluginconfpfx)

            hidden = spec.get('hidden', False)
            if not hidden:
                self.add_operation(name)

        except Exception, e:
            self.logger.error("Unable to load local plugin '%s': %s" % (
                name, str(e)))
        
    def add_global_plugin(self, spec):
        try:
            name = spec.setdefault('name', spec.get('klass', spec.module))
            self.global_plugins[name] = spec
            
            self.mm.loadModule(spec.module, pfx=pluginconfpfx)

            self.gpmon.loadPlugin(name, spec)
            self.start_global_plugin(name)
                
        except Exception, e:
            self.logger.error("Unable to load global plugin '%s': %s" % (
                name, str(e)))

    def show_error(self, errmsg, raisetab=True):
        obj = self.gpmon.getPlugin('Errors')
        obj.add_error(errmsg)
        if raisetab:
            self.ds.raise_tab('Errors')
        
    # BASIC IMAGE OPERATIONS

    def guess_filetype(self, filepath):
        # If we have python-magic, use it to determine file type
        typ = None
        if have_magic:
            try:
                typ = magic.from_file(filepath, mime=True)
            except Exception, e:
                pass

        if typ == None:
            try:
                typ, enc = mimetypes.guess_type(filepath)
            except Exception, e:
                pass

        if typ:
            typ, subtyp = typ.split('/')
            self.logger.debug("MIME type is %s/%s" % (typ, subtyp))
            return (typ, subtyp)

        raise ControlError("Can't determine file type of '%s'" % (filepath))

    def load_image(self, filepath):
        # Create an image.  Assume type to be an AstroImage unless
        # the MIME association says it is something different.
        try:
            typ, subtyp = self.guess_filetype(filepath)
        except Exception:
            # Can't determine file type: assume and attempt FITS
            typ, subtyp = 'image', 'fits'
        
        if (typ == 'image') and (subtyp != 'fits'):
            image = RGBImage.RGBImage(logger=self.logger)
        else:
            image = AstroImage.AstroImage(logger=self.logger)

        try:
            self.logger.info("Loading image from %s" % (filepath))
            image.load_file(filepath)
            #self.gui_do(chinfo.fitsimage.onscreen_message, "")

        except Exception, e:
            errmsg = "Failed to load file '%s': %s" % (
                filepath, str(e))
            self.logger.error(errmsg)
            try:
                (type, value, tb) = sys.exc_info()
                tb_str = "\n".join(traceback.format_tb(tb))
            except Exception, e:
                tb_str = "Traceback information unavailable."
            self.gui_do(self.show_error, errmsg + '\n' + tb_str)
            #chinfo.fitsimage.onscreen_message("Failed to load file", delay=1.0)
            raise ControlError(errmsg)

        self.logger.debug("Successfully loaded file into image object.")
        return image

    def load_file(self, filepath, chname=None, wait=True,
                  create_channel=True):
        """Load a file from filesystem and display it.

        Parameters
        ----------
        `filepath`: string
            the path of the file to load
        `chname`: string (optional)
            the name of the channel in which to display the image
        `wait`: boolean (optional)
            if True, then wait for the file to be loaded before returning
              (synchronous behavior)
        `create_channel`: boolean (optional)
            if not False, then will create the channel if it does not exist
        Returns
        -------
        image:
            the image object that was loaded
        """
        if not chname:
            chinfo = self.get_channelInfo()
            chname = chinfo.name
        else:
            if not self.has_channel(chname) and create_channel:
                self.gui_call(self.add_channel, chname)
            chinfo = self.get_channelInfo(chname)
            chname = chinfo.name

        # Sometimes there is a newline at the end of this..
        filepath = filepath.strip()

        # TODO: need progress bar or other visual indicator
        #self.gui_do(chinfo.fitsimage.onscreen_message, "Loading file...")
        image = self.load_image(filepath)

        (path, filename) = os.path.split(filepath)

        image.set(name=filename, path=filepath, chname=chname)

        # Display image.  If the wait parameter is False then don't wait
        # for the image to load into the viewer
        if wait:
            self.gui_call(self.add_image, filename, image, chname=chname)
        else:
            self.gui_do(self.bulk_add_image, filename, image, chname)
            #self.gui_do(self.add_image, filename, image, chname=chname)

        # Return the image
        return image

    def add_preload(self, chname, imname, path):
        bnch = Bunch.Bunch(chname=chname, imname=imname, path=path)
        with self.preloadLock:
            self.preloadList.append(bnch)
        self.nongui_do(self.preload_scan)
        
    def preload_scan(self):
        # preload any pending files
        # TODO: do we need any throttling of loading here?
        with self.preloadLock:
            while len(self.preloadList) > 0:
                bnch = self.preloadList.pop(0)
                self.nongui_do(self.preload_file, bnch.chname,
                                  bnch.imname, bnch.path)

    def preload_file(self, chname, imname, path):
        # sanity check to see if the file is already in memory
        self.logger.debug("preload: checking %s in %s" % (imname, chname))
        chinfo = self.get_channelInfo(chname)
        datasrc = chinfo.datasrc
        self.logger.debug("has item: %s" % datasrc.has_key(imname))
        if not chinfo.datasrc.has_key(imname):
            # not there--load image in a non-gui thread, then have the
            # gui add it to the channel silently
            self.logger.info("preloading image %s" % (path))
            image = self.load_image(path)
            self.gui_do(self.add_image, imname, image,
                           chname=chname, silent=True)
        self.logger.debug("end preload")
    
    def zoom_in(self):
        fitsimage = self.getfocus_fitsimage()
        fitsimage.zoom_in()
        return True

    def zoom_out(self):
        fitsimage = self.getfocus_fitsimage()
        fitsimage.zoom_out()
        return True

    def zoom_1_to_1(self):
        fitsimage = self.getfocus_fitsimage()
        fitsimage.zoom_to(1)
        return True

    def zoom_fit(self):
        fitsimage = self.getfocus_fitsimage()
        fitsimage.zoom_fit()
        return True

    def auto_levels(self):
        fitsimage = self.getfocus_fitsimage()
        fitsimage.auto_levels()

    def prev_img(self):
        chinfo = self.get_channelInfo()
        with self.lock:
            self.logger.debug("Previous image")
            if chinfo.cursor <= 0:
                self.showStatus("No previous image!")
                self.logger.error("No previous image!")
            else:
                chinfo.cursor -= 1
                image = chinfo.datasrc[chinfo.cursor]
                self._switch_image(chinfo, image)
            
        return True

    def next_img(self):
        chinfo = self.get_channelInfo()
        with self.lock:
            self.logger.debug("Next image")
            n = len(chinfo.datasrc) - 1
            if chinfo.cursor >= n:
                self.showStatus("No next image!")
                self.logger.error("No next image!")
            else:
                chinfo.cursor += 1
                image = chinfo.datasrc[chinfo.cursor]
                self._switch_image(chinfo, image)

        return True

        
    def add_workspace(self, wsname, wstype, inSpace='channels'):

        bnch = self.ds.make_ws(name=wsname, group=1, wstype=wstype)
        if inSpace != 'top level':
            self.ds.add_tab(inSpace, bnch.widget, 1, bnch.name)
        else:
            #width, height = 700, 800
            #self.ds.create_toplevel_ws(width, height, group=1)
            self.ds.add_toplevel(bnch.widget, bnch.name)
        return True
        
    # CHANNEL MANAGEMENT

    def add_image(self, imname, image, chname=None, silent=False):
        if not chname:
            # no channel name provided, so add to current channel
            chname = self.chinfo.name
        self.logger.debug("Adding image '%s' in channel %s" % (
            imname, chname))

        # add image to named channel
        if not self.has_channel(chname):
            chinfo = self.add_channel(chname)
        else:
            chinfo = self.get_channelInfo(chname)
        chinfo.datasrc[imname] = image

        #self.make_callback('add-image', chinfo.name, image)

        if not silent:
            self._add_image_update(chinfo, image)


    def _add_image_update(self, chinfo, image):
        self.make_callback('add-image', chinfo.name, image)

        current = chinfo.datasrc.youngest()
        curname = current.get('name')
        self.logger.debug("image=%s youngest=%s" % (image.get('name'), curname))
        if current != image:
            return

        # switch to current image?
        if chinfo.prefs['switchnew']:
            #and chinfo.switchfn(image):
            self.logger.debug("switching to new image '%s'" % (curname))
            self._switch_image(chinfo, image)
            
        if chinfo.prefs['raisenew']:
            curinfo = self.get_channelInfo()
            if chinfo.name != curinfo.name:
                self.change_channel(chinfo.name)

    def bulk_add_image(self, imname, image, chname):
        if not self.has_channel(chname):
            chinfo = self.add_channel(chname)
        else:
            chinfo = self.get_channelInfo(chname)
        chinfo.datasrc[imname] = image

        #self.update_pending(timeout=0)

        # By delaying the update here, more images may be bulk added
        # before the _add_image_update executes--it will then only
        # update the gui for the latest image, which saves wasted work
        self.gui_do(self._add_image_update, chinfo, image)

        
    def update_image(self, imname, image, chname):
        self.logger.debug("Updating image '%s' in channel %s" % (
            imname, chname))

        # add image to named channel
        if not self.has_channel(chname):
            self.add_channel(chname)
        chinfo = self.get_channelInfo(chname)
        chinfo.datasrc[imname] = image

        self._switch_image(chinfo, image)

    def get_image(self, chname, fitsname):
        chinfo = self.get_channelInfo(chname)
        image = chinfo.datasrc[fitsname]
        return image

    def getfocus_fitsimage(self):
        chinfo = self.get_channelInfo()
        if chinfo == None:
            return None
        return chinfo.fitsimage
        
    def get_fitsimage(self, chname):
        chinfo = self.get_channelInfo(chname)
        if chinfo == None:
            return None
        return chinfo.fitsimage
        
    def switch_name(self, chname, imname, path=None):
        chinfo = self.get_channelInfo(chname)
        if chinfo.datasrc.has_key(imname):
            # Image is still in the heap
            image = chinfo.datasrc[imname]
            self.change_channel(chname, image=image)

        else:
            if path != None:
                self.logger.debug("Image '%s' is no longer in memory; attempting to load from %s" % (
                    imname, path))
                self.load_file(path, chname=chname)

            else:
                raise ControlError("No image by the name '%s' found" % (
                    imname))

            
    def _switch_image(self, chinfo, image):
        # update cursor to match image
        try:
            name = image.get('name')
            chinfo.cursor = chinfo.datasrc.index(name)
        except Exception, e:
            self.logger.warn("Couldn't find index: %s" % (str(e)))
            chinfo.cursor = 0

        with self.lock:
            self.logger.info("Update image start")
            start_time = time.time()
            try:
                curimage = chinfo.fitsimage.get_image()
                if curimage != image:
                    self.logger.info("Setting image...")
                    chinfo.fitsimage.set_image(image)

                    # Update active plugins
                    opmon = chinfo.opmon
                    for key in opmon.get_active():
                        ## bnch = opmon.get_info(key)
                        obj = opmon.getPlugin(key)
                        try:
                            obj.redo()
                        except Exception, e:
                            self.logger.error("Failed to continue operation: %s" % (
                                str(e)))

                else:
                    self.logger.debug("Apparently no need to set large fits image.")
                    # TODO: there is a bug here, we shouldn't have to do this!
                    #chinfo.fitsimage.set_image(image)

                split_time1 = time.time()
                self.logger.info("Large image update: %.4f sec" % (
                    split_time1 - start_time))

            finally:
                pass

        return True


    def change_channel(self, chname, image=None, raisew=True):
        name = chname.lower()
        if not self.chinfo:
            oldchname = None
        else:
            oldchname = self.chinfo.name.lower()

        chinfo = self.get_channelInfo(name)
        if name != oldchname:
            with self.lock:
                self.chinfo = chinfo

            # change plugin manager info
            chinfo.opmon.update_taskbar(localmode=False)
                
            # Update the channel control
            self.w.channel.show_text(chinfo.name)

        if name != oldchname:
            # raise tab
            if raisew:
                #self.ds.raise_tab(chinfo.workspace)
                self.ds.raise_tab(name)

            if oldchname != None:
                try:
                    self.ds.highlight_tab(oldchname, False)
                except:
                    # old channel may not exist!
                    pass
            self.ds.highlight_tab(name, True)

            ## # Update title bar
            title = chinfo.name
            ## if image != None:
            ##     name = image.get('name', 'Noname')
            ##     title += ": %s" % (name)
            self.set_titlebar(title)

        if image:
            self._switch_image(chinfo, image)
        
        ## elif len(chinfo.datasrc) > 0:
        ##     n = chinfo.cursor
        ##     image = chinfo.datasrc[n]
        ##     self._switch_image(chinfo, image)
            
        self.make_callback('active-image', chinfo.fitsimage)

        self.update_pending()
        return True

    def has_channel(self, chname):
        name = chname.lower()
        with self.lock:
            return self.channel.has_key(name)
                
    def get_channelInfo(self, chname=None):
        with self.lock:
            if not chname:
                return self.chinfo
            name = chname.lower()
            return self.channel[name]
                
    def get_channelName(self, fitsimage):
        with self.lock:
            items = self.channel.items()
        for name, chinfo in items:
            if chinfo.fitsimage == fitsimage:
                return name
        return None
                
    def add_channel_internal(self, chname, datasrc=None, num_images=1):
        name = chname.lower()
        with self.lock:
            try:
                chinfo = self.channel[name]
            except KeyError:
                self.logger.debug("Adding channel '%s'" % (chname))
                if datasrc == None:
                    datasrc = Datasrc.Datasrc(num_images)

                chinfo = Bunch.Bunch(datasrc=datasrc,
                                 name=chname, cursor=0)
            
                self.channel[name] = chinfo
        return chinfo

        
    def add_channel(self, chname, datasrc=None, workspace=None,
                    num_images=None):
        """Create a new Ginga channel.

        Parameters
        ----------
        `chname`: string
            the name of the channel to create.

        Returns
        -------
        chinfo: bunch
            the channel info bunch
        """
        if self.has_channel(chname):
            return self.get_channelInfo(chname)
        
        name = chname
        prefs = self.prefs.createCategory('channel_'+name)
        try:
            prefs.load(onError='raise')

        except Exception, e:
            self.logger.warn("no saved preferences found for channel '%s': %s" % (
                name, str(e)))
            # copy "Image" prefs to new channel
            try:
                oprefs = self.prefs.getSettings('channel_Image')
                self.logger.debug("Copying settings from 'Image' to '%s'" % (
                    name))
                oprefs.copySettings(prefs)
            except KeyError:
                pass
            
        num_images = self.settings.get('numImages', 1)
        use_readout = not self.settings.get('shareReadout', True)
        
        # Make sure these preferences are at least defined
        prefs.setDefaults(switchnew=True, numImages=num_images,
                          raisenew=True, genthumb=True)

        chinfo = self.add_channel_internal(name,
                                           num_images=prefs['numImages'])

        with self.lock:
            bnch = self.add_viewer(chname, prefs,
                                   use_readout=use_readout,
                                   workspace=workspace)

            opmon = self.getPluginManager(self.logger, self,
                                          self.ds, self.mm)
            opmon.set_widget(self.w.optray)
            
            chinfo.setvals(widget=bnch.view,
                           readout=bnch.readout,
                           container=bnch.container,
                           workspace=bnch.workspace,
                           fitsimage=bnch.fitsimage,
                           prefs=prefs,
                           opmon=opmon)
            
            # Update the channels control
            self.channelNames.append(chname)
            self.channelNames.sort()
            #print "CHANNELS ARE %s" % self.channelNames
            self.w.channel.insert_alpha(chname)
            
        # Prepare local plugins for this channel
        for opname, spec in self.local_plugins.items():
            opmon.loadPlugin(opname, spec, chinfo=chinfo)

        self.make_callback('add-channel', chinfo)
        return chinfo
            
    def delete_channel(self, chname):
        name = chname.lower()
        # TODO: need to close plugins open on this channel
            
        with self.lock:
            chinfo = self.channel[name]

            # Update the channels control
            self.channelNames.remove(chname)
            self.channelNames.sort()
            #print "CHANNELS ARE %s" % self.channelNames
            self.w.channel.delete_alpha(chname)

            self.ds.remove_tab(chname)
            del self.channel[name]

        self.make_callback('delete-channel', chinfo)
        
    def get_channelNames(self):
        with self.lock:
            return [ self.channel[key].name for key in self.channel.keys() ]

    def scale2text(self, scalefactor):
        if scalefactor >= 1.0:
            #text = '%dx' % (int(scalefactor))
            text = '%.2fx' % (scalefactor)
        else:
            #text = '1/%dx' % (int(1.0/scalefactor))
            text = '1/%.2fx' % (1.0/scalefactor)
        return text
    
    def get_sky_image(self, key, params):

        #filename = 'sky-' + str(time.time()).replace('.', '-') + '.fits'
        filename = 'sky-' + str(self.dsscnt) + '.fits'
        self.dsscnt = (self.dsscnt + 1) % 5
        filepath = os.path.join("/tmp", filename)
        try:
            os.remove(filepath)
        except Exception, e:
            self.logger.error("failed to remove tmp file '%s': %s" % (
                filepath, str(e)))
        try:
            dstpath = self.imgsrv.getImage(key, filepath, **params)
            return dstpath

        except Exception, e:
            errmsg = "Failed to load sky image: %s" % (str(e))
            self.show_error(errmsg)
            raise ControlError(errmsg)

    def get_catalog(self, key, params):
        try:
            starlist, info = self.imgsrv.getCatalog(key, None, **params)
            return starlist, info
            
        except Exception, e:
            errmsg ="Failed to load catalog: %s" % (str(e))
            raise ControlError(errmsg)


    def banner(self, raiseTab=True):
        bannerFile = os.path.join(self.iconpath, 'ginga-splash.ppm')
        chname = 'Ginga'
        self.add_channel(chname)
        self.nongui_do(self.load_file, bannerFile, chname=chname)
        if raiseTab:
            self.change_channel(chname)
        chinfo = self.get_channelInfo(chname)
        chinfo.fitsimage.zoom_fit()

    def followFocus(self, tf):
        self.channel_follows_focus = tf

    def showStatus(self, text):
        """Write a message to the status bar.  _text_ is the message.
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
        self.logger.debug("Subclass could override this to play sound file '%s'" % (
            filepath))

    def get_color_maps(self):
        """Get the list of named color maps.

        Parameters
        ----------
        None
            
        Returns
        -------
        `names`: list
            A list of all named colormaps installed

        """
        return cmap.get_names()

    def get_intensity_maps(self):
        """Get the list of named intensity maps.

        Parameters
        ----------
        None
            
        Returns
        -------
        `names`: list
            A list of all named intensity maps installed

        """
        return imap.get_names()


class GuiLogHandler(logging.Handler):
    """Logs to a pane in the GUI."""

    def __init__(self, fv, level=logging.NOTSET):
        self.fv = fv
        logging.Handler.__init__(self, level=level)
        
    def emit(self, record):
        text = self.format(record)
        self.fv.logit(text)

# END
