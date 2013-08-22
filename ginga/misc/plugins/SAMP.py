#
# SAMP.py -- SAMP plugin for Ginga fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
# NOTE: to run this plugin you need to install astropy that has the
# vo.samp module or else the older "sampy" module from here:
#   https://pypi.python.org/pypi/sampy/
#
"""
The SAMP plugin implements a SAMP interface for the Ginga FITS
viewer.
"""
import os

try:
    import astropy.vo.samp as sampy
except ImportError:
    # TODO: remove once astropy.vo.samp module is shipped with astropy
    import sampy

from ginga import GingaPlugin
from ginga import Catalog

class SAMPError(Exception):
    pass

class SAMP(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(SAMP, self).__init__(fv)

        # channel to use to load images into
        self.chname = 'SAMP'
        # where to download files
        self.filedir = '/tmp'
        self.count = 0
        
        self.ev_quit = fv.ev_quit

        # Used to fetch data
        self.fetcher = Catalog.ImageServer(self.logger, "SAMP Image Fetcher",
                                           "SAMP", "none", "SAMP handler")

    # NO GUI...yet
    #def build_gui(self, container):
    #    pass
    
    def start(self):
        self.robj = GingaWrapper(self.fv, self.logger)
        
        client = sampy.SAMPIntegratedClient(metadata = {
            "samp.name":"ginga",
            "samp.description.text":"Ginga viewer",
            "ginga.version":"1.3"})
        self.client = client
        client.connect()

        # TODO: need to handle some administrative messages
        #client.bindReceiveNotification("samp.app.*", self.samp_placeholder)
        #client.bindReceiveCall("samp.app.*", self.samp_placeholder)

        # Loads a 2-dimensional FITS image.
        # Arguments:
        #   url (string): URL of the FITS image to load
        #   image-id (string) optional: Identifier which may be used
        #           to refer to the loaded image in subsequent messages
        #   name (string) optional: name which may be used to label the
        #           loaded image in the application GUI 
        # Return Values: none 
        client.bindReceiveCall("image.load.fits", self.samp_call_load_fits)
        client.bindReceiveNotification("image.load.fits",
                                       self.samp_notify_load_fits)

        # Not yet implemented.  Not sure if/how these are different
        # from the image.load.fits variants
        client.bindReceiveCall("table.load.fits", self.samp_placeholder)
        client.bindReceiveNotification("table.load.fits", self.samp_placeholder)

        # Directs attention (e.g. by moving a cursor or shifting the field
        #   of view) to a given point on the celestial sphere.
        # Arguments:
        #   ra (SAMP float): right ascension in degrees
        #   dec (SAMP float): declination in degrees 
        # Return Values: none 
        client.bindReceiveCall("coord.pointAt.sky", self.samp_placeholder)
        client.bindReceiveNotification("coord.pointAt.sky",
                                       self.samp_placeholder)

        # Loads a table in VOTable format. This is the usual way to
        # exchange table data between SAMP clients.
        # Arguments:
        #   url (string): URL of the VOTable document to load
        #   table-id (string) optional: identifier which may be used to
        #     refer to the loaded table in subsequent messages
        #   name (string) optional: name which may be used to label the
        #     loaded table in the application GUI 
        # Return Values: none 
        client.bindReceiveCall("table.load.votable", self.samp_placeholder)
        client.bindReceiveNotification("table.load.votable",
                                       self.samp_placeholder)

        # TODO: this should eventually shut down the sampy 
        self.fv.nongui_do(self.monitor_shutdown)
        
    def stop(self):
        try:
            print "disconnecting..."
            self.client.disconnect()
        except:
            pass
        print "stopping client..."
        self.client.stop()
        print "client should be stopped."

    def monitor_shutdown(self):
        # the thread running this method waits until the entire viewer
        # is exiting and then shuts down the SAMP XML-RPC server which is
        # running in a different thread
        self.ev_quit.wait()
        self.stop()

    def samp_placeholder(self, private_key, sender_id, msg_id, mtype, params,
                         extra):
        self.logger.debug("key=%s sender=%s msg_id=%s mtype=%s" % (
            private_key, sender_id, msg_id, mtype))
        self.logger.debug("params=%s extra=%s" % (params, extra))
        self.logger.warn("SAMP message (%s) handler not yet implemented." % (
            str(msg_id)))

    def _load_fits(self, private_key, sender_id, msg_id, mtype, params,
                     extra):

        url = params['url']
        # TODO: unmangle the 'name' parameter to a filename (if provided)
        self.count += 1
        name = "samp_%d.fits" % (self.count)
        
        fitspath = os.path.join(self.filedir, name)
        
        chname = self.chname
        dowait = True

        # fetch the file, if necessary
        self.logger.debug("downloading %s <-- %s" % (fitspath, url))
        try:
            self.fetcher.fetch(url, filepath=fitspath)

            # load into the viewer
            self.robj.display_fitsfile(chname, fitspath, dowait)
        
        except Exception as e:
            errmsg = "Error loading FITS file '%s': %s" % (
                fitspath, str(e))
            self.logger.error(errmsg)
            raise SAMPError(errmsg)


    def samp_notify_load_fits(self, private_key, sender_id, msg_id, mtype,
                              params, extra):
        self._load_fits(private_key, sender_id, msg_id, mtype,
                        params, extra)

    def samp_call_load_fits(self, private_key, sender_id, msg_id, mtype,
                            params, extra):
        result = {}
        try:

            self._load_fits(private_key, sender_id, msg_id, mtype,
                            params, extra)
            status = sampy.SAMP_STATUS_OK

        except Exception as e:
            errmsg = str(e)
            result['errmsg'] = errmsg
            status = sampy.SAMP_STATUS_ERROR

        self.client.ereply(msg_id, status, result=result)

    def __str__(self):
        return 'samp'

    
class GingaWrapper(object):

    def __init__(self, fv, logger):
        self.fv = fv
        self.logger = logger

    def display_fitsfile(self, chname, fitspath, dowait):
        """Load (fitspath) into channel (chname).  If (dowait) is True
        then wait for the file to be loaded before returning (synchronous).
        """
        self.fv.load_file(fitspath, chname=chname, wait=dowait)
        return 0

#END
