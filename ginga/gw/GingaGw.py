#
# GingaGw.py -- Gw display handler for the Ginga reference viewer.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
# stdlib imports
import sys, os
import platform
import glob
import traceback
import time

# GUI imports
from ginga.gw import GwHelp, GwMain, PluginManager
from ginga.gw import Widgets, Viewers, Desktop
from ginga import toolkit

# Local application imports
from ginga import cmap, imap
from ginga.misc import Bunch
from ginga.canvas.types.layer import DrawingCanvas
from ginga.util import iohelper
from ginga.util.six.moves import map, zip

moduleHome = os.path.split(sys.modules[__name__].__file__)[0]
sys.path.insert(0, moduleHome)
# pick up plugins specific to our chosen toolkit
pfx, sfx = os.path.split(moduleHome)
tkname = toolkit.get_family()
if tkname is not None:
    # TODO: this relies on a naming convention for widget directories!
    childDir = os.path.join(pfx, tkname + 'w', 'plugins')
sys.path.insert(0, childDir)

icon_path = os.path.abspath(os.path.join(moduleHome, '..', 'icons'))


class GingaViewError(Exception):
    pass

class GingaView(GwMain.GwMain, Widgets.Application):

    def __init__(self, logger, ev_quit, thread_pool):
        GwMain.GwMain.__init__(self, logger=logger, ev_quit=ev_quit,
                               app=self, thread_pool=thread_pool)
        Widgets.Application.__init__(self, logger=logger)

        self.w = Bunch.Bunch()
        self.iconpath = icon_path
        self._lastwsname = 'channels'
        self.layout = None
        self._lsize = None
        self._rsize = None

        self.filesel = None
        self.menubar = None

        # this holds registered viewers
        self.viewer_db = {}

        self.register_viewer(Viewers.CanvasView)
        self.register_viewer(Viewers.TableViewGw)


    def set_layout(self, layout):
        self.layout = layout

    def get_screen_dimensions(self):
        return (self.screen_wd, self.screen_ht)

    def build_toplevel(self):

        self.font = self.getFont('fixedFont', 12)
        self.font11 = self.getFont('fixedFont', 11)
        self.font14 = self.getFont('fixedFont', 14)
        self.font18 = self.getFont('fixedFont', 18)

        self.w.tooltips = None

        self.ds = Desktop.Desktop(self)
        self.ds.make_desktop(self.layout, widgetDict=self.w)
        # TEMP: FIX ME!
        self.gpmon.ds = self.ds

        for win in self.ds.toplevels:
            # add delete/destroy callbacks
            win.add_callback('close', self.quit)
            win.set_title("Ginga")
            root = win
        self.ds.add_callback('all-closed', self.quit)

        self.w.root = root
        self.w.fscreen = None

        # get informed about window closures in existing workspaces
        for wsname in self.ds.get_wsnames():
            ws = self.ds.get_ws(wsname)
            self.init_workspace(ws)

        if 'menu' in self.w:
            menuholder = self.w['menu']
            self.w.menubar = self.add_menus(menuholder)

        self.add_dialogs()

        if 'status' in self.w:
            statusholder = self.w['status']
            self.add_statusbar(statusholder)

        self.w.root.show()

    def get_plugin_manager(self, logger, fitsview, ds, mm):
        return PluginManager.PluginManager(logger, fitsview, ds, mm)

    def _name_mangle(self, name, pfx=''):
        newname = []
        for c in name.lower():
            if not (c.isalpha() or c.isdigit() or (c == '_')):
                newname.append('_')
            else:
                newname.append(c)
        return pfx + ''.join(newname)

    def add_menus(self, holder):

        menubar = Widgets.Menubar()
        self.menubar = menubar

        # NOTE: Special hack for Mac OS X. From the Qt documentation:
        # "If you want all windows in a Mac application to share one
        #  menu bar, you must create a menu bar that does not have a
        #  parent."
        macos_ver = platform.mac_ver()[0]
        if len(macos_ver) > 0:
            pass
        else:
            holder.add_widget(menubar, stretch=1)

        # create a File pulldown menu, and add it to the menu bar
        filemenu = menubar.add_name("File")

        item = filemenu.add_name("Load Image")
        item.add_callback('activated', lambda *args: self.gui_load_file())

        item = filemenu.add_name("Remove Image")
        item.add_callback("activated", lambda *args: self.remove_current_image())

        filemenu.add_separator()

        item = filemenu.add_name("Quit")
        item.add_callback('activated', lambda *args: self.window_close())

        # create a Channel pulldown menu, and add it to the menu bar
        chmenu = menubar.add_name("Channel")

        item = chmenu.add_name("Add Channel")
        item.add_callback('activated', lambda *args: self.gui_add_channel())

        item = chmenu.add_name("Add Channels")
        item.add_callback('activated', lambda *args: self.gui_add_channels())

        item = chmenu.add_name("Delete Channel")
        item.add_callback('activated', lambda *args: self.gui_delete_channel())

        # create a Window pulldown menu, and add it to the menu bar
        wsmenu = menubar.add_name("Workspace")

        item = wsmenu.add_name("Add Workspace")
        item.add_callback('activated', lambda *args: self.gui_add_ws())

        # # create a Option pulldown menu, and add it to the menu bar
        # optionmenu = menubar.add_name("Option")

        # create a Plugins pulldown menu, and add it to the menu bar
        plugmenu = menubar.add_name("Plugins")
        self.w.menu_plug = plugmenu

        # create a Help pulldown menu, and add it to the menu bar
        helpmenu = menubar.add_name("Help")

        item = helpmenu.add_name("About")
        item.add_callback('activated', lambda *args: self.banner(raiseTab=True))

        item = helpmenu.add_name("Documentation")
        item.add_callback('activated', lambda *args: self.help())

        return menubar

    def add_menu(self, name):
        """Add a menu with name `name` to the global menu bar.
        Returns a menu widget.
        """
        if self.menubar is None:
            raise ValueError("No menu bar configured")
        return self.menubar.add_name(name)

    def get_menu(self, name):
        """Get the menu with name `name` from the global menu bar.
        Returns a menu widget.
        """
        if self.menubar is None:
            raise ValueError("No menu bar configured")
        return self.menubar.get_menu(name)

    def add_dialogs(self):
        if hasattr(GwHelp, 'FileSelection'):
            self.filesel = GwHelp.FileSelection(self.w.root.get_widget())

    def add_plugin_menu(self, name):
        # NOTE: self.w.menu_plug is a ginga.Widgets wrapper
        if 'menu_plug' in self.w:
            item = self.w.menu_plug.add_name("Start %s" % (name))
            item.add_callback('activated',
                              lambda *args: self.start_global_plugin(name))

    def add_statusbar(self, holder):
        self.w.status = Widgets.StatusBar()
        holder.add_widget(self.w.status, stretch=1)

    def fullscreen(self):
        self.w.root.fullscreen()

    def normalsize(self):
        self.w.root.unfullscreen()

    def maximize(self):
        self.w.root.maximize()

    def toggle_fullscreen(self):
        if not self.w.root.is_fullscreen():
            self.w.root.fullscreen()
        else:
            self.w.root.unfullscreen()

    def build_fullscreen(self):
        w = self.w.fscreen
        self.w.fscreen = None
        if w is not None:
            w.delete()
            return

        # Get image from current focused channel
        channel = self.get_current_channel()
        viewer = channel.fitsimage
        settings = viewer.get_settings()
        rgbmap = viewer.get_rgbmap()

        root = Widgets.TopLevel()
        vbox = Widgets.VBox()
        vbox.set_border_width(0)
        vbox.set_spacing(0)
        root.add_widget(vbox, stretch=1)

        fi = self.build_viewpane(settings, rgbmap=rgbmap)
        iw = fi.get_widget()
        vbox.add_widget(iw, stretch=1)

        # Get image from current focused channel
        image = viewer.get_image()
        if image is None:
            return
        fi.set_image(image)

        # Copy attributes of the frame
        viewer.copy_attributes(fi,
                                  [#'transforms',
                                   #'cutlevels',
                                   'rgbmap'])

        root.fullscreen()
        self.w.fscreen = root

    def register_viewer(self, vclass):
        """Register a channel viewer with the reference viewer.
        `vclass` is the class of the viewer.
        """
        self.viewer_db[vclass.vname] = Bunch.Bunch(vname=vclass.vname,
                                                   vclass=vclass,
                                                   vtypes=vclass.vtypes)

    def get_viewer_names(self, dataobj):
        """Returns a list of viewer names that are registered that
        can view `dataobj`.
        """
        res = []
        for bnch in self.viewer_db.values():
            for vtype in bnch.vtypes:
                if isinstance(dataobj, vtype):
                    res.append(bnch.vname)
        return res

    def make_viewer(self, vname, channel):
        """Make a viewer whose type name is `vname` and add it to `channel`.
        """
        if not vname in self.viewer_db:
            raise ValueError("I don't know how to build a '%s' viewer" % (
                vname))

        stk_w = channel.widget
        settings = channel.settings

        bnch = self.viewer_db[vname]

        viewer = bnch.vclass(logger=self.logger,
                             settings=channel.settings)
        stk_w.add_widget(viewer.get_widget(), title=vname)

        # let the GUI respond to this widget addition
        self.update_pending()

        # let the channel object do any necessary initialization
        channel.connect_viewer(viewer)

        # finally, let the viewer do any viewer-side initialization
        viewer.initialize_channel(self, channel)

    ####################################################
    # THESE METHODS ARE CALLED FROM OTHER MODULES & OBJECTS
    ####################################################

    def set_titlebar(self, text):
        self.w.root.set_title("Ginga: %s" % text)

    def build_viewpane(self, settings, rgbmap=None, size=(1, 1)):
        # instantiate bindings loaded with users preferences
        bclass = Viewers.ImageViewCanvas.bindingsClass
        bindprefs = self.prefs.createCategory('bindings')
        bd = bclass(self.logger, settings=bindprefs)

        fi = Viewers.ImageViewCanvas(logger=self.logger,
                                     rgbmap=rgbmap,
                                     settings=settings,
                                     bindings=bd)
        fi.set_desired_size(size[0], size[1])

        canvas = DrawingCanvas()
        canvas.enable_draw(False)
        fi.set_canvas(canvas)

        fi.set_enter_focus(settings.get('enter_focus', False))
        fi.enable_auto_orient(True)

        fi.add_callback('motion', self.motion_cb)
        fi.add_callback('cursor-down', self.force_focus_cb)
        fi.set_callback('keydown-none', self.keypress)
        fi.add_callback('drag-drop', self.dragdrop)
        fi.ui_setActive(True)

        bd = fi.get_bindings()
        bd.enable_all(True)

        fi.set_bg(0.2, 0.2, 0.2)
        return fi

    def add_viewer(self, name, settings, workspace=None):

        vbox = Widgets.VBox()
        vbox.set_border_width(1)
        vbox.set_spacing(0)

        if not workspace:
            workspace = 'channels'
        w = self.ds.get_nb(workspace)

        size = (1, 1)
        if isinstance(w, Widgets.MDIWidget) and w.true_mdi:
            size = (300, 300)

        # build image viewer & widget
        fi = self.build_viewpane(settings, size=size)
        iw = Viewers.GingaViewerWidget(viewer=fi)

        stk_w = Widgets.StackWidget()
        stk_w.add_widget(iw, title='image')

        fi.add_callback('focus', self.focus_cb, name)
        vbox.add_widget(stk_w, stretch=1)
        fi.set_name(name)

        # Add the viewer to the specified workspace
        self.ds.add_tab(workspace, vbox, 1, name)

        self.update_pending()

        bnch = Bunch.Bunch(image_viewer=fi,
                           widget=stk_w, container=vbox,
                           workspace=workspace)
        return bnch


    def gui_add_channel(self, chname=None):
        chpfx = "Image"
        ws = self.get_current_workspace()
        if ws is not None:
            chpfx = ws.extdata.get('chpfx', chpfx)

        if not chname:
            chname = self.make_channel_name(chpfx)

        captions = (('New channel name:', 'label', 'channel_name', 'entry'),
                    ('In workspace:', 'label', 'workspace', 'combobox'),
                    )

        w, b = Widgets.build_info(captions, orientation='vertical')

        # populate values
        b.channel_name.set_text(chname)
        names = self.ds.get_wsnames()
        try:
            idx = names.index(self._lastwsname)
        except:
            idx = 0
        for name in names:
            b.workspace.append_text(name)
        b.workspace.set_index(idx)

        # build dialog
        dialog = Widgets.Dialog(title="Add Channel",
                                flags=0,
                                buttons=[['Cancel', 0], ['Ok', 1]],
                                parent=self.w.root)
        dialog.add_callback('activated',
                            lambda w, rsp: self.add_channel_cb(w, rsp, b, names))
        box = dialog.get_content_area()
        box.add_widget(w, stretch=0)

        self.ds.show_dialog(dialog)

    def gui_add_channels(self):

        chpfx = "Image"
        ws = self.get_current_workspace()
        if ws is not None:
            chpfx = ws.extdata.get('chpfx', chpfx)

        captions = (('Prefix:', 'label', 'Prefix', 'entry'),
                    ('Number:', 'label', 'Number', 'spinbutton'),
                    ('In workspace:', 'label', 'workspace', 'combobox'),
                    )

        w, b = Widgets.build_info(captions)
        b.prefix.set_text(chpfx)
        b.number.set_limits(1, 12, incr_value=1)
        b.number.set_value(1)

        cbox = b.workspace
        names = self.ds.get_wsnames()
        try:
            idx = names.index('channels')
        except:
            idx = 0
        for name in names:
            b.workspace.append_text(name)
        b.workspace.set_index(idx)
        dialog = Widgets.Dialog(title="Add Channels",
                                flags=0,
                                buttons=[['Cancel', 0], ['Ok', 1]],
                                parent=self.w.root)
        dialog.add_callback('activated',
                            lambda w, rsp: self.add_channels_cb(w, rsp, b, names))
        box = dialog.get_content_area()
        box.add_widget(w, stretch=0)

        self.ds.show_dialog(dialog)

    def gui_delete_channel(self, chname=None):
        channel = self.get_channel(chname)
        if (len(self.get_channel_names()) == 0) or (channel is None):
            self.show_error("There are no more channels to delete.",
                            raisetab=True)
            return

        chname = channel.name
        lbl = Widgets.Label("Really delete channel '%s' ?" % (chname))
        dialog = Widgets.Dialog(title="Delete Channel",
                                flags=0,
                                buttons=[['Cancel', 0], ['Ok', 1]],
                                parent=self.w.root)
        dialog.add_callback('activated',
                            lambda w, rsp: self.delete_channel_cb(w, rsp, chname))
        box = dialog.get_content_area()
        box.add_widget(lbl, stretch=0)

        self.ds.show_dialog(dialog)

    def gui_delete_channel_ws(self, ws):
        children = list(ws.nb.get_children())
        if len(children) == 0:
            self.show_error("No channels in this workspace to delete.",
                            raisetab=True)
            return
        idx = ws.nb.get_index()
        child = ws.nb.index_to_widget(idx)
        chname = child.extdata.tab_title
        self.gui_delete_channel(chname)

    def gui_add_ws(self):

        chpfx = "Image"
        ws = self.get_current_workspace()
        if ws is not None:
            chpfx = ws.extdata.get('chpfx', chpfx)

        captions = (('Workspace name:', 'label', 'Workspace name', 'entry'),
                    ('Workspace type:', 'label', 'Workspace type', 'combobox'),
                    ('In workspace:', 'label', 'workspace', 'combobox'),
                    ('Channel prefix:', 'label', 'Channel prefix', 'entry'),
                    ('Number of channels:', 'label', 'num_channels', 'spinbutton'),
                    ('Share settings:', 'label', 'Share settings', 'entry'),
                    )
        w, b = Widgets.build_info(captions)

        self.wscount += 1
        wsname = "ws%d" % (self.wscount)
        b.workspace_name.set_text(wsname)
        #b.share_settings.set_length(60)

        cbox = b.workspace_type
        cbox.append_text("Grid")
        cbox.append_text("Tabs")
        cbox.append_text("MDI")
        cbox.append_text("Stack")
        cbox.set_index(0)

        cbox = b.workspace
        names = self.ds.get_wsnames()
        names.insert(0, 'top level')
        try:
            idx = names.index('channels')
        except:
            idx = 0
        for name in names:
            cbox.append_text(name)
        cbox.set_index(idx)

        b.channel_prefix.set_text(chpfx)
        spnbtn = b.num_channels
        spnbtn.set_limits(0, 36, incr_value=1)
        spnbtn.set_value(4)

        dialog = Widgets.Dialog(title="Add Workspace",
                                flags=0,
                                buttons=[['Cancel', 0], ['Ok', 1]],
                                parent=self.w.root)
        dialog.add_callback('activated',
                            lambda w, rsp: self.add_ws_cb(w, rsp, b, names))
        box = dialog.get_content_area()
        box.add_widget(w, stretch=1)
        self.ds.show_dialog(dialog)

    def gui_load_file(self, initialdir=None):
        #self.start_operation('FBrowser')
        self.filesel.popup("Load File", self.load_file,
                           initialdir=initialdir)

    def status_msg(self, format, *args):
        if not format:
            s = ''
        else:
            s = format % args

        if 'status' in self.w:
            self.w.status.set_message(s)

    def set_pos(self, x, y):
        self.w.root.move(x, y)

    def set_size(self, wd, ht):
        self.w.root.resize(wd, ht)

    def set_geometry(self, geometry):
        # translation of X window geometry specification WxH+X+Y
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

        if dim is not None:
            # user specified dimensions
            dim = list(map(int, dim.split('x')))
            self.set_size(*dim)

        if len(coords) > 0:
            # user specified position
            coords = list(map(int, coords))
            self.set_pos(*coords)


    def collapse_pane(self, side):
        """
        Toggle collapsing the left or right panes.
        """
        # TODO: this is too tied to one configuration, need to figure
        # out how to generalize this
        hsplit = self.w['hpnl']
        sizes = hsplit.get_sizes()
        lsize, msize, rsize = sizes
        if self._lsize is None:
            self._lsize, self._rsize = lsize, rsize
        self.logger.debug("left=%d mid=%d right=%d" % (
            lsize, msize, rsize))
        if side == 'right':
            if rsize < 10:
                # restore pane
                rsize = self._rsize
                msize -= rsize
            else:
                # minimize pane
                self._rsize = rsize
                msize += rsize
                rsize = 0
        elif side == 'left':
            if lsize < 10:
                # restore pane
                lsize = self._lsize
                msize -= lsize
            else:
                # minimize pane
                self._lsize = lsize
                msize += lsize
                lsize = 0
        hsplit.set_sizes([lsize, msize, rsize])

    def get_font(self, fontType, pointSize):
        font_family = self.settings.get(fontType)
        return GwHelp.get_font(font_family, pointSize)

    def get_icon(self, icondir, filename):
        iconpath = os.path.join(icondir, filename)
        icon = GwHelp.get_icon(iconpath)
        return icon

    ####################################################
    # CALLBACKS
    ####################################################

    def window_close(self, *args):
        """Quit the application.
        """
        self.quit()

    def quit(self, *args):
        """Quit the application.
        """
        self.logger.info("Attempting to shut down the application...")
        self.stop()

        root = self.w.root
        self.w.root = None
        while len(self.ds.toplevels) > 0:
            w = self.ds.toplevels.pop()
            w.delete()

    def add_channel_cb(self, w, rsp, b, names):
        chname = str(b.channel_name.get_text())
        idx = b.workspace.get_index()
        if idx < 0:
            idx = 0
        wsname = names[idx]
        self.ds.remove_dialog(w)
        # save name for next add
        self._lastwsname = wsname
        if rsp == 0:
            return

        if self.has_channel(chname):
            self.show_error("Channel name already in use: '%s'" % (chname))
            return True

        self.add_channel(chname, workspace=wsname)
        return True

    def add_channels_cb(self, w, rsp, b, names):
        chpfx = b.prefix.get_text()
        idx = b.workspace.get_index()
        wsname = names[idx]
        num = int(b.number.get_value())
        self.ds.remove_dialog(w)
        if (rsp == 0) or (num <= 0):
            return

        for i in range(num):
            chname = self.make_channel_name(chpfx)
            self.add_channel(chname, workspace=wsname)
        return True

    def delete_channel_cb(self, w, rsp, chname):
        self.ds.remove_dialog(w)
        if rsp == 0:
            return
        self.delete_channel(chname)

        return True

    def init_workspace(self, ws):

        # add close handlers
        ws.add_callback('ws-close', self.workspace_closed_cb)

        if ws.nb.has_callback('page-closed'):
            ws.nb.add_callback('page-closed', self.page_closed_cb,
                                   ws.name)
        if ws.nb.has_callback('page-switch'):
            ws.nb.add_callback('page-switch', self.page_switch_cb)

        if ws.toolbar is not None:
            tb = ws.toolbar
            tb.add_separator()

            # add toolbar buttons for navigating images in the channel
            iconpath = os.path.join(self.iconpath, "up_48.png")
            btn = tb.add_action(None, iconpath=iconpath, iconsize=(18, 18))
            btn.set_tooltip("Previous object in current channel")
            btn.add_callback('activated', lambda w: self.prev_img())
            iconpath = os.path.join(self.iconpath, "down_48.png")
            btn = tb.add_action(None, iconpath=iconpath, iconsize=(18, 18))
            btn.set_tooltip("Next object in current channel")
            btn.add_callback('activated', lambda w: self.next_img())

            tb.add_separator()

            # add toolbar buttons for navigating between channels
            iconpath = os.path.join(self.iconpath, "prev_48.png")
            btn = tb.add_action(None, iconpath=iconpath, iconsize=(18, 18))
            btn.set_tooltip("Focus previous channel in this workspace")
            btn.add_callback('activated', lambda w: self.prev_channel_ws(ws))
            iconpath = os.path.join(self.iconpath, "next_48.png")
            btn = tb.add_action(None, iconpath=iconpath, iconsize=(18, 18))
            btn.set_tooltip("Focus next channel in this workspace")
            btn.add_callback('activated', lambda w: self.next_channel_ws(ws))

            tb.add_separator()

            # add toolbar buttons adding and deleting channels
            btn = tb.add_action('+')
            btn.set_tooltip("Add a channel to this workspace")
            btn.add_callback('activated',
                             lambda w: self.add_channel_auto_ws(ws))
            btn = tb.add_action('-')
            btn.set_tooltip("Delete current channel from this workspace")
            btn.add_callback('activated',
                             lambda w: self.gui_delete_channel_ws(ws))

    def add_ws_cb(self, w, rsp, b, names):
        try:
            wsname = str(b.workspace_name.get_text())
            idx = b.workspace_type.get_index()
            if rsp == 0:
                self.ds.remove_dialog(w)
                return

            try:
                nb = self.ds.get_nb(wsname)
                self.show_error("Workspace name '%s' cannot be used, sorry." % (
                    wsname))
                self.ds.remove_dialog(w)
                return

            except KeyError:
                pass

            d = { 0: 'grid', 1: 'tabs', 2: 'mdi', 3: 'stack' }
            wstype = d[idx]
            idx = b.workspace.get_index()
            in_space = names[idx]

            chpfx = b.channel_prefix.get_text().strip()
            num = int(b.num_channels.get_value())
            share_list = b.share_settings.get_text().split()

            self.ds.remove_dialog(w)

            ws = self.error_wrap(self.add_workspace, wsname, wstype,
                                 inSpace=in_space)
            ws.extdata.chpfx = chpfx

            self.init_workspace(ws)

            if num <= 0:
                return

            # Create a settings template to copy settings from
            name = "channel_template_%f" % (time.time())
            settings = self.prefs.createCategory(name)
            try:
                settings_template = self.prefs.getSettings('channel_Image')
                settings_template.copySettings(settings)
            except KeyError:
                settings_template = None

            for i in range(num):
                chname = self.make_channel_name(chpfx)
                self.add_channel(chname, workspace=wsname,
                                 settings_template=settings_template,
                                 settings_share=settings,
                                 share_keylist=share_list)
        except Exception as e:
            self.logger.error("Exception building workspace: %s" % (str(e)))

        return True

    def load_file_cb(self, w, rsp):
        w.hide()
        if rsp == 0:
            return

        filename = w.selected_files()[0]

        # Normal load
        if os.path.isfile(filename):
            self.logger.debug('Loading {0}'.format(filename))
            self.load_file(filename)

        # Fancy load (first file only)
        # TODO: If load all the matches, might get (Qt) QPainter errors
        else:
            info = iohelper.get_fileinfo(filename)
            ext = iohelper.get_hdu_suffix(info.numhdu)
            paths = ['{0}{1}'.format(fname, ext)
                     for fname in glob.iglob(info.filepath)]
            self.logger.debug(
                'Found {0} and only loading {1}'.format(paths, paths[0]))
            self.load_file(paths[0])

    def _get_channel_by_container(self, child):
        for chname in self.get_channel_names():
            channel = self.get_channel(chname)
            if channel.container == child:
                return channel
        return None

    def page_switch_cb(self, tab_w, child):
        self.logger.debug("page switched to %s" % (str(child)))

        # Find the channel that contains this widget
        channel = self._get_channel_by_container(child)
        self.logger.debug("channel: %s" % (str(channel)))
        if channel is not None:
            viewer = channel.viewer
            if viewer != self.getfocus_viewer():
                chname = channel.name
                self.logger.debug("Active channel switch to '%s'" % (
                    chname))
                self.change_channel(chname, raisew=False)

        return True

    def workspace_closed_cb(self, ws):
        self.logger.debug("workspace requests close")
        children = list(ws.nb.get_children())
        if len(children) > 0:
            self.show_error("Please close all windows in this workspace first!",
                            raisetab=True)
            return

        # TODO: this will prompt the user if we should close the workspace
        lbl = Widgets.Label("Really delete workspace '%s' ?" % (ws.name))
        dialog = Widgets.Dialog(title="Delete Workspace",
                                flags=0,
                                buttons=[['Cancel', 0], ['Ok', 1]],
                                parent=self.w.root)
        dialog.add_callback('activated',
                            lambda w, rsp: self.delete_workspace_cb(w, rsp,
                                                                    ws))
        box = dialog.get_content_area()
        box.add_widget(lbl, stretch=0)

        self.ds.show_dialog(dialog)

    def delete_workspace_cb(self, w, rsp, ws):
        self.ds.remove_dialog(w)
        if rsp == 0:
            return

        top_w = ws.extdata.get('top_w', None)
        if top_w is None:
            self.ds.remove_tab(ws.name)
        else:
            # this is a top-level window
            self.ds.remove_toplevel(top_w)

        # inform desktop we are no longer tracking this
        self.ds.delete_ws(ws.name)

        return True

    def page_closed_cb(self, widget, child, wsname):
        self.logger.debug("page closed in %s: '%s'" % (wsname, str(child)))

        channel = self._get_channel_by_container(child)
        if channel is not None:
            self.gui_delete_channel(channel.name)


    ########################################################
    ### NON-PEP8 PREDECESSORS: TO BE DEPRECATED

    getFont = get_font
    getPluginManager = get_plugin_manager
    statusMsg = status_msg

# END
