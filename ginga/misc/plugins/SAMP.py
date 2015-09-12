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
# vo.samp module
#
"""
The SAMP plugin implements a SAMP interface for the Ginga FITS
viewer.
"""
import os

try:
    import astropy.vo.samp as samp
    have_samp = True

except ImportError as e:
    have_samp = False

from ginga import GingaPlugin
from ginga.util import catalog
from ginga.version import version
from ginga.gw import Widgets

class SAMPError(Exception):
    pass

class SAMP(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(SAMP, self).__init__(fv)

        self.count = 0
        self.ev_quit = fv.ev_quit

        # objects that are recreated when the plugin is started
        # via start()
        self.client = None
        self.hub = None
        self.fetcher = None
        self.robj = None

        # get plugin settings
        prefs = self.fv.get_preferences()
        self.settings = prefs.createCategory('plugin_SAMP')
        self.settings.addDefaults(SAMP_channel='Image',
                                  cache_location=self.fv.tmpdir,
                                  default_connect=True,
                                  start_hub=True)
        self.settings.load(onError='silent')


    def build_gui(self, container):
        if not have_samp:
            raise GingaPlugin.PluginError("To run this plugin you need to install the astropy.vo.samp module")

        vbox = Widgets.VBox()
        vbox.set_border_width(4)
        vbox.set_spacing(2)

        msgFont = self.fv.getFont("sansFont", 12)
        tw = Widgets.TextArea(wrap=True, editable=False)
        tw.set_font(msgFont)
        self.tw = tw

        fr = Widgets.Frame("Instructions")
        fr.set_widget(tw)
        vbox.add_widget(fr, stretch=0)

        fr = Widgets.Frame("SAMP")

        captions = [('Start hub', 'checkbutton'),
                    ('Connect client', 'checkbutton'),
                    ]
        w, b = Widgets.build_info(captions)
        self.w.update(b)
        b.start_hub.set_tooltip("Start a SAMP hub")
        b.start_hub.set_state(self.settings.get('start_hub', True))
        b.start_hub.add_callback('activated', self.start_hub_cb)
        b.connect_client.set_tooltip("Register with a SAMP hub")
        b.connect_client.set_state(self.settings.get('default_connect',
                                                     True))
        b.connect_client.add_callback('activated', self.connect_client_cb)

        fr.set_widget(w)
        vbox.add_widget(fr, stretch=0)

        # stretch
        vbox.add_widget(Widgets.Label(''), stretch=1)

        btns = Widgets.HBox()
        btns.set_border_width(4)
        btns.set_spacing(4)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn)
        btns.add_widget(Widgets.Label(''), stretch=1)
        vbox.add_widget(btns, stretch=0)

        container.add_widget(vbox, stretch=1)

    def instructions(self):
        self.tw.set_text("""SAMP hub/client control.""")

    def start(self):
        self.instructions()

        self.robj = GingaWrapper(self.fv, self.logger)

        # Create a HUB
        self.hub = samp.SAMPHubServer()
        try:
            if self.w.start_hub.get_state():
                self.hub.start()

        except Exception as e:
            self.logger.warn("Cannot start hub: %s" % (str(e)))

        # Used to fetch data
        self.fetcher = catalog.ImageServer(self.logger, "SAMP Image Fetcher",
                                           "SAMP", "none", "SAMP handler")

        # Create the client
        try:
            if self.w.connect_client.get_state():
                self.client = self._connect_client()

        except Exception as e:
            self.fv.show_error("Cannot connect client: %s" % (str(e)))

        # TODO: this should eventually shut down the samp
        self.fv.nongui_do(self.monitor_shutdown)

    def stop(self):
        try:
            self.logger.info("disconnecting client...")
            if self.client is not None:
                self.client.disconnect()
        except Exception as e:
            pass
        try:
            self.logger.info("stopping client...")
            if self.client is not None:
                self.client.stop()
        except Exception as e:
            pass

        # Try to stop the hub, if any
        if self.hub is not None:
            self.hub.stop()
        self.w.start_hub.set_state(False)

    def start_hub_cb(self, w, tf):
        try:
            if tf:
                self.logger.info("starting hub...")
                self.hub.start()

            else:
                self.logger.info("stopping hub...")
                self.hub.stop()

        except Exception as e:
            self.fv.show_error("Cannot start/stop hub: %s" % (str(e)))

    def _connect_client(self):
        client = samp.SAMPIntegratedClient(metadata = {
            "samp.name": "ginga",
            "samp.description.text": "Ginga viewer",
            "ginga.version": version})
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
        client.bind_receive_call("image.load.fits", self.samp_call_load_fits)
        client.bind_receive_notification("image.load.fits",
                                       self.samp_notify_load_fits)

        # Not yet implemented.  Not sure if/how these are different
        # from the image.load.fits variants
        client.bind_receive_call("table.load.fits", self.samp_placeholder)
        client.bind_receive_notification("table.load.fits", self.samp_placeholder)

        # Directs attention (e.g. by moving a cursor or shifting the field
        #   of view) to a given point on the celestial sphere.
        # Arguments:
        #   ra (SAMP float): right ascension in degrees
        #   dec (SAMP float): declination in degrees
        # Return Values: none
        client.bind_receive_call("coord.pointAt.sky", self.samp_placeholder)
        client.bind_receive_notification("coord.pointAt.sky",
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
        client.bind_receive_call("table.load.votable", self.samp_placeholder)
        client.bind_receive_notification("table.load.votable",
                                         self.samp_placeholder)
        return client

    def connect_client_cb(self, w, tf):
        if tf:
            self.logger.info("connecting client...")
            self.client = self._connect_client()
        else:
            self.logger.info("disconnecting client...")
            if self.client is not None:
                self.client.disconnect()
                self.client = None
                self.w.connect_client.set_state(False)

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

        filedir = self.settings.get('cache_location', self.fv.tmpdir)
        fitspath = os.path.join(filedir, name)

        chname = self.settings.get('SAMP_channel', 'SAMP')
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
        self.logger.info("received load fits params=%s" % (str(params)))
        result = {}
        try:

            self._load_fits(private_key, sender_id, msg_id, mtype,
                            params, extra)
            status = samp.SAMP_STATUS_OK

        except Exception as e:
            errmsg = str(e)
            result['errmsg'] = errmsg
            status = samp.SAMP_STATUS_ERROR

        self.client.ereply(msg_id, status, result=result)

    def close(self):
        self.fv.stop_global_plugin(str(self))
        self.tw = None
        return True

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
