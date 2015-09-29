#
# GingaQt.py -- Qt display handler for the Ginga reference viewer.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
# stdlib imports
import sys, os
import traceback
import platform
import time

# GUI imports
from ginga.qtw.QtHelp import QtGui, QtCore, QFont, \
     QImage, QIcon, QPixmap, MenuBar
from ginga.qtw import Widgets

# Local application imports
from ginga import cmap, imap
from ginga.misc import Bunch
from ginga.canvas.types.layer import DrawingCanvas
from ginga.util.six.moves import map, zip

moduleHome = os.path.split(sys.modules[__name__].__file__)[0]
sys.path.insert(0, moduleHome)
childDir = os.path.join(moduleHome, 'plugins')
sys.path.insert(0, childDir)

from ginga.qtw import ColorBar, Readout, PluginManagerQt, \
     QtHelp, QtMain, ImageViewCanvasQt

icon_path = os.path.abspath(os.path.join(moduleHome, '..', 'icons'))
rc_file = os.path.join(moduleHome, "qt_rc")


class GingaViewError(Exception):
    pass

class GingaView(QtMain.QtMain):

    def __init__(self, logger, ev_quit):
        # call superclass constructors--sets self.app
        QtMain.QtMain.__init__(self, logger=logger, ev_quit=ev_quit)
        if os.path.exists(rc_file):
            self.app.setStyleSheet(rc_file)

        # defaults for height and width
        #self.default_height = min(900, self.screen_ht - 100)
        #self.default_width  = min(1600, self.screen_wd)

        self.w = Bunch.Bunch()
        self.iconpath = icon_path
        self._lastwsname = 'channels'
        self.layout = None
        self._lsize = None
        self._rsize = None

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
        QtGui.QToolTip.setFont(self.font11)

        self.ds = QtHelp.Desktop()
        self.ds.make_desktop(self.layout, widgetDict=self.w)
        # TEMP: FIX ME!
        self.gpmon.ds = self.ds

        for root in self.ds.toplevels:
            # add delete/destroy callbacks
            ## root.connect(root, QtCore.SIGNAL('closeEvent()'),
            ##              self.quit)
            #root.setApp(self)
            root.setWindowTitle("Ginga")
        self.ds.add_callback('all-closed', self.quit)

        self.w.root = root
        self.w.fscreen = None

        # Create main (center) FITS image pane
        self.w.vbox = self.w['main'].layout()
        self.w.vbox.setSpacing(0)
        self.w.mnb = self.w['channels']
        if isinstance(self.w.mnb, QtGui.QMdiArea):
            self.w.mnb.subWindowActivated.connect(self.page_switch_mdi_cb)
            self.w.mnb.set_mode('tabs')
        else:
            self.w.mnb.currentChanged.connect(self.page_switch_cb)

        # readout
        if self.settings.get('share_readout', True):
            self.readout = self.build_readout()
            self.add_callback('field-info', self.readout_cb, self.readout, None)
            rw = self.readout.get_widget()
            self.w.vbox.addWidget(rw, stretch=0)

        # bottom buttons
        plw = QtGui.QWidget()
        hbox = QtGui.QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(2)
        plw.setLayout(hbox)

        cbox1 = QtHelp.ComboBox()
        self.w.channel = cbox1
        cbox1.setToolTip("Select a channel")
        cbox1.activated.connect(self.channel_select_cb)
        hbox.addWidget(cbox1, stretch=0)

        opmenu = QtGui.QMenu()
        self.w.operation = opmenu
        btn = QtGui.QPushButton("Operation")
        btn.clicked.connect(self.invoke_op_cb)
        btn.setToolTip("Invoke operation")
        self.w.opbtn = btn
        hbox.addWidget(btn, stretch=0)

        w = QtGui.QWidget()
        self.w.optray = QtGui.QHBoxLayout()
        self.w.optray.setContentsMargins(0, 0, 0, 0)
        self.w.optray.setSpacing(2)
        w.setLayout(self.w.optray)
        hbox.addWidget(w, stretch=1, alignment=QtCore.Qt.AlignLeft)

        self.w.vbox.addWidget(plw, stretch=0)

        # Add colormap bar
        cbar = self.build_colorbar()
        self.w.vbox.addWidget(cbar, stretch=0)

        menuholder = self.w['menu']
        # NOTE: menubar is a ginga.Widgets wrapper
        self.w.menubar = self.add_menus(menuholder)

        self.add_dialogs()
        statusholder = self.w['status']
        self.add_statusbar(statusholder)

        self.w.root.show()

    def getPluginManager(self, logger, fitsview, ds, mm):
        return PluginManagerQt.PluginManager(logger, fitsview, ds, mm)

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

        menubar_w = menubar.get_widget()
        # NOTE: Special hack for Mac OS X, otherwise the menus
        # do not get added to the global OS X menu
        macos_ver = platform.mac_ver()[0]
        if len(macos_ver) > 0:
            self.w['top'].layout().addWidget(menubar_w, stretch=0)
        else:
            holder.layout().addWidget(menubar_w, stretch=1)

        # create a File pulldown menu, and add it to the menu bar
        filemenu = menubar.add_name("File")

        item = filemenu.add_name("Load Image")
        item.add_callback('activated', lambda *args: self.gui_load_file())

        item = filemenu.add_name("Remove Image")
        item.add_callback("activated", lambda *args: self.remove_current_image())

        filemenu.add_separator()

        item = filemenu.add_name("Quit")
        item.add_callback('activated', lambda *args: self.windowClose())

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

        item = wsmenu.add_name("Take Tab")
        item.add_callback('activated',
                          lambda *args: self.ds.take_tab_cb(self.w.mnb,
                                                                 args))

        if isinstance(self.w.mnb, QtGui.QMdiArea):
            item = wsmenu.add_name("Panes as Tabs")
            item.add_callback(lambda *args: self.tabstoggle_cb())
            item.get_widget().setCheckable(True)
            is_tabs = (self.w.mnb.get_mode() == 'tabs')
            item.get_widget().setChecked(is_tabs)

            item = wsmenu.add_name("Tile Panes")
            item.add_callback('activated', lambda *args: self.tile_panes_cb())

            item = wsmenu.add_name("Cascade Panes")
            item.add_callback(lambda *args: self.cascade_panes_cb())

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

    def add_dialogs(self):
        filesel = QtGui.QFileDialog(self.w.root)
        filesel.setFileMode(QtGui.QFileDialog.ExistingFile)
        filesel.setViewMode(QtGui.QFileDialog.Detail)
        self.filesel = filesel

    def add_plugin_menu(self, name):
        # NOTE: self.w.menu_plug is a ginga.Widgets wrapper
        item = self.w.menu_plug.add_name("Start %s" % (name))
        item.add_callback('activated',
                          lambda *args: self.start_global_plugin(name))

    def add_statusbar(self, holder):
        self.w.status = QtGui.QStatusBar()
        holder.layout().addWidget(self.w.status, stretch=1)

    def fullscreen(self):
        self.w.root.showFullScreen()

    def normalsize(self):
        self.w.root.showNormal()

    def maximize(self):
        self.w.root.showMaximized()

    def toggle_fullscreen(self):
        if not self.w.root.isFullScreen():
            self.w.root.showFullScreen()
        else:
            self.w.root.showNormal()

    def build_fullscreen(self):
        w = self.w.fscreen
        self.w.fscreen = None
        if w is not None:
            w.destroy()
            return

        # Get image from current focused channel
        chinfo = self.get_channelInfo()
        fitsimage = chinfo.fitsimage
        settings = fitsimage.get_settings()
        rgbmap = fitsimage.get_rgbmap()

        root = QtHelp.TopLevel()
        vbox = QtGui.QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)
        root.setLayout(vbox)

        fi = self.build_viewpane(settings, rgbmap=rgbmap)
        iw = fi.get_widget()
        vbox.addWidget(iw, stretch=1)

        # Get image from current focused channel
        image = fitsimage.get_image()
        if image is None:
            return
        fi.set_image(image)

        # Copy attributes of the frame
        fitsimage.copy_attributes(fi,
                                  [#'transforms',
                                   #'cutlevels',
                                   'rgbmap'])

        root.showFullScreen()
        self.w.fscreen = root

    def add_operation(self, title):
        opmenu = self.w.operation
        item = QtGui.QAction(title, opmenu)
        item.triggered.connect(lambda: self.start_operation_cb(title))
        opmenu.addAction(item)
        self.operations.append(title)

    ####################################################
    # THESE METHODS ARE CALLED FROM OTHER MODULES & OBJECTS
    ####################################################

    def make_button(self, name, wtyp, icon=None, tooltip=None):
        picon = None
        if icon:
            iconfile = os.path.join(self.iconpath, '%s.png' % icon)
            try:
                image = QImage(iconfile)
                pixmap = QPixmap.fromImage(image)
                picon = QIcon(pixmap)
                qsize = QtCore.QSize(24, 24)
            except Exception as e:
                self.logger.error("Error loading icon '%s': %s" % (
                    iconfile, str(e)))

        if wtyp == 'button':
            if picon:
                w = Widgets.Button()
                _w = w.get_widget()
                _w.setIconSize(qsize)
                _w.setIcon(picon)
            else:
                w = Widgets.Button(name)
        elif wtyp == 'toggle':
            if picon:
                w = Widgets.ToggleButton()
                _w = w.get_widget()
                _w.setIconSize(qsize)
                _w.setIcon(picon)
            else:
                w = Widgets.ToggleButton()

        return w

    def set_titlebar(self, text):
        self.w.root.setWindowTitle("Ginga: %s" % text)

    def build_readout(self):
        readout = Readout.Readout(-1, 20)
        # NOTE: Special hack for Mac OS X, otherwise the font on the readout
        # is too small
        macos_ver = platform.mac_ver()[0]
        if len(macos_ver) > 0:
            readout.set_font(self.font14)
        else:
            readout.set_font(self.font11)
        return readout

    def build_colorbar(self):
        cbar = ColorBar.ColorBar(self.logger)
        cbar.set_cmap(self.cm)
        cbar.set_imap(self.im)
        cbar.resize(700, 15)
        #cbar.show()
        self.colorbar = cbar
        self.add_callback('active-image', self.change_cbar, cbar)
        cbar.add_callback('motion', self.cbar_value_cb)

        fr = QtGui.QFrame()
        fr.setContentsMargins(0, 0, 0, 0)
        layout = QtGui.QHBoxLayout()
        fr.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        fr.setFrameStyle(QtGui.QFrame.Box | QtGui.QFrame.Raised)
        layout.addWidget(cbar, stretch=1)
        return fr

    def build_viewpane(self, settings, rgbmap=None):
        # instantiate bindings loaded with users preferences
        bclass = ImageViewCanvasQt.ImageViewCanvas.bindingsClass
        bindprefs = self.prefs.createCategory('bindings')
        bd = bclass(self.logger, settings=bindprefs)

        fi = ImageViewCanvasQt.ImageViewCanvas(logger=self.logger,
                                               rgbmap=rgbmap,
                                               settings=settings,
                                               bindings=bd)
        canvas = DrawingCanvas()
        canvas.enable_draw(False)
        fi.set_canvas(canvas)

        fi.set_follow_focus(settings.get('follow_focus', True))
        fi.enable_auto_orient(True)

        fi.add_callback('motion', self.motion_cb)
        fi.add_callback('cursor-down', self.force_focus_cb)
        fi.add_callback('key-press', self.keypress)
        fi.add_callback('drag-drop', self.dragdrop)
        fi.ui_setActive(True)

        for name in ['cuts']:
            settings.getSetting(name).add_callback('set',
                               self.change_range_cb, fi, self.colorbar)

        bd = fi.get_bindings()
        bd.enable_all(True)

        rgbmap = fi.get_rgbmap()
        rgbmap.add_callback('changed', self.rgbmap_cb, fi)
        fi.set_bg(0.2, 0.2, 0.2)
        return fi

    def add_viewer(self, name, settings,
                   use_readout=False, workspace=None):

        vwidget = QtGui.QWidget()
        vbox = QtGui.QVBoxLayout()
        vbox.setContentsMargins(1, 1, 1, 1)
        vbox.setSpacing(0)
        vwidget.setLayout(vbox)

        fi = self.build_viewpane(settings)
        iw = fi.get_widget()

        fi.add_callback('focus', self.focus_cb, name)
        vbox.addWidget(iw, stretch=1)
        fi.set_name(name)

        if use_readout:
            readout = self.build_readout()
            # TEMP: hack
            readout.fitsimage = fi
            fi.add_callback('image-set', self.readout_config, readout)
            self.add_callback('field-info', self.readout_cb, readout, name)
            rw = readout.get_widget()
            rw.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed,
                                               QtGui.QSizePolicy.Fixed))
            vbox.addWidget(rw, stretch=0, alignment=QtCore.Qt.AlignLeft)
        else:
            readout = None

        # Add a page to the specified notebook
        if not workspace:
            workspace = 'channels'
        self.ds.add_tab(workspace, vwidget, 1, name)

        self.update_pending()
        bnch = Bunch.Bunch(fitsimage=fi, view=iw, container=vwidget,
                           readout=readout, workspace=workspace)
        return bnch


    def gui_add_channel(self, chname=None):
        if not chname:
            self.chncnt += 1
            chname = "Image%d" % self.chncnt
        lbl = QtGui.QLabel('New channel name:')
        ent = QtGui.QLineEdit()
        ent.setText(chname)
        lbl2 = QtGui.QLabel('Workspace:')
        cbox = QtHelp.ComboBox()
        names = self.ds.get_wsnames()
        try:
            idx = names.index(self._lastwsname)
        except:
            idx = 0
        for name in names:
            cbox.append_text(name)
        cbox.setCurrentIndex(idx)
        dialog = QtHelp.Dialog("Add Channel",
                               0,
                               [['Cancel', 0], ['Ok', 1]],
                               lambda w, rsp: self.add_channel_cb(w, rsp, ent, cbox, names))
        box = dialog.get_content_area()
        layout = QtGui.QVBoxLayout()
        box.setLayout(layout)

        layout.addWidget(lbl, stretch=0)
        layout.addWidget(ent, stretch=0)
        layout.addWidget(lbl2, stretch=0)
        layout.addWidget(cbox, stretch=0)
        dialog.show()

    def gui_add_channels(self):
        captions = (('Prefix', 'entry'),
                    ('Number', 'spinbutton'),
                    ('Workspace', 'combobox'),
                    )
        w, b = QtHelp.build_info(captions)
        b.prefix.setText("Image")
        b.number.setRange(1, 12)
        b.number.setSingleStep(1)
        b.number.setValue(1)

        cbox = b.workspace
        names = self.ds.get_wsnames()
        try:
            idx = names.index('channels')
        except:
            idx = 0
        for name in names:
            cbox.append_text(name)
        cbox.setCurrentIndex(idx)

        dialog = QtHelp.Dialog("Add Channels",
                               0,
                               [['Cancel', 0], ['Ok', 1]],
                               lambda w, rsp: self.add_channels_cb(w, rsp,
                                                                   b, names))
        box = dialog.get_content_area()
        layout = QtGui.QVBoxLayout()
        box.setLayout(layout)

        layout.addWidget(w, stretch=1)
        dialog.show()

    def gui_delete_channel(self):
        chinfo = self.get_channelInfo()
        chname = chinfo.name
        lbl = QtGui.QLabel("Really delete channel '%s' ?" % (chname))
        dialog = QtHelp.Dialog("Delete Channel",
                               0,
                               [['Cancel', 0], ['Ok', 1]],
                               lambda w, rsp: self.delete_channel_cb(w, rsp, chname))
        box = dialog.get_content_area()
        layout = QtGui.QVBoxLayout()
        box.setLayout(layout)
        layout.addWidget(lbl, stretch=0)
        dialog.show()

    def gui_add_ws(self):
        captions = (('Workspace name', 'entry'),
                    ('Workspace type', 'combobox'),
                    ('In workspace', 'combobox'),
                    ('Channel prefix', 'entry'),
                    ('Number of channels', 'spinbutton'),
                    ('Share settings', 'entry'),
                    )
        w, b = QtHelp.build_info(captions)

        self.wscount += 1
        wsname = "ws%d" % (self.wscount)
        b.workspace_name.setText(wsname)
        b.share_settings.setMaxLength(60)

        cbox = b.workspace_type
        cbox.append_text("Tabs")
        cbox.append_text("Grid")
        cbox.append_text("MDI")
        cbox.setCurrentIndex(1)

        cbox = b.in_workspace
        names = self.ds.get_wsnames()
        names.insert(0, 'top level')
        try:
            idx = names.index('channels')
        except:
            idx = 0
        for name in names:
            cbox.append_text(name)
        cbox.setCurrentIndex(idx)

        b.channel_prefix.setText("Image")
        spnbtn = b.number_of_channels
        spnbtn.setRange(0, 12)
        spnbtn.setSingleStep(1)
        spnbtn.setValue(4)

        dialog = QtHelp.Dialog("Add Workspace",
                               0,
                               [['Cancel', 0], ['Ok', 1]],
                               lambda w, rsp: self.new_ws_cb(w, rsp, b, names))
        box = dialog.get_content_area()
        layout = QtGui.QVBoxLayout()
        box.setLayout(layout)

        layout.addWidget(w, stretch=1)
        dialog.show()

    def new_ws_cb(self, w, rsp, b, names):
        w.close()
        wsname = str(b.workspace_name.text())
        idx = b.workspace_type.currentIndex()
        if rsp == 0:
            return
        d = { 0: 'nb', 1: 'grid', 2: 'mdi' }
        wstype = d[idx]
        idx = b.in_workspace.currentIndex()
        inSpace = names[idx]

        self.add_workspace(wsname, wstype, inSpace=inSpace)

        chpfx = b.channel_prefix.text()
        num = int(b.number_of_channels.value())
        if num <= 0:
            return

        # Create a settings template to copy settings from
        settings_template = self.prefs.getSettings('channel_Image')
        name = "channel_template_%f" % (time.time())
        settings = self.prefs.createCategory(name)
        settings_template.copySettings(settings)
        share_list = b.share_settings.text().split()

        chbase = self.chncnt
        self.chncnt += num
        for i in range(num):
            chname = "%s%d" % (chpfx, chbase+i)
            self.add_channel(chname, workspace=wsname,
                             settings_template=settings_template,
                             settings_share=settings,
                             share_keylist=share_list)
        return True

    def gui_load_file(self, initialdir=None):
        if self.filesel.exec_():
            fileNames = list(map(str, list(self.filesel.selectedFiles())))
            self.load_file(fileNames[0])
        #self.start_operation_cb('FBrowser')

    def statusMsg(self, format, *args):
        if not format:
            s = ''
        else:
            s = format % args

        # remove message in about 10 seconds
        self.w.status.showMessage(s, 10000)


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

        if dim is not None:
            # user specified dimensions
            dim = list(map(int, dim.split('x')))
            self.setSize(*dim)

        if len(coords) > 0:
            # user specified position
            coords = list(map(int, coords))
            self.setPos(*coords)


    def collapse_pane(self, side):
        """
        Toggle collapsing the left or right panes.
        """
        # TODO: this is too tied to one configuration, need to figure
        # out how to generalize this
        hsplit = self.w['hpnl']
        sizes = hsplit.sizes()
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
        hsplit.setSizes((lsize, msize, rsize))


    def getFont(self, fontType, pointSize):
        fontFamily = self.settings.get(fontType)
        font = QFont(fontFamily, pointSize)
        return font

    ####################################################
    # CALLBACKS
    ####################################################

    def windowClose(self, *args):
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
            w.deleteLater()

    def channel_select_cb(self, index):
        if index >= 0:
            chname = self.channelNames[index]
            self.logger.debug("Channel changed, index=%d chname=%s" % (
                index, chname))
            self.change_channel(chname)

    def add_channel_cb(self, w, rsp, ent, cbox, names):
        chname = str(ent.text())
        idx = cbox.currentIndex()
        wsname = names[idx]
        w.close()
        # save name for next add
        self._lastwsname = wsname
        if rsp == 0:
            return
        self.add_channel(chname, workspace=wsname)
        return True

    def add_channels_cb(self, w, rsp, b, names):
        chpfx = b.prefix.text()
        idx = b.workspace.currentIndex()
        wsname = names[idx]
        num = int(b.number.value())
        w.close()
        if (rsp == 0) or (num <= 0):
            return

        chbase = self.chncnt
        self.chncnt += num
        for i in range(num):
            chname = "%s%d" % (chpfx, chbase+i)
            self.add_channel(chname, workspace=wsname)
        return True

    def delete_channel_cb(self, w, rsp, chname):
        w.close()
        if rsp == 0:
            return
        self.delete_channel(chname)
        return True

    def invoke_op_cb(self):
        menu = self.w.operation
        menu.popup(self.w.opbtn.mapToGlobal(QtCore.QPoint(0,0)))

    def start_operation_cb(self, name):
        index = self.w.channel.currentIndex()
        chname = str(self.w.channel.itemText(index))
        return self.start_local_plugin(chname, name, None)

    def tile_panes_cb(self):
        self.w.mnb.tileSubWindows()

    def cascade_panes_cb(self):
        self.w.mnb.cascadeSubWindows()

    def tabstoggle_cb(self, useTabs):
        if useTabs:
            self.w.mnb.setViewMode(QtGui.QMdiArea.TabbedView)
        else:
            self.w.mnb.setViewMode(QtGui.QMdiArea.SubWindowView)

    def page_switch_cb(self, index):
        self.logger.debug("index switched to %d" % (index))
        if index >= 0:
            container = self.w.mnb.widget(index)
            self.logger.debug("container is %s" % (container))

            # Find the channel that contains this widget
            chnames = self.get_channelNames()
            for chname in chnames:
                chinfo = self.get_channelInfo(chname)
                if 'container' in chinfo and (chinfo.container == container):
                    fitsimage = chinfo.fitsimage
                    if fitsimage != self.getfocus_fitsimage():
                        self.logger.debug("Active channel switch to '%s'" % (
                            chname))
                        self.change_channel(chname, raisew=False)

        return True

    def page_switch_mdi_cb(self, w):
        if w is not None:
            index = self.w.mnb.indexOf(w.widget())
            return self.page_switch_cb(index)


# END
