"""
The IRAF plugin implements a remote control interface for the Ginga FITS
viewer from an IRAF session.  In particular it supports the use of the
IRAF 'display' and 'imexamine' commands.

Instructions for use:

Set the environment variable IMTDEV appropriately, e.g.

    $ export IMTDEV=inet:45005         (or)
    $ export IMTDEV=unix:/tmp/.imtg45

Ginga will try to use the default value if none is assigned.

Start IRAF plugin (Plugins->Start IRAF).

From Ginga you can load images and then use 'imexamine' from IRAF to load
them, do photometry, etc.  You can also use the 'display' command from IRAF
to show images in Ginga.  The 'IRAF' tab will show the mapping from Ginga
channels to IRAF numerical 'frames'.

When using imexamine, the plugin disables normal UI processing on the
channel image so that keystrokes, etc. are passed through to IRAF.  You can
toggle back and forth between local Ginga control and IRAF control using
the radio buttons at the top of the tab or using the space bar.

IRAF commands that have been tested: display, imexam, rimcur and tvmark.
"""
import sys, os
import logging
import threading
import socket
import ginga.util.six as six
if six.PY2:
    import Queue
else:
    import queue as Queue
import array
import numpy
import time

from ginga import GingaPlugin, AstroImage
from ginga import cmap, imap
from ginga.gw import Widgets, Viewers
from ginga.misc import Bunch

# XImage protocol support
import IIS_DataListener as iis


class IRAF(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(IRAF, self).__init__(fv)

        self.keyqueue = Queue.Queue()
        self.keyevent = threading.Event()
        self.keymap = {
            'comma': ',',
            }
        self.ctrldown = False

        self.layertag = 'iraf-canvas'
        # this will be set in initialize()
        self.canvas = None
        self.dc = fv.getDrawClasses()

        self.addr = iis.get_interface()

        self.ev_quit = self.fv.ev_quit
        self.dataTask = None

        # Holds frame buffers
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

        # colormap for use with IRAF displays
        self.cm_iis = cmap.ColorMap('iis_iraf', cmap_iis_iraf)
        self.im_iis = imap.get_imap('ultrasmooth')

        fv.add_callback('add-channel', self.add_channel)
        fv.add_callback('delete-channel', self.delete_channel)
        #fv.set_callback('active-image', self.focus_cb)

        self.gui_up = False

    def build_gui(self, container):

        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(False)
        ## canvas.set_callback('none-move', self.cursormotion)
        canvas.add_callback('key-press', self.window_key_press)
        canvas.add_callback('key-release', self.window_key_release)
        self.canvas = canvas

        vbox = Widgets.VBox()

        fr = Widgets.Frame("IRAF")

        captions = [
            ("Addr:", 'label', "Addr", 'llabel', 'Restart', 'button'),
            ("Set Addr:", 'label', "Set Addr", 'entry'),
            ("Control", 'hbox'),
            ("Channel:", 'label', 'Channel', 'llabel'),
            ]
        w, b = Widgets.build_info(captions)
        self.w.update(b)

        addr = str(self.addr.name)
        b.addr.set_text(addr)
        b.restart.set_tooltip("Restart the server")
        b.restart.add_callback('activated', self.restart_cb)

        b.set_addr.set_length(100)
        b.addr.set_text(addr)
        b.set_addr.set_tooltip("Set address to run remote control server")
        b.set_addr.add_callback('activated', self.set_addr_cb)

        self.w.mode_d = {}
        btn1 = Widgets.RadioButton("Ginga")
        btn1.set_state(True)
        btn1.add_callback('activated', lambda w, val: self.switchMode('ginga'))
        self.w.mode_d['ginga'] = btn1
        self.w.control.add_widget(btn1)
        btn2 = Widgets.RadioButton("IRAF", group=btn1)
        btn2.add_callback('activated', lambda w, val: self.switchMode('iraf'))
        self.w.mode_d['iraf'] = btn2
        self.w.control.add_widget(btn2)

        fr.set_widget(w)
        vbox.add_widget(fr, stretch=0)

        fr = Widgets.Frame("Frame/Channel")

        lbl = Widgets.Label("")
        self.w.frch = lbl

        fr.set_widget(lbl)
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
        self.gui_up = True

        fmap = self.get_channel_frame_mapping()
        self.update_chinfo(fmap)


    def update_chinfo(self, fmap):
        if not self.gui_up:
            return
        # Update the GUI with the new frame/channel mapping
        fmap.sort(lambda x, y: x[1] - y[1])

        s = ["%2d: %s" % (num, name) for (name, num) in fmap]
        self.w.frch.set_text("\n".join(s))

    def _setMode(self, modeStr, chname):
        modeStr = modeStr.lower()
        self.w.mode_d[modeStr].set_state(True)
        self.w.channel.set_text(chname)

        self.switchMode(modeStr)

    def setMode(self, modeStr, chname):
        self.imexam_chname = chname
        self.fv.gui_do(self._setMode, modeStr, chname)

    def toggleMode(self):
        isIRAF = self.w.mode_d['iraf'].get_state()
        chname = self.imexam_chname
        if isIRAF:
            self.logger.info("setting mode to Ginga")
            self.setMode('Ginga', chname)
        else:
            self.logger.info("setting mode to IRAF")
            self.setMode('IRAF', chname)


    def add_channel(self, viewer, chinfo):
        self.logger.debug("channel %s added." % (chinfo.name))

        n = self.channel_to_frame(chinfo.name)
        if n is None:
            found = len(self.fb)
            for n, fb in self.fb.items():
                if fb.chname is None:
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
        if n is not None:
            self.fb[n].chname = None

        fmap = self.get_channel_frame_mapping()
        self.fv.gui_do(self.update_chinfo, fmap)

    def switchMode(self, modeStr):
        modeStr = modeStr.lower()
        chname = self.imexam_chname
        chinfo = self.fv.get_channelInfo(chname)

        if modeStr == 'iraf':
            self.ui_disable(chinfo.fitsimage)
        else:
            self.ui_enable(chinfo.fitsimage)

    def start(self):
        try:
            if self.addr.prot == 'unix':
                os.remove(self.addr.path)
        except:
            pass

        # start the data listener task, if appropriate
        ev_quit = threading.Event()
        self.dataTask = iis.IIS_DataListener(
            self.addr, controller=self,
            ev_quit=ev_quit, logger=self.logger)
        self.fv.nongui_do(self.dataTask.mainloop)

    def stop(self):
        if self.dataTask:
            self.dataTask.stop()
        self.gui_up = False

    def restart_cb(self, w):
        # restart server
        if self.dataTask:
            self.dataTask.stop()
        self.start()

    def set_addr_cb(self, w):
        # get and parse address
        addr = w.get_text()
        self.addr = iis.get_interface(addr=addr)
        addr = str(self.addr.name)
        self.w.addr.set_text(addr)

    def channel_to_frame(self, chname):
        for n, fb in self.fb.items():
            if fb.chname == chname:
                return n
        return None

    def get_channel_frame_mapping(self):
        l = [ (fb.chname, n+1) for n, fb in self.fb.items() ]
        return l

    def new_image_cb(self, fitsimage, image, chinfo):
        if not self.gui_up:
            return
        # check if this is an image we received from IRAF or
        # one that was loaded locally.
        ct = image.get('ct', None)
        if ct is not None:
            # This image was sent by IRAF--we don't need to
            # construct extra fb information for it
            return

        n = self.channel_to_frame(chinfo.name)
        if n is None:
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
        if (fb and fb.ct.a is not None):
            wcs = "%s\n%f %f %f %f %f %f %f %f %d\n" % (
                fb.ct.imtitle, fb.ct.a, fb.ct.b, fb.ct.c, fb.ct.d,
                fb.ct.tx, fb.ct.ty, fb.ct.z1, fb.ct.z2, fb.ct.zt)
        else:
            wcs = "[NOSUCHWCS]\n"
        if (fb and fb.ct.sx is not None):
            mapping = "%s %f %f %d %d %d %d %d %d\n%s\n" % (
                fb.ct.region, fb.ct.sx, fb.ct.sy, fb.ct.snx, fb.ct.sny,
                fb.ct.dx, fb.ct.dy, fb.ct.dnx, fb.ct.dny, fb.ct.ref)
        else:
            mapping = ""
        fb.wcs = wcs + mapping
        self.logger.debug("filled wcs info")


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
        if chname is None:
            chname = 'Frame%d' % (frame+1)
            fb.chname = chname

        self.logger.debug("display to %s" %(chname))

        try:
            data = fb.buffer
            byteswap = False
            dims = (fb.height, fb.width)
            dtype = numpy.uint8
            metadata = {}

            image = IRAF_AstroImage(logger=self.logger)
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

        except Exception as e:
            # Some kind of error unpacking the data
            errmsg = "Error creating image data for '%s': %s" % (
                chname, str(e))
            self.logger.error(errmsg)
            raise GingaPlugin.PluginError(errmsg)

        # Do the GUI bits as the GUI thread
        self.fv.gui_do(self._gui_display_image, fitsname, image, chname)

    def _gui_display_image(self, fitsname, image, chname):

        if not self.fv.has_channel(chname):
            chinfo = self.fv.add_channel(chname)
        else:
            chinfo = self.fv.get_channelInfo(chname)
        fitsimage = chinfo.fitsimage

        # Set the RGB mapping appropriate for IIS/IRAF
        rgbmap = fitsimage.get_rgbmap()
        rgbmap.set_imap(self.im_iis, callback=False)
        rgbmap.set_cmap(self.cm_iis, callback=False)
        rgbmap.set_hash_size(65535, callback=False)
        rgbmap.set_hash_algorithm('linear', callback=True)

        # various settings that should apply
        settings = fitsimage.get_settings()
        settings.setDict(dict(autocuts='off', flip_x=False, flip_y=False,
                              swap_xy=False, rot_deg=0.0), callback=True)

        # Set cut levels
        fitsimage.cut_levels(0.0, 255.0, no_reset=True)

        # Enqueue image to display datasrc
        self.fv.add_image(fitsname, image, chname=chname)
        self.fv.ds.raise_tab('IRAF')

    def get_cursor(self):
        self.logger.info("get_cursor() called")
        chinfo = self.fv.get_channelInfo()
        # Find out which frame we are looking at
        #frame = self.current_frame
        frame = self.channel_to_frame(chinfo.name)
        fitsimage = chinfo.fitsimage
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
        # NOTE: can't disable main canvas ui because it won't propagate
        # events to layered canvases
        #fitsimage.ui_setActive(False)
        #self.canvas.ui_setActive(True)
        self.mode = 'iraf'

    def ui_enable(self, fitsimage):
        fitsimage.ui_setActive(True)
        #self.canvas.ui_setActive(False)
        self.mode = 'ginga'

    def start_imexamine(self, fitsimage, chname):
        self.logger.info("STARTING")
        # Turn off regular UI processing in the frame
        self.canvas.setSurface(fitsimage)
        # insert layer if it is not already
        try:
            obj = fitsimage.getObjectByTag(self.layertag)

        except KeyError:
            # Add canvas layer
            fitsimage.add(self.canvas, tag=self.layertag)
        self.canvas.ui_setActive(True)

        self.imexam_active = True
        self.setMode('IRAF', chname)
        self.fv.gui_do(self.fv.ds.raise_tab, 'IRAF')
        self.logger.info("FINISHING")

    def stop_imexamine(self, fitsimage, chname):
        self.logger.info("STARTING")
        self.imexam_active = False
        self.setMode('Ginga', chname)
        self.logger.info("FINISHING")

    def window_key_press(self, canvas, keyname):
        if not self.imexam_active:
            return False
        self.logger.info("key pressed: %s" % (keyname))
        if len(keyname) > 1:
            if keyname in ('shift_l', 'shift_r'):
                # ignore these keystrokes
                return False
            elif keyname in ('control_l', 'control_r'):
                # control key combination
                self.ctrldown = True
                return False
            elif keyname == 'space':
                self.toggleMode()
                return True
            keyname = self.keymap.get(keyname, '?')

        if self.mode != 'iraf':
            return False

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

        # add framebuffer information if it is not there already
        self.new_image_cb(fitsimage, image, chinfo)

        self.keyqueue.put(Bunch.Bunch(x=last_x, y=last_y, key=keyname,
                                      frame=frame))
        self.keyevent.set()
        return True

    def window_key_release(self, canvas, keyname):
        if not self.imexam_active:
            return False
        self.logger.info("key released: %s" % (keyname))
        if len(keyname) > 1:
            if keyname in ('control_l', 'control_r'):
                # control key combination
                self.ctrldown = False

        return False

    def cursormotion(self, canvas, event, data_x, data_y):
        if self.mode != 'iraf':
            return False

        fitsimage = self.fv.getfocus_fitsimage()

        if event.state == 'move':
            self.fv.showxy(fitsimage, data_x, data_y)
            return True

        return False

    def close(self):
        self.fv.stop_global_plugin(str(self))
        return True

    def __str__(self):
        return 'iraf'


class IRAF_AstroImage(AstroImage.AstroImage):

    def info_xy(self, data_x, data_y, settings):
        ct = self.get('ct', None)
        # Get the value under the data coordinates
        try:
            # We report the value across the pixel, even though the coords
            # change halfway across the pixel
            x, y = int(data_x+0.5), int(data_y+0.5)
            value = self.get_data_xy(x, y)

            # Mapping from bytescaled values back to original values
            value = iis.wcs_pix_transform(ct, value)
        except Exception as e:
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

        except Exception as e:
            self.logger.warn("Bad coordinate conversion: %s" % (
                str(e)))
            ra_txt  = 'BAD WCS'
            dec_txt = 'BAD WCS'

        # Note: FITS coordinates are 1-based, whereas numpy FITS arrays
        # are 0-based
        ra_lbl, dec_lbl = unichr(945), unichr(948)
        fits_x, fits_y = data_x + 1, data_y + 1

        info = Bunch.Bunch(itype='astro', data_x=data_x, data_y=data_y,
                           fits_x=fits_x, fits_y=fits_y,
                           x=fits_x, y=fits_y,
                           ra_txt=ra_txt, dec_txt=dec_txt,
                           ra_lbl=ra_lbl, dec_lbl=dec_lbl,
                           value=value)
        return info

    def get_corrected_xy(self, data_x, data_y):
        ct = self.get('ct', None)
        if ct is not None:
            # Subtract offsets of data in framebuffer and add offsets of
            # rect beginning in source
            data_x = data_x - (ct.dx-1) + (ct.sx-1)
            data_y = data_y - (ct.dy-1) + (ct.sy-1)
        return data_x, data_y


# this is a specialized color map for use with IRAF displays
#
cmap_iis_iraf = (
    (0.000000, 0.000000, 0.000000),   # 0: black
    (0.004975, 0.004975, 0.004975),   # 1-200: frame buffer greyscale values
    (0.009950, 0.009950, 0.009950),
    (0.014925, 0.014925, 0.014925),
    (0.019900, 0.019900, 0.019900),
    (0.024876, 0.024876, 0.024876),
    (0.029851, 0.029851, 0.029851),
    (0.034826, 0.034826, 0.034826),
    (0.039801, 0.039801, 0.039801),
    (0.044776, 0.044776, 0.044776),
    (0.049751, 0.049751, 0.049751),
    (0.054726, 0.054726, 0.054726),
    (0.059701, 0.059701, 0.059701),
    (0.064677, 0.064677, 0.064677),
    (0.069652, 0.069652, 0.069652),
    (0.074627, 0.074627, 0.074627),
    (0.079602, 0.079602, 0.079602),
    (0.084577, 0.084577, 0.084577),
    (0.089552, 0.089552, 0.089552),
    (0.094527, 0.094527, 0.094527),
    (0.099502, 0.099502, 0.099502),
    (0.104478, 0.104478, 0.104478),
    (0.109453, 0.109453, 0.109453),
    (0.114428, 0.114428, 0.114428),
    (0.119403, 0.119403, 0.119403),
    (0.124378, 0.124378, 0.124378),
    (0.129353, 0.129353, 0.129353),
    (0.134328, 0.134328, 0.134328),
    (0.139303, 0.139303, 0.139303),
    (0.144279, 0.144279, 0.144279),
    (0.149254, 0.149254, 0.149254),
    (0.154229, 0.154229, 0.154229),
    (0.159204, 0.159204, 0.159204),
    (0.164179, 0.164179, 0.164179),
    (0.169154, 0.169154, 0.169154),
    (0.174129, 0.174129, 0.174129),
    (0.179104, 0.179104, 0.179104),
    (0.184080, 0.184080, 0.184080),
    (0.189055, 0.189055, 0.189055),
    (0.194030, 0.194030, 0.194030),
    (0.199005, 0.199005, 0.199005),
    (0.203980, 0.203980, 0.203980),
    (0.208955, 0.208955, 0.208955),
    (0.213930, 0.213930, 0.213930),
    (0.218905, 0.218905, 0.218905),
    (0.223881, 0.223881, 0.223881),
    (0.228856, 0.228856, 0.228856),
    (0.233831, 0.233831, 0.233831),
    (0.238806, 0.238806, 0.238806),
    (0.243781, 0.243781, 0.243781),
    (0.248756, 0.248756, 0.248756),
    (0.253731, 0.253731, 0.253731),
    (0.258706, 0.258706, 0.258706),
    (0.263682, 0.263682, 0.263682),
    (0.268657, 0.268657, 0.268657),
    (0.273632, 0.273632, 0.273632),
    (0.278607, 0.278607, 0.278607),
    (0.283582, 0.283582, 0.283582),
    (0.288557, 0.288557, 0.288557),
    (0.293532, 0.293532, 0.293532),
    (0.298507, 0.298507, 0.298507),
    (0.303483, 0.303483, 0.303483),
    (0.308458, 0.308458, 0.308458),
    (0.313433, 0.313433, 0.313433),
    (0.318408, 0.318408, 0.318408),
    (0.323383, 0.323383, 0.323383),
    (0.328358, 0.328358, 0.328358),
    (0.333333, 0.333333, 0.333333),
    (0.338308, 0.338308, 0.338308),
    (0.343284, 0.343284, 0.343284),
    (0.348259, 0.348259, 0.348259),
    (0.353234, 0.353234, 0.353234),
    (0.358209, 0.358209, 0.358209),
    (0.363184, 0.363184, 0.363184),
    (0.368159, 0.368159, 0.368159),
    (0.373134, 0.373134, 0.373134),
    (0.378109, 0.378109, 0.378109),
    (0.383085, 0.383085, 0.383085),
    (0.388060, 0.388060, 0.388060),
    (0.393035, 0.393035, 0.393035),
    (0.398010, 0.398010, 0.398010),
    (0.402985, 0.402985, 0.402985),
    (0.407960, 0.407960, 0.407960),
    (0.412935, 0.412935, 0.412935),
    (0.417910, 0.417910, 0.417910),
    (0.422886, 0.422886, 0.422886),
    (0.427861, 0.427861, 0.427861),
    (0.432836, 0.432836, 0.432836),
    (0.437811, 0.437811, 0.437811),
    (0.442786, 0.442786, 0.442786),
    (0.447761, 0.447761, 0.447761),
    (0.452736, 0.452736, 0.452736),
    (0.457711, 0.457711, 0.457711),
    (0.462687, 0.462687, 0.462687),
    (0.467662, 0.467662, 0.467662),
    (0.472637, 0.472637, 0.472637),
    (0.477612, 0.477612, 0.477612),
    (0.482587, 0.482587, 0.482587),
    (0.487562, 0.487562, 0.487562),
    (0.492537, 0.492537, 0.492537),
    (0.497512, 0.497512, 0.497512),
    (0.502488, 0.502488, 0.502488),
    (0.507463, 0.507463, 0.507463),
    (0.512438, 0.512438, 0.512438),
    (0.517413, 0.517413, 0.517413),
    (0.522388, 0.522388, 0.522388),
    (0.527363, 0.527363, 0.527363),
    (0.532338, 0.532338, 0.532338),
    (0.537313, 0.537313, 0.537313),
    (0.542289, 0.542289, 0.542289),
    (0.547264, 0.547264, 0.547264),
    (0.552239, 0.552239, 0.552239),
    (0.557214, 0.557214, 0.557214),
    (0.562189, 0.562189, 0.562189),
    (0.567164, 0.567164, 0.567164),
    (0.572139, 0.572139, 0.572139),
    (0.577114, 0.577114, 0.577114),
    (0.582090, 0.582090, 0.582090),
    (0.587065, 0.587065, 0.587065),
    (0.592040, 0.592040, 0.592040),
    (0.597015, 0.597015, 0.597015),
    (0.601990, 0.601990, 0.601990),
    (0.606965, 0.606965, 0.606965),
    (0.611940, 0.611940, 0.611940),
    (0.616915, 0.616915, 0.616915),
    (0.621891, 0.621891, 0.621891),
    (0.626866, 0.626866, 0.626866),
    (0.631841, 0.631841, 0.631841),
    (0.636816, 0.636816, 0.636816),
    (0.641791, 0.641791, 0.641791),
    (0.646766, 0.646766, 0.646766),
    (0.651741, 0.651741, 0.651741),
    (0.656716, 0.656716, 0.656716),
    (0.661692, 0.661692, 0.661692),
    (0.666667, 0.666667, 0.666667),
    (0.671642, 0.671642, 0.671642),
    (0.676617, 0.676617, 0.676617),
    (0.681592, 0.681592, 0.681592),
    (0.686567, 0.686567, 0.686567),
    (0.691542, 0.691542, 0.691542),
    (0.696517, 0.696517, 0.696517),
    (0.701493, 0.701493, 0.701493),
    (0.706468, 0.706468, 0.706468),
    (0.711443, 0.711443, 0.711443),
    (0.716418, 0.716418, 0.716418),
    (0.721393, 0.721393, 0.721393),
    (0.726368, 0.726368, 0.726368),
    (0.731343, 0.731343, 0.731343),
    (0.736318, 0.736318, 0.736318),
    (0.741294, 0.741294, 0.741294),
    (0.746269, 0.746269, 0.746269),
    (0.751244, 0.751244, 0.751244),
    (0.756219, 0.756219, 0.756219),
    (0.761194, 0.761194, 0.761194),
    (0.766169, 0.766169, 0.766169),
    (0.771144, 0.771144, 0.771144),
    (0.776119, 0.776119, 0.776119),
    (0.781095, 0.781095, 0.781095),
    (0.786070, 0.786070, 0.786070),
    (0.791045, 0.791045, 0.791045),
    (0.796020, 0.796020, 0.796020),
    (0.800995, 0.800995, 0.800995),
    (0.805970, 0.805970, 0.805970),
    (0.810945, 0.810945, 0.810945),
    (0.815920, 0.815920, 0.815920),
    (0.820896, 0.820896, 0.820896),
    (0.825871, 0.825871, 0.825871),
    (0.830846, 0.830846, 0.830846),
    (0.835821, 0.835821, 0.835821),
    (0.840796, 0.840796, 0.840796),
    (0.845771, 0.845771, 0.845771),
    (0.850746, 0.850746, 0.850746),
    (0.855721, 0.855721, 0.855721),
    (0.860697, 0.860697, 0.860697),
    (0.865672, 0.865672, 0.865672),
    (0.870647, 0.870647, 0.870647),
    (0.875622, 0.875622, 0.875622),
    (0.880597, 0.880597, 0.880597),
    (0.885572, 0.885572, 0.885572),
    (0.890547, 0.890547, 0.890547),
    (0.895522, 0.895522, 0.895522),
    (0.900498, 0.900498, 0.900498),
    (0.905473, 0.905473, 0.905473),
    (0.910448, 0.910448, 0.910448),
    (0.915423, 0.915423, 0.915423),
    (0.920398, 0.920398, 0.920398),
    (0.925373, 0.925373, 0.925373),
    (0.930348, 0.930348, 0.930348),
    (0.935323, 0.935323, 0.935323),
    (0.940299, 0.940299, 0.940299),
    (0.945274, 0.945274, 0.945274),
    (0.950249, 0.950249, 0.950249),
    (0.955224, 0.955224, 0.955224),
    (0.960199, 0.960199, 0.960199),
    (0.965174, 0.965174, 0.965174),
    (0.970149, 0.970149, 0.970149),
    (0.975124, 0.975124, 0.975124),
    (0.980100, 0.980100, 0.980100),
    (0.985075, 0.985075, 0.985075),
    (0.990050, 0.990050, 0.990050),
    (0.995025, 0.995025, 0.995025),   # 200: end of IRAF greyscale
    (1.000000, 1.000000, 1.000000),   # 201: white
    (0.000000, 0.000000, 0.000000),   # 202: black
    (1.000000, 1.000000, 1.000000),   # 203: white
    (1.000000, 0.000000, 0.000000),   # 204: red
    (0.000000, 1.000000, 0.000000),   # 205: green
    (0.000000, 0.000000, 1.000000),   # 206: blue
    (1.000000, 1.000000, 0.000000),   # 207: yellow
    (0.000000, 1.000000, 1.000000),   # 208: cyan
    (1.000000, 0.000000, 1.000000),   # 209: magenta
    (1.000000, 0.498039, 0.313725),   # 210: coral
    (0.690196, 0.188235, 0.376470),   # 211: maroon
    (1.000000, 0.647058, 0.000000),   # 212: orange
    (0.941176, 0.901960, 0.549019),   # 213: khaki
    (0.854901, 0.439215, 0.839215),   # 214: orchid
    (0.250980, 0.878431, 0.815686),   # 215: turquoise
    (0.933333, 0.509803, 0.933333),   # 216: violet
    (0.960784, 0.870588, 0.701960),   # 217: wheat
    (1.000000, 0.000000, 0.000000),   # 218-254: reserved
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (1.000000, 0.000000, 0.000000),
    (0.000000, 0.000000, 0.000000),   # 255: black
    )


#END
