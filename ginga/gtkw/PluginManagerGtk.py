#
# PluginManagerGtk.py -- Simple class to manage plugins.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.gtkw import gtksel
import gtk
from ginga.misc.PluginManager import PluginManagerBase, PluginManagerError

class PluginManager(PluginManagerBase):
    """
    This provides the GUI support methods for the PluginManager.
    See PluginManagerBase for the general logic of this class.
    """

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

    def add_taskbar(self, bnch):
        lblname = bnch.lblname
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

        lname = bnch.pInfo.name.lower()
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
        evbox.connect("button_press_event", self.button_press_event,
                      lname)

        bnch.setvals(widget=fr, label=lbl, evbox=evbox,
                     menu=menu)
        self.logger.debug("added to taskbar: %s" % (bnch.pInfo.name))

    def remove_taskbar(self, bnch):
        self.logger.debug("removing widget from taskbar")
        self.hbox.remove(bnch.widget)
        bnch.widget = None
        bnch.label = None
        
    def highlight_taskbar(self, bnch):
        self.logger.debug("highlighting widget")
        bnch.evbox.modify_bg(gtk.STATE_NORMAL,
                             gtk.gdk.color_parse(self.focuscolor))
        ## bnch.label.set_markup('<span background="green">%s</span>' % (
        ##     bnch.lblname))

    def unhighlight_taskbar(self, bnch):
        self.logger.debug("unhighlighting widget")
        bnch.evbox.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("grey"))
        ## bnch.label.set_markup('<span>%s</span>' % (bnch.lblname))

    def finish_gui(self, pInfo, vbox):
        vbox.get_widget().show_all()
        
    def dispose_gui(self, pInfo):
        vbox = pInfo.widget
        pInfo.widget = None
        vbox.get_widget().destroy()
        
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

#END
