#
# IRAFBase.py -- IRAF plugin base class for Ginga fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
The IRAF plugin implements a remote control interface for the Ginga FITS
viewer from an IRAF session.  In particular it supports the use of the
IRAF 'display' and 'imexamine' commands.

The IRAFBase class is a non-GUI specific base class for the plugin.

Instructions for use:

Set the environment variable IMTDEV appropriately, e.g.

    $ export IMTDEV=inet:45005         (or)
    $ export IMTDEV=unix:/tmp/.imtg45
    
Start Ginga with an option to load the IRAF plugin as a global:

$ ./ginga.py --modules=IRAF

Start IRAF.

From Ginga you can load images and then use 'imexamine' from IRAF to load
them, do photometry, etc.  You can also use the 'display' command from IRAF
to show images in Ginga.  The 'IRAF' tab will show the mapping from Ginga
channels to IRAF numerical 'frames'.

When using imexamine, the plugin disables normal UI processing on the
channel image so that keystrokes, etc. are passed through to IRAF.  You can
toggle back and forth between local Ginga control and IRAF control using
the radio buttons at the top of the tab or using the space bar.
"""
import sys, os
import logging
import threading
import socket
import Queue
import array
import numpy
import time

import GingaPlugin
import AstroImage
import Bunch

# XImage protocol support
import IIS_DataListener as iis


class IRAFBase(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(IRAFBase, self).__init__(fv)

        self.keyqueue = Queue.Queue()
        self.keyevent = threading.Event()
        self.keymap = {
            'comma': ',',
            }
        self.ctrldown = False

        self.layertag = 'iraf-canvas'
        # this will be set in initialize()
        self.canvas = None

        self.addr = iis.get_interface()
        
        self.ev_quit = self.fv.ev_quit
        self.dataTask = None

        fv.add_callback('add-channel', self.add_channel)
        fv.add_callback('delete-channel', self.delete_channel)
        #fv.set_callback('active-image', self.focus_cb)


    def add_channel(self, viewer, chinfo):
        self.logger.debug("channel %s added." % (chinfo.name))

        n = self.channel_to_frame(chinfo.name)
        if n == None:
            found = len(self.fb)
            for n, fb in self.fb.items():
                if fb.chname == None:
                    found = n
            fb = self.init_frame(found)
            fb.chname = chinfo.name
            
        fmap = self.get_channel_frame_mapping()
        self.fv.gui_do(self.update_chinfo, fmap)

        chinfo.fitsimage.add_callback('image-set', self.new_image_cb,
                                      chinfo)

    def delete_channel(self, viewer, chinfo):
        self.logger.debug("delete channel %s" % (chinfo.name))

        n = self.channel_to_frame(chinfo.name)
        if n != None:
            self.fb[n].chname = None

        fmap = self.get_channel_frame_mapping()
        self.fv.gui_do(self.update_chinfo, fmap)

    def setMode(self, modeStr, chname):
        self.imexam_chname = chname
        self.fv.gui_do(self._setMode, modeStr, chname)
        
    def switchMode(self, modeStr):
        modeStr = modeStr.lower()
        chname = self.imexam_chname
        chinfo = self.fv.get_channelInfo(chname)

        if modeStr == 'iraf':
            self.ui_disable(chinfo.fitsimage)
        else:
            self.ui_enable(chinfo.fitsimage)

    def start(self):
        # holds frame buffers
        self.fb = {}
        self.current_frame = 0
        
        # cursor position
        self.cursor_x = 1.0
        self.cursor_y = 1.0
        
        self.mode = 'ginga'
        self.imexam_active = False
        self.imexam_chname = None

        # init the first frame(frame 0)
        self.init_frame(0)

        try:
            if self.addr.prot == 'unix':
                os.remove(self.addr.path)
        except:
            pass
        
        # start the data listener task, if appropriate
        #ev_quit = threading.Event()
        self.dataTask = iis.IIS_DataListener(
            self.addr, controller=self,
            ev_quit=self.ev_quit, logger=self.logger)
        self.fv.nongui_do(self.dataTask.mainloop)

        
    def stop(self):
        if self.dataTask:
            self.dataTask.stop()

    def channel_to_frame(self, chname):
        for n, fb in self.fb.items():
            if fb.chname == chname:
                return n
        return None

    def get_channel_frame_mapping(self):
        l = [ (fb.chname, n+1) for n, fb in self.fb.items() ]
        return l
    
    def new_image_cb(self, fitsimage, image, chinfo):
        # check if this is an image we received from IRAF or
        # one that was loaded locally.
        ct = image.get('ct', None)
        if ct != None:
            # This image was sent by IRAF--we don't need to
            # construct extra fb information for it
            return
        
        n = self.channel_to_frame(chinfo.name)
        if n == None:
            return
        self.logger.debug("new image, frame is %d" % (n))
        fb = self.get_frame(n)
        #image = fitsimage.get_image()
        newpath  = image.get('path', 'NO_PATH')
        host = socket.getfqdn()
        newhost  = image.get('host', host)
        # protocol has a bizarre 16-char limit on hostname
        newhost = newhost[:16]

        # this is just a placeholder so that IIS_RequestHandler will
        # report something in this buffer
        fb.buffer = array.array('B', ' ')

        # Update IRAF "wcs" info so that IRAF can load this image

        #print "filling wcs info"
        fb.ct = iis.coord_tran()
        image.set(ct=ct)
        
        # iis version 1 data
        fb.ct.valid = 1
        fb.ct.a = 1
        fb.ct.b = 0
        fb.ct.c = 0
        fb.ct.d = 1
        fb.ct.tx = 0
        fb.ct.ty = 0
        fb.ct.z1 = 0
        fb.ct.z2 = 1
        fb.ct.zt = iis.W_UNITARY
        fb.ct.format = ''
        fb.ct.imtitle = ''
        
        # iis version 1+ data
        fb.ct.region = 'image'
        #x1, y1, x2, y2 = fitsimage.get_datarect()
        #wd, ht = x2-x1, y2-y1
        #x1, y1, x2, y2 = x1+1, y1+1, x2+1, y2+1
        #fb.ct.sx, fb.ct.sy = float(x1), float(y1)
        wd, ht = image.get_size()
        fb.ct.sx, fb.ct.sy = float(1), float(1)
        fb.ct.snx, fb.ct.sny = wd, ht
        fb.ct.dx, fb.ct.dy = 1, 1
        fb.ct.dnx, fb.ct.dny = wd, ht
        
        # ref
        newref = "!".join([newhost, newpath])
        fb.ct.ref = newref

        # TODO: we shouldn't have to know about this here...
        if (fb and fb.ct.a != None):
            wcs = "%s\n%f %f %f %f %f %f %f %f %d\n" % (
                fb.ct.imtitle, fb.ct.a, fb.ct.b, fb.ct.c, fb.ct.d,
                fb.ct.tx, fb.ct.ty, fb.ct.z1, fb.ct.z2, fb.ct.zt)
        else:
            wcs = "[NOSUCHWCS]\n"
        if (fb and fb.ct.sx != None):
            mapping = "%s %f %f %d %d %d %d %d %d\n%s\n" % (
                fb.ct.region, fb.ct.sx, fb.ct.sy, fb.ct.snx, fb.ct.sny, 
                fb.ct.dx, fb.ct.dy, fb.ct.dnx, fb.ct.dny, fb.ct.ref)
        else:
            mapping = ""
        fb.wcs = wcs + mapping
        #print "filled wcs info"
        

    # ------ BEGIN (methods called by IIS server) ----------------
    def init_frame(self, n):
        """
        NOTE: this is called from the IIS_RequestHandler
        """
        self.logger.debug("initializing frame %d" % (n))
        # create the frame, if needed
        try:
            fb = self.get_frame(n)
        except KeyError:
            fb = iis.framebuffer()
            self.fb[n] = fb

        fb.width = None
        fb.height = None
        fb.wcs = ''
        fb.image = None
        fb.bitmap = None
        fb.zoom = 1.0
        fb.buffer = array.array('B')
        fb.ct = iis.coord_tran()
        #fb.chname = None
        return fb
    
    def get_frame(self, n):
        """
        NOTE: this is called from the IISRequestHandler
        Will raise KeyError if frame is not initialized.
        """
        return self.fb[n]

    def set_frame(self, n):
        """
        NOTE: this is called from the IISRequestHandler
        """
        self.current_frame = n

    def display(self, frame, width, height, reverse=False):
        """
        NOTE: this is called from the IISRequestHandler
        """
        
        fb = self.get_frame(frame)
        self.current_frame = frame
        
        if reverse:
            fb.buffer.reverse()

        # frames are indexed from 1 in IRAF
        chname = fb.chname
        if chname == None:
            chname = 'Frame%d' % (frame+1)
            fb.chname = chname
            
        self.logger.debug("display to %s" %(chname))

        try:
            data = fb.buffer
            byteswap = False
            dims = (fb.height, fb.width)
            dtype = numpy.uint8
            metadata = {}

            image = IRAF_AstroImage()
            #image.load_buffer(fb.buffer, dims, dtype, byteswap=byteswap,
            #                  metadata=metadata)
            data = numpy.fromstring(fb.buffer, dtype=dtype)
            data = data.reshape(dims)
            # Image comes in from IRAF flipped for screen display
            data = numpy.flipud(data)
            image.set_data(data, metadata=metadata)
            # Save coordinate transform info
            image.set(ct=fb.ct)

            # make up a name (is there a protocol slot for the name?)
            fitsname = str(time.time())

            # extract path from ref
            oldref = fb.ct.ref
            items = oldref.split('!')
            host = items[0]
            path = '!'.join(items[1:])

            image.set(name=fitsname, path=path, host=host)
            #image.update_keywords(header)
        
        except Exception, e:
            # Some kind of error unpacking the data
            errmsg = "Error creating image data for '%s': %s" % (
                chname, str(e))
            self.logger.error(errmsg)
            raise GingaPlugin.PluginError(errmsg)

        # Enqueue image to display datasrc
        self.fv.gui_do(self.fv.add_image, fitsname, image,
                            chname=chname)

    def get_cursor(self):
        self.logger.info("get_cursor() called")
        chinfo = self.fv.get_channelInfo()
        # Find out which frame we are looking at
        #frame = self.current_frame
        frame = self.channel_to_frame(chinfo.name)
        fitsimage = chinfo.fitsimage
        image = fitsimage.get_image()
        last_x, last_y = fitsimage.get_last_data_xy()

        # Correct for surrounding framebuffer
        image = fitsimage.get_image()
        if isinstance(image, IRAF_AstroImage):
            last_x, last_y = image.get_corrected_xy(last_x, last_y)

        res = Bunch.Bunch(x=last_x, y=last_y, frame=frame)
        return res

    def get_keystroke(self):
        self.logger.info("get_keystroke() called")
        chinfo = self.fv.get_channelInfo()
        fitsimage = chinfo.fitsimage
        # Find out which frame we are looking at
        #frame = self.current_frame
        frame = self.channel_to_frame(chinfo.name)
        image = fitsimage.get_image()

        self.start_imexamine(fitsimage, chinfo.name)
        
        self.keyevent.wait()
        evt = self.keyqueue.get()

        self.stop_imexamine(fitsimage, chinfo.name)

        res = Bunch.Bunch(x=evt.x, y=evt.y, key=evt.key, frame=frame)
        return res

    def set_cursor(self, x, y):
        self.logger.info("TODO: set_cursor() called")
    
    # ------ END (methods called by IIS server) ----------------

    def ui_disable(self, fitsimage):
        fitsimage.ui_setActive(False)
        #self.canvas.ui_setActive(True)
        self.mode = 'iraf'

    def ui_enable(self, fitsimage):
        fitsimage.ui_setActive(True)
        #self.canvas.ui_setActive(False)
        self.mode = 'ginga'

    def start_imexamine(self, fitsimage, chname):
        # Turn off regular UI processing in the frame
        self.canvas.setSurface(fitsimage)
        # insert layer if it is not already
        try:
            obj = fitsimage.getObjectByTag(self.layertag)

        except KeyError:
            # Add canvas layer
            fitsimage.add(self.canvas, tag=self.layertag,
                          redraw=False)
        self.canvas.ui_setActive(True)

        self.imexam_active = True
        self.setMode('IRAF', chname)
        self.fv.gui_do(self.fv.ds.raise_tab, 'IRAF')

    def stop_imexamine(self, fitsimage, chname):
        self.imexam_active = False
        self.setMode('Ginga', chname)

    def window_key_press(self, canvas, keyname):
        if not self.imexam_active:
            return
        self.logger.info("key pressed: %s" % (keyname))
        if len(keyname) > 1:
            if keyname in ('shift_l', 'shift_r'):
                # ignore these keystrokes
                return
            elif keyname in ('control_l', 'control_r'):
                # control key combination
                self.ctrldown = True
                return
            elif keyname == 'space':
                self.toggleMode()
                return
            keyname = self.keymap.get(keyname, '?')

        if self.mode != 'iraf':
            return

        if self.ctrldown:
            if keyname == 'd':
                # User typed ^D
                keyname = chr(4)

        # Get cursor position
        fitsimage = canvas.getSurface()
        last_x, last_y = fitsimage.get_last_data_xy()

        # Correct for surrounding framebuffer
        image = fitsimage.get_image()
        if isinstance(image, IRAF_AstroImage):
            last_x, last_y = image.get_corrected_xy(last_x, last_y)

        # Get frame info
        #frame = self.current_frame
        chname = self.fv.get_channelName(fitsimage)
        chinfo = self.fv.get_channelInfo(chname)
        frame = self.channel_to_frame(chinfo.name)

        self.keyqueue.put(Bunch.Bunch(x=last_x, y=last_y, key=keyname,
                                      frame=frame))
        self.keyevent.set()

    def window_key_release(self, canvas, keyname):
        if not self.imexam_active:
            return
        self.logger.info("key released: %s" % (keyname))
        if len(keyname) > 1:
            if keyname in ('control_l', 'control_r'):
                # control key combination
                self.ctrldown = False

    def cursormotion(self, canvas, button, data_x, data_y):
        if self.mode != 'iraf':
            return
        
        fitsimage = self.fv.getfocus_fitsimage()

        if button == 0:
            return self.fv.showxy(fitsimage, data_x, data_y)

        return False

    def __str__(self):
        return 'iraf'

    
class IRAF_AstroImage(AstroImage.AstroImage):

    def info_xy(self, data_x, data_y):
        ct = self.get('ct', None)
        # Get the value under the data coordinates
        try:
            # We report the value across the pixel, even though the coords
            # change halfway across the pixel
            x, y = int(data_x+0.5), int(data_y+0.5)
            value = self.get_data_xy(x, y)

            # Mapping from bytescaled values back to original values
            value = iis.wcs_pix_transform(ct, value)
        except Exception, e:
            self.logger.error("Exception getting value at %d,%d: %s" % (
                x, y, str(e)))
            value = None

        # Calculate WCS RA, if available
        try:
            # Subtract offsets of data in framebuffer and add offsets of
            # rect beginning in source
            data_x = data_x - (ct.dx-1) + (ct.sx-1)
            data_y = data_y - (ct.dy-1) + (ct.sy-1)

            #ra_deg, dec_deg = wcs_coord_transform(ct, data_x, data_y)

            #ra_txt, dec_txt = self.wcs.deg2fmt(ra_deg, dec_deg, 'str')
            ra_txt  = 'BAD WCS'
            dec_txt = 'BAD WCS'
            
        except Exception, e:
            self.logger.warn("Bad coordinate conversion: %s" % (
                str(e)))
            ra_txt  = 'BAD WCS'
            dec_txt = 'BAD WCS'

        # Note: FITS coordinates are 1-based, whereas numpy FITS arrays
        # are 0-based
        fits_x, fits_y = data_x + 1, data_y + 1

        info = Bunch.Bunch(itype='astro', data_x=data_x, data_y=data_y,
                           fits_x=fits_x, fits_y=fits_y,
                           x=fits_x, y=fits_y,
                           ra_txt=ra_txt, dec_txt=dec_txt,
                           value=value)
        return info

    def get_corrected_xy(self, data_x, data_y):
        ct = self.get('ct', None)
        # Subtract offsets of data in framebuffer and add offsets of
        # rect beginning in source
        data_x = data_x - (ct.dx-1) + (ct.sx-1)
        data_y = data_y - (ct.dy-1) + (ct.sy-1)
        return data_x, data_y

#END
