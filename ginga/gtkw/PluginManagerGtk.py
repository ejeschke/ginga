#
# PluginManagerGtk.py -- Simple class to manage plugins.
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

from ginga.gtkw import gtksel
import gtk

from ginga.misc import Bunch, Future


class PluginManagerError(Exception):
    pass

class PluginManager(object):

    def __init__(self, logger, fitsview, ds, mm):
        super(PluginManager, self).__init__()
        
        self.logger = logger
        self.fv = fitsview
        self.ds = ds
        self.mm = mm

        self.lock = threading.RLock()
        self.plugin = Bunch.caselessDict()
        self.active = {}
        self.focus  = set([])
        self.exclusive = set([])
        self.focuscolor = "green"
        
        self.hbox = None

    def set_widget(self, hbox):
        self.hbox = hbox
        
    def loadPlugin(self, name, spec, chinfo=None):
        try:
            module = self.mm.getModule(spec.module)
            className = spec.get('klass', spec.module)
            klass = getattr(module, className)

            if chinfo == None:
                # global plug in
                obj = klass(self.fv)
                fitsimage = None
            else:
                # local plugin
                fitsimage = chinfo.fitsimage
                obj = klass(self.fv, fitsimage)

            ## # If this plugin has a GUI, add it to the Dialog pane
            ## vbox = None
            ## if hasattr(obj, 'build_gui'):
            ##     vbox = gtk.VBox()
            ##     obj.build_gui(vbox)
            vbox = None

            # Prepare configuration for module
            opname = name.lower()
            self.plugin[opname] = Bunch.Bunch(klass=klass, obj=obj,
                                              widget=vbox, name=name,
                                              spec=spec,
                                              fitsimage=fitsimage,
                                              chinfo=chinfo)
            
            self.logger.info("Plugin '%s' loaded." % name)
        
        except Exception, e:
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
    
    def update_taskbar(self, localmode=True):
        ## with self.lock:
        if localmode:
            for child in self.hbox.get_children():
                #self.hbox.remove(child)
                child.hide()
        for name in self.active.keys():
            bnch = self.active[name]
            #self.hbox.pack_start(bnch.widget, expand=False, fill=False)
            bnch.widget.show()

    def activate(self, pInfo, exclusive=True):
        name = pInfo.tabname
        lname = pInfo.name.lower()
        if not self.active.has_key(lname):
            tup = name.split(':')
            lblname = ' ' + tup[0] + ':\n' + tup[1] + ' '
            lbl = gtk.Label(lblname)
            lbl.set_justify(gtk.JUSTIFY_CENTER)
            lbl.set_tooltip_text("Right click for menu")
            evbox = gtk.EventBox()
            evbox.add(lbl)
            fr = gtk.Frame()
            fr.set_shadow_type(gtk.SHADOW_OUT)
            fr.add(evbox)
            #fr = evbox
            fr.show_all()
            self.hbox.pack_start(fr, expand=False, fill=False)

            menu = gtk.Menu()
            item = gtk.MenuItem("Focus")
            item.show()
            item.connect("activate", lambda w: self.set_focus(lname))
            menu.append(item)
            item = gtk.MenuItem("Unfocus")
            item.show()
            item.connect("activate", lambda w: self.clear_focus(lname))
            menu.append(item)
            item = gtk.MenuItem("Stop")
            item.show()
            item.connect("activate", lambda w: self.deactivate(lname))
            menu.append(item)
            
            bnch = Bunch.Bunch(widget=fr, label=lbl, lblname=lblname,
                               evbox=evbox,
                               menu=menu, pInfo=pInfo, exclusive=exclusive)
            self.active[lname] = bnch
            if exclusive:
                self.exclusive.add(lname)
            evbox.connect("button_press_event", self.button_press_event,
                          lname)

    
    def button_press_event(self, widget, event, name):
        # event.button, event.x, event.y
        bnch = self.active[name]
        if event.button == 1:
            return self.set_focus(name)

        elif event.button == 3:
            if gtksel.have_gtk3:
                return bnch.menu.popup(None, None, None, None,
                                       event.button, event.time)
            else:
                return bnch.menu.popup(None, None, None,
                                       event.button, event.time)

        return False

    def deactivate(self, name):
        self.logger.debug("deactivating %s" % (name))
        lname = name.lower()
        if lname in self.focus:
            self.clear_focus(lname)
            
        if self.active.has_key(lname):
            bnch = self.active[lname]
            self.logger.debug("stopping plugin")
            self.stop_plugin(bnch.pInfo)
            if bnch.widget != None:
                self.logger.debug("removing widget")
                self.hbox.remove(bnch.widget)
            del self.active[lname]

        # Set focus to another plugin if one is running
        active = self.active.keys()
        if len(active) > 0:
            name = active[0]
            self.set_focus(name)

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

    def set_focus(self, name):
        self.logger.info("Focusing plugin '%s'" % (name))
        lname = name.lower()
        bnch = self.active[lname]
        if bnch.exclusive:
            self.logger.debug("focus=%s exclusive=%s" % (
                self.focus, self.exclusive))
            defocus = filter(lambda x: x in self.exclusive, self.focus)
            self.logger.debug("defocus: %s" % (str(defocus)))
            for xname in defocus:
                self.clear_focus(xname)

        pInfo = bnch.pInfo
        # If this is a local plugin, raise the channel associated with the
        # plug in
        if pInfo.chinfo != None:
            itab = pInfo.chinfo.name
            self.logger.debug("raising tab %s" % (itab))
            self.ds.raise_tab(itab)
            
        pInfo.obj.resume()
        self.focus.add(lname)
        ## bnch.label.set_markup('<span background="green">%s</span>' % (
        ##     bnch.lblname))
        bnch.evbox.modify_bg(gtk.STATE_NORMAL,
                             gtk.gdk.color_parse(self.focuscolor))
        if pInfo.widget != None:
            self.ds.raise_tab('Dialogs')
            self.ds.raise_tab(pInfo.tabname)

    def clear_focus(self, name):
        self.logger.debug("Unfocusing plugin '%s'" % (name))
        lname = name.lower()
        bnch = self.active[lname]
        try:
            self.focus.remove(lname)
            bnch.pInfo.obj.pause()
        except:
            pass
        bnch.evbox.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("grey"))
        ## bnch.label.set_markup('<span>%s</span>' % (bnch.lblname))

    def start_plugin(self, chname, opname, alreadyOpenOk=False):
        return self.start_plugin_future(chname, opname, None,
                                        alreadyOpenOk=alreadyOpenOk)

    def start_plugin_future(self, chname, opname, future,
                            alreadyOpenOk=False):
        pInfo = self.getPluginInfo(opname)
        plname = chname.upper() + ': ' + pInfo.name
        lname = pInfo.name.lower()
        if self.active.has_key(lname):
            if alreadyOpenOk:
                # TODO: raise widgets, rerun start()?
                return
            raise PluginManagerError("Plugin %s is already active." % (
                plname))

        # Raise tab with GUI
        pInfo.tabname = plname
        vbox = None
        had_error = False
        try:
            if hasattr(pInfo.obj, 'build_gui'):
                vbox = gtk.VBox()
                if future:
                    pInfo.obj.build_gui(vbox, future=future)
                else:
                    pInfo.obj.build_gui(vbox)

        except Exception, e:
            errstr = "Plugin UI failed to initialize: %s" % (
                str(e))
            self.logger.error(errstr)
            try:
                (type, value, tb) = sys.exc_info()
                tb_str = "".join(traceback.format_tb(tb))
                self.logger.error("Traceback:\n%s" % (tb_str))
                
            except Exception, e:
                tb_str = "Traceback information unavailable."
                self.logger.error(tb_str)

            textw = gtk.TextView()
            buf = textw.get_buffer()
            buf.set_text(errstr + '\n' + tb_str)
            textw.set_editable(False)
            vbox.pack_start(textw, fill=True, expand=True)
            
            #raise PluginManagerError(e)
            
        if not had_error:
            try:
                if future:
                    pInfo.obj.start(future=future)
                else:
                    pInfo.obj.start()

            except Exception, e:
                had_error = True
                errstr = "Plugin failed to start correctly: %s" % (
                    str(e))
                self.logger.error(errstr)
                try:
                    (type, value, tb) = sys.exc_info()
                    tb_str = "".join(traceback.format_tb(tb))
                    self.logger.error("Traceback:\n%s" % (tb_str))

                except Exception, e:
                    tb_str = "Traceback information unavailable."
                    self.logger.error(tb_str)

                textw = gtk.TextView()
                buf = textw.get_buffer()
                buf.set_text(errstr + '\n' + tb_str)
                textw.set_editable(False)
                vbox.pack_start(textw, fill=True, expand=True)
            
                #raise PluginManagerError(e)

        if vbox != None:
            vbox.show_all()
            self.ds.add_tab('Dialogs', vbox, 2, pInfo.tabname, pInfo.tabname)
            pInfo.widget = vbox

            self.activate(pInfo)
            self.set_focus(pInfo.name)
        else:
            # If this is a local plugin, raise the channel associated with the
            # plug in
            if pInfo.chinfo != None:
                itab = pInfo.chinfo.name
                self.ds.raise_tab(itab)
            
    def stop_plugin(self, pInfo):
        self.logger.debug("stopping plugin %s" % (str(pInfo)))
        wasError = False
        try:
            pInfo.obj.stop()

        except Exception, e:
            wasError = True
            self.logger.error("Plugin failed to stop correctly: %s" % (
                str(e)))
            try:
                (type, value, tb) = sys.exc_info()
                tb_str = "".join(traceback.format_tb(tb))
                self.logger.error("Traceback:\n%s" % (tb_str))
                
            except Exception:
                self.logger.error("Traceback information unavailable.")

        if pInfo.widget != None:
            self.ds.remove_tab(pInfo.tabname)
            pInfo.widget.destroy()

        # If there are no more dialogs present, raise Thumbs
        nb = self.ds.get_nb('Dialogs')
        num_dialogs = nb.get_n_pages()
        if num_dialogs == 0:
            try:
                self.ds.raise_tab('Thumbs')
            except:
                # No Thumbs tab--OK
                pass

        if wasError:
            raise PluginManagerError(e)
        

#END
