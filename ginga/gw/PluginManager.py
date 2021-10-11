#
# PluginManager.py -- Simple class to manage plugins.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys
import threading
import traceback

from ginga.gw import Widgets
from ginga.misc import Bunch, Callback


class PluginManagerError(Exception):
    pass


class PluginManager(Callback.Callbacks):
    """
    A PluginManager manages the start and stop of plugins.
    """

    def __init__(self, logger, gshell, ds, mm):
        super(PluginManager, self).__init__()

        self.logger = logger
        self.fv = gshell
        self.ds = ds
        self.mm = mm

        self.lock = threading.RLock()
        self.plugin = Bunch.caselessDict()
        self.active = {}
        self.focus = set([])
        self.exclusive = set([])

        for name in ('activate-plugin', 'deactivate-plugin',
                     'focus-plugin', 'unfocus-plugin'):
            self.enable_callback(name)

    def load_plugin(self, name, spec, chinfo=None):
        try:
            module = self.mm.get_module(spec.module)
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

            # Prepare configuration for module.  This becomes the p_info
            # object referred to in later code.
            opname = name.lower()
            self.plugin[opname] = Bunch.Bunch(klass=klass, obj=obj,
                                              widget=None, name=name,
                                              is_toplevel=False,
                                              spec=spec,
                                              fitsimage=fitsimage,
                                              chinfo=chinfo)

            self.logger.info("Plugin '%s' loaded." % name)

        except Exception as e:
            self.logger.error("Failed to load plugin '{}': {}".format(
                name, e), exc_info=True)
            #raise PluginManagerError(e)

    def reload_plugin(self, plname, chinfo=None):
        p_info = self.get_plugin_info(plname)
        return self.load_plugin(p_info.name, p_info.spec, chinfo=chinfo)

    def has_plugin(self, plname):
        plname = plname.lower()
        return plname in self.plugin

    def get_plugin_info(self, plname):
        plname = plname.lower()
        p_info = self.plugin[plname]
        return p_info

    def get_plugin(self, name):
        p_info = self.get_plugin_info(name)
        return p_info.obj

    def get_names(self):
        return list(self.plugin.keys())

    def deactivate_focused(self):
        names = self.get_focus()
        for name in names:
            self.deactivate(name)

    def get_active(self):
        return list(self.active.keys())

    def is_active(self, key):
        lname = key.lower()
        return lname in self.get_active()

    def get_focus(self):
        return list(self.focus)

    def has_focus(self, name):
        lname = name.lower()
        names = self.get_focus()
        return lname in names

    def get_info(self, name):
        lname = name.lower()
        return self.active[lname]

    def activate(self, p_info, exclusive=True):
        name = p_info.tabname
        lname = p_info.name.lower()
        if lname in self.active:
            # plugin already active
            return

        bnch = Bunch.Bunch(pInfo=p_info, lblname=name, widget=None,
                           exclusive=exclusive)

        if p_info.chinfo is not None:
            # local plugin
            tup = name.split(':')
            bnch.lblname = ' ' + tup[0] + ':\n' + tup[1] + ' '
        else:
            # global plugin
            bnch.exclusive = False

        self.active[lname] = bnch
        if bnch.exclusive:
            self.exclusive.add(lname)

        self.make_callback('activate-plugin', bnch)

    def deactivate(self, name):
        self.logger.debug("deactivating %s" % (name))
        lname = name.lower()
        if lname in self.focus:
            self.clear_focus(lname)

        if lname not in self.active:
            # plugin already deactivated
            return

        self.logger.debug("removing from task bar: %s" % (lname))
        bnch = self.active[lname]

        del self.active[lname]

        try:
            self.stop_plugin(bnch.pInfo)

        except Exception as e:
            self.logger.error("Error deactivating plugin: {}".format(e),
                              exc_info=True)

        # Set focus to another plugin if one is running, but only if it
        # is a local plugin
        if bnch.pInfo.spec.ptype != 'global':
            active = list(self.active.keys())
            if len(active) > 0:
                name = active[0]
                self.logger.debug("focusing: %s" % (name))
                self.set_focus(name)

        self.make_callback('deactivate-plugin', bnch)

    def stop_reload_start(self, name):
        # deactivate the running plugin, if active
        if self.is_active(name):
            self.deactivate(name)

        self.fv.update_pending(timeout=0.1)

        # reload the plugin
        p_info = self.get_plugin_info(name)
        chname = None
        if p_info.chinfo is not None:
            chname = p_info.chinfo.name

        self.reload_plugin(name, chinfo=p_info.chinfo)

        # and start it up again
        self.start_plugin_future(chname, name, None)

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

        p_info = bnch.pInfo
        # If this is a local plugin, raise the channel associated with the
        # plug in
        if p_info.chinfo is not None:
            self.logger.debug("resuming plugin %s" % (name))
            p_info.obj.resume()

        self.focus.add(lname)
        self.make_callback('focus-plugin', bnch)

        self.raise_plugin(p_info)

    def raise_plugin(self, p_info):
        if p_info.widget is not None:
            self.logger.debug("raising plugin tab %s" % (p_info.tabname))
            if p_info.is_toplevel:
                p_info.widget.raise_()
            else:
                self.ds.raise_tab(p_info.tabname)

        if p_info.chinfo is not None:
            chname = p_info.chinfo.name
            self.logger.debug("changing channel to %s" % (chname))
            # Alternative could just be to raise the channel tab rather
            # than making all the global plugins switch over to the new
            # channel
            #self.ds.raise_tab(chname)
            self.fv.change_channel(chname)

    def clear_focus(self, name):
        self.logger.debug("Unfocusing plugin '%s'" % (name))
        lname = name.lower()
        bnch = self.active[lname]
        p_info = bnch.pInfo
        try:
            self.focus.remove(lname)

            if p_info.chinfo is not None:
                p_info.obj.pause()

            self.make_callback('unfocus-plugin', bnch)

        except Exception as e:
            self.logger.error("Error unfocusing plugin '%s': %s" % (
                name, str(e)))

    def start_plugin(self, chname, opname, alreadyOpenOk=False):
        return self.start_plugin_future(chname, opname, None,
                                        alreadyOpenOk=alreadyOpenOk)

    def start_plugin_future(self, chname, opname, future,
                            alreadyOpenOk=True):
        try:
            p_info = self.get_plugin_info(opname)

        except KeyError:
            self.fv.show_error("No plugin information for plugin '%s'" % (
                opname))
            return

        if chname is not None:
            # local plugin
            plname = chname.upper() + ': ' + p_info.spec.get('tab', p_info.name)
            p_info.tabname = plname
        else:
            # global plugin
            plname = p_info.name
            p_info.tabname = p_info.spec.get('tab', plname)

        lname = p_info.name.lower()

        if lname in self.active:
            # <-- plugin is supposedly already active
            if alreadyOpenOk:
                self.set_focus(p_info.name)
                return

            raise PluginManagerError("Plugin %s is already active." % (
                plname))

        # Build GUI phase
        vbox = None
        try:
            if hasattr(p_info.obj, 'build_gui'):
                vbox = Widgets.VBox()

                in_ws = p_info.spec.get('workspace', None)
                if in_ws is None:
                    # to be deprecated
                    in_ws = p_info.spec.ws

                if in_ws.startswith('in:'):
                    # TODO: how to set this size appropriately
                    # Which plugins are actually using this attribute?
                    vbox.size = (400, 900)

                else:
                    # attach size of workspace to container so plugin
                    # can plan for how to configure itself
                    wd, ht = self.ds.get_ws_size(in_ws)
                    vbox.size = (wd, ht)

                if future:
                    p_info.obj.build_gui(vbox, future=future)
                else:
                    p_info.obj.build_gui(vbox)

        except Exception as e:
            errstr = "Plugin UI failed to initialize: {}".format(e)
            self.logger.error(errstr)
            try:
                (type, value, tb) = sys.exc_info()
                tb_str = "".join(traceback.format_tb(tb))
                self.logger.error("Traceback:\n%s" % (tb_str))

            except Exception as e:
                tb_str = "Traceback information unavailable."
                self.logger.error(tb_str)

            self.fv.show_error(errstr + '\n' + tb_str)
            #raise PluginManagerError(e)
            return

        # start phase
        try:
            if future:
                p_info.obj.start(future=future)
            else:
                p_info.obj.start()

        except Exception as e:
            errstr = "Plugin failed to start correctly: {}".format(e)
            self.logger.error(errstr)
            try:
                (type, value, tb) = sys.exc_info()
                tb_str = "".join(traceback.format_tb(tb))
                self.logger.error("Traceback:\n%s" % (tb_str))

            except Exception as e:
                tb_str = "Traceback information unavailable."
                self.logger.error(tb_str)

            self.fv.show_error(errstr + '\n' + tb_str)
            #raise PluginManagerError(e)
            return

        if vbox is not None:
            self.finish_gui(p_info, vbox)

            self.activate(p_info)
            # focusing plugin will also raise plugin and associated
            # channel viewer
            self.set_focus(p_info.name)

        else:
            self.activate(p_info)

            # If this is a local plugin, raise the channel viewer
            # associated with the plug in
            if p_info.chinfo is not None:
                itab = p_info.chinfo.name
                self.ds.raise_tab(itab)

    def stop_plugin(self, p_info):
        self.logger.debug("stopping plugin %s" % (str(p_info)))
        wasError = False
        e = None
        try:
            p_info.obj.stop()

        except Exception as e:
            wasError = True
            self.logger.error("Plugin '{}' failed to stop correctly: {}".format(p_info.name, e),
                              exc_info=True)

        if p_info.widget is not None:
            self.dispose_gui(p_info)
            self.ds.remove_tab(p_info.tabname)

        if wasError:
            raise PluginManagerError(e)

    def stop_all_plugins(self):
        for plugin_name in self.get_active():
            try:
                p_info = self.get_plugin_info(plugin_name)
                self.stop_plugin(p_info)
            except Exception as e:
                self.logger.error("Exception while calling stop for plugin '{}': {}".format(plugin_name, e),
                                  exc_info=True)
        return True

    def plugin_build_error(self, box, text):
        textw = Widgets.TextArea(editable=False, wrap=True)
        textw.append_text(text)
        box.add_widget(textw, stretch=1)

    def finish_gui(self, p_info, vbox):
        # add container to workspace
        # TODO: how to figure out the appropriate size for top-levels?
        wd, ht = vbox.get_size()

        try:
            in_ws = p_info.spec.get('workspace', None)
            if in_ws is None:
                # to be deprecated
                in_ws = p_info.spec.ws

            if in_ws == 'in:toplevel':
                topw = vbox.get_app().make_window()
                topw.add_callback('close',
                                  lambda *args: self.deactivate(p_info.name))
                topw.resize(wd, ht)
                topw.set_title(p_info.tabname)
                topw.set_widget(vbox)
                p_info.widget = topw
                p_info.is_toplevel = True
                topw.show()

            elif in_ws == 'in:dialog':
                dialog = Widgets.Dialog(title=p_info.name,
                                        flags=0,
                                        buttons=[],
                                        parent=self.fv.w.root)
                dialog.resize(wd, ht)
                box = dialog.get_content_area()
                box.add_widget(vbox, stretch=1)
                p_info.widget = dialog
                p_info.is_toplevel = True
                # TODO: need to add callback to remove from Desktop
                # dialog list?
                self.ds.show_dialog(dialog)

            else:
                bnch = self.ds.add_tab(in_ws, vbox, 2, p_info.tabname,
                                       p_info.tabname)
                bnch.plugin_info = p_info

                ws = self.ds.get_ws(in_ws)
                ws.add_callback('page-close', self.tab_closed_cb)

                ws_w = self.ds.get_nb(in_ws)
                ws_w.add_callback('page-switch', self.tab_switched_cb)
                p_info.widget = vbox
                p_info.is_toplevel = False

        except Exception as e:
            self.fv.show_error("Error finishing plugin UI for '%s': %s" % (
                p_info.name, str(e)))

    def tab_switched_cb(self, tab_w, widget):
        # A tab in a workspace in which we started a plugin has been
        # raised.  Check for this widget and focus the plugin
        title = widget.extdata.get('tab_title', None)
        # is this a local plugin tab?
        if title is None or ':' not in title:
            return

        chname, plname = title.split(':')
        plname = plname.strip()
        try:
            info = self.get_info(plname)
        except KeyError:
            # no
            return
        p_info = info.pInfo
        # important: make sure channel matches ours!
        if p_info.tabname == title:
            if self.is_active(p_info.name):
                if not self.has_focus(p_info.name):
                    self.set_focus(p_info.name)
                elif p_info.chinfo is not None:
                    # raise the channel associated with the plugin
                    chname = p_info.chinfo.name
                    # Alternative could just be to raise the channel tab
                    # rather than making all the global plugins switch
                    # over to the new channel
                    #self.ds.raise_tab(chname)
                    self.fv.change_channel(chname)

    def tab_closed_cb(self, ws, widget):
        bnch = self.ds._find_tab(widget)
        if bnch is not None:
            p_info = bnch.get('plugin_info', None)
            if p_info is not None:
                self.deactivate(p_info.name)

    def dispose_gui(self, p_info):
        self.logger.debug("disposing of gui")
        vbox = p_info.widget
        p_info.widget = None
        vbox.hide()
        vbox.delete()

    ########################################################
    ### NON-PEP8 PREDECESSORS: TO BE DEPRECATED

    loadPlugin = load_plugin
    reloadPlugin = reload_plugin
    getPluginInfo = get_plugin_info
    getPlugin = get_plugin
    getNames = get_names

# END
