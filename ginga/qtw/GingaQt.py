#
# GingaQt.py -- Qt display handler for the Ginga FITS tool.
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
# TEMP:
import platform
        
# GUI imports
from ginga.qtw.QtHelp import QtGui, QtCore

# Local application imports
from ginga import cmap, imap
from ginga import ImageView
from ginga.misc import Bunch


moduleHome = os.path.split(sys.modules[__name__].__file__)[0]
sys.path.insert(0, moduleHome)
childDir = os.path.join(moduleHome, 'plugins')
sys.path.insert(0, childDir)

from ginga.qtw import ImageViewCanvasQt, ColorBar, Readout, PluginManagerQt, \
     QtHelp, QtMain, ImageViewCanvasTypesQt

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
        
        # Get screen size
        desktop = self.app.desktop()
        #rect = desktop.screenGeometry()
        rect = desktop.availableGeometry()
        size = rect.size()
        self.screen_wd = size.width()
        self.screen_ht = size.height()

        # defaults for height and width
        self.default_height = min(900, self.screen_ht - 100)
        self.default_width  = min(1600, self.screen_wd)

        self.w = Bunch.Bunch()
        self.iconpath = icon_path
        self._lastwsname = 'channels'
        self.layout = None

    def set_layout(self, layout):
        self.layout = layout
        
    def get_screen_dimensions(self):
        return (self.screen_wd, self.screen_ht)
        
    def build_toplevel(self):

        self.font = self.getFont('fixedFont', 12)
        self.font11 = self.getFont('fixedFont', 11)
        self.font14 = self.getFont('fixedFont', 14)

        self.w.tooltips = None
        QtGui.QToolTip.setFont(self.font11)

        self.ds = QtHelp.Desktop()
        self.ds.make_desktop(self.layout, widgetDict=self.w)
        # TEMP: FIX ME!
        self.gpmon.ds = self.ds

        for root in self.ds.toplevels:
            # add delete/destroy callbacks
            root.connect(root, QtCore.SIGNAL('closeEvent()'),
                         self.quit)
            #root.setApp(self)
            root.setWindowTitle("Ginga")
        
        self.w.root = root
        self.w.fscreen = None

        menuholder = self.w['menu']
        self.add_menus(menuholder)

        # Create main (center) FITS image pane
        self.w.vbox = self.w['main'].layout()
        self.w.vbox.setSpacing(0)
        #self.w.mnb = self.ds.make_ws(name='main', group=1, wstype='grid').nb
        ## self.w.mnb.subWindowActivated.connect(self.page_switch_mdi_cb)
        #self.w.mnb = self.ds.make_ws(name='main', group=1).nb
        self.w.mnb = self.w['channels']
        self.w.mnb.currentChanged.connect(self.page_switch_cb)
        
        # readout
        if self.settings.get('shareReadout', True):
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

        menubar = QtGui.QMenuBar()

        # NOTE: Special hack for Mac OS X, otherwise the menus
        # do not get added to the global OS X menu
        macos_ver = platform.mac_ver()[0]
        if len(macos_ver) > 0:
            self.w['top'].layout().addWidget(menubar, stretch=0)
        else:
            holder.layout().addWidget(menubar, stretch=1)

        # create a File pulldown menu, and add it to the menu bar
        filemenu = menubar.addMenu("File")

        item = QtGui.QAction("Load Image", menubar)
        item.triggered.connect(self.gui_load_file)
        filemenu.addAction(item)

        sep = QtGui.QAction(menubar)
        sep.setSeparator(True)
        filemenu.addAction(sep)
        
        item = QtGui.QAction("Quit", menubar)
        item.triggered.connect(self.windowClose)
        filemenu.addAction(item)

        # create a Channel pulldown menu, and add it to the menu bar
        chmenu = menubar.addMenu("Channel")

        item = QtGui.QAction("Add Channel", menubar)
        item.triggered.connect(self.gui_add_channel)
        chmenu.addAction(item)
        
        item = QtGui.QAction("Add Channels", menubar)
        item.triggered.connect(self.gui_add_channels)
        chmenu.addAction(item)
        
        item = QtGui.QAction("Delete Channel", menubar)
        item.triggered.connect(self.gui_delete_channel)
        chmenu.addAction(item)

        # create a Window pulldown menu, and add it to the menu bar
        winmenu = menubar.addMenu("Workspace")

        item = QtGui.QAction("Add Workspace", menubar)
        item.triggered.connect(self.gui_add_ws)
        winmenu.addAction(item)
        
        # # create a Option pulldown menu, and add it to the menu bar
        # optionmenu = menubar.addMenu("Option")

        ## # create a Workspace pulldown menu, and add it to the menu bar
        ## wsmenu = menubar.addMenu("Workspace")

        ## item = QtGui.QAction("Panes as Tabs", menubar)
        ## item.triggered.connect(self.tabstoggle_cb)
        ## item.setCheckable(True)
        ## # TODO: check the state of the workspace first
        ## item.setChecked(True)
        ## wsmenu.addAction(item)
        
        ## item = QtGui.QAction("Tile Panes", menubar)
        ## item.triggered.connect(self.tile_panes_cb)
        ## wsmenu.addAction(item)
        
        ## item = QtGui.QAction("Cascade Panes", menubar)
        ## item.triggered.connect(self.cascade_panes_cb)
        ## wsmenu.addAction(item)
        
        # create a Help pulldown menu, and add it to the menu bar
        helpmenu = menubar.addMenu("Help")

        item = QtGui.QAction("About", menubar)
        item.triggered.connect(lambda: self.banner(raiseTab=True))
        helpmenu.addAction(item)
        return menubar

    def add_dialogs(self):
        filesel = QtGui.QFileDialog(self.w.root)
        filesel.setFileMode(QtGui.QFileDialog.ExistingFile)
        filesel.setViewMode(QtGui.QFileDialog.Detail)
        self.filesel = filesel

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
        if w != None:
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
        if image == None:
            return
        fi.set_image(image)

        # Copy attributes of the frame
        fitsimage.copy_attributes(fi,
                                  [#'transforms',
                                   #'cutlevels',
                                   'rgbmap'],
                                  redraw=False)

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
                image = QtGui.QImage(iconfile)
                pixmap = QtGui.QPixmap.fromImage(image)
                picon = QtGui.QIcon(pixmap)
                qsize = QtCore.QSize(24, 24)
            except Exception, e:
                self.logger.error("Error loading icon '%s': %s" % (
                    iconfile, str(e)))

        if wtyp == 'button':
            if picon:
                w = QtGui.QPushButton()
                w.setIconSize(qsize)
                w.setIcon(picon)
            else:
                w = QtGui.QPushButton(name)
        elif wtyp == 'toggle':
            if picon:
                w = QtGui.QPushButton()
                w.setCheckable(True)
                w.setIconSize(qsize)
                w.setIcon(picon)
            else:
                w = QtGui.QPushButton(name)
                w.setCheckable(True)

        return w

    def set_titlebar(self, text):
        self.w.root.setWindowTitle("Ginga: %s" % text)
        
    def build_readout(self):
        readout = Readout.Readout(-1, 20)
        readout.set_font(self.font11)
        return readout

    def getDrawClass(self, drawtype):
        drawtype = drawtype.lower()
        return ImageViewCanvasTypesQt.drawCatalog[drawtype]
    
    def getDrawClasses(self):
        return Bunch.Bunch(ImageViewCanvasTypesQt.drawCatalog,
                           caseless=True)
        
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
        fi = ImageViewCanvasQt.ImageViewCanvas(logger=self.logger,
                                               rgbmap=rgbmap,
                                               settings=settings)
        fi.enable_draw(False)
        fi.enable_auto_orient(True)
        fi.add_callback('motion', self.motion_cb)
        fi.add_callback('cursor-down', self.force_focus_cb)
        fi.add_callback('key-press', self.keypress)
        fi.add_callback('drag-drop', self.dragdrop)
        for name in ['cuts']:
            settings.getSetting(name).add_callback('set',
                               self.change_range_cb, fi, self.colorbar)

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


    def start_global_plugin(self, pluginName):

        pInfo = self.gpmon.getPluginInfo(pluginName)
        spec = pInfo.spec

        vbox = None
        try:
            wsName = spec.get('ws', None)
            if wsName and hasattr(pInfo.obj, 'build_gui'):
                tabName = spec.get('tab', pInfo.name)
                pInfo.tabname = tabName

                widget = QtGui.QWidget()
                vbox = QtGui.QVBoxLayout()
                vbox.setContentsMargins(4, 4, 4, 4)
                vbox.setSpacing(2)
                widget.setLayout(vbox)

                pInfo.obj.build_gui(vbox)

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
                textw = QtGui.QTextEdit()
                textw.append(str(e) + '\n')
                textw.append(tb_str)
                textw.setReadOnly(True)
                vbox.addWidget(textw, stretch=1)
                
        if vbox:
            self.ds.add_tab(wsName, widget, 2, tabName)
            pInfo.widget = widget
                
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
                    ('Number of channels', 'spinbutton'))
        w, b = QtHelp.build_info(captions)

        self.wscount += 1
        wsname = "ws%d" % (self.wscount)
        b.workspace_name.setText(wsname)

        cbox = b.workspace_type
        cbox.append_text("Tabs")
        cbox.append_text("Grid")
        cbox.setCurrentIndex(0)

        cbox = b.in_workspace
        names = self.ds.get_wsnames()
        names.insert(0, 'top level')
        try:
            idx = names.index('top level')
        except:
            idx = 0
        for name in names:
            cbox.append_text(name)
        cbox.setCurrentIndex(idx)

        b.channel_prefix.setText("Image")
        spnbtn = b.number_of_channels
        spnbtn.setRange(0, 12)
        spnbtn.setSingleStep(1)
        spnbtn.setValue(1)

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
        d = { 0: 'nb', 1: 'grid' }
        wstype = d[idx]
        idx = b.in_workspace.currentIndex()
        inSpace = names[idx]
        
        self.add_workspace(wsname, wstype, inSpace=inSpace)

        chpfx = b.channel_prefix.text()
        num = int(b.number_of_channels.value())
        if num <= 0:
            return

        chbase = self.chncnt
        self.chncnt += num
        for i in xrange(num):
            chname = "%s%d" % (chpfx, chbase+i)
            self.add_channel(chname, workspace=wsname)
        
        return True
        
    def gui_load_file(self, initialdir=None):
        if self.filesel.exec_():
            fileNames = map(str, list(self.filesel.selectedFiles()))
            self.load_file(fileNames[0])
        #self.start_operation('FBrowser')
        
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
        font = QtGui.QFont(fontFamily, pointSize)
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
        for i in xrange(num):
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
        return self.start_operation_channel(chname, name, None)
        
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
                if chinfo.has_key('container') and (chinfo.container == container):
                    fitsimage = chinfo.fitsimage
                    if fitsimage != self.getfocus_fitsimage():
                        self.logger.debug("Active channel switch to '%s'" % (
                            chname))
                        self.change_channel(chname, raisew=False)

        return True

    def page_switch_mdi_cb(self, w):
        if w != None:
            index = self.w.mnb.indexOf(w)
            return self.page_switch_cb(index)

        
# END
