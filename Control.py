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

# Local application imports
import imap, cmap
import Catalog
import AstroImage
import PythonImage
import Bunch
import Datasrc
import Callback
import FitsImage

default_cmap = 'ramp'
default_imap = 'ramp'
default_autoscale = 'override'
default_autolevels = 'on'
default_autocut_method = 'histogram'

#pluginconfpfx = 'plugins'
pluginconfpfx = None


class ControlError(Exception):
    pass

class GingaControl(Callback.Callbacks):
     
    def __init__(self, logger, threadPool, module_manager, settings,
                 ev_quit=None, datasrc_length=20, follow_focus=False):
        Callback.Callbacks.__init__(self)

        self.logger = logger
        self.threadPool = threadPool
        self.mm = module_manager
        self.settings = settings
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

        self.lock = threading.RLock()
        self.channel = {}
        self.channelNames = []
        self.chinfo = None
        self.chncnt = 0
        self.statustask = None

        # Preferences
        # Should channel change as mouse moves between windows
        self.channel_follows_focus = follow_focus
        
        # defaults
        self.default_cmap = default_cmap
        self.default_imap = default_imap
        self.default_autoscale = default_autoscale
        self.default_autolevels = default_autolevels
        self.default_autocut_method = default_autocut_method
        # Number of images to keep around in memory
        self.default_datasrc_length = datasrc_length
        
        self.cm = cmap.get_cmap(self.default_cmap)
        self.im = imap.get_imap(self.default_imap)

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

        try:
            gprefs = self.settings.getSettings('ginga')
        except KeyError:
            gprefs = self.settings.createCategory('ginga')
        gprefs.setvals(color_map='ramp', intensity_map='ramp',
                       auto_scale='off')
        

    def get_ServerBank(self):
        return self.imgsrv

    def get_settings(self):
        return self.settings

    ####################################################
    # CALLBACKS
    ####################################################
    
    def showxy(self, fitsimage, data_x, data_y):
        # Note: FITS coordinates are 1-based, whereas numpy FITS arrays
        # are 0-based
        fits_x, fits_y = data_x + 1, data_y + 1
        # Get the value under the data coordinates
        try:
            #value = fitsimage.get_data(data_x, data_y)
            # We report the value across the pixel, even though the coords
            # change halfway across the pixel
            value = fitsimage.get_data(int(data_x+0.5), int(data_y+0.5))

        except (Exception, FitsImage.FitsImageCoordsError):
            value = None

        # Calculate WCS RA
        try:
            # NOTE: image function operates on DATA space coords
            image = fitsimage.get_image()
            if image == None:
                # No image loaded for this channel
                return
            ## ra_txt, dec_txt = image.pixtoradec(data_x, data_y,
            ##                                    format='str')
            ra_txt, dec_txt = image.pixtoradec(fits_x, fits_y,
                                               format='str', coords='fits')
        except Exception, e:
            self.logger.warn("Bad coordinate conversion: %s" % (
                str(e)))
            ra_txt  = 'BAD WCS'
            dec_txt = 'BAD WCS'

        self.make_callback('field-info', fitsimage,
                           fits_x, fits_y, value, ra_txt, dec_txt)
        
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

    def readout_cb(self, viewer, fitsimage,
                   fits_x, fits_y, value, ra_txt, dec_txt, readout, name):
        # TEMP: hack
        if readout.fitsimage != fitsimage:
            return

        # If this is a multiband image, then average the values for the readout
        if isinstance(value, numpy.ndarray):
            avg = numpy.average(value)
            value = avg
            
        # Update the readout
        maxx = readout.maxx
        maxy = readout.maxy
        maxv = readout.maxv
        fits_x = "%.3f" % fits_x
        fits_y = "%.3f" % fits_y
        text = "RA: %-12.12s  DEC: %-12.12s  X: %-*.*s  Y: %-*.*s  Value: %-*.*s" % (
            ra_txt, dec_txt, maxx, maxx, fits_x,
            maxy, maxy, fits_y, maxv, maxv, value)
        readout.set_text(text)

        # Draw colorbar value wedge
        #self.colorbar.set_current_value(value)

    def motion_cb(self, fitsimage, button, data_x, data_y):
        """Motion event in the big fits window.  Show the pointing
        information under the cursor.
        """
        if button == 0:
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
        elif keyname == 'f':
            self.toggle_fullscreen()
        elif keyname == 'F':
            self.build_fullscreen()
        elif keyname == 'm':
            self.maximize()
        elif keyname == 'escape':
            chinfo = self.get_channelInfo(chname)
            opmon = chinfo.opmon
            opmon.deactivate_focused()
        elif keyname in self.fn_keys:
            index = self.fn_keys.index(keyname)
            if (index >= 0) and (index < len(self.operations)):
                opname = self.operations[index]
                self.start_operation_channel(chname, opname, None)

    def dragdrop(self, fitsimage, urls):
        """Called when a drop operation is performed on our main window.
        We are called back with a URL and we attempt to load it if it
        names a file.
        """
        for url in urls:
            match = re.match(r"^file://(.+)$", url)
            if match:
                fitspath = match.group(1)
                #self.load_file(fitspath)
                chname = self.get_channelName(fitsimage)
                self.nongui_do(self.load_file, fitspath, chname=chname,
                               wait=False)

    def _match_cmap(self, fitsimage, colorbar):
        rgbmap = fitsimage.get_rgbmap()
        loval, hival = fitsimage.get_cut_levels()
        colorbar.set_range(loval, hival, redraw=False)
        colorbar.set_rgbmap(rgbmap)
        
    def change_cbar(self, viewer, fitsimage, cbar):
        self._match_cmap(fitsimage, cbar)
        
    def change_range_cb(self, fitsimage, loval, hival, cbar):
        if fitsimage != self.getfocus_fitsimage():
            return False
        cbar.set_range(loval, hival)
        
    def cbar_value_cb(self, cbar, value, event):
        #print "CBAR VALUE = %f" % (value)
        chinfo = self.get_channelInfo()
        readout = chinfo.readout
        maxv = readout.maxv
        text = "Value: %-*.*s" % (maxv, maxv, value)
        readout.set_text(text)
        
    def rgbmap_cb(self, rgbmap, fitsimage):
        if fitsimage != self.getfocus_fitsimage():
            return False
        self.change_cbar(self, fitsimage, self.colorbar)
        
    def focus_cb(self, fitsimage, tf, name):
        """Called when _fitsimage_ gets (tf==True) or loses (tf==False)
        the focus."""
        self.logger.debug("Focus %s=%s" % (name, tf))
        if tf:
            if fitsimage != self.getfocus_fitsimage():
                self.change_channel(name, raisew=False)
                # TODO: this is a hack to force the cursor change on the new
                # window--make this better
                fitsimage.to_default_mode()

            #self._match_cmap(fitsimage, self.colorbar)

        return True

    def stop(self):
        self.ev_quit.set()

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

    def load_image(self, filepath):
        # Create an image.  Assume type to be an AstroImage unless
        # the MIME association says it is something different.
        image = AstroImage.AstroImage(logger=self.logger)
        try:
            self.logger.info("Loading image from %s" % (filepath))
            typ, enc = mimetypes.guess_type(filepath)
            if typ:
                typ, subtyp = typ.split('/')
                self.logger.info("MIME type is %s/%s" % (typ, subtyp))
                if (typ == 'image') and (subtyp != 'fits'):
                    image = PythonImage.PythonImage(logger=self.logger)

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

    def load_file(self, filepath, chname=None, wait=True):
        if not chname:
            chinfo = self.get_channelInfo()
            chname = chinfo.name
        else:
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

        
    # CHANNEL MANAGEMENT

    def add_image(self, imname, image, chname=None):
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

        self._add_image_update(chinfo, image)


    def _add_image_update(self, chinfo, image):
        current = chinfo.datasrc.youngest()
        curname = current.get('name')
        self.logger.debug("image=%s youngest=%s" % (image.get('name'), curname))
        if current != image:
            return

        # switch to current image?
        if chinfo.prefs.switchnew:
            #and chinfo.switchfn(image):
            self.logger.debug("switching to new image '%s'" % (curname))
            self._switch_image(chinfo, image)
            
        if chinfo.prefs.raisenew:
            curinfo = self.get_channelInfo()
            if chinfo.name != curinfo.name:
                self.change_channel(chinfo.name)

        self.make_callback('add-image', chinfo.name, image)

    def bulk_add_image(self, imname, image, chname):
        if not self.has_channel(chname):
            chinfo = self.add_channel(chname)
        else:
            chinfo = self.get_channelInfo(chname)
        chinfo.datasrc[imname] = image

        #self.make_callback('add-image', chinfo.name, image)
        #self.update_pending(timeout=0)

        # By delaying the update here, more images may be bulk added
        # before the _add_image_update executes--it will then only
        # update the gui for the latest image, which saves lots of work
        self.gui_do(self._add_image_update, chinfo, image)
        #self._add_image_update(chinfo, image)

        
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

        print "1"
        chinfo = self.get_channelInfo(name)
        if name != oldchname:
            with self.lock:
                self.chinfo = chinfo

            # change plugin manager info
            chinfo.opmon.update_taskbar(localmode=False)
                
            # Update the channel control
            self.w.channel.show_text(chinfo.name)

        print "2"
        if name != oldchname:
            # raise tab
            if raisew:
                self.ds.raise_tab(name)

            if oldchname != None:
                self.ds.highlight_tab(oldchname, False)
            self.ds.highlight_tab(name, True)

            ## # Update title bar
            title = chinfo.name
            ## if image != None:
            ##     name = image.get('name', 'Noname')
            ##     title += ": %s" % (name)
            self.set_titlebar(title)

        print "3"
        if image:
            self._switch_image(chinfo, image)
        
        ## elif len(chinfo.datasrc) > 0:
        ##     n = chinfo.cursor
        ##     image = chinfo.datasrc[n]
        ##     self._switch_image(chinfo, image)
            
        print "4"
        self.make_callback('active-image', chinfo.fitsimage)

        print "5"
        self.update_pending()
        print "6"
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
                
    def add_channel_internal(self, chname, num_images=None):
        name = chname.lower()
        with self.lock:
            try:
                chinfo = self.channel[name]
            except KeyError:
                self.logger.debug("Adding channel '%s'" % (chname))
                if not num_images:
                    num_images = self.default_datasrc_length
                datasrc = Datasrc.Datasrc(num_images)

                chinfo = Bunch.Bunch(datasrc=datasrc,
                                 name=chname, cursor=0)
            
                self.channel[name] = chinfo
        return chinfo

        
    def add_channel(self, chname, datasrc=None, workspace=None,
                    num_images=None):

        if self.has_channel(chname):
            return self.get_channelInfo(chname)
        
        chinfo = self.add_channel_internal(chname, num_images=num_images)

        with self.lock:
            name = chinfo.name
            bnch = self.add_viewer(chname, self.cm, self.im,
                                   workspace=workspace)

            prefs = None
            try:
                self.logger.debug("loading preferences for channel '%s'" % (
                    name))
                prefs = self.settings.load(name, "prefs")

            except Exception, e:
                self.logger.warn("no saved preferences found for channel '%s': %s" % (
                    name, str(e)))
                self.settings.createCategory(name)

            # Make sure these preferences are at least defined
            self.settings.setDefaults(name, switchnew=True,
                                      raisenew=True,
                                      genthumb=True)
            prefs = self.settings.getSettings(name)
            self.logger.debug("prefs for '%s' are %s" % (name, str(prefs)))

            try:
                self.preferences_to_fitsimage(prefs, bnch.fitsimage,
                                                  redraw=False)
            except Exception, e:
                self.logger.error("failed to get or set preferences for channel '%s': %s" % (
                    name, str(e)))

            opmon = self.getPluginManager(self.logger, self,
                                          self.ds, self.mm)
            opmon.set_widget(self.w.optray)
            
            chinfo.setvals(widget=bnch.view,
                           readout=bnch.readout,
                           container=bnch.container,
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
        with self.lock:
            chinfo = self.channel[name]
            self.ds.remove_tab(chname)
            del self.channel[name]

            # Update the channels control
            self.channelNames.remove(chname)
            self.channelNames.sort()
            #print "CHANNELS ARE %s" % self.channelNames
            self.w.channel.delete_alpha(chname)

        # TODO: need to close plugins open on this channel
            
        self.make_callback('delete-channel', chinfo)
        
    def get_channelNames(self):
        with self.lock:
            return [ self.channel[key].name for key in self.channel.keys() ]
                
    def preferences_to_fitsimage(self, prefs, fitsimage, redraw=False):
        print "prefs=%s" % (str(prefs))

        rgbmap = fitsimage.get_rgbmap()

        cm = rgbmap.get_cmap()
        prefs.color_map = prefs.get('color_map', cm.name)
        cm = cmap.get_cmap(prefs.color_map)
        fitsimage.set_cmap(cm, redraw=False)

        im = rgbmap.get_imap()
        prefs.intensity_map = prefs.get('intensity_map', im.name)
        im = imap.get_imap(prefs.intensity_map)
        fitsimage.set_imap(im, redraw=False)

        prefs.auto_levels = prefs.get('auto_levels',
                                      fitsimage.t_autolevels)
        fitsimage.enable_autolevels(prefs.auto_levels)
        ## prefs.usesavedcuts = prefs.get('usesavedcuts',
        ##                                fitsimage.t_use_saved_cuts)
        ## fitsimage.t_use_saved_cuts = prefs.usesavedcuts

        prefs.autocut_method = prefs.get('autocut_method',
                                      fitsimage.t_autocut_method)
        prefs.autocut_hist_pct = prefs.get('autocut_hist_pct',
                                        fitsimage.t_autocut_hist_pct)
        fitsimage.set_autolevel_params(prefs.autocut_method,
                                            pct=prefs.autocut_hist_pct)
                                             
        prefs.auto_scale = prefs.get('auto_scale', fitsimage.t_autoscale)
        fitsimage.enable_autoscale(prefs.auto_scale)

        zmin, zmax = fitsimage.get_autoscale_limits()
        prefs.zoom_min = prefs.get('zoom_min', zmin)
        prefs.zoom_max = prefs.get('zoom_max', zmax)
        fitsimage.set_autoscale_limits(prefs.zoom_min, prefs.zoom_max)

        (flipX, flipY, swapXY) = fitsimage.get_transforms()
        prefs.flipX = prefs.get('flipX', flipX)
        prefs.flipY = prefs.get('flipY', flipY)
        prefs.swapXY = prefs.get('swapXY', swapXY)
        fitsimage.transform(prefs.flipX, prefs.flipY, prefs.swapXY,
                                 redraw=redraw)

        revpan = fitsimage.get_pan_reverse()
        prefs.reverse_pan = prefs.get('reverse_pan', revpan)
        fitsimage.set_pan_reverse(revpan)

    def scale2text(self, scalefactor):
        if scalefactor >= 1.0:
            text = '%dx' % (int(scalefactor))
        else:
            text = '1/%dx' % (int(1.0/scalefactor))
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
            self.imgsrv.getImage(key, filepath, **params)

            return filepath
        except Exception, e:
            errmsg = "Failed to load sky image: %s" % (str(e))
            self.show_error(errmsg)
            raise ControlError(errmsg)

    def get_catalog(self, key, params):

        try:
            starlist = self.imgsrv.getCatalog(key, None, **params)
            return starlist
            
        except Exception, e:
            errmsg ="Failed to load catalog: %s" % (str(e))
            raise ControlError(errmsg)


    def save_file(self, filepath, format='png', quality=90):
        chinfo = self.get_channelInfo()
        chinfo.fitsimage.save_image_as_file(filepath, format,
                                            quality=quality)
        
    def banner(self):
        bannerFile = os.path.join(self.iconpath, 'ginga-splash.ppm')
        chname = 'Ginga'
        self.add_channel(chname)
        self.nongui_do(self.load_file, bannerFile, chname=chname)
        self.change_channel(chname)

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


class GuiLogHandler(logging.Handler):
    """Logs to a pane in the GUI."""

    def __init__(self, fv, level=logging.NOTSET):
        self.fv = fv
        logging.Handler.__init__(self, level=level)
        
    def emit(self, record):
        text = self.format(record)
        self.fv.logit(text)

# END
