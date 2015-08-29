#
# QtHelp.py -- customized Qt widgets and convenience functions
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from __future__ import print_function
import time
import os
import math

import ginga.toolkit
from functools import reduce

have_pyqt4 = False
have_pyside = False
have_pyqt5 = False
configured = False

toolkit = ginga.toolkit.toolkit

if toolkit in ('qt5', 'choose') and (not configured):
    try:
        from PyQt5 import QtCore
        from PyQt5 import QtWidgets as QtGui
        from PyQt5.QtGui import QImage, QColor, QFont, QPixmap, QIcon, \
             QCursor, QPainter, QPen, QPolygonF, QPolygon, QTextCursor, \
             QDrag, QPainterPath
        from PyQt5.QtCore import QItemSelectionModel
        from PyQt5.QtWidgets import QApplication
        have_pyqt5 = True
        try:
            from PyQt5 import QtWebKit
            from PyQt5.QtWebKitWidgets import QWebView
        except ImportError as e:
            pass

        # for Matplotlib
        os.environ['QT_API'] = 'pyqt'
        configured = True
    except ImportError as e:
        pass

if toolkit in ('qt4', 'choose') and (not configured):
    try:
        import sip
        for cl in ('QString', 'QVariant'):
            sip.setapi(cl, 2)

        from PyQt4 import QtCore, QtGui
        from PyQt4.QtGui import QImage, QColor, QFont, QPixmap, QIcon, \
             QCursor, QPainter, QPen, QPolygonF, QPolygon, QTextCursor, \
             QDrag, QItemSelectionModel, QPainterPath, QApplication
        have_pyqt4 = True
        try:
            from PyQt4 import QtWebKit
            from PyQt4.QtWebKit import QWebView
        except ImportError:
            pass

        # for Matplotlib
        os.environ['QT_API'] = 'pyqt'
        configured = True
    except ImportError as e:
        pass

if toolkit in ('pyside', 'choose') and (not configured):
    try:
        from PySide import QtCore, QtGui
        from PySide.QtGui import QImage, QColor, QFont, QPixmap, QIcon, \
             QCursor, QPainter, QPen, QPolygonF, QPolygon, QTextCursor, \
             QDrag, QItemSelectionModel, QPainterPath
        have_pyside = True
        try:
            from PySide import QtWebKit
            from PySide.QtWebKit import QWebView
        except ImportError:
            pass

        # for Matplotlib
        os.environ['QT_API'] = 'pyside'
        configured = True
    except ImportError:
        pass

if have_pyqt5:
    ginga.toolkit.use('qt5')
elif have_pyqt4:
    ginga.toolkit.use('qt4')
elif have_pyside:
    ginga.toolkit.use('pyside')
else:
    raise ImportError("Failed to import qt4, qt5 or pyside. There may be an issue with the toolkit module or it is not installed")

from ginga.misc import Bunch, Callback

tabwidget_style = """
QTabWidget::pane { margin: 0px,0px,0px,0px; padding: 0px; }
QMdiSubWindow { margin: 0px; padding: 2px; }
"""


class TopLevel(QtGui.QWidget):

    app = None
    ## def __init__(self, *args, **kwdargs):
    ##     return super(TopLevel, self).__init__(self, *args, **kwdargs)

    def closeEvent(self, event):
        if not (self.app is None):
            self.app.quit()

    def setApp(self, app):
        self.app = app

class TabWidget(QtGui.QTabWidget):
    pass

class StackedWidget(QtGui.QStackedWidget):

    def addTab(self, widget, label):
        self.addWidget(widget)

    def removeTab(self, index):
        self.removeWidget(self.widget(index))

class TabWorkspace(QtGui.QTabWidget):

    def __init__(self):
        super(TabWorkspace, self).__init__()

        self.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred,
                                             QtGui.QSizePolicy.Preferred))

    def window(self):
        return self.currentWidget()

    def sizeHint(self):
        return QtCore.QSize(300, 300)

    def to_next(self):
        num_tabs = self.count()
        cur_idx = self.currentIndex()
        new_idx = (cur_idx + 1) % num_tabs
        self.setCurrentIndex(new_idx)

    def to_previous(self):
        num_tabs = self.count()
        new_idx = self.currentIndex() - 1
        if new_idx < 0:
            new_idx = max(num_tabs - 1, 0)
        self.setCurrentIndex(new_idx)

class MDIWorkspace(QtGui.QMdiArea):

    def __init__(self):
        super(MDIWorkspace, self).__init__()
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        #self.setViewMode(QtGui.QMdiArea.TabbedView)

        self.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding,
                                             QtGui.QSizePolicy.Expanding))

    def get_mode(self):
        if self.viewMode() == QtGui.QMdiArea.TabbedView:
            return 'tabs'
        return 'mdi'

    def set_mode(self, mode):
        mode = mode.lower()
        if mode == 'tabs':
            self.setViewMode(QtGui.QMdiArea.TabbedView)
        elif mode == 'mdi':
            self.setViewMode(QtGui.QMdiArea.SubWindowView)
        else:
            raise ValueError("Don't understand mode='%s'" % (mode))

    def addTab(self, widget, label):
        w = self.addSubWindow(widget)
        w.setWindowTitle(label)
        widget.show()
        w.show()

    def removeTab(self, index):
        l = list(self.subWindowList())
        sw = l[index]
        widget = sw.widget()
        sw.deleteLater()
        self.removeSubWindow(widget)

    def indexOf(self, widget):
        try:
            l = [ sw.widget() for sw in self.subWindowList() ]
            idx = l.index(widget)
            return idx
        except (IndexError, ValueError) as e:
            return -1

    def widget(self, index):
        l = list(self.subWindowList())
        sw = l[index]
        return sw.widget()

    def window(self):
        sw = self.activeSubWindow()
        #return sw
        return sw.widget()

    def tabBar(self):
        return None

    def setCurrentIndex(self, index):
        l = list(self.subWindowList())
        w = l[index]
        self.setActiveSubWindow(w)

    def sizeHint(self):
        return QtCore.QSize(600, 600)

    def to_next(self):
        pass
    def to_previous(self):
        pass

class GridWorkspace(QtGui.QWidget):

    def __init__(self):
        super(GridWorkspace, self).__init__()

        self.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding,
                                             QtGui.QSizePolicy.Expanding))

        layout = QtGui.QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)
        self.layout = layout
        self.widgets = []
        self.current_idx = -1

    def _relayout(self):
        # calculate number of rows and cols, try to maintain a square
        # TODO: take into account the window geometry
        num_widgets = len(self.widgets)
        rows = int(round(math.sqrt(num_widgets)))
        cols = rows
        if rows**2 < num_widgets:
            cols += 1

        # remove all the old widgets
        for w in self.widgets:
            self.layout.removeWidget(w)

        # add them back in, in a grid
        for i in range(0, rows):
            for j in range(0, cols):
                index = i*cols + j
                if index < num_widgets:
                    widget = self.widgets[index]
                self.layout.addWidget(widget, i, j)

    def addTab(self, widget, label):
        ## widget.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding,
        ##                                        QtGui.QSizePolicy.MinimumExpanding))
        widget.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding,
                                               QtGui.QSizePolicy.Expanding))
        self.widgets.append(widget)
        self._relayout()

    def removeTab(self, idx):
        widget = self.widget(idx)
        self.widgets.remove(widget)
        self.layout.removeWidget(widget)
        self._relayout()

    def indexOf(self, widget):
        try:
            return self.widgets.index(widget)
        except (IndexError, ValueError) as e:
            return -1

    def widget(self, index):
        return self.widgets[index]

    def tabBar(self):
        return None

    def setCurrentIndex(self, index):
        widget = self.widget(index)
        # TODO: focus widget
        self.current_idx = index

    def window(self):
        return self.widget(self.current_idx)

    def sizeHint(self):
        return QtCore.QSize(300, 300)

    def to_next(self):
        pass
    def to_previous(self):
        pass

class ComboBox(QtGui.QComboBox):

    def insert_alpha(self, text):
        index = 0
        while True:
            itemText = self.itemText(index)
            if len(itemText) == 0:
                break
            if itemText > text:
                self.insertItem(index, text)
                return
            index += 1
        self.addItem(text)

    def delete_alpha(self, text):
        index = self.findText(text)
        self.removeItem(index)

    def show_text(self, text):
        index = self.findText(text)
        self.setCurrentIndex(index)

    def append_text(self, text):
        self.addItem(text)

class VBox(QtGui.QWidget):
    def __init__(self, *args, **kwdargs):
        super(VBox, self).__init__(*args, **kwdargs)

        layout = QtGui.QVBoxLayout()
        # because of ridiculous defaults
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def addWidget(self, w, **kwdargs):
        self.layout().addWidget(w, **kwdargs)

    def setSpacing(self, val):
        self.layout().setSpacing(val)

class HBox(QtGui.QWidget):
    def __init__(self, *args, **kwdargs):
        super(HBox, self).__init__(*args, **kwdargs)

        layout = QtGui.QHBoxLayout()
        # because of ridiculous defaults
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def addWidget(self, w, **kwdargs):
        self.layout().addWidget(w, **kwdargs)

    def setSpacing(self, val):
        self.layout().setSpacing(val)

class Frame(QtGui.QFrame):
    def __init__(self, title=None):
        super(Frame, self).__init__()

        self.setFrameStyle(QtGui.QFrame.Box | QtGui.QFrame.Raised)
        vbox = QtGui.QVBoxLayout()
        # because of ridiculous defaults
        vbox.setContentsMargins(2, 2, 2, 2)
        self.setLayout(vbox)
        if title:
            lbl = QtGui.QLabel(title)
            lbl.setAlignment(QtCore.Qt.AlignHCenter)
            vbox.addWidget(lbl, stretch=0)
            self.label = lbl
        else:
            self.label = None

    def getLabel(self):
        return self.label

    def addWidget(self, w, **kwdargs):
        self.layout().addWidget(w, **kwdargs)

class Dialog(QtGui.QDialog):
    def __init__(self, title=None, flags=None, buttons=None,
                 callback=None):
        QtGui.QDialog.__init__(self)
        self.setModal(True)

        vbox = QtGui.QVBoxLayout()
        self.setLayout(vbox)

        self.content = QtGui.QWidget()
        vbox.addWidget(self.content, stretch=1)

        hbox_w = QtGui.QWidget()
        hbox = QtGui.QHBoxLayout()
        hbox_w.setLayout(hbox)

        def mklocal(val):
            def cb():
                callback(self, val)
            return cb

        for name, val in buttons:
            btn = QtGui.QPushButton(name)
            if callback:
                btn.clicked.connect(mklocal(val))
            hbox.addWidget(btn, stretch=0)

        vbox.addWidget(hbox_w, stretch=0)
        #self.w.connect("close", self.close)

    def get_content_area(self):
        return self.content


class MenuBar(QtGui.QMenuBar):

    def __init__(self, parent=None):
        super(MenuBar, self).__init__(parent=parent)

    def add_name(self, name):
        menu = self.addMenu(name)
        return menu

    def make_action(self, name):
        item = QtGui.QAction(name, self)
        return item


class ToolBar(QtGui.QToolBar):

    def __init__(self, parent=None):
        super(ToolBar, self).__init__(parent=parent)

    def add_name(self, name):
        menu = QtGui.QMenu()
        # TODO: need to get this to behave a little more like a regular menu
        action = self.addAction(name, lambda *args: self._press_cb(menu))
        return menu

    def _press_cb(self, menu):
        menu.popup(self.mapToGlobal(QtCore.QPoint(0,0)))

    def make_action(self, name):
        item = QtGui.QAction(name, self)
        return item


class Desktop(Callback.Callbacks):

    def __init__(self):
        super(Desktop, self).__init__()

        # for tabs
        self.tab = Bunch.caselessDict()
        self.tabcount = 0
        self.notebooks = Bunch.caselessDict()

        self.toplevels = []

        for name in ('page-switch', 'page-select', 'all-closed'):
            self.enable_callback(name)
        self.popmenu = None

    # --- Tab Handling ---

    def make_ws(self, name=None, group=1, show_tabs=True, show_border=False,
                detachable=True, tabpos=None, scrollable=True, closeable=False,
                wstype='nb'):
        if tabpos is None:
            tabpos = QtGui.QTabWidget.North

        if wstype == 'mdi':
            nb = MDIWorkspace()

        elif wstype == 'grid':
            nb = GridWorkspace()

        elif show_tabs:
            nb = TabWorkspace()
            nb.setTabPosition(tabpos)
            nb.setUsesScrollButtons(scrollable)
            nb.setTabsClosable(closeable)
            nb.setMovable(True)   # reorderable
            nb.setAcceptDrops(True)
            nb.currentChanged.connect(lambda idx: self.switch_page_cb(idx, nb))

            tb = nb.tabBar()
            ## tb.setAcceptDrops(True)
            tb.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            tb.customContextMenuRequested.connect(lambda point: self.on_context_menu(nb, group, point))

        else:
            nb = StackedWidget()
            nb.currentChanged.connect(lambda idx: self.switch_page_cb(idx, nb))

        nb.setStyleSheet(tabwidget_style)
        if not name:
            name = str(time.time())
        bnch = Bunch.Bunch(nb=nb, name=name, nbtype=wstype,
                           widget=nb, group=group)
        self.notebooks[name] = bnch
        return bnch

    def get_nb(self, name):
        return self.notebooks[name].nb

    def get_size(self, widget):
        wd, ht = widget.width(), widget.height()
        return (wd, ht)

    def get_ws_size(self, name):
        w = self.get_nb(name)
        return self.get_size(w)

    def get_wsnames(self, group=1):
        res = []
        for name in self.notebooks.keys():
            bnch = self.notebooks[name]
            if group is None:
                res.append(name)
            elif group == bnch.group:
                res.append(name)
        return res

    def get_tabnames(self, group=1):
        res = []
        for name in self.tab.keys():
            bnch = self.tab[name]
            if group is None:
                res.append(name)
            elif group == bnch.group:
                res.append(name)
        return res

    def on_context_menu(self, nb, group, point):
        # create context menu
        popmenu = QtGui.QMenu(nb)
        submenu = QtGui.QMenu(popmenu)
        submenu.setTitle("Take Tab")
        popmenu.addMenu(submenu)

        tabnames = self.get_tabnames(group=group)
        tabnames.sort()
        for tabname in tabnames:
            item = QtGui.QAction(tabname, nb)
            item.triggered.connect(self._mk_take_tab_cb(tabname, nb))
            submenu.addAction(item)

        popmenu.exec_(nb.mapToGlobal(point))
        self.popmenu = popmenu


    def take_tab_cb(self, nb, args):
        popmenu = QtGui.QMenu(nb)

        group = 1
        tabnames = self.get_tabnames(group=group)
        tabnames.sort()
        for tabname in tabnames:
            item = QtGui.QAction(tabname, nb)
            item.triggered.connect(self._mk_take_tab_cb(tabname, nb))
            popmenu.addAction(item)

        point = QtCore.QPoint(100, 100)
        popmenu.exec_(nb.mapToGlobal(point))

    def add_tab(self, wsname, widget, group, labelname, tabname=None,
                data=None):
        tab_w = self.get_nb(wsname)
        self.tabcount += 1
        if not tabname:
            tabname = labelname
            if tabname in self.tab:
                tabname = 'tab%d' % self.tabcount

        tab_w.addTab(widget, labelname)
        self.tab[tabname] = Bunch.Bunch(widget=widget, name=labelname,
                                        tabname=tabname, data=data,
                                        group=group)
        return tabname

    def _find_nb(self, tabname):
        widget = self.tab[tabname].widget
        for bnch in self.notebooks.values():
            nb = bnch.nb
            page_num = nb.indexOf(widget)
            if page_num < 0:
                continue
            return (nb, page_num)
        return (None, None)

    def _find_tab(self, widget):
        for key, bnch in self.tab.items():
            if widget == bnch.widget:
                return bnch
        return None

    def select_cb(self, widget, event, name, data):
        self.make_callback('page-select', name, data)

    def raise_tab(self, tabname):
        nb, index = self._find_nb(tabname)
        widget = self.tab[tabname].widget
        if (nb is not None) and (index >= 0):
            nb.setCurrentIndex(index)
            # bring window to the user's attention
            win = nb.window()
            if win is not None:
                win.raise_()
                win.activateWindow()

    def remove_tab(self, tabname):
        nb, index = self._find_nb(tabname)
        widget = self.tab[tabname].widget
        if (nb is not None) and (index >= 0):
            nb.removeTab(index)

    def highlight_tab(self, tabname, onoff):
        nb, index = self._find_nb(tabname)
        if nb:
            tb = nb.tabBar()
            if tb is None:
                return
            widget = tb.tabButton(index, QtGui.QTabBar.RightSide)
            if widget is None:
                return
            name = self.tab[tabname].name
            if onoff:
                widget.setStyleSheet('QPushButton {color: palegreen}')
            else:
                widget.setStyleSheet('QPushButton {color: grey}')

    def add_toplevel(self, bnch, wsname, width=700, height=700):
        topw = TopLevel()
        topw.resize(width, height)
        self.toplevels.append(topw)
        #topw.setTitle(wsname)

        layout = QtGui.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        topw.setLayout(layout)

        menubar = MenuBar()
        layout.addWidget(menubar, stretch=0)

        # create a Workspace pulldown menu, and add it to the menu bar
        winmenu = menubar.add_name("Workspace")

        item = menubar.make_action("Take Tab")
        item.triggered.connect(lambda *args: self.take_tab_cb(bnch.nb, args))
        winmenu.addAction(item)

        sep = menubar.make_action('')
        sep.setSeparator(True)
        winmenu.addAction(sep)

        closeitem = menubar.make_action("Close")
        bnch.widget.closeEvent = lambda event: self.close_page_cb(bnch, event)
        closeitem.triggered.connect(lambda: self._close_page(bnch))
        winmenu.addAction(closeitem)

        layout.addWidget(bnch.widget, stretch=1)
        topw.showNormal()
        return topw

    def create_toplevel_ws(self, width, height, group=2, x=None, y=None):
        # create main frame
        root = TopLevel()
        ## root.setTitle(title)
        # TODO: this needs to be more sophisticated

        layout = QtGui.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        root.setLayout(layout)

        menubar = MenuBar()
        layout.addWidget(menubar, stretch=0)

        # create a Window pulldown menu, and add it to the menu bar
        winmenu = menubar.add_name("Window")

        ## item = menubar.make_action("Take Tab")
        ## item.triggered.connect(self.gui_load_file)
        ## winmenu.addAction(item)

        sep = menubar.add_action('')
        sep.setSeparator(True)
        winmenu.addAction(sep)

        quititem = menubar.make_action("Quit")
        winmenu.addAction(quititem)

        bnch = self.make_ws(group=1)
        bnch.root = root
        layout.addWidget(bnch.nb, stretch=1)
        root.closeEvent = lambda event: self.close_page_cb(bnch, event)
        quititem.triggered.connect(lambda: self._close_page(bnch))

        root.show()
        root.resize(width, height)
        if x is not None:
            root.moveTo(x, y)
        return True

    def detach_page_cb(self, source, widget, x, y, group):
        # Detach page to new top-level workspace
        ## page = self.widgetToPage(widget)
        ## if not page:
        ##     return None
        width, height = widget.size()

        ## self.logger.info("detaching page %s" % (page.name))
        bnch = self.create_toplevel_ws(width, height, x=x, y=y)

        return bnch.nb

    def _mk_take_tab_cb(self, tabname, to_nb):
        def _foo():
            nb, index = self._find_nb(tabname)
            widget = self.tab[tabname].widget
            if (nb is not None) and (index >= 0):
                nb.removeTab(index)
                to_nb.addTab(widget, tabname)

        return _foo

    def _close_page(self, bnch):
        num_children = bnch.nb.count()
        if num_children == 0:
            del self.notebooks[bnch.name]
            root = bnch.root
            bnch.root = None
            #root.destroy()
            root.deleteLater()
        return True

    def close_page_cb(self, bnch, event):
        num_children = bnch.nb.count()
        if num_children == 0:
            del self.notebooks[bnch.name]
            #bnch.root.destroy()
            event.accept()
        else:
            event.ignore()
        return True

    def switch_page_cb(self, page_num, nbw):
        pagew = nbw.currentWidget()
        bnch = self._find_tab(pagew)
        if bnch is not None:
            self.make_callback('page-switch', bnch.name, bnch.data)
        return False

    def make_desktop(self, layout, widgetDict=None):
        if widgetDict is None:
            widgetDict = {}

        def process_common_params(widget, inparams):
            params = Bunch.Bunch(name=None, height=-1, width=-1, xpos=-1, ypos=-1)
            params.update(inparams)

            if params.name:
                widgetDict[params.name] = widget

            # User is specifying the size of the widget
            if ((params.width >= 0) or (params.height >= 0)) and \
                   isinstance(widget, QtGui.QWidget):
                if params.width < 0:
                    width = widget.width()
                else:
                    width = params.width
                if params.height < 0:
                    height = widget.height()
                else:
                    height = params.height
                widget.resize(width, height)

            # User wants to place window somewhere
            if (params.xpos >= 0) and isinstance(widget, QtGui.QWidget):
                widget.move(params.xpos, params.ypos)

        def make_widget(kind, paramdict, args, pack):
            kind = kind.lower()

            # Process workspace parameters
            params = Bunch.Bunch(name=None, title=None, height=-1,
                                 width=-1, group=1, show_tabs=True,
                                 show_border=False, scrollable=True,
                                 detachable=True, wstype='nb',
                                 tabpos=QtGui.QTabWidget.North)
            params.update(paramdict)

            if kind == 'widget':
                widget = args[0]

            elif kind == 'ws':
                group = int(params.group)
                widget = self.make_ws(name=params.name, group=group,
                                      show_tabs=params.show_tabs,
                                      show_border=params.show_border,
                                      detachable=params.detachable,
                                      tabpos=params.tabpos,
                                      wstype=params.wstype,
                                      scrollable=params.scrollable).nb
                #debug(widget)

            # If a title was passed as a parameter, then make a frame to
            # wrap the widget using the title.
            if params.title:
                fr = Frame(params.title)
                fr.layout().addWidget(widget, stretch=1)
                pack(fr)
            else:
                pack(widget)

            process_common_params(widget, params)

            if (kind in ('ws', 'mdi', 'grid')) and (len(args) > 0):
                # <-- Notebook ws specified a sub-layout.  We expect a list
                # of tabname, layout pairs--iterate over these and add them
                # to the workspace as tabs.
                for tabname, layout in args[0]:
                    def pack(w):
                        # ?why should group be the same as parent group?
                        self.add_tab(params.name, w, group,
                                     tabname, tabname.lower())

                    make(layout, pack)

            #return widget

        # Horizontal adjustable panel
        def horz(params, cols, pack):
            if len(cols) >= 2:
                hpaned = QtGui.QSplitter()
                hpaned.setOrientation(QtCore.Qt.Horizontal)

                for col in cols:
                    make(col, lambda w: hpaned.addWidget(w))
                widget = hpaned

            elif len(cols) == 1:
                widget = QtGui.QWidget()
                layout = QtGui.QHBoxLayout()
                layout.setContentsMargins(0, 0, 0, 0)
                make(cols[0], lambda w: layout.addWidget(w, stretch=1))
                widget.setLayout(layout)
                #widget.show()

            process_common_params(widget, params)
            pack(widget)

        # Vertical adjustable panel
        def vert(params, rows, pack):
            if len(rows) >= 2:
                vpaned = QtGui.QSplitter()
                vpaned.setOrientation(QtCore.Qt.Vertical)

                for row in rows:
                    make(row, lambda w: vpaned.addWidget(w))
                widget = vpaned

            elif len(rows) == 1:
                widget = QtGui.QWidget()
                layout = QtGui.QVBoxLayout()
                layout.setContentsMargins(0, 0, 0, 0)
                make(rows[0], lambda w: layout.addWidget(w, stretch=1))
                widget.setLayout(layout)
                #widget.show()

            process_common_params(widget, params)
            pack(widget)

        # Horizontal fixed array
        def hbox(params, cols, pack):
            widget = QtGui.QWidget()
            layout = QtGui.QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            widget.setLayout(layout)

            for dct in cols:
                if isinstance(dct, dict):
                    stretch = dct.get('stretch', 0)
                    col = dct.get('col', None)
                else:
                    # assume a list defining the col
                    stretch = align = 0
                    col = dct
                if col is not None:
                    make(col, lambda w: layout.addWidget(w,
                                                         stretch=stretch))
            process_common_params(widget, params)

            pack(widget)

        # Vertical fixed array
        def vbox(params, rows, pack):
            widget = QtGui.QWidget()
            layout = QtGui.QVBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            widget.setLayout(layout)

            for dct in rows:
                if isinstance(dct, dict):
                    stretch = dct.get('stretch', 0)
                    row = dct.get('row', None)
                else:
                    # assume a list defining the row
                    stretch = align = 0
                    row = dct
                if row is not None:
                    make(row, lambda w: layout.addWidget(w,
                                                         stretch=stretch))
            process_common_params(widget, params)

            pack(widget)

        # Sequence of separate items
        def seq(params, cols, pack):
            def mypack(w):
                self.toplevels.append(w)
                def closeEvent(*args):
                    #self.logger.debug("window %s closed" % str(w))
                    self.toplevels.remove(w)
                    w.deleteLater()
                    if len(self.toplevels) == 0:
                        self.make_callback('all-closed')

                w.closeEvent = closeEvent
                w.showNormal()

            for dct in cols:
                if isinstance(dct, dict):
                    stretch = dct.get('stretch', 0)
                    col = dct.get('col', None)
                else:
                    # assume a list defining the col
                    stretch = align = 0
                    col = dct
                if col is not None:
                    make(col, mypack)

            widget = QtGui.QLabel("Placeholder")
            pack(widget)

        def make(constituents, pack):
            kind = constituents[0]
            params = constituents[1]
            if len(constituents) > 2:
                rest = constituents[2:]
            else:
                rest = []

            if kind == 'vpanel':
                vert(params, rest, pack)
            elif kind == 'hpanel':
                horz(params, rest, pack)
            elif kind == 'vbox':
                vbox(params, rest, pack)
            elif kind == 'hbox':
                hbox(params, rest, pack)
            elif kind == 'seq':
                seq(params, rest, pack)
            elif kind in ('ws', 'mdi', 'widget'):
                make_widget(kind, params, rest, pack)

        make(layout, lambda w: None)

def _name_mangle(name, pfx=''):
    newname = []
    for c in name.lower():
        if not (c.isalpha() or c.isdigit() or (c == '_')):
            newname.append('_')
        else:
            newname.append(c)
    return pfx + ''.join(newname)

def _make_widget(tup, ns):
    swap = False
    title = tup[0]
    if not title.startswith('@'):
        name  = _name_mangle(title)
        w1 = QtGui.QLabel(title + ':')
        w1.setAlignment(QtCore.Qt.AlignRight)
    else:
        # invisible title
        swap = True
        name  = _name_mangle(title[1:])
        w1 = QtGui.QLabel('')

    wtype = tup[1]
    if wtype == 'label':
        w2 = QtGui.QLabel('')
        w2.setAlignment(QtCore.Qt.AlignLeft)
    elif wtype == 'xlabel':
        w2 = QtGui.QLabel('')
        w2.setAlignment(QtCore.Qt.AlignLeft)
        name = 'xlbl_' + name
    elif wtype == 'entry':
        w2 = QtGui.QLineEdit()
        w2.setMaxLength(12)
    elif wtype == 'combobox':
        w2 = ComboBox()
    elif wtype == 'spinbutton':
        w2 = QtGui.QSpinBox()
    elif wtype == 'spinfloat':
        w2 = QtGui.QDoubleSpinBox()
    elif wtype == 'vbox':
        w2 = VBox()
    elif wtype == 'hbox':
        w2 = HBox()
    elif wtype == 'hscale':
        w2 = QtGui.QSlider(QtCore.Qt.Horizontal)
    elif wtype == 'vscale':
        w2 = QtGui.QSlider(QtCore.Qt.Vertical)
    elif wtype == 'checkbutton':
        w1 = QtGui.QLabel('')
        w2 = QtGui.QCheckBox(title)
        swap = True
    elif wtype == 'radiobutton':
        w1 = QtGui.QLabel('')
        w2 = QtGui.QRadioButton(title)
        swap = True
    elif wtype == 'togglebutton':
        w1 = QtGui.QLabel('')
        w2 = QtGui.QPushButton(title)
        w2.setCheckable(True)
        swap = True
    elif wtype == 'button':
        w1 = QtGui.QLabel('')
        w2 = QtGui.QPushButton(title)
        swap = True
    elif wtype == 'spacer':
        w1 = QtGui.QLabel('')
        w2 = QtGui.QLabel('')
    else:
        raise ValueError("Bad wtype=%s" % wtype)

    lblname = 'lbl_%s' % (name)
    if swap:
        w1, w2 = w2, w1
        ns[name] = w1
        ns[lblname] = w2
    else:
        ns[name] = w2
        ns[lblname] = w1
    return (w1, w2)

def build_info(captions):
    numrows = len(captions)
    numcols = reduce(lambda acc, tup: max(acc, len(tup)), captions, 0)

    widget = QtGui.QWidget()
    table = QtGui.QGridLayout()
    widget.setLayout(table)
    table.setVerticalSpacing(2)
    table.setHorizontalSpacing(4)
    table.setContentsMargins(2, 2, 2, 2)

    wb = Bunch.Bunch()
    row = 0
    for tup in captions:
        col = 0
        while col < numcols:
            if col < len(tup):
                tup1 = tup[col:col+2]
                w1, w2 = _make_widget(tup1, wb)
                table.addWidget(w1, row, col)
                table.addWidget(w2, row, col+1)
            col += 2
        row += 1

    return widget, wb

def debug(widget):
    foo = dir(widget)
    print("---- %s ----" % str(widget))
    for x in foo:
        if x.startswith('set'):
            print(x)

def children(layout):
    i = 0
    res = []
    child = layout.itemAt(i)
    while child is not None:
        res.append(child.widget())
        i += 1
        child = layout.itemAt(i)
    return res

def removeWidget(layout, widget):
    kids = children(layout)
    if widget in kids:
        idx = kids.index(widget)
        w = kids[idx]
        #layout.removeWidget(widget)
        #layout.removeItem(w)
        widget.setParent(None)
        widget.deleteLater()
        #widget.delete()
    else:
        #print "widget is not present"
        pass

def cmap2pixmap(cmap, steps=50):
    """Convert a Ginga colormap into a QPixmap
    """
    inds = numpy.linspace(0, 1, steps)
    n = len(cmap.clst) - 1
    tups = [ cmap.clst[int(x*n)] for x in inds ]
    rgbas = [QColor(int(r * 255), int(g * 255),
                    int(b * 255), 255).rgba() for r, g, b in tups]
    im = QImage(steps, 1, QImage.Format_Indexed8)
    im.setColorTable(rgbas)
    for i in range(steps):
        im.setPixel(i, 0, i)
    im = im.scaled(128, 32)
    pm = QPixmap.fromImage(im)
    return pm

def get_scroll_info(event):
    """
    Returns the (degrees, direction) of a scroll motion Qt event.
    """

    # 15 deg is standard 1-click turn for a wheel mouse
    # delta() usually returns 120
    if have_pyqt5:
        # TODO: use pixelDelta() for better handling on hi-res devices
        point = event.angleDelta()
        delta = math.sqrt(point.x() ** 2 + point.y() ** 2)
        if point.y() < 0:
            delta = -delta
        orientation = QtCore.Qt.Vertical
    else:
        delta = event.delta()
        orientation = event.orientation()
    numDegrees = abs(delta) / 8.0

    direction = None
    if orientation == QtCore.Qt.Horizontal:
        if delta > 0:
            direction = 270.0
        elif delta < 0:
            direction = 90.0
    else:
        if delta > 0:
            direction = 0.0
        elif delta < 0:
            direction = 180.0

    return (numDegrees, direction)

def get_icon(iconpath, size=None):
    image = QImage(iconpath)
    if size is not None:
        qsize = QtCore.QSize(*size)
        image = image.scaled(qsize)
    pixmap = QPixmap.fromImage(image)
    iconw = QIcon(pixmap)
    return iconw


#END
