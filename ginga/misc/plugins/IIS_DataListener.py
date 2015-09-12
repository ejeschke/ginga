#
# IIS_DataListener.py -- IIS (XImtool protocol) server
#
# Eric Jeschke (eric@naoj.org)
#
# This file contains code by "fpierfed" (email addr unknown) downloaded from:
#   http://pyimtool.cvs.sourceforge.net/viewvc/pyimtool/pyimtool/src/
# and modified.
#
# Modifications Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from __future__ import print_function
import sys, os
import socket, select
import threading
import logging
import time
import struct
import array
import re
import string

from ginga.misc import Bunch
import ginga.util.six as six
if six.PY2:
    import SocketServer
else:
    import socketserver as SocketServer

# internal globals
MEMORY            = 0o1              # frame buffer i/o
LUT               = 0o2              # lut i/o
FEEDBACK          = 0o5              # used for frame clears
IMCURSOR          = 0o20             # logical image cursor
WCS               = 0o21             # used to set WCS

IIS_VERSION       = 10              # version 1.0

PACKED            = 0o040000
COMMAND           = 0o100000
IIS_READ          = 0o100000
IMC_SAMPLE        = 0o040000
IMT_FBCONFIG      = 0o77
XYMASK            = 0o77777

MAX_FBCONFIG      = 128             # max possible frame buf sizes
MAX_FRAMES        = 15              #  max number of frames (start from 0)
MAX_CLIENTS       = 8               #  max display server clients
DEF_NFRAMES       = 1               #  save memory; only one frame
DEF_FRAME_WIDTH   = 512             #  512 square frame
DEF_FRAME_HEIGHT  = 512             #  512 square frame

SZ_LABEL          = 256             #  main frame label string
SZ_IMTITLE        = 128             # image title string
SZ_WCSBUF         = 1024            # WCS text buffer size
SZ_OLD_WCSBUF     = 320             # old WCS text buffer size
SZ_FIFOBUF        = 4000            # transfer size for FIFO i/o
SZ_FNAME          = 256
SZ_LINE           = 256
SZ_IMCURVAL       = 160

# WCS definitions.
W_UNITARY         = 0
W_LINEAR          = 1
W_LOG             = 2
W_DEFFORMAT       = " %7.2f %7.2f %7.1f%c"

VERBOSE           = 1


class socketTimeout(Exception):
    pass

class IIS_DataListener(object):
    """
    A class that listens to a socket/fifo for incoming data.
    It uses the XImtool protocol (libiio.a).
    """
    def __init__(self, addr, name='DataListener',
                 controller=None, ev_quit=None, logger=None):
        self.timeout = 0.5
        self.addr = addr
        self.nconnections = 5

        if (addr.prot == 'inet'):
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            #s_address = (addr.host, addr.port)
            s_address = ('', addr.port)
        else:
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s_address = addr.path

        # attach a RequestHandler to the server
        self.RequestHandlerClass = IIS_RequestHandler

        # attach the interface controller class we will call this
        # class' display_data() method.
        self.controller = controller

        # Controlled stop of server
        if ev_quit is None:
            ev_quit = threading.Event()
        self.ev_quit = ev_quit

        if logger is None:
            logger = logging.getLogger(name)
        self.logger = logger

        # allow reuse of the socket
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.settimeout(self.timeout)
        # bind the socket and start listening
        self.socket.bind(s_address)
        self.socket.listen(self.nconnections)

    # so we don't have to block indefinitely on the socket.accept() method.
    # See SocketServer.py
    def get_request(self):
        while not self.ev_quit.isSet():
            #self.logger.debug("Ready to accept request, socket %s" % (
            #        str(self.socket)))
            inputs = [ self.socket ]
            try:
                (sin, sout, sexp) = select.select(inputs, [], [], self.timeout)

            except KeyboardInterrupt as e:
                raise e

            except select.error as e:
                self.logger.error("select.error: %s" % str(e))
                (code, msg) = e
                # code==4 is interrupted system call.  This typically happens
                # when the process receives a signal.
                if code == 4:
                    raise socketTimeout('select() timed out, system call interrupted')
                raise e

            for i in sin:
                if i == self.socket:
                    conn = self.socket.accept()
                    # wierd hack dues to Solaris 10 handling of sockets
                    conn[0].setblocking(1)
                    return conn

            # Normal timeout, nothing to do.
            raise socketTimeout('select() timed out')


    def handle_request(self):
        """
        Handles incoming connections, one at the time.
        """
        try:
            (request, client_address) = self.get_request()

        except socket.error as e:
            # Error handling goes here.
            self.logger.error("error opening the connection: %s" % (
                str(e)))
            for exctn in sys.exc_info():
                print (exctn)
            return

        try:
            self.RequestHandlerClass(request, client_address, self)
        except Exception as e:
            # Error handling goes here.
            self.logger.error('error handling the request: %s' % (
                str(e)))
            for exctn in sys.exc_info():
                print (exctn)
            return


    def mainloop(self):
        """main control loop."""
        try:
            while (not self.ev_quit.isSet()):
                try:
                    self.handle_request()

                except socketTimeout:
                    continue
        finally:
            self.socket.close()

    def stop(self):
        self.ev_quit.set()
        self.logger.info("stop() invoked on IIS DataListener.")

        if (self.addr.prot == 'unix'):
            try:
                os.remove(self.addr.path)

            except Exception as e:
                self.logger.error("Failed to cleanup the pipe " + self.addr.path +
                                  (": %s" % (str(e))))



class IIS_RequestHandler(SocketServer.StreamRequestHandler):
    """
    This class does the actual work of parsing the incoming streams and
    perform the necessary actions (display image, overlay regions
    and so on).

                                    IIS Header Packet Summary

                      TID            Subunit     Tct   X   Y    Z   T    Data
              +------------------+-------------+-----+---+---+----+---+--------+
Read Data     | IIS_READ|PACKED  | MEMORY      | -NB | x | y | fr | - | nbytes |
Write Data    | IIS_WRITE|PACKED | MEMORY      | -NB | x | y | fr | - | nbytes |
Read Cursor   | IIS_READ         | IMCURSOR    |  -  | - | - | wcs| - | -      |
Write Cursor  | IIS_WRITE        | IMCURSOR    |  -  | x | y | wcs| - | -      |
Set Frame     | IIS_WRITE        | LUT|COMMAND | -1  | - | - | -  | - | 2      |
Erase Frame   | IIS_WRITE | fb   | FEEDBACK    |  -  | - | - | fr | - | -      |
              |                  |             |     |   |   |    |   |        |
Old Read WCS  | IIS_READ         | WCS         |  -  | - | - | fr | - | 320    |
Old Write WCS | IIS_WRITE|PACKED | WCS         | -N  | - | - | fr |fb | 320    |
              |                  |             |     |   |   |    |   |        |
WCS Version?  | IIS_READ         | WCS         |  -  | 1 | 1 | -  | - | 320    |
WCS by Num.?  | IIS_READ         | WCS         |  -  | 1 | - | fr |wcs| 1024   |
New Read WCS  | IIS_READ         | WCS         |  -  | 1 | - | fr | - | 1024   |
New Write WCS | IIS_WRITE|PACKED | WCS         | -N  | 1 | - | fr |fb | 1024   |
              +------------------+-------------+-----+---+---+----+---+--------+

Where   nbytes | NB  = number of bytes expected or written
        x            = x position of operation in frame buffer coords
        y            = y position of operation in frame buffer coords
        fr           = frame number (passed as bitflag (i.e. 1, 2 ,4 8, etc)
        fb           = frame buffer config number (zero indexed)
        N            = length of WCS string
        wcs          = WCS number (usually zero)
        Data         = the number of bytes of data to be read or written
                       following the header packet.
    """
    needs_update = False
    # these NEED to be set automatically
    # from the client interaction
    width = None
    height = None
    frame = 0
    x = 0
    y = 0
    y1 = -1
    #sequence = -1
    #key = None
    #got_key = None


    def decode_frameno(self, z):
        try:
            z = int(z)
        except:
            z = 1
        if (not z):
            z = 1
        n = 0
        while (not (z & 1)):
            n += 1
            z >>= 1

        frame = max (1, n + 1)
        return frame

    def wcs_update(self, wcs_text, fb=None):
        """
        parses the wcs_text and populates the fields
        of a coord_tran instance.
        we start from the coord_tran of the input
        frame buffer, if any
        """
        if (fb):
            ct = fb.ct
        else:
            ct = coord_tran ()
        if (not ct.valid):
            ct.zt = W_UNITARY

            # read wcs_text
            data = string.split(wcs_text, '\n')
            ct.imtitle = data[0]
            # we are expecting 8 floats and 1 int
            try:
                (ct.a, ct.b, ct.c, ct.d,
                 ct.tx, ct.ty, ct.z1, ct.z2,
                 ct.zt) = string.split(data[1])
                ct.a = float(ct.a)
                ct.b = float(ct.b)
                ct.c = float(ct.c)
                ct.d = float(ct.d)
                ct.tx = float(ct.tx)
                ct.ty = float(ct.ty)
                ct.z1 = float(ct.z1)
                ct.z2 = float(ct.z2)
                ct.zt = int(ct.zt)
            except:
                ct.imtitle = "[NO WCS]"
                ct.a = 1
                ct.d = 1
                ct.b = 0
                ct.c = 0
                ct.tx = 0
                ct.ty = 0
                ct.zt = W_UNITARY
            ct.valid += 1

            # determine the best format for WCS output
            if (ct.valid and ct.zt == W_LINEAR):
                z1 = ct.z1
                z2 = ct.z2
                zrange = abs(z1 - z2)
                zavg = (abs(z1) + abs(z2)) / 2.0
                if (zrange < 100.0 and zavg < 200.0):
                    ct.format = " %7.2f %7.2f %7.3f%c"
                elif (zrange > 99999.0 or zavg > 99999.0):
                    ct.format = " %7.2f %7.2f %7.3g%c"
                else:
                    ct.format = W_DEFFORMAT
            else:
                ct.format = " %7.2f %7.2f %7.0f%c"

            # add_mapping, if we can
            if (len(data) < 4):
                return(ct)

            # we are expecting 1 string, 2 floats, and 6 int
            try:
                print("updating WCS: %s" % str(data[2]))
                (ct.region, ct.sx, ct.sy, ct.snx,
                 ct.sny, ct.dx, ct.dy, ct.dnx,
                 ct.dny) = string.split(data[2])
                ct.sx = float(ct.sx)
                ct.sy = float(ct.sy)
                ct.snx = int(ct.snx)
                ct.sny = int(ct.sny)
                # dx, dy: offset into frame where actual data starts
                ct.dx = int(ct.dx)
                ct.dy = int(ct.dy)
                # dnx, dny: length of actual data in frame from offsets
                ct.dnx = int(ct.dnx)
                ct.dny = int(ct.dny)
                ct.ref = string.strip(data[3])
                # if this works, we also have the real size of the image
                fb.img_width = ct.dnx + 1   # for some reason, the width is always
                                            # 1 pixel smaller...
                fb.img_height = ct.dny
            except:
                ct.region = 'none'
                ct.sx = 1.0
                ct.sy = 1.0
                ct.snx = fb.width
                ct.sny = fb.height
                ct.dx = 1
                ct.dy = 1
                ct.dnx = fb.width
                ct.dny = fb.height
                ct.ref = 'none'
        return (ct)

    def return_cursor(self, dataout, sx, sy, frame, wcs, key, strval=''):
        """
        writes the cursor position to dataout.
        input:
            dataout:    the output stream
            sx:         x coordinate
            sy:         y coordinate
            wcs:        nonzero if we want WCS translation
            frame:      frame buffer index
            key:        keystroke used as trigger
            strval:     optional string value
        """
        #print "RETURN CURSOR"
        wcscode = (frame + 1) * 100 + wcs
        if (key == '\32'):
            curval = "EOF"
        else:
            if (key in string.printable and not key in string.whitespace):
                keystr = key
            else:
                keystr = "\\%03o" % (ord(key))

        # send the necessary infor to the client
        curval = "%10.3f %10.3f %d %s %s\n" % (sx, sy, wcscode, keystr, strval)
        dataout.write(right_pad(curval, SZ_IMCURVAL))
        #print "END RETURN CURSOR"

    def handle_feedback(self, pkt):
        """This part of the protocol is used by IRAF to erase a frame in
        the framebuffers.
        """
        self.logger.debug("handle feedback")
        self.frame = self.decode_frameno(pkt.z & 0o7777) - 1

        # erase the frame buffer
        fb = self.server.controller.init_frame(self.frame)
        self.server.controller.set_frame(self.frame)


    def handle_lut(self, pkt):
        """This part of the protocol is used by IRAF to set the frame number.
        """
        self.logger.debug("handle lut")
        if pkt.subunit & COMMAND:
            data_type = str(pkt.nbytes / 2) + 'h'
            size = struct.calcsize(data_type)
            line = pkt.datain.read(pkt.nbytes)
            n = len(line)
            if (n < pkt.nbytes):
                return
            try:
                x = struct.unpack(data_type, line)
            except Exception as e:
                self.logger.error("Error unpacking struct: %s" % (str(e)))
                return

            if len(x) < 14:
                # pad it with zeroes
                y = []
                for i in range(14):
                    try:
                        y.append(x[i])
                    except:
                        y.append(0)
                x = y
                del(y)

            if len(x) == 14:
                z = int(x[0])
                # frames start from 1, we start from 0
                self.frame = self.decode_frameno(z) - 1

                if (self.frame > MAX_FRAMES):
                    self.logger.error("attempt to select non existing frame.")
                    return

                # init the framebuffer
                #self.server.controller.init_frame(self.frame)
                try:
                    fb = self.server.controller.get_frame(self.frame)
                except KeyError:
                    fb = self.server.controller.init_frame(self.frame)
                return

            self.logger.error("unable to select a frame.")
            return

        self.logger.error("what shall I do?")


    def handle_wcs(self, pkt):
        """
        This part of the protocol is used by IRAF to bidirectionally
        communicate metadata about frames in the framebuffers.

        IIS WCS format:
        name - title\n
        a b c d tx ty z1 z2 zt\n
        region_name sx sy snx sny dx dy dnx dny\n
        object_ref

        where the new parameters are defined as

            region_name       - user-defined name for the region (e.g. 'image',
                                'subras1', 'ccd3', etc).
            sx, sy, snx, sny  - source rect in the object
            dx, dy, dnx, dny  - dest rect in the display frame buffer
            object_ref        - full node!/path/image[sec] image name, same as
                                was immap'd when the image was displayed.  Used
                                for access after the display
        """
        self.logger.debug("handle wcs")
        if pkt.tid & IIS_READ:
            self.logger.debug("iis read")
            # Return the WCS for the referenced frame.
            if (pkt.x & 0o17777) and (pkt.y & 0o17777):
                # return IIS version number
                text = "version=" + str(IIS_VERSION)
                text = right_pad(text, SZ_OLD_WCSBUF)
            else:
                frame  = self.decode_frameno(pkt.z & 0o177777) - 1
                try:
                    fb = self.server.controller.get_frame(frame)
                except KeyError:
                    fb = None
                self.logger.debug("frame=%d fb=%s" % (frame, fb))

                if (pkt.x & 0o17777) and (pkt.t & 0o17777):
                    self.frame = frame
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
                    text = wcs + mapping
                    text = right_pad(text, SZ_WCSBUF)
                else:
                    if (frame < 0) or (fb is None) or (fb.buffer is None) or \
                        (len(fb.buffer) == 0):
                        text = "[NOSUCHFRAME]"
                    else:
                        text = fb.wcs

                    # old style or new style?
                    if pkt.x & 0o777:
                        text = right_pad(text, SZ_WCSBUF)
                    else:
                        text = right_pad(text, SZ_OLD_WCSBUF)
            self.logger.debug("WCS: " + text)
            pkt.dataout.write(text)

        else:
            self.logger.debug("iis write")
            # Read the WCS information from the client
            # frames start from 1, we start from 0
            self.frame = self.decode_frameno(pkt.z & 0o7777) - 1

            try:
                fb = self.server.controller.get_frame(self.frame)

            except KeyError:
                # the selected frame does not exist, create it
                fb = self.server.controller.init_frame(self.frame)

            # set the width and height of the framebuffer
            fb_config = (pkt.t & 0o777) + 1
            try:
                (nframes, fb.width, fb.height) = fbconfigs [fb_config]

            except KeyError:
                self.logger.warn('Non existing framebuffer config (%s)' % (
                        str(fb_config)))
                self.logger.info('Adding a new framebuffer config (%s)' % (
                        str(fb_config)))
                fbconfigs[fb_config] = [1, None, None]
                fb.width = None
                fb.height = None

            # do we have to deal with the new WCS format? (not used, for now)
            new_wcs = (pkt.x & 0o777)

            # read the WCS info
            line = pkt.datain.read(pkt.nbytes)

            # paste it in the frame buffer
            fb.wcs = line

            fb.ct.format = W_DEFFORMAT
            fb.ct.imtitle = ''
            fb.ct.valid = 0
            fb.ct = self.wcs_update(line, fb)
        # end of handle_wcs()

    def handle_memory(self, pkt):
        """This part of the protocol is used by IRAF to read/write image data
        in the framebuffers.
        """
        self.logger.debug("handle memory")

        # get the frame number, we start from 0
        self.frame = self.decode_frameno(pkt.z & 0o7777) - 1
        try:
            fb = self.server.controller.get_frame(self.frame)
        except KeyError:
            # the selected frame does not exist, create it
            fb = self.server.controller.init_frame(self.frame)

        self.x = pkt.x & XYMASK
        self.y = pkt.y & XYMASK
        self.logger.debug("memory frame=%d x,y=%d,%d fb width=%s height=%s" % (
            self.frame, self.x, self.y, fb.width, fb.height))

        if (pkt.tid & IIS_READ):
            self.logger.debug("start memory read")

            # read the data and send back to server
            start = self.x + self.y * fb.width
            end = start + pkt.nbytes
            data = fb.buffer[start:end]
            if len(data) != pkt.nbytes:
                self.logger.warn("buffer length/packet size mismatch: %d != %d" % (
                        len(data), pkt.nbytes))
            #data.reverse()
            #self.logger.debug("DATA=%s" % str(data))
            buf = data.tostring()
            pkt.dataout.write(buf)
            pkt.dataout.flush()
            self.logger.debug("end memory read")

        else:
            self.logger.debug("start memory write")
            # read the data from socket
            t_bytes = 0
            self.logger.debug("data bytes=%d needs_update=%s" % (
                pkt.nbytes, self.needs_update))
            if (fb.width is not None) and (fb.height is not None):
                if not self.needs_update:
                    #del fb.buffer
                    #fb.buffer = array.array('B', ' ' * fb.width * fb.height)
                    if len(fb.buffer) != fb.width * fb.height:
                        fb.buffer = array.array('B', '\000' * fb.width * fb.height)
                        #self.needs_update = True
                start = self.x + self.y * fb.width
                end = start + pkt.nbytes
                fb.buffer[start:end] = array.array('B', pkt.datain.read(pkt.nbytes))
            else:
                self.logger.warn("uninitialized framebuffer frame=%d" % (
                        self.frame))
                if not self.needs_update:
                    # init the framebuffer
                    fb.buffer.fromstring(pkt.datain.read(pkt.nbytes))
                    fb.buffer.reverse()
                    #self.needs_update = True
                else:
                    data = array.array('B', pkt.datain.read(pkt.nbytes))
                    data.reverse()
                    fb.buffer += data

            self.needs_update = True
            self.logger.debug("end memory write")

            # width = fb.width
            # if (not width and self.y1 < 0):
            #     self.y1 = self.y
            #     self.logger.debug('saved y coordinate.')
            # elif not width:
            #     delta_y = self.y - self.y1
            #     width = int(abs(len(data) / delta_y))
            #     self.logger.debug('resetting framebuffer width=%d' % (
            #             width))
            #     fb.width = width
            #     # if we added a new fbconfigs entry, let's update
            #     # the value for the framebuffer width!
            #     if fbconfigs.has_key(fb.config):
            #         fbconfigs[fb.config][1] = width


    def handle_imcursor(self, pkt):
        """This part of the protocol is used by IRAF to read the cursor
        position and keystrokes from the display client.
        """
        self.logger.debug("handle imcursor")
        done = 0

        if pkt.tid & IIS_READ:
            if pkt.tid & IMC_SAMPLE:
                self.logger.debug("SAMPLE")
                # return the cursor position
                wcsflag = int(pkt.z)
                #wcsflag = 0
                res = self.server.controller.get_keystroke()

                self.return_cursor(pkt.dataout, res.x, res.y,
                                   res.frame, wcsflag, '0', '')
            else:
                self.logger.debug("OTHER")
                res = self.server.controller.get_keystroke()
                self.logger.debug("FRAME=%d X,Y=%f,%f" % (
                    res.frame, res.x, res.y))
                ## sx = self.x
                self.x = res.x
                self.y = res.y
                self.frame = res.frame
                ## sy = self.y
                ## frame = self.frame
                #wcsflag = 1
                wcsflag = 0

                #self.return_cursor(pkt.dataout, sx, sy, frame, 1, key, '')
                self.return_cursor(pkt.dataout, res.x, res.y,
                                   res.frame, wcsflag, res.key, '')
        else:
            self.logger.debug("READ")
            # read the cursor position in logical coordinates
            sx = int(pkt.x)
            sy = int(pkt.y)
            wx = float(pkt.x)
            wy = float(pkt.y)
            wcs = int(pkt.z)

            if wcs:
                # decode the WCS info for the current frame
                try:
                    fb = self.server.controller.get_frame(self.frame)
                except KeyError:
                    # the selected frame does not exist, create it
                    fb = self.server.controller.init_frame(self.frame)
                fb.ct = self.wcs_update(fb.wcs)

                if fb.ct.valid:
                    if abs(fb.ct.a) > 0.001:
                        sx = int((wx - fb.ct.tx) / fb.ct.a)
                    if abs(fb.ct.d) > 0.001:
                        sy = int((wy - xt.ty) / fb.ct.d)

            self.server.controller.set_cursor(sx, sy)


    def handle(self):
        """
        This is where the action starts.
        """
        self.logger = self.server.logger

        # create a packet structure
        packet = iis()
        packet.datain = self.rfile
        packet.dataout = self.wfile

        # decode the header
        size = struct.calcsize('8h')
        line = packet.datain.read(size)
        n = len(line)
        if n < size:
            return

        while n > 0:
            try:
                bytes = struct.unpack('8h', line)
            except:
                self.logger.error('error unpacking the data.')
                for exctn in sys.exc_info():
                    print (exctn)

            # TODO: verify checksum

            # decode the packet fields
            subunit = bytes[2]
            subunit077 = subunit & 0o77
            tid = bytes[0]
            x = bytes[4] & 0o177777
            y = bytes[5] & 0o177777
            z = bytes[6] & 0o177777
            t = bytes[7] & 0o17777
            ndatabytes = - bytes[1]

            # are the bytes packed?
            if (not(tid & PACKED)):
                ndatabytes *= 2

            # populate the packet structure
            packet.subunit = subunit
            packet.subunit077 = subunit077
            packet.tid = tid
            packet.x = x
            packet.y = y
            packet.z = z
            packet.t = t
            packet.nbytes = ndatabytes

            # decide what to do, depending on the
            # value of subunit
            self.logger.debug("PACKET IS %o" % packet.subunit)

            if packet.subunit077 == FEEDBACK:
                self.handle_feedback(packet)

            elif packet.subunit077 == LUT:
                self.handle_lut(packet)
                # read the next packet
                line = packet.datain.read(size)
                n = len(line)
                continue

            elif packet.subunit077 == MEMORY:
                self.handle_memory(packet)
                if self.needs_update:
                    #self.display_image()
                    pass
                # read the next packet
                line = packet.datain.read(size)
                n = len(line)
                continue

            elif packet.subunit077 == WCS:
                self.handle_wcs(packet)
                line = packet.datain.read(size)
                n = len(line)
                continue

            elif packet.subunit077 == IMCURSOR:
                self.handle_imcursor(packet)
                line = packet.datain.read(size)
                n = len(line)
                continue

            else:
                self.logger.debug('?NO OP (0%o)' % (packet.subunit077))

            if not (packet.tid & IIS_READ):
                # OK, discard the rest of the data
                nbytes = packet.nbytes
                while nbytes > 0:
                    # for (nbytes = ndatabytes;  nbytes > 0;  nbytes -= n):
                    if nbytes < SZ_FIFOBUF:
                        n = nbytes
                    else:
                        n = SZ_FIFOBUF
                    m = self.rfile.read(n)
                    if m <= 0:
                        break
                    nbytes -= n

            # read the next packet
            line = packet.datain.read(size)
            n = len(line)
            if n < size:
                return
        # <--- end of the while (n) loop
        if self.needs_update:
            self.display_image()
            self.needs_update = False


    def display_image(self, reset=1):
        """Utility routine used to display an updated frame from a framebuffer.
        """
        try:
            fb = self.server.controller.get_frame(self.frame)
        except KeyError:
            # the selected frame does not exist, create it
            fb = self.server.controller.init_frame(self.frame)

        if not fb.height:
            width = fb.width
            height = int(len(fb.buffer) / width)
            fb.height = height

            # display the image
            if (len(fb.buffer) > 0) and (height > 0):
                self.server.controller.display(self.frame, width, height,
                                                True)
        else:
            self.server.controller.display(self.frame, fb.width, fb.height,
                                            False)


    def decode_iis(self, data):
        f = file('/tmp/pippo', 'wb')
        f.write(data)
        f.close()
        return (decoded_data)


# Frame buffer configurations
fbconfigs = {
    1: [2, 512, 512],
    2: [2, 800, 800],
    3: [2, 1024, 1024],
    4: [1, 1600, 1600],
    5: [1, 2048, 2048],
    6: [1, 4096, 4096],
    7: [1, 8192, 8192],
    8: [1, 1024, 4096],
    9: [2, 1144, 880],
    10: [2, 1144, 764],
    11: [2, 128, 128],
    12: [2, 256, 256],
    13: [2, 128, 1056],
    14: [2, 256, 1056],
    15: [2, 1056, 128],
    16: [2, 1056, 256],
    17: [2, 1008, 648],
    18: [2, 1024, 680],
    19: [1, 4096, 1024],
    20: [2, 388, 576],
    21: [1, 3040, 976],
    22: [1, 128, 1520],
    23: [1, 256, 1520],
    24: [1, 512, 1520],
    25: [1, 960, 1520],
    26: [1, 1232, 800],
    27: [1, 3104, 512],
    28: [1, 976, 3040],
    29: [1, 800, 256],
    30: [1, 256, 800],
    31: [1, 1240, 400],
    32: [2, 832, 800],
    33: [2, 544, 512],
    34: [1, 1056, 1024],
    35: [1, 2080, 2048],
    36: [2, 832, 820],
    37: [2, 520, 512],
    38: [1, 3104, 1024],
    39: [1, 1232, 800],
    40: [4, 1200, 600],
    41: [1, 8800, 8800],
    42: [1, 4400, 4400],
    43: [1, 2200, 2200],
    44: [1, 1100, 1100],
    45: [1, 2080, 4644],
    46: [1, 6400, 4644],
    47: [1, 3200, 2322],
    48: [1, 1600, 1161],
    49: [1, 800, 581],
    50: [1, 2048, 2500]}


class iis(object):
    def __init__ (self):
        self.tid = None
        self.subunit = None
        self.subunit077 = None
        self.nbytes = None
        self.x = None
        self.y = None
        self.z = None
        self.t = None
        self.datain = None
        self.dataout = None


class coord_tran(object):
    def __init__ (self):
        # coordinate transformation:
        # screen -> physical
        self.valid = 0          # has the WCS been validated/parsed?
        self.a = 1              # x scale factor
        self.b = 0              # y scale factor
        self.c = 0              # x cross factor
        self.d = 1              # y cross factor
        self.tx = 0             # translation in x
        self.ty = 0             # translation in y
        self.z1 = 0             # min greyscale value
        self.z2 = 1             # max greyscale value
        self.zt = W_UNITARY     # greyscale mapping
        self.format = ''        # WCS output format
        self.imtitle = ''       # image title from WCS
        # physical -> celestial
        self.regid = None
        self.id = None
        # src/dst region mapping
        self.ref = ''
        self.region = ''
        self.sx = 1.0
        self.sy = 1.0
        self.snx = DEF_FRAME_WIDTH
        self.sny = DEF_FRAME_WIDTH
        self.dx = 1
        self.dy = 1
        self.dnx = DEF_FRAME_WIDTH
        self.dny = DEF_FRAME_WIDTH


class framebuffer(object):

    def __init__ (self):
        self.width = None           # width of the framebuffer
        self.height = None          # height of the framebuffer
        self.img_width = None       # width of the image
        self.img_height = None      # height of the image
        self.config = None          # framebuffer config index
                                    # (see fbconfigs dictionary)
        self.wcs = None             # WCS
        self.image = None           # the image data itself
        self.bitmap = None          # the image bitmap
        self.buffer = None          # used for screen updates
        self.zoom = 1.0             # zoom level
        self.ct = coord_tran()
        self.chname = None


# utility routines
def wcs_pix_transform (ct, i, format=0):
    """Computes the WCS corrected pixel value given a coordinate
    transformation and the raw pixel value.

    Input:
    ct      coordinate transformation. instance of coord_tran.
    i       raw pixel intensity.
    format  format string (optional).

    Returns:
    WCS corrected pixel value
    """
    z1 = float (ct.z1)
    z2 = float (ct.z2)
    i = float (i)

    yscale = 128.0 / (z2 - z1)
    if (format == 'T' or format == 't'):
        format = 1

    if (i == 0):
        t = 0.
    else:
        if (ct.zt == W_LINEAR):
            t = ((i - 1) * (z2 - z1) / 199.0) + z1;
            t = max (z1, min (z2, t))
        else:
            t = float (i)
    if (format > 1):
        t = (z2 - t) * yscale
    return (t)


def wcs_coord_transform (ct, x, y):
    """Computes tha WCS corrected pixel coordinates (RA and Dec
    in degrees) given a coordinate transformation and the screen
    coordinates (x and y, in pixels).

    Input:
    ct      coordinate transformation. instance of coord_tran.
    x       x coordinate in pixels.
    y       y coordinate in pixels.

    Returns:
    (RA, Dec) in degrees (as floats).
    """
    x = float (x)
    y = float (y)
    if (ct.valid):
        # The imtool WCS assumes that the center of the first display
        # pixel is at (0,0) but actually it is at (0.5,0.5).
        #x -= 0.5
        #y -= 0.5

        if (abs(ct.a) > .001):
            ra = ct.a * x + ct.c * y + ct.tx
        if (abs(ct.d) > .001):
            dec = ct.b * x + ct.d * y + ct.ty
    else:
        ra = x
        dec = y
    return ((ra, dec))


def sex2deg(sex, sep=':'):
    try:
        (dd, mm, ss) = string.split(string.strip(sex), sep)
    except:
        (dd, mm) = string.split(string.strip(sex), sep)
        ss = '0'
    if(float(dd) >= 0):
        return(float(dd) + float(mm) / 60.0 + float(ss) / 3600.0)
    else:
        return(float(dd) - float(mm) / 60.0 - float(ss) / 3600.0)


def deg2sex (deg, sep=':'):
    try:
        deg = float (deg)
    except:
        return ('')

    degrees = int (deg)
    if(degrees >= 0):
        temp = (deg - degrees) * 60
        minutes = int (temp)
        seconds = int ((temp - minutes) * 60)
    else:
        temp = - (deg - degrees) * 60
        minutes = int (temp)
        seconds = int ((temp - minutes) * 60)

    sex = "%02d%c%02d%c%05.2f" % (degrees, sep, minutes, sep, seconds)
    return (sex)


def right_pad (strg, length, ch=' '):
    """As seen on http://www.halfcooked.com/mt/archives/000640.html"""
    return (strg + ch * (length - len(strg)))


def get_interface(addr=None):
    if addr:
        imtdev = addr

    else:
        try:
            imtdev = os.environ['IMTDEV']

        except KeyError:
            #port = 5137
            uid = os.getuid()
            path = '/tmp/.IMT' + str(uid)
            prot = 'unix'
            name = "%s:%s" % (prot, path)
            return Bunch.Bunch(prot=prot, path=path, name=name)

    n, match = 1, re.match(r'^(inet)\:(\d+)\:([\w\._\-]+)$', imtdev)
    if not match:
        n, match = 2, re.match(r'^(inet)\:(\d+)$', imtdev)
    if not match:
        n, match = 3, re.match(r'^(unix)\:(.+)$', imtdev)
    if not match:
        n, match = 4, re.match(r'^(\d+)$', imtdev)
    if not match:
        # Error
        raise socketError("I don't understand the format of addr IMTDEV: '%s'" % (imtdev))

    if n == 1:
        prot, port, host = match.groups()
        port = int(port)
        return Bunch.Bunch(prot=prot, port=port, host=host, name=imtdev)

    elif n == 2:
        prot, port = match.groups()
        port = int(port)
        return Bunch.Bunch(prot=prot, port=port, host='', name=imtdev)

    elif n == 3:
        prot, path = match.groups()
        return Bunch.Bunch(prot=prot, path=path, name=imtdev)

    elif n == 4:
        port = match.group(1)
        port = int(port)
        prot = 'inet'
        return Bunch.Bunch(prot=prot, port=port, host='', name=imtdev)


#END
