#
# PluginManager.py -- Simple base class to manage plugins.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys
import threading
import traceback

from ginga.gw import Widgets
from ginga.misc import Bunch
from ginga.util.six.moves import filter

class PluginManagerError(Exception):
    pass

class PluginManagerBase(object):

    def __init__(self, logger, fitsview, ds, mm):
        super(PluginManagerBase, self).__init__()

        self.logger = logger
        self.fv = fitsview
        self.ds = ds
        self.mm = mm

        self.lock = threading.RLock()
        self.plugin = Bunch.caselessDict()
        self.active = {}
        self.focus  = set([])
        self.exclusive = set([])
        self.focuscolor = "lightgreen"

        self.hbox = None

    def set_widget(self, hbox):
        self.hbox = hbox

    def loadPlugin(self, name, spec, chinfo=None):
        try:
            module = self.mm.getModule(spec.module)
            className = spec.get('klass', spec.module)
            klass = getattr(module, className)

            if chinfo is None:
                # global plug in
                obj = klass(self.fv)
                fitsimage = None
            else:
                # local plugin
                fitsimage = chinfo.fitsimage
                obj = klass(self.fv, fitsimage)

            # Prepare configuration for module.  This becomes the pInfo
            # object referred to in later code.
            opname = name.lower()
            self.plugin[opname] = Bunch.Bunch(klass=klass, obj=obj,
                                              widget=None, name=name,
                                              spec=spec,
                                              fitsimage=fitsimage,
                                              chinfo=chinfo)

            self.logger.info("Plugin '%s' loaded." % name)

        except Exception as e:
            self.logger.error("Failed to load plugin '%s': %s" % (
                name, str(e)))
            #raise PluginManagerError(e)

    def reloadPlugin(self, plname, chinfo=None):
        pInfo = self.getPluginInfo(plname)
        return self.loadPlugin(pInfo.name, pInfo.spec, chinfo=chinfo)

    def getPluginInfo(self, plname):
        plname = plname.lower()
        pInfo = self.plugin[plname]
        return pInfo

    def getPlugin(self, name):
        pInfo = self.getPluginInfo(name)
        return pInfo.obj

    def getNames(self):
        return self.plugin.keys()

    def deactivate_focused(self):
        names = self.get_focus()
        for name in names:
            self.deactivate(name)

    def get_active(self):
        return self.active.keys()

    def is_active(self, key):
        lname = key.lower()
        return lname in self.get_active()

    def get_focus(self):
        return list(self.focus)

    def get_info(self, name):
        lname = name.lower()
        return self.active[lname]

    def activate(self, pInfo, exclusive=True):
        name = pInfo.tabname
        lname = pInfo.name.lower()
        if lname not in self.active:
            bnch = Bunch.Bunch(pInfo=pInfo, lblname=None, widget=None,
                               exclusive=exclusive)

            if pInfo.chinfo is not None:
                # local plugin
                tup = name.split(':')
                bnch.lblname = ' ' + tup[0] + ':\n' + tup[1] + ' '
                self.add_taskbar(bnch)
            else:
                # global plugin
                bnch.exclusive = False

            self.active[lname] = bnch
            if bnch.exclusive:
                self.exclusive.add(lname)

    def deactivate(self, name):
        self.logger.debug("deactivating %s" % (name))
        lname = name.lower()
        if lname in self.focus:
            self.clear_focus(lname)

        if lname in self.active:
            bnch = self.active[lname]
            self.stop_plugin(bnch.pInfo)
            if bnch.widget is not None:
                self.remove_taskbar(bnch)
            del self.active[lname]

        # Set focus to another plugin if one is running
        active = self.active.keys()
        if len(active) > 0:
            name = active[0]
            self.set_focus(name)

    def set_focus(self, name):
        self.logger.debug("Focusing plugin '%s'" % (name))
        lname = name.lower()
        bnch = self.active[lname]
        if bnch.exclusive:
            self.logger.debug("focus=%s exclusive=%s" % (
                self.focus, self.exclusive))
            defocus = list(filter(lambda x: x in self.exclusive, self.focus))
            self.logger.debug("defocus: %s" % (str(defocus)))
            for xname in defocus:
                self.clear_focus(xname)

        pInfo = bnch.pInfo
        # If this is a local plugin, raise the channel associated with the
        # plug in
        if pInfo.chinfo is not None:
            itab = pInfo.chinfo.name
            self.logger.debug("raising tab %s" % (itab))
            self.ds.raise_tab(itab)

            self.logger.debug("resuming plugin %s" % (name))
            pInfo.obj.resume()
            self.highlight_taskbar(bnch)
            # TODO: Need to account for the fact that not all plugins
            # end up in the workspace "Dialogs"
            self.ds.raise_tab('Dialogs')

        self.focus.add(lname)
        if pInfo.widget is not None:
            self.logger.debug("raising tab %s" % (pInfo.tabname))
            self.ds.raise_tab(pInfo.tabname)

    def clear_focus(self, name):
        self.logger.debug("Unfocusing plugin '%s'" % (name))
        lname = name.lower()
        bnch = self.active[lname]
        pInfo = bnch.pInfo
        try:
            self.focus.remove(lname)

            if pInfo.chinfo is not None:
                bnch.pInfo.obj.pause()
                self.unhighlight_taskbar(bnch)
        except:
            pass

    def start_plugin(self, chname, opname, alreadyOpenOk=False):
        return self.start_plugin_future(chname, opname, None,
                                        alreadyOpenOk=alreadyOpenOk)

    def start_plugin_future(self, chname, opname, future,
                            alreadyOpenOk=True):
        pInfo = self.getPluginInfo(opname)
        if chname is not None:
            # local plugin
            plname = chname.upper() + ': ' + pInfo.name
        else:
            # global plugin
            plname = pInfo.name
        lname = pInfo.name.lower()
        if lname in self.active:
            if alreadyOpenOk:
                self.set_focus(pInfo.name)
                return
            raise PluginManagerError("Plugin %s is already active." % (
                plname))

        # Raise tab with GUI
        pInfo.tabname = pInfo.spec.get('tab', plname)
        vbox = None
        had_error = False
        try:
            if hasattr(pInfo.obj, 'build_gui'):
                vbox = Widgets.VBox()
                # attach size of workspace to container so plugin
                # can plan for how to configure itself
                wd, ht = self.ds.get_ws_size(pInfo.spec.ws)
                vbox.size = (wd, ht)
                if future:
                    pInfo.obj.build_gui(vbox, future=future)
                else:
                    pInfo.obj.build_gui(vbox)

        except Exception as e:
            errstr = "Plugin UI failed to initialize: %s" % (
                str(e))
            self.logger.error(errstr)
            try:
                (type, value, tb) = sys.exc_info()
                tb_str = "".join(traceback.format_tb(tb))
                self.logger.error("Traceback:\n%s" % (tb_str))

            except Exception as e:
                tb_str = "Traceback information unavailable."
                self.logger.error(tb_str)

            self.plugin_build_error(vbox, errstr + '\n' + tb_str)
            #raise PluginManagerError(e)

        if not had_error:
            try:
                if future:
                    pInfo.obj.start(future=future)
                else:
                    pInfo.obj.start()

            except Exception as e:
                had_error = True
                errstr = "Plugin failed to start correctly: %s" % (
                    str(e))
                self.logger.error(errstr)
                try:
                    (type, value, tb) = sys.exc_info()
                    tb_str = "".join(traceback.format_tb(tb))
                    self.logger.error("Traceback:\n%s" % (tb_str))

                except Exception as e:
                    tb_str = "Traceback information unavailable."
                    self.logger.error(tb_str)

                self.plugin_build_error(vbox, errstr + '\n' + tb_str)
                #raise PluginManagerError(e)

        if vbox is not None:
            self.finish_gui(pInfo, vbox)
            ws = pInfo.spec.ws
            child_w = vbox.get_widget()
            self.ds.add_tab(ws, child_w, 2, pInfo.tabname, pInfo.tabname)
            pInfo.widget = vbox

            self.activate(pInfo)
            self.set_focus(pInfo.name)
        else:
            # If this is a local plugin, raise the channel associated with the
            # plug in
            if pInfo.chinfo is not None:
                itab = pInfo.chinfo.name
                self.ds.raise_tab(itab)

    def stop_plugin(self, pInfo):
        self.logger.debug("stopping plugin %s" % (str(pInfo)))
        wasError = False
        try:
            pInfo.obj.stop()

        except Exception as e:
            wasError = True
            self.logger.error("Plugin failed to stop correctly: %s" % (
                str(e)))
            try:
                (type, value, tb) = sys.exc_info()
                tb_str = "".join(traceback.format_tb(tb))
                self.logger.error("Traceback:\n%s" % (tb_str))

            except Exception:
                self.logger.error("Traceback information unavailable.")

        if pInfo.widget is not None:
            self.ds.remove_tab(pInfo.tabname)
            self.dispose_gui(pInfo)

        ## # If there are no more dialogs present, raise Thumbs
        ## nb = self.ds.get_nb('Dialogs')
        ## num_dialogs = nb.get_n_pages()   # gtk
        ## num_dialogs = len(nb.children()) # qt
        ## if num_dialogs == 0:
        ##     try:
        ##         self.ds.raise_tab('Thumbs')
        ##     except:
        ##         # No Thumbs tab--OK
        ##         pass

        if wasError:
            raise PluginManagerError(e)

    def plugin_build_error(self, box, text):
        textw = Widgets.TextArea(editable=False, wrap=True)
        textw.append_text(text)
        box.add_widget(textw, stretch=1)


#END
