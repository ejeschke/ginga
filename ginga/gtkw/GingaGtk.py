#
# GingaGtk.py -- Gtk display handler for the Ginga FITS tool.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
# stdlib imports
import sys, os
import Queue
import traceback

# GUI imports
from ginga.gtkw import gtksel
import gtk
import gobject
import pango

# Local application imports
from ginga import ImageView
from ginga import cmap, imap
from ginga.misc import Bunch

moduleHome = os.path.split(sys.modules[__name__].__file__)[0]
sys.path.insert(0, moduleHome)
childDir = os.path.join(moduleHome, 'plugins')
sys.path.insert(0, childDir)

from ginga.gtkw import ImageViewCanvasGtk, ColorBar, Readout, FileSelection, \
     PluginManagerGtk, GtkHelp, GtkMain, ImageViewCanvasTypesGtk

icon_path = os.path.abspath(os.path.join(moduleHome, '..', 'icons'))
rc_file = os.path.join(moduleHome, "gtk_rc")
if os.path.exists(rc_file):
    gtk.rc_parse(rc_file) 

try:
    screen = gtk.gdk.screen_get_default()
    screen_ht = screen.get_height()
    screen_wd = screen.get_width()
    root = None
except:
    screen_wd = 1600
    screen_ht = 1200
#print "screen dimensions %dx%d" % (screen_wd, screen_ht)

default_height = min(900, screen_ht - 100)
default_width  = min(1600, screen_wd)

# svg not supported well on pygtk/MacOSX yet
#icon_ext = '.svg'
icon_ext = '.png'

class GingaViewError(Exception):
    pass

class GingaView(GtkMain.GtkMain):
     
    def __init__(self, logger, ev_quit):
        GtkMain.GtkMain.__init__(self, logger=logger, ev_quit=ev_quit)
        # defaults
        self.default_height = default_height
        self.default_width  = default_width

        self.w = Bunch.Bunch()
        self.iconpath = icon_path

        self.window_is_fullscreen = False
        self.w.fscreen = None
        self._lastwsname = 'channels'
        self.layout = None
        
    def get_screen_dimensions(self):
        return (screen_wd, screen_ht)
        
    def set_layout(self, layout):
        self.layout = layout
        
    def build_toplevel(self):

        self.font = self.getFont('fixedFont', 12)
        self.font11 = self.getFont('fixedFont', 11)

        # Hack to enable images in Buttons in recent versions of gnome.
        # Why did they change the default?  Grrr....
        s = gtk.settings_get_default()
        try:
            s.set_property("gtk-button-images", True)
        except:
            pass

        self.ds = GtkHelp.Desktop()
        self.ds.make_desktop(self.layout, widgetDict=self.w)
        # TEMP: FIX ME!
        self.gpmon.ds = self.ds

        for root in self.ds.toplevels:
            # Create root window and add delete/destroy callbacks
            root.set_title("Ginga")
            root.set_border_width(2)
            root.connect("destroy", self.quit)
            root.connect("delete_event", self.delete_event)
            root.connect('window-state-event', self.window_state_change)
        
        self.w.root = root

        menuholder = self.w['menu']
        self.add_menus(menuholder)

        # Create main (center) FITS image pane
        self.w.vbox = self.w['main']
        #bnch = self.ds.make_ws(name='main', group=1, wstype='nb')
        #bnch = self.ds.make_ws(name='main', group=1, wstype='grid')
        self.ds.add_callback("page-select", self.page_switch_cb)

        # readout
        if self.settings.get('shareReadout', True):
            self.readout = self.build_readout()
            self.add_callback('field-info', self.readout_cb, self.readout, None)
            rw = self.readout.get_widget()
            self.w.vbox.pack_start(rw, padding=0, fill=True, expand=False)
            
        # bottom buttons
        hbox = gtk.HBox()

        cbox = GtkHelp.combo_box_new_text()
        self.w.channel = cbox
        cbox.set_tooltip_text("Select a channel")
        cbox.connect("changed", self.channel_select_cb)
        hbox.pack_start(cbox, fill=False, expand=False, padding=4)

        opmenu = gtk.Menu()
        self.w.operation = opmenu
        btn = gtk.Button("Operation")
        btn.connect('button-press-event', self.invoke_op_cb)
        btn.set_tooltip_text("Invoke operation")
        hbox.pack_start(btn, fill=False, expand=False, padding=2)

        self.w.optray = gtk.HBox()
        hbox.pack_start(self.w.optray, fill=True, expand=True, padding=2)
        
        self.w.vbox.pack_start(hbox, padding=0, fill=True, expand=False)

        # Add colormap bar
        cbar = self.build_colorbar()
        self.w.vbox.pack_start(cbar, padding=0, fill=True, expand=False)

        self.w.vbox.show_all()

        self.add_dialogs()
        statusholder = self.w['status']
        self.add_statusbar(statusholder)

        self.w.root.show_all()


    def getPluginManager(self, logger, fitsview, ds, mm):
        return PluginManagerGtk.PluginManager(logger, fitsview, ds, mm)
    
    def make_button(self, name, wtyp, icon=None, tooltip=None):
        image = None
        if icon:
            iconfile = os.path.join(self.iconpath, icon+icon_ext)
            try:
                pixbuf = gtksel.pixbuf_new_from_file_at_size(iconfile, 24, 24)
                if pixbuf != None:
                    image = gtk.image_new_from_pixbuf(pixbuf)
            except:
                pass

        if wtyp == 'button':
            if image:
                w = gtk.Button()
                w.set_image(image)
            else:
                w = gtk.Button(name)
        elif wtyp == 'toggle':
            if image:
                w = gtk.ToggleButton()
                w.set_image(image)
            else:
                w = gtk.ToggleButton(name)

        return w

    def add_menus(self, menuholder):

        menubar = gtk.MenuBar()
        menuholder.pack_start(menubar, expand=False)

        # create a File pulldown menu, and add it to the menu bar
        filemenu = gtk.Menu()
        file_item = gtk.MenuItem(label="File")
        menubar.append(file_item)
        file_item.show()
        file_item.set_submenu(filemenu)

        w = gtk.MenuItem("Load Image")
        filemenu.append(w)
        w.connect("activate", lambda w: self.gui_load_file())


        sep = gtk.SeparatorMenuItem()
        filemenu.append(sep)
        sep.show()
        quit_item = gtk.MenuItem(label="Exit")
        filemenu.append(quit_item)
        quit_item.connect_object ("activate", self.quit, "file.exit")
        quit_item.show()

        # create a Channel pulldown menu, and add it to the menu bar
        chmenu = gtk.Menu()
        ch_item = gtk.MenuItem(label="Channel")
        menubar.append(ch_item)
        ch_item.show()
        ch_item.set_submenu(chmenu)

        w = gtk.MenuItem("Add Channel")
        chmenu.append(w)
        w.connect("activate", lambda w: self.gui_add_channel())
        w = gtk.MenuItem("Add Channels")
        chmenu.append(w)
        w.connect("activate", lambda w: self.gui_add_channels())
        w = gtk.MenuItem("Delete Channel")
        chmenu.append(w)
        w.connect("activate", lambda w: self.gui_delete_channel())

        # create a Workspace pulldown menu, and add it to the menu bar
        winmenu = gtk.Menu()
        item = gtk.MenuItem(label="Workspace")
        menubar.append(item)
        item.show()
        item.set_submenu(winmenu)

        w = gtk.MenuItem("Add Workspace")
        winmenu.append(w)
        w.connect("activate", lambda w: self.gui_add_ws())

        # create a Option pulldown menu, and add it to the menu bar
        ## optionmenu = gtk.Menu()
        ## item = gtk.MenuItem(label="Option")
        ## menubar.append(item)
        ## item.show()
        ## item.set_submenu(optionmenu)

        helpmenu = gtk.Menu()
        item = gtk.MenuItem(label="Help")
        menubar.append(item)
        item.show()
        item.set_submenu(helpmenu)

        w = gtk.MenuItem("About")
        helpmenu.append(w)
        w.connect("activate", lambda w: self.banner(raiseTab=True))

        menuholder.show_all()

    def add_dialogs(self):
        self.filesel = FileSelection.FileSelection(action=gtk.FILE_CHOOSER_ACTION_OPEN)
        
    def add_statusbar(self, statusholder):
        ## lbl = gtk.Label('')
        ## lbl.set_justify(gtk.JUSTIFY_CENTER)
        lbl = gtk.Statusbar()
        if not gtksel.have_gtk3:
            lbl.set_has_resize_grip(True)
        self.w.ctx_id = None
        self.w.status = lbl
        statusholder.pack_end(self.w.status, expand=False, fill=True,
                              padding=2)
        statusholder.show_all()

    def window_state_change(self, window, event):
        self.window_is_fullscreen = bool(
            gtk.gdk.WINDOW_STATE_FULLSCREEN & event.new_window_state)

    def fullscreen(self):
        self.w.root.fullscreen()
            
    def normalsize(self):
        self.w.root.unfullscreen()
            
    def maximize(self):
        self.w.root.maximize()
            
    def toggle_fullscreen(self):
        if not self.window_is_fullscreen:
            self.w.root.fullscreen()
        else:
            self.w.root.unfullscreen()

    def add_operation(self, title):
        menu = self.w.operation
        item = gtk.MenuItem(label=title)
        menu.append(item)
        item.show()
        item.connect_object ("activate", self.start_operation_cb, title)
        self.operations.append(title)

       
    ####################################################
    # THESE METHODS ARE CALLED FROM OTHER MODULES & OBJECTS
    ####################################################

    def set_titlebar(self, text):
        self.w.root.set_title("Ginga: %s" % text)
        
    def build_readout(self):
        readout = Readout.Readout(-1, 20)
        readout.set_font(self.font11)
        return readout

    def getDrawClass(self, drawtype):
        drawtype = drawtype.lower()
        return ImageViewCanvasTypesGtk.drawCatalog[drawtype]
    
    def getDrawClasses(self):
        return Bunch.Bunch(ImageViewCanvasTypesGtk.drawCatalog,
                           caseless=True)
        
    def build_colorbar(self):
        cbar = ColorBar.ColorBar(self.logger)
        cbar.set_cmap(self.cm)
        cbar.set_imap(self.im)
        cbar.show()
        self.colorbar = cbar
        self.add_callback('active-image', self.change_cbar, cbar)
        cbar.add_callback('motion', self.cbar_value_cb)

        fr = gtk.Frame()
        fr.set_shadow_type(gtk.SHADOW_ETCHED_OUT)
        fr.add(cbar)
        return fr
    
    def build_viewpane(self, settings, rgbmap=None):
        fi = ImageViewCanvasGtk.ImageViewCanvas(logger=self.logger,
                                                rgbmap=rgbmap,
                                                settings=settings)
        fi.add_callback('motion', self.motion_cb)
        fi.add_callback('cursor-down', self.force_focus_cb)
        fi.add_callback('key-press', self.keypress)
        fi.add_callback('drag-drop', self.dragdrop)
        for name in ['cuts']:
            settings.getSetting(name).add_callback('set',
                               self.change_range_cb, fi, self.colorbar)
        fi.enable_auto_orient(True)
        fi.enable_draw(False)

        bd = fi.get_bindings()
        bd.enable_pan(True)
        bd.enable_zoom(True)
        bd.enable_cuts(True)
        bd.enable_flip(True)
        bd.enable_rotate(True)
        bd.enable_cmap(True)
        
        rgbmap = fi.get_rgbmap()
        rgbmap.add_callback('changed', self.rgbmap_cb, fi)
        fi.set_bg(0.2, 0.2, 0.2)
        fi.ui_setActive(True)
        return fi

    def add_viewer(self, name, settings,
                   use_readout=False, workspace=None):

        vbox = gtk.VBox(spacing=0)
        
        fi = self.build_viewpane(settings)
        iw = fi.get_widget()

        fi.add_callback('focus', self.focus_cb, name)
        vbox.pack_start(iw, padding=0, fill=True,
                               expand=True)
        fi.set_name(name)

        if use_readout:
            readout = self.build_readout()
            # TEMP: hack
            readout.fitsimage = fi
            fi.add_callback('image-set', self.readout_config, readout)
            self.add_callback('field-info', self.readout_cb, readout, name)
            rw = readout.get_widget()
            vbox.pack_start(rw, padding=0, fill=True, expand=False)
        else:
            readout = None
        vbox.show_all()

        # Add a page to the specified notebook
        if not workspace:
            workspace = 'channels'

        bnch = Bunch.Bunch(fitsimage=fi, view=iw, container=vbox,
                           readout=readout, workspace=workspace)

        self.ds.add_tab(workspace, vbox, 1, name, data=bnch)

        self.update_pending()
        return bnch

    def build_fullscreen(self):
        w = self.w.fscreen
        self.w.fscreen = None
        if w != None:
            w.destroy()
            return
        
        # Get image from current focused channel
        chinfo = self.get_channelInfo()
        fitsimage = chinfo.fitsimage
        settings = fitsimage.get_settings()
        rgbmap = fitsimage.get_rgbmap()

        root = gtk.Window(gtk.WINDOW_TOPLEVEL)
        fi = self.build_viewpane(settings, rgbmap=rgbmap)
        iw = fi.get_widget()
        root.add(iw)

        image = fitsimage.get_image()
        if image == None:
            return
        fi.set_image(image)

        # Copy attributes of the frame
        fitsimage.copy_attributes(fi,
                                  [#'transforms',
                                   #'cutlevels',
                                   'rgbmap'],
                                  redraw=False)

        root.fullscreen()
        self.w.fscreen = root
        root.show()

    def mktextwidget(self, text):
        sw = gtk.ScrolledWindow()
        sw.set_border_width(2)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        tw = gtk.TextView()
        buf = tw.get_buffer()
        buf.set_text(text)
        tw.set_editable(False)
        tw.set_wrap_mode(gtk.WRAP_NONE)
        tw.set_left_margin(4)
        tw.set_right_margin(4)
        tw.modify_font(self.font11)
        sw.add(tw)
        sw.show_all()
        return Bunch.Bunch(widget=sw, textw=tw, buf=buf)

    def start_global_plugin(self, pluginName):

        pInfo = self.gpmon.getPluginInfo(pluginName)
        spec = pInfo.spec

        vbox = None
        try:
            wsName = spec.get('ws', None)
            if wsName and hasattr(pInfo.obj, 'build_gui'):
                tabName = spec.get('tab', pInfo.name)
                pInfo.tabname = tabName

                vbox = gtk.VBox(spacing=2)
                vbox.set_border_width(0)
        
                pInfo.obj.build_gui(vbox)
                vbox.show_all()

            pInfo.obj.start()

        except Exception, e:
            errmsg = "Failed to load global plugin '%s': %s" % (
                pluginName, str(e))
            try:
                (type, value, tb) = sys.exc_info()
                tb_str = "\n".join(traceback.format_tb(tb))

            except Exception, e:
                tb_str = "Traceback information unavailable."

            self.logger.error(errmsg)
            self.logger.error("Traceback:\n%s" % (tb_str))
            if vbox:
                bnch = self.mktextwidget(errmsg + '\n' + tb_str)
                vbox.pack_start(bnch.widget, fill=True, expand=True)
                vbox.show_all()

        if vbox:
            pInfo.widget = vbox
            self.ds.add_tab(wsName, vbox, 2, tabName)

    def stop_global_plugin(self, pluginName):
        self.logger.debug("Attempting to stop plugin '%s'" % (pluginName))
        try:
            pluginObj = self.gpmon.getPlugin(pluginName)
            pluginObj.stop()
        except Exception, e:
            self.logger.error("Failed to stop global plugin '%s': %s" % (
                pluginName, str(e)))

    def gui_add_channel(self, chname=None):
        if not chname:
            self.chncnt += 1
            chname = "Image%d" % self.chncnt
        lbl = gtk.Label('New channel name:')
        ent = gtk.Entry()
        ent.set_text(chname)
        ent.set_activates_default(True)
        lbl2 = gtk.Label('Workspace:')
        cbox = gtk.combo_box_new_text()
        names = self.ds.get_wsnames()
        try:
            idx = names.index(self._lastwsname)
        except:
            idx = 0
        for name in names:
            cbox.append_text(name)
        cbox.set_active(idx)
        dialog = GtkHelp.Dialog("Add Channel",
                                gtk.DIALOG_DESTROY_WITH_PARENT,
                                [['Cancel', 0], ['Ok', 1]],
                                lambda w, rsp: self.add_channel_cb(w, rsp, ent, cbox, names))
        box = dialog.get_content_area()
        box.pack_start(lbl, True, False, 0)
        box.pack_start(ent, True, True, 0)
        box.pack_start(lbl2, True, False, 0)
        box.pack_start(cbox, True, True, 0)
        dialog.show_all()
        
    def gui_add_channels(self):
        captions = (('Prefix', 'entry'),
                    ('Number', 'spinbutton'),
                    ('Workspace', 'combobox'),
                    #('Base on Channel', 'combobox'),
                    #('Copy Settings', 'button'),
                    #'Share Settings', 'button'),
                    #('Cancel', 'button', 'Ok', 'button')
                    )
        w, b = GtkHelp.build_info(captions)
        b.prefix.set_text("Image")
        adj = b.number.get_adjustment()
        lower = 1
        upper = 12
        adj.configure(lower, lower, upper, 1, 1, 0)
        adj.set_value(lower)
        
        cbox = b.workspace
        names = self.ds.get_wsnames()
        try:
            idx = names.index('channels')
        except:
            idx = 0
        for name in names:
            cbox.append_text(name)
        cbox.set_active(idx)

        ## cbox = b.base_on_channel
        ## names = self.get_channelNames()
        ## for name in names:
        ##     cbox.append_text(name)
            
        ## prefs = self.prefs.getSettings('channel_Image')
        ## d = prefs.getDict()

        ## cbox = b.copy_settings
        ## for name in d.keys():
        ##     cbox.append_text(name)
            
        ## cbox = b.share_settings
        ## for name in d.keys():
        ##     cbox.append_text(name)
            
        dialog = GtkHelp.Dialog("Add Channels",
                                gtk.DIALOG_DESTROY_WITH_PARENT,
                                [['Cancel', 0], ['Ok', 1]],
                                lambda w, rsp: self.add_channels_cb(w, rsp,
                                                                    b, names))
        box = dialog.get_content_area()
        box.pack_start(w, True, True, 0)
        dialog.show_all()
        
    def gui_add_ws(self):
        captions = (('Workspace name', 'entry'),
                    ('Workspace type', 'combobox'),
                    ('In workspace', 'combobox'),
                    ('Channel prefix', 'entry'),
                    ('Number of channels', 'spinbutton'))
        w, b = GtkHelp.build_info(captions)

        self.wscount += 1
        wsname = "ws%d" % (self.wscount)
        b.workspace_name.set_text(wsname)

        cbox = b.workspace_type
        cbox.append_text("Tabs")
        cbox.append_text("Grid")
        cbox.set_active(0)

        cbox = b.in_workspace
        names = self.ds.get_wsnames()
        names.insert(0, 'top level')
        try:
            idx = names.index('top level')
        except:
            idx = 0
        for name in names:
            cbox.append_text(name)
        cbox.set_active(idx)

        b.channel_prefix.set_text("Image")
        adj = b.number_of_channels.get_adjustment()
        lower = 0
        upper = 12
        adj.configure(lower, lower, upper, 1, 1, 0)
        adj.set_value(1)

        dialog = GtkHelp.Dialog("Add Workspace",
                                gtk.DIALOG_DESTROY_WITH_PARENT,
                                [['Cancel', 0], ['Ok', 1]],
                                lambda w, rsp: self.new_ws_cb(w, rsp, b, names))
        box = dialog.get_content_area()
        box.pack_start(w, expand=True, fill=True)
        dialog.show_all()
        
    def new_ws_cb(self, w, rsp, b, names):
        wsname = b.workspace_name.get_text()
        idx = b.workspace_type.get_active()
        if rsp == 0:
            w.destroy()
            return
        d = { 0: 'nb', 1: 'grid', }
        wstype = d[idx]

        idx = b.in_workspace.get_active()
        inSpace = names[idx]
        
        self.add_workspace(wsname, wstype, inSpace=inSpace)

        chpfx = b.channel_prefix.get_text()
        num = int(b.number_of_channels.get_value())

        w.destroy()
        if num <= 0:
            return

        chbase = self.chncnt
        self.chncnt += num
        for i in xrange(num):
            chname = "%s%d" % (chpfx, chbase+i)
            self.add_channel(chname, workspace=wsname)
        
        return True
        
    def gui_delete_channel(self):
        chinfo = self.get_channelInfo()
        chname = chinfo.name
        lbl = gtk.Label("Really delete channel '%s' ?" % (chname))
        dialog = GtkHelp.Dialog("Delete Channel",
                                gtk.DIALOG_DESTROY_WITH_PARENT,
                                [['Cancel', 0], ['Ok', 1]],
                                lambda w, rsp: self.delete_channel_cb(w, rsp, chname))
        box = dialog.get_content_area()
        box.pack_start(lbl, True, False, 0)
        dialog.show_all()
        
    def gui_load_file(self, initialdir=None):
        #self.start_operation('FBrowser')
        self.filesel.popup("Load FITS file", self.load_file,
                           initialdir=initialdir)
        
    def statusMsg(self, format, *args):
        if not format:
            s = ''
        else:
            s = format % args

        ## self.w.status.set_text(s)
        try:
            self.w.status.remove_all(self.w.ctx_id)
        except:
            pass
        self.w.ctx_id = self.w.status.get_context_id('status')
        self.w.status.push(self.w.ctx_id, s)
        
        # remove message in about 10 seconds
        if self.statustask:
            gobject.source_remove(self.statustask)
        self.statustask = gobject.timeout_add(10000, self.statusMsg, '')


    def setPos(self, x, y):
        self.w.root.move(x, y)

    def setSize(self, wd, ht):
        self.w.root.resize(wd, ht)

    def setGeometry(self, geometry):
        # Painful translation of X window geometry specification
        # into correct calls to Qt
        coords = geometry.replace('+', ' +')
        coords = coords.replace('-', ' -')
        coords = coords.split()
        if 'x' in coords[0]:
            # spec includes dimensions
            dim = coords[0]
            coords = coords[1:]
        else:
            # spec is position only
            dim = None

        if dim != None:
            # user specified dimensions
            dim = map(int, dim.split('x'))
            self.setSize(*dim)

        if len(coords) > 0:
            # user specified position
            coords = map(int, coords)
            self.setPos(*coords)

    def getFont(self, fontType, pointSize):
        fontFamily = self.settings.get(fontType)
        font = pango.FontDescription('%s %d' % (fontFamily, pointSize))
        return font
    
    ####################################################
    # CALLBACKS
    ####################################################
    
    def delete_event(self, widget, event, data=None):
        """Someone is trying to close the application."""
        self.quit(widget)
        return True

    def quit(self, widget):
        """Quit the application.
        """
        self.stop()
        self.ev_quit.set()
        return True

    def channel_select_cb(self, w):
        index = w.get_active()
        chname = self.channelNames[index]
        self.change_channel(chname)
        
    def add_channel_cb(self, w, rsp, ent, cbox, names):
        chname = ent.get_text()
        idx = cbox.get_active()
        wsname = names[idx]
        # save name for next add
        self._lastwsname = wsname
        w.destroy()
        if rsp == 0:
            return
        self.add_channel(chname, workspace=wsname)
        return True
        
    def add_channels_cb(self, w, rsp, b, names):
        chpfx = b.prefix.get_text()
        idx = b.workspace.get_active()
        wsname = names[idx]
        num = int(b.number.get_value())
        w.destroy()
        if (rsp == 0) or (num <= 0):
            return

        chbase = self.chncnt
        self.chncnt += num
        for i in xrange(num):
            chname = "%s%d" % (chpfx, chbase+i)
            self.add_channel(chname, workspace=wsname)
        return True
        
    def delete_channel_cb(self, w, rsp, chname):
        w.destroy()
        if rsp == 0:
            return
        self.delete_channel(chname)
        return True
        
    def invoke_op_cb(self, button, event):
        menu = self.w.operation
        menu.show_all()
        if gtksel.have_gtk3:
            menu.popup(None, None, None, None, event.button, event.time)
        else:
            menu.popup(None, None, None, event.button, event.time)
        
    def start_operation_cb(self, name):
        index = self.w.channel.get_active()
        model = self.w.channel.get_model()
        chname = model[index][0]
        return self.start_operation_channel(chname, name, None)
        
    def page_switch_cb(self, ds, name, data):
        if data == None:
            return
        
        fitsimage = data.fitsimage
        if fitsimage != self.getfocus_fitsimage():
            chname = self.get_channelName(fitsimage)
            self.logger.debug("Active channel switch to '%s'" % (
                chname))
            self.change_channel(chname, raisew=False)

        return True

# END
