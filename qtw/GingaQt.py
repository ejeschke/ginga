#
# GingaQt.py -- Qt display handler for the Ginga FITS tool.
#
#[ Eric Jeschke (eric@naoj.org) --
#  Last edit: Fri Jun 22 15:45:18 HST 2012
#]
#
# Copyright (c) 2011-2012, Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
# stdlib imports
import sys, os
import Queue
import traceback

# GUI imports
from PyQt4 import QtGui, QtCore

import Bunch

# Local application imports
import FitsImage

moduleHome = os.path.split(sys.modules[__name__].__file__)[0]
sys.path.insert(0, moduleHome)
childDir = os.path.join(moduleHome, 'plugins')
sys.path.insert(0, childDir)

import FitsImageCanvasQt
import ColorBar
import Readout
import PluginManagerQt
import QtHelp
import QtMain

icon_path = os.path.abspath(os.path.join(moduleHome, '..', 'icons'))
rc_file = os.path.join(moduleHome, "qt_rc")


class FitsViewError(Exception):
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

        self.font = QtGui.QFont('Monospace', 12)
        self.font11 = QtGui.QFont('Monospace', 11)

        self.w.tooltips = None
        QtGui.QToolTip.setFont(self.font11)
        

    def build_toplevel(self, layout):
        # Create root window and add delete/destroy callbacks
        #root = QtGui.QWidget()
        #root.connect(root, QtCore.SIGNAL('closed()'), 
        #             self.foo)
        root = QtHelp.TopLevel()
        root.setApp(self)
        root.resize(self.default_width, self.default_height)
        root.setWindowTitle("Ginga")
        #root.set_border_width(2)
        
        self.w.root = root

        self.ds = QtHelp.Desktop()
        
        # create main frame
        vbox = QtGui.QVBoxLayout()
        vbox.setContentsMargins(2, 2, 2, 2)
        vbox.setSpacing(2)
        root.setLayout(vbox)
        self.w.mframe = vbox

        self.add_menus()

        self.w.mvbox = self.ds.make_desktop(layout, widgetDict=self.w)
        #self.w.mvbox.show_all()
        self.w.mframe.addWidget(self.w.mvbox, stretch=1)

        # Create main (center) FITS image pane
        self.w.vbox = self.w['main'].layout()
        self.w.vbox.setSpacing(0)
        #self.w.mnb = self.ds.make_ws(name='main', group=1, wstype='mdi').nb
        self.w.mnb = self.ds.make_ws(name='main', group=1).nb
        self.w.mnb.currentChanged.connect(self.page_switch_cb)
        self.w.vbox.addWidget(self.w.mnb, stretch=1)
        
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

        cbox2 = QtHelp.ComboBox()
        self.w.operation = cbox2
        ## index = 0
        ## for name in self.operations:
        ##     cbox2.addItem(name, userData=index)
        ##     index += 1
        ## cbox2.setCurrentIndex(0)
        cbox2.setToolTip("Select operation and press Start")
        hbox.addWidget(cbox2, stretch=0)

        btn = QtGui.QPushButton("Start")
        btn.setToolTip("Start operation")
        btn.clicked.connect(self.start_operation_cb)
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
        cbar.show()
        self.w.vbox.addWidget(cbar, stretch=0)

        self.add_dialogs()
        self.add_statusbar()

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
    
    def add_menus(self):

        menubar = QtGui.QMenuBar()
        self.w.mframe.addWidget(menubar, stretch=0)

        # create a File pulldown menu, and add it to the menu bar
        filemenu = menubar.addMenu("File")

        item = QtGui.QAction(QtCore.QString("Load Image"), menubar)
        item.triggered.connect(self.gui_load_file)
        filemenu.addAction(item)

        item = QtGui.QAction(QtCore.QString("Save image as PNG"), menubar)
        item.triggered.connect(lambda: self.save_file('/tmp/fitsimage.png',
                                                      'png'))
        filemenu.addAction(item)

        sep = QtGui.QAction(menubar)
        sep.setSeparator(True)
        filemenu.addAction(sep)
        
        item = QtGui.QAction(QtCore.QString("Quit"), menubar)
        item.triggered.connect(self.windowClose)
        filemenu.addAction(item)

        # create a Channel pulldown menu, and add it to the menu bar
        chmenu = menubar.addMenu("Channel")

        item = QtGui.QAction(QtCore.QString("Add Channel"), menubar)
        item.triggered.connect(self.gui_add_channel)
        chmenu.addAction(item)
        
        item = QtGui.QAction(QtCore.QString("Delete Channel"), menubar)
        item.triggered.connect(self.gui_delete_channel)
        chmenu.addAction(item)

        # create a Option pulldown menu, and add it to the menu bar
        ## optionmenu = menubar.addMenu("Option")

        ## # create a Workspace pulldown menu, and add it to the menu bar
        ## wsmenu = menubar.addMenu("Workspace")

        ## item = QtGui.QAction(QtCore.QString("Panes as Tabs"), menubar)
        ## item.triggered.connect(self.tabstoggle_cb)
        ## item.setCheckable(True)
        ## # TODO: check the state of the workspace first
        ## item.setChecked(True)
        ## wsmenu.addAction(item)
        
        ## item = QtGui.QAction(QtCore.QString("Tile Panes"), menubar)
        ## item.triggered.connect(self.tile_panes_cb)
        ## wsmenu.addAction(item)
        
        ## item = QtGui.QAction(QtCore.QString("Cascade Panes"), menubar)
        ## item.triggered.connect(self.cascade_panes_cb)
        ## wsmenu.addAction(item)
        

    def add_dialogs(self):
        filesel = QtGui.QFileDialog(self.w.root)
        filesel.setFileMode(QtGui.QFileDialog.ExistingFile)
        filesel.setViewMode(QtGui.QFileDialog.Detail)
        self.filesel = filesel

    def add_statusbar(self):
        self.w.status = QtGui.QStatusBar()
        self.w.mframe.addWidget(self.w.status)

    def add_operation(self, title):
        cbox = self.w.operation
        cbox.addItem(title)
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

    def build_colorbar(self):
        cbar = ColorBar.ColorBar(self.logger)
        cbar.set_cmap(self.cm)
        cbar.set_imap(self.im)
        cbar.resize(700, 15)
        #cbar.show()
        self.colorbar = cbar
        self.add_callback('active-image', self.change_cbar, cbar)

        fr = QtGui.QFrame()
        fr.setContentsMargins(0, 0, 0, 0)
        layout = QtGui.QHBoxLayout()
        fr.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        fr.setFrameStyle(QtGui.QFrame.Box | QtGui.QFrame.Raised)
        layout.addWidget(cbar, stretch=1)
        return fr
    
    def build_viewpane(self, cm, im):
        fi = FitsImageCanvasQt.FitsImageCanvas(logger=self.logger)
        fi.enable_autoscale(self.default_autoscale)
        fi.set_autoscale_limits(-20, 3)
        fi.enable_autolevels(self.default_autolevels)
        fi.enable_zoom(True)
        fi.enable_cuts(True)
        fi.enable_flip(True)
        fi.enable_draw(False)
        fi.set_cmap(cm, redraw=False)
        fi.set_imap(im, redraw=False)
        fi.add_callback('motion', self.motion_cb)
        fi.add_callback('key-press', self.keypress)
        fi.add_callback('drag-drop', self.dragdrop)
        rgbmap = fi.get_rgbmap()
        rgbmap.add_callback('changed', self.rgbmap_cb, fi)
        fi.set_bg(0.2, 0.2, 0.2)
        return fi

    def add_viewer(self, name, cm, im, use_readout=True, workspace=None):

        vwidget = QtGui.QWidget()
        vbox = QtGui.QVBoxLayout()
        vbox.setContentsMargins(4, 4, 4, 4)
        vbox.setSpacing(0)
        vwidget.setLayout(vbox)
        
        fi = self.build_viewpane(cm, im)
        iw = fi.get_widget()

        if self.channel_follows_focus:
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
            vbox.addWidget(rw, stretch=0)
        else:
            readout = None

        # Add a page to the specified notebook
        if not workspace:
            workspace = 'main'
        nb = self.ds.get_nb(workspace)
        self.ds.add_tab(nb, vwidget, 1, name)

        self.update_pending()
        bnch = Bunch.Bunch(fitsimage=fi, view=iw, container=vwidget,
                           readout=readout)
        return bnch


    def add_global_pane(self, pluginName, paneName, nbw):
        self.logger.debug("Adding pane '%s'" % (paneName))
        widget = QtGui.QWidget()
        vbox = QtGui.QVBoxLayout()
        vbox.setContentsMargins(4, 4, 4, 4)
        vbox.setSpacing(2)
        widget.setLayout(vbox)
        self.ds.add_tab(nbw, widget, 2, paneName)

        try:
            pluginObj = self.gpmon.getPlugin(pluginName)
            pluginObj.initialize(vbox)

            pluginObj.start()
        except Exception, e:
            self.logger.error("Failed to load global plugin '%s': %s" % (
                pluginName, str(e)))
            try:
                (type, value, tb) = sys.exc_info()
                tb_str = "\n".join(traceback.format_tb(tb))
                self.logger.error("Traceback:\n%s" % (tb_str))
                textw = QtGui.QTextEdit()
                textw.append(str(e) + '\n')
                textw.append(tb_str)
                textw.setReadOnly(True)
                vbox.addWidget(textw, stretch=1)
                
            except Exception, e:
                self.logger.error("Traceback information unavailable.")
                
        self.logger.debug("pane '%s' added." % (paneName))
        return vbox
    
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
        #ent.set_activates_default(True)
        dialog = QtHelp.Dialog("New Channel",
                               0,
                               [['Cancel', 0], ['Ok', 1]],
                               lambda w, rsp: self.new_channel_cb(w, rsp, ent))
        box = dialog.get_content_area()
        layout = QtGui.QVBoxLayout()
        box.setLayout(layout)
        
        layout.addWidget(lbl, stretch=0)
        layout.addWidget(ent, stretch=0)
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
        
    def gui_load_file(self, initialdir=None):
        if self.filesel.exec_():
            fileNames = map(str, list(self.filesel.selectedFiles()))
            self.load_file(fileNames[0])
        #self.start_operation('FBrowser')
        
    # def build_dialogpane(self):
    #     nb = self.ds.make_nb(name="dialogs", group=3).nb
    #     nb.show_all()
    #     self.w.dialogs = nb
    #     return nb
        
    # def add_dialogpane(self, name, nbw):
    #     w = self.build_dialogpane()

    #     # Add the Dialogs page to the LH notebook
    #     self.ds.add_tab(nbw, w, 2, "Dialogs")
    #     return w
        
    def statusMsg(self, format, *args):
        if not format:
            s = ''
        else:
            s = format % args

        # remove message in about 10 seconds
        self.w.status.showMessage(s, 10000)
        ## if self.statustask:
        ##     gobject.source_remove(self.statustask)
        ## self.statustask = gobject.timeout_add(10000, self.statusMsg, '')


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
        self.stop()

        # NOTE: root doesn't actually have a close() method, but this
        # seems to work around a segfault at exit in PyQt4 4.7.2
        root = self.w.root
        self.w.root = None
        root.close()

    def channel_select_cb(self, index):
        if index >= 0:
            chname = self.channelNames[index]
            self.logger.debug("Channel changed, index=%d chname=%s" % (
                index, chname))
            self.change_channel(chname)
        
    def new_channel_cb(self, w, rsp, ent):
        w.close()
        chname = str(ent.text())
        if rsp == 0:
            return
        self.add_channel(chname)
        return True
        
    def delete_channel_cb(self, w, rsp, chname):
        w.close()
        if rsp == 0:
            return
        self.delete_channel(chname)
        return True
        
    def start_operation_cb(self):
        index = self.w.operation.currentIndex()
        name = self.operations[index]
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
                if chinfo.container == container:
                    fitsimage = chinfo.fitsimage
                    if fitsimage != self.getfocus_fitsimage():
                        self.logger.debug("Active channel switch to '%s'" % (
                            chname))
                        self.change_channel(chname, raisew=False)
                        # TODO: this is a hack to force the cursor change on the new
                        # window--make this better
                        fitsimage.to_default_mode()

        return True

# END
